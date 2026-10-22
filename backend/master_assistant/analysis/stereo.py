"""Stereo analysis: width, correlation, and mid/side balance.

The module reduces a stereo file to mid/side signals, estimates a Welch PSD for
each, aggregates the two PSDs into the same ISO third-octave bands used by
``spectrum.py``, and derives per-band and overall correlation and side-to-mid
ratios. It only uses ``numpy``, ``scipy``, and ``soundfile``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import soundfile

from master_assistant.analysis._bands import (
    BAND_CENTERS_HZ,
    SILENCE_DB,
    band_mask,
    band_name,
    welch_psd,
)
from master_assistant.analysis.errors import AudioReadError
from master_assistant.models.schemas import (
    StereoBandDelta,
    StereoBandMetrics,
    StereoComparison,
    StereoMetrics,
)

# Side-to-mid ratio (in dB) below which a band is considered effectively mono.
# -20 dB means the side carries under 1% of the mid energy, which is where a
# widening plugin or a listener stops perceiving any width. This is a heuristic
# threshold, not a standard.
_MONO_SIDE_TO_MID_DB = -20.0
# Reported width when every band is effectively mono.
_FULL_BANDWIDTH_HZ = 20_000.0
# Correlation deltas are unitless in [-2, 2]; they need tighter thresholds than
# the dB-based spectral severity scale.
_MINOR_CORRELATION = 0.1
_MAJOR_CORRELATION = 0.25
_TOP_PROBLEM_COUNT = 3
# Floor applied to the side energy so the ratio stays finite when the side
# channel is digitally silent.
_SIDE_FLOOR = 1e-30


def analyze_stereo(path: Path) -> StereoMetrics:
    """Measure stereo width, correlation, and mid/side balance.

    Mid/side convention: ``mid = (L + R) / 2`` and ``side = (L - R) / 2``.

    Correlation is reported as ``(M² - S²) / (M² + S²)`` on band-integrated
    Welch PSDs (mid and side estimated separately with identical parameters).
    That is the goniometer definition used by commercial analyzers, not the
    sample-wise Pearson coefficient: on narrow bands a Pearson estimate is
    dominated by phase noise and is unstable, while the energy ratio is robust.
    It reads 1.0 for fully mono content, 0.0 for uncorrelated content and -1.0
    for fully out-of-phase content. Silent bands report 1.0 and -120.0 dB.

    Files with more than two channels are reduced to the first two channels,
    taken to be the conventional L/R pair; centre and surround channels are
    ignored because mid/side is only defined for a stereo pair.

    Args:
        path: Path to the audio file to analyze.

    Returns:
        StereoMetrics with per-band correlation and side-to-mid ratio in dB,
        the same metrics overall, and the width in Hz below which the file is
        effectively mono.

    Raises:
        ValueError: If the file has fewer than two channels.
        AudioReadError: If the file cannot be opened or decoded.
    """
    data, sample_rate = _read_stereo(path)
    left = data[:, 0]
    right = data[:, 1]

    mid = 0.5 * (left + right)
    side = 0.5 * (left - right)

    freqs, psd_mid = welch_psd(mid, sample_rate)
    _, psd_side = welch_psd(side, sample_rate)

    bands: list[StereoBandMetrics] = []
    for center_hz in BAND_CENTERS_HZ:
        mask = band_mask(freqs, center_hz)
        mid_energy = float(np.sum(psd_mid[mask]))
        side_energy = float(np.sum(psd_side[mask]))
        bands.append(
            StereoBandMetrics(
                name=band_name(center_hz),
                freq_hz=center_hz,
                correlation=_correlation(mid_energy, side_energy),
                side_to_mid_db=_side_to_mid_db(mid_energy, side_energy),
            )
        )

    total_mid = float(np.sum(psd_mid))
    total_side = float(np.sum(psd_side))

    return StereoMetrics(
        bands=bands,
        overall_correlation=_correlation(total_mid, total_side),
        overall_side_to_mid_db=_side_to_mid_db(total_mid, total_side),
        width_hz=_width_hz(bands),
    )


def compare_stereo(user_path: Path, reference_path: Path) -> StereoComparison:
    """Compare the stereo image of a user track against a reference master.

    Both files are analyzed independently and aligned by band name. Deltas are
    ``user - reference``. Severity is driven by the correlation delta, the more
    meaningful descriptor of stereo image, using thresholds suited to its
    unitless 0-1 scale rather than the dB-based spectral thresholds.

    Args:
        user_path: Path to the user's unmastered track.
        reference_path: Path to the reference master.

    Returns:
        StereoComparison with per-band deltas, the overall correlation and
        side-to-mid deltas, the width delta, and the three largest non-``ok``
        deviations ordered by absolute correlation delta.

    Raises:
        ValueError: If either file has fewer than two channels.
        AudioReadError: If either file cannot be opened or decoded.
    """
    user = analyze_stereo(user_path)
    reference = analyze_stereo(reference_path)
    reference_by_name = {band.name: band for band in reference.bands}

    deltas: list[StereoBandDelta] = []
    for user_band in user.bands:
        reference_band = reference_by_name.get(user_band.name)
        if reference_band is None:
            # Band names come from the same fixed table, so this is defensive
            # only and should never trigger in practice.
            continue
        correlation_delta = user_band.correlation - reference_band.correlation
        side_to_mid_delta_db = user_band.side_to_mid_db - reference_band.side_to_mid_db
        deltas.append(
            StereoBandDelta(
                name=user_band.name,
                freq_hz=user_band.freq_hz,
                user_correlation=user_band.correlation,
                reference_correlation=reference_band.correlation,
                correlation_delta=correlation_delta,
                user_side_to_mid_db=user_band.side_to_mid_db,
                reference_side_to_mid_db=reference_band.side_to_mid_db,
                side_to_mid_delta_db=side_to_mid_delta_db,
                severity=_severity(correlation_delta),
            )
        )

    problems = sorted(
        (delta for delta in deltas if delta.severity != "ok"),
        key=lambda delta: (abs(delta.correlation_delta), abs(delta.side_to_mid_delta_db)),
        reverse=True,
    )

    return StereoComparison(
        bands=deltas,
        overall_correlation_delta=user.overall_correlation - reference.overall_correlation,
        overall_side_to_mid_delta_db=(
            user.overall_side_to_mid_db - reference.overall_side_to_mid_db
        ),
        width_hz_delta=user.width_hz - reference.width_hz,
        top_problems=problems[:_TOP_PROBLEM_COUNT],
    )


def _read_stereo(path: Path) -> tuple[np.ndarray, int]:
    """Read an audio file and keep at most the first two channels.

    Args:
        path: Path to the audio file.

    Returns:
        A tuple of a ``(samples, channels)`` float64 array with one or two
        columns and the sample rate in Hz.

    Raises:
        AudioReadError: If the file is missing, corrupt, empty, or has an
            invalid sample rate.
        ValueError: If the file has fewer than two channels.
    """
    try:
        data, sample_rate = soundfile.read(path, dtype="float64", always_2d=True)
    except Exception as exc:  # soundfile raises several unrelated exception types
        raise AudioReadError(f"Could not read audio file '{path}': {exc}") from exc

    if data.size == 0 or data.shape[0] == 0 or sample_rate <= 0:
        raise AudioReadError(f"Audio file '{path}' contains no decodable samples")

    if data.shape[1] < 2:
        raise ValueError(
            "Stereo analysis requires at least 2 channels; "
            f"got mono ({data.shape[1]} channel) in '{path}'"
        )

    return data[:, :2], int(sample_rate)


def _correlation(mid_energy: float, side_energy: float) -> float:
    """Compute the goniometer-style correlation from band energies.

    Args:
        mid_energy: Integrated mid power in the band (or over the spectrum).
        side_energy: Integrated side power in the band (or over the spectrum).

    Returns:
        ``(M² - S²) / (M² + S²)``, or ``1.0`` when both energies are zero.
    """
    total = mid_energy + side_energy
    if not np.isfinite(total) or total <= 0.0:
        return 1.0
    return float((mid_energy - side_energy) / total)


def _side_to_mid_db(mid_energy: float, side_energy: float) -> float:
    """Express the side energy relative to the mid energy in dB.

    Args:
        mid_energy: Integrated mid power in the band (or over the spectrum).
        side_energy: Integrated side power in the band (or over the spectrum).

    Returns:
        ``10 * log10(side / mid)`` with a floor on both energies, or ``-120.0``
        when both are zero.
    """
    mid = float(max(mid_energy, 0.0))
    side = float(max(side_energy, 0.0))
    if mid <= 0.0 and side <= 0.0:
        return SILENCE_DB

    mid = max(mid, _SIDE_FLOOR)
    side = max(side, _SIDE_FLOOR)
    return float(10.0 * np.log10(side / mid))


def _width_hz(bands: list[StereoBandMetrics]) -> float:
    """Find the highest frequency where the side signal is still negligible.

    Bands are scanned in ascending frequency order; the result is the highest
    center frequency such that every band up to and including it has
    ``side_to_mid_db < -20``. If no band qualifies the width is ``0.0``; if all
    qualify it is capped at 20 kHz.

    Args:
        bands: Per-band stereo metrics ordered by ascending frequency.

    Returns:
        The width limit in Hz.
    """
    width_hz = 0.0
    for band in bands:
        if band.side_to_mid_db >= _MONO_SIDE_TO_MID_DB:
            break
        width_hz = band.freq_hz
    if width_hz >= BAND_CENTERS_HZ[-1]:
        return _FULL_BANDWIDTH_HZ
    return width_hz


def _severity(correlation_delta: float) -> Literal["ok", "minor", "major"]:
    """Classify the magnitude of a correlation difference.

    Args:
        correlation_delta: Difference between user and reference correlation.

    Returns:
        ``"ok"`` below 0.1, ``"minor"`` below 0.25, otherwise ``"major"``.
    """
    magnitude = abs(correlation_delta)
    if magnitude < _MINOR_CORRELATION:
        return "ok"
    if magnitude < _MAJOR_CORRELATION:
        return "minor"
    return "major"
