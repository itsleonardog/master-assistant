"""Orchestration of loudness, spectral, and stereo comparisons.

The module composes the three independent analysis layers into a single
``ComparisonReport`` for one user track against one reference master. It adds no
new signal processing: it only calls ``analyze_loudness``, ``compare_spectra``,
and ``compare_stereo`` and derives the loudness deltas and report warnings.
"""

from __future__ import annotations

from pathlib import Path

from master_assistant.analysis.loudness import analyze_loudness
from master_assistant.analysis.spectrum import compare_spectra
from master_assistant.analysis.stereo import compare_stereo
from master_assistant.models.schemas import (
    ComparisonReport,
    LoudnessDelta,
    LoudnessMetrics,
)

_DURATION_RATIO_THRESHOLD = 2.0


def analyze_pair(user_path: Path, reference_path: Path) -> ComparisonReport:
    """Analyze a user track against a reference master in one pass.

    The user file is analyzed before the reference so that a missing or
    unreadable user file fails before time is spent on the reference.

    Spectral deltas are **absolute** ``user - reference`` values in dB; they are
    not normalized for loudness. A quieter user track therefore shows a positive
    delta in every band. The Step 5 rule engine can subtract
    ``loudness_delta.integrated_lufs_delta`` from each band delta to obtain the
    tonal deltas. Stereo ``correlation_delta`` values range over ``[-2, +2]``,
    not ``[-1, +1]``, because they are differences of two values that each lie in
    ``[-1, +1]``.

    Args:
        user_path: Path to the user's unmastered track.
        reference_path: Path to the reference master.

    Returns:
        ComparisonReport with both loudness measurements, the loudness deltas,
        the spectral comparison, the stereo comparison (``None`` when either
        file is mono), and non-fatal warnings.

    Raises:
        AudioReadError: If either file cannot be opened or decoded. The error is
            propagated rather than converted into a partial report.
    """
    # TODO: This reads each file three times (once for loudness, once for
    # spectrum, once for stereo). If performance becomes a problem, refactor the
    # three analyze_* functions to accept ``(data, sample_rate)`` instead of a
    # path so the file is decoded once.
    user_loudness = analyze_loudness(user_path)
    reference_loudness = analyze_loudness(reference_path)
    loudness_delta = _delta_loudness(user_loudness, reference_loudness)
    spectrum = compare_spectra(user_path, reference_path)

    warnings: list[str] = []
    try:
        stereo = compare_stereo(user_path, reference_path)
    except ValueError as exc:
        # Mono input is the only documented ValueError of compare_stereo; it is
        # not an analysis failure, so the report is still useful without stereo.
        stereo = None
        warnings.append(f"Stereo comparison skipped: {exc}")

    duration_warning = _duration_warning(
        user_loudness.duration_s,
        reference_loudness.duration_s,
        ratio_threshold=_DURATION_RATIO_THRESHOLD,
    )
    if duration_warning is not None:
        warnings.append(duration_warning)

    return ComparisonReport(
        user_loudness=user_loudness,
        reference_loudness=reference_loudness,
        loudness_delta=loudness_delta,
        spectrum=spectrum,
        stereo=stereo,
        warnings=warnings,
    )


def _delta_loudness(user: LoudnessMetrics, reference: LoudnessMetrics) -> LoudnessDelta:
    """Compute ``user - reference`` for every loudness metric.

    Args:
        user: Loudness metrics of the user's track.
        reference: Loudness metrics of the reference master.

    Returns:
        LoudnessDelta with one difference per metric. ``duration_s`` is excluded
        because the two files may have different durations.
    """
    return LoudnessDelta(
        integrated_lufs_delta=user.integrated_lufs - reference.integrated_lufs,
        short_term_max_lufs_delta=user.short_term_max_lufs - reference.short_term_max_lufs,
        momentary_max_lufs_delta=user.momentary_max_lufs - reference.momentary_max_lufs,
        loudness_range_lu_delta=user.loudness_range_lu - reference.loudness_range_lu,
        true_peak_dbtp_delta=user.true_peak_dbtp - reference.true_peak_dbtp,
        sample_peak_dbfs_delta=user.sample_peak_dbfs - reference.sample_peak_dbfs,
        crest_factor_db_delta=user.crest_factor_db - reference.crest_factor_db,
    )


def _duration_warning(
    user_dur: float,
    ref_dur: float,
    ratio_threshold: float = 2.0,
) -> str | None:
    """Warn when the two files differ substantially in length.

    Spectral and stereo metrics are averaged over each file's full duration, so
    a large length mismatch can skew the comparison.

    Args:
        user_dur: User track duration in seconds.
        ref_dur: Reference master duration in seconds.
        ratio_threshold: Maximum tolerated ratio between the longer and the
            shorter duration before a warning is produced.

    Returns:
        The warning message, or ``None`` when the durations are compatible or
        one of them is not positive.
    """
    shorter = min(user_dur, ref_dur)
    longer = max(user_dur, ref_dur)
    if shorter <= 0.0:
        return None

    ratio = longer / shorter
    if ratio <= ratio_threshold:
        return None

    return (
        f"File durations differ significantly: "
        f"user={user_dur:.1f}s, reference={ref_dur:.1f}s. "
        "Spectral comparison is time-averaged and may be skewed."
    )
