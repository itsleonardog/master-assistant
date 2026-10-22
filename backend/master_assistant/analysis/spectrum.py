"""Spectral analysis: frequency balance, tonal profile, and reference comparison.

The module profiles an audio file with a Welch power spectral density (PSD),
aggregates it into ISO third-octave bands, derives tilt, centroid, rolloff, and
flatness descriptors, and compares those measurements against a reference
master. It only uses ``numpy``, ``scipy``, and ``soundfile``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import soundfile

# The Welch estimator, ISO band center table, band naming and band bin
# selection were extracted into the internal ``_bands`` module so that
# ``stereo.py`` can reuse them. Importing the underscore-prefixed helpers from
# this module instead would have coupled stereo analysis to another module's
# private API, so the shared module is the cleaner of the two options; public
# behavior here is unchanged.
from master_assistant.analysis._bands import (
    BAND_CENTERS_HZ,
    band_energy_db,
    band_name,
    welch_psd,
)
from master_assistant.analysis.errors import AudioReadError
from master_assistant.models.schemas import (
    BandDelta,
    SpectralBand,
    SpectralComparison,
    SpectralMetrics,
)

_FLATNESS_EPS = 1e-12
_TILT_MIN_HZ = 100.0
_TILT_MAX_HZ = 10_000.0
_ROLLOFF_FRACTION = 0.85
_MINOR_DB = 1.5
_MAJOR_DB = 3.0
_TOP_PROBLEM_COUNT = 3


def analyze_spectrum(path: Path) -> SpectralMetrics:
    """Profile the spectral balance of an audio file.

    The channels are averaged into a single mono signal before the Welch PSD is
    estimated. Downmix to mono discards stereo width information; side-channel
    content will be analyzed separately in stereo.py.

    Args:
        path: Path to the audio file to analyze.

    Returns:
        SpectralMetrics with third-octave band energies, spectral tilt in dB per
        octave, spectral centroid and 85% rolloff in Hz, and flatness.

    Raises:
        AudioReadError: If the file cannot be opened or decoded.
    """
    mono, sample_rate = _read_mono(path)
    freqs, psd = welch_psd(mono, sample_rate)

    bands = [
        SpectralBand(
            name=band_name(center_hz),
            freq_hz=center_hz,
            energy_db=band_energy_db(freqs, psd, center_hz),
        )
        for center_hz in BAND_CENTERS_HZ
    ]

    return SpectralMetrics(
        bands=bands,
        tilt_db_per_octave=_spectral_tilt(bands),
        spectral_centroid_hz=_spectral_centroid_hz(freqs, psd),
        rolloff_85_hz=_rolloff_hz(freqs, psd),
        flatness=_flatness(psd),
    )


def compare_spectra(user_path: Path, reference_path: Path) -> SpectralComparison:
    """Compare the spectral balance of a user track against a reference master.

    Both files are analyzed independently and aligned by band name. Differences
    are absolute (no level normalization), so a user track that is simply louder
    will show a positive delta in every band; callers are expected to correct
    for overall gain before interpreting tonal balance.

    Durations may differ: each file is analyzed over its own full length. This is
    the simplest choice and keeps the function free of extra parameters.

    Args:
        user_path: Path to the user's unmastered track.
        reference_path: Path to the reference master.

    Returns:
        SpectralComparison with per-band deltas, the tilt difference, and the
        three largest non-``ok`` deviations ordered by absolute magnitude.

    Raises:
        AudioReadError: If either file cannot be opened or decoded.
    """
    user = analyze_spectrum(user_path)
    reference = analyze_spectrum(reference_path)
    reference_by_name = {band.name: band for band in reference.bands}

    deltas: list[BandDelta] = []
    for user_band in user.bands:
        reference_band = reference_by_name.get(user_band.name)
        if reference_band is None:
            # Band names come from the same fixed table, so this is defensive
            # only and should never trigger in practice.
            continue
        delta_db = user_band.energy_db - reference_band.energy_db
        deltas.append(
            BandDelta(
                name=user_band.name,
                freq_hz=user_band.freq_hz,
                user_db=user_band.energy_db,
                reference_db=reference_band.energy_db,
                delta_db=delta_db,
                severity=_severity(delta_db),
            )
        )

    problems = sorted(
        (delta for delta in deltas if delta.severity != "ok"),
        key=lambda delta: abs(delta.delta_db),
        reverse=True,
    )

    return SpectralComparison(
        bands=deltas,
        tilt_delta_db_per_octave=user.tilt_db_per_octave - reference.tilt_db_per_octave,
        top_problems=problems[:_TOP_PROBLEM_COUNT],
    )


def _read_mono(path: Path) -> tuple[np.ndarray, int]:
    """Read an audio file and downmix it to a mono float64 signal.

    Args:
        path: Path to the audio file.

    Returns:
        A tuple of the one-dimensional mono signal and the sample rate in Hz.

    Raises:
        AudioReadError: If the file is missing, corrupt, empty, or has an
            invalid sample rate.
    """
    try:
        data, sample_rate = soundfile.read(path, dtype="float64", always_2d=True)
    except Exception as exc:  # soundfile raises several unrelated exception types
        raise AudioReadError(f"Could not read audio file '{path}': {exc}") from exc

    if data.size == 0 or data.shape[0] == 0 or sample_rate <= 0:
        raise AudioReadError(f"Audio file '{path}' contains no decodable samples")

    mono = np.mean(data, axis=1, dtype=np.float64)
    return mono, int(sample_rate)


def _spectral_tilt(bands: list[SpectralBand]) -> float:
    """Fit band energy against log2 frequency to estimate spectral tilt.

    Only bands between 100 Hz and 10 kHz are used, since those carry the tonal
    balance of a mix and are less affected by subsonic rumble and ultrasonic
    content. Natural music typically has a negative slope (more low-end energy).

    Args:
        bands: Measured third-octave bands.

    Returns:
        The slope of the linear regression in dB per octave, or ``0.0`` when
        fewer than two bands fall inside the fitted range.
    """
    selected = [band for band in bands if _TILT_MIN_HZ <= band.freq_hz <= _TILT_MAX_HZ]
    if len(selected) < 2:
        return 0.0

    log2_freqs = np.log2([band.freq_hz for band in selected])
    energies = np.array([band.energy_db for band in selected], dtype=np.float64)
    slope = np.polyfit(log2_freqs, energies, 1)[0]
    return float(slope)


def _spectral_centroid_hz(freqs: np.ndarray, psd: np.ndarray) -> float:
    """Compute the energy-weighted mean frequency.

    Args:
        freqs: Frequency bins in Hz.
        psd: Power spectral density aligned with ``freqs``.

    Returns:
        The spectral centroid in Hz, or ``0.0`` for a silent spectrum.
    """
    total = float(np.sum(psd))
    if total <= 0.0:
        return 0.0
    return float(np.sum(freqs * psd) / total)


def _rolloff_hz(freqs: np.ndarray, psd: np.ndarray) -> float:
    """Find the frequency below which 85% of the spectral energy lies.

    Args:
        freqs: Frequency bins in Hz.
        psd: Power spectral density aligned with ``freqs``.

    Returns:
        The 85% rolloff frequency in Hz, or ``0.0`` for a silent spectrum.
    """
    total = float(np.sum(psd))
    if total <= 0.0:
        return 0.0

    cumulative = np.cumsum(psd) / total
    index = int(np.searchsorted(cumulative, _ROLLOFF_FRACTION))
    return float(freqs[min(index, freqs.size - 1)])


def _flatness(psd: np.ndarray) -> float:
    """Measure how close the spectrum is to flat noise.

    Args:
        psd: Power spectral density.

    Returns:
        The ratio of geometric to arithmetic mean power, between 0 and 1. It
        approaches 1 for white noise and 0 for tonal content.
    """
    mean_power = float(np.mean(psd))
    if mean_power <= 0.0:
        return 0.0

    geometric_mean = float(np.exp(np.mean(np.log(psd + _FLATNESS_EPS))))
    return geometric_mean / mean_power


def _severity(delta_db: float) -> Literal["ok", "minor", "major"]:
    """Classify the magnitude of a band difference.

    Args:
        delta_db: Difference between user and reference band energy in dB.

    Returns:
        ``"ok"`` below 1.5 dB, ``"minor"`` below 3.0 dB, otherwise ``"major"``.
    """
    magnitude = abs(delta_db)
    if magnitude < _MINOR_DB:
        return "ok"
    if magnitude < _MAJOR_DB:
        return "minor"
    return "major"
