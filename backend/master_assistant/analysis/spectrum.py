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
from scipy.signal import welch

from master_assistant.analysis.errors import AudioReadError
from master_assistant.models.schemas import (
    BandDelta,
    SpectralBand,
    SpectralComparison,
    SpectralMetrics,
)

# Welch parameters. 8192 samples at 48 kHz gives ~5.9 Hz resolution, fine
# enough to resolve the lowest third-octave band while keeping enough segments
# for a stable estimate on a 5 s clip.
_NPERSEG = 8192
_OVERLAP_NUMERATOR = 3
_OVERLAP_DENOMINATOR = 4
# Floor used when a band has no measurable energy (silence or out-of-range).
_SILENCE_DB = -120.0
_FLATNESS_EPS = 1e-12
_TILT_MIN_HZ = 100.0
_TILT_MAX_HZ = 10_000.0
_ROLLOFF_FRACTION = 0.85
_MINOR_DB = 1.5
_MAJOR_DB = 3.0
_TOP_PROBLEM_COUNT = 3
_BAND_EDGE_RATIO = 2.0 ** (1.0 / 6.0)

# ISO 266 third-octave band centers in Hz.
_BAND_CENTERS_HZ: tuple[float, ...] = (
    20.0,
    25.0,
    31.5,
    40.0,
    50.0,
    63.0,
    80.0,
    100.0,
    125.0,
    160.0,
    200.0,
    250.0,
    315.0,
    400.0,
    500.0,
    630.0,
    800.0,
    1000.0,
    1250.0,
    1600.0,
    2000.0,
    2500.0,
    3150.0,
    4000.0,
    5000.0,
    6300.0,
    8000.0,
    10000.0,
    12500.0,
    16000.0,
    20000.0,
)


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
    freqs, psd = _welch_psd(mono, sample_rate)

    bands = [
        SpectralBand(
            name=_band_name(center_hz),
            freq_hz=center_hz,
            energy_db=_band_energy_db(freqs, psd, center_hz),
        )
        for center_hz in _BAND_CENTERS_HZ
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


def _welch_psd(mono: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    """Estimate the one-sided power spectral density with Welch's method.

    Args:
        mono: One-dimensional mono audio signal.
        sample_rate: Sample rate in Hz.

    Returns:
        A tuple of frequency bins in Hz and the PSD in units of power per Hz.
    """
    freqs, psd = welch(
        mono,
        fs=sample_rate,
        window="hann",
        nperseg=_NPERSEG,
        noverlap=_NPERSEG * _OVERLAP_NUMERATOR // _OVERLAP_DENOMINATOR,
        scaling="density",
        detrend=False,
        return_onesided=True,
    )
    return freqs, psd


def _band_name(center_hz: float) -> str:
    """Format a band center frequency as a stable, human-readable name.

    Args:
        center_hz: Band center frequency in Hz.

    Returns:
        A name such as ``"1kHz"`` for integer kilohertz or ``"31.5Hz"``.
    """
    if center_hz >= 1000.0 and center_hz % 1000.0 == 0.0:
        return f"{center_hz / 1000.0:g}kHz"
    return f"{center_hz:g}Hz"


def _band_energy_db(freqs: np.ndarray, psd: np.ndarray, center_hz: float) -> float:
    """Integrate the PSD over one third-octave band and convert it to dB.

    The band spans ``center / 2**(1/6)`` to ``center * 2**(1/6)``. Because the
    PSD is already a density, the mean of the bins inside the interval is used
    as the band energy. Bands entirely above the Nyquist frequency, bands with
    no bins, and silent bands return ``-120.0``.

    Args:
        freqs: Frequency bins in Hz.
        psd: Power spectral density aligned with ``freqs``.
        center_hz: Band center frequency in Hz.

    Returns:
        Mean band power in dB, or ``-120.0`` when the band is unmeasurable.
    """
    f_lo = center_hz / _BAND_EDGE_RATIO
    f_hi = center_hz * _BAND_EDGE_RATIO
    if f_lo >= freqs[-1]:
        return _SILENCE_DB

    mask = (freqs >= f_lo) & (freqs < f_hi)
    if not np.any(mask):
        return _SILENCE_DB

    mean_power = float(np.mean(psd[mask]))
    if not np.isfinite(mean_power) or mean_power <= 0.0:
        return _SILENCE_DB

    return float(10.0 * np.log10(mean_power))


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
