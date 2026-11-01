"""Tests for the rule engine that converts comparison reports into suggestions.

Reports are built by hand instead of running the audio analysis stack: the rule
engine only consumes measurement objects, so synthetic reports keep the suite
fast and deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from master_assistant.models.schemas import (
    BandDelta,
    ComparisonReport,
    LoudnessDelta,
    LoudnessMetrics,
    SpectralComparison,
    StereoBandDelta,
    StereoComparison,
)
from master_assistant.suggestions import rule_engine
from master_assistant.suggestions.rule_engine import generate_suggestions

_NEUTRAL_INTEGRATED_LUFS = -14.0
_NEUTRAL_TP_DBTP = -3.0
_NEUTRAL_LRA_LU = 6.0

# Frequencies used by the synthetic stereo report; 20-120 Hz are the bass bands.
_STEREO_BANDS_HZ = (20.0, 63.0, 120.0, 250.0, 1000.0, 4000.0)


def _loudness(
    *,
    integrated_lufs: float = _NEUTRAL_INTEGRATED_LUFS,
    true_peak_dbtp: float = _NEUTRAL_TP_DBTP,
    loudness_range_lu: float = _NEUTRAL_LRA_LU,
) -> LoudnessMetrics:
    """Build loudness metrics, overriding only the fields a test cares about."""
    return LoudnessMetrics(
        integrated_lufs=integrated_lufs,
        short_term_max_lufs=integrated_lufs + 1.0,
        momentary_max_lufs=integrated_lufs + 2.0,
        loudness_range_lu=loudness_range_lu,
        true_peak_dbtp=true_peak_dbtp,
        sample_peak_dbfs=true_peak_dbtp - 0.1,
        crest_factor_db=12.0,
        duration_s=180.0,
    )


def _make_report(
    *,
    integrated_lufs_delta: float = 0.0,
    user_true_peak_dbtp: float = _NEUTRAL_TP_DBTP,
    user_lra_lu: float = _NEUTRAL_LRA_LU,
    bands: Sequence[tuple[float, float]] = (),
    stereo_bass_correlation: float | None = 1.0,
) -> ComparisonReport:
    """Build a neutral ``ComparisonReport`` with only the requested deviations.

    Args:
        integrated_lufs_delta: ``user - reference`` integrated loudness in LUFS.
        user_true_peak_dbtp: User true peak in dBTP.
        user_lra_lu: User loudness range in LU.
        bands: ``(freq_hz, delta_db)`` pairs for the spectral comparison. Deltas
            are absolute, exactly like the real analysis layer produces them.
        stereo_bass_correlation: Correlation assigned to stereo bands at or below
            120 Hz. ``None`` makes ``report.stereo`` ``None``, simulating mono.

    Returns:
        A report whose untouched fields hold neutral values that trigger no rule.
    """
    band_deltas = [
        BandDelta(
            name=f"{freq_hz:.0f}Hz",
            freq_hz=freq_hz,
            user_db=delta_db,
            reference_db=0.0,
            delta_db=delta_db,
            severity="ok",
        )
        for freq_hz, delta_db in bands
    ]
    spectrum = SpectralComparison(
        bands=band_deltas,
        tilt_delta_db_per_octave=0.0,
        top_problems=[],
    )

    stereo: StereoComparison | None = None
    if stereo_bass_correlation is not None:
        stereo = StereoComparison(
            bands=[
                StereoBandDelta(
                    name=f"{freq_hz:.0f}Hz",
                    freq_hz=freq_hz,
                    user_correlation=(
                        stereo_bass_correlation if freq_hz <= rule_engine.BASS_MAX_HZ else 1.0
                    ),
                    reference_correlation=1.0,
                    correlation_delta=0.0,
                    user_side_to_mid_db=0.0,
                    reference_side_to_mid_db=0.0,
                    side_to_mid_delta_db=0.0,
                    severity="ok",
                )
                for freq_hz in _STEREO_BANDS_HZ
            ],
            overall_correlation_delta=0.0,
            overall_side_to_mid_delta_db=0.0,
            width_hz_delta=0.0,
            top_problems=[],
        )

    return ComparisonReport(
        user_loudness=_loudness(
            true_peak_dbtp=user_true_peak_dbtp,
            loudness_range_lu=user_lra_lu,
        ),
        reference_loudness=_loudness(),
        loudness_delta=LoudnessDelta(
            integrated_lufs_delta=integrated_lufs_delta,
            short_term_max_lufs_delta=0.0,
            momentary_max_lufs_delta=0.0,
            loudness_range_lu_delta=0.0,
            true_peak_dbtp_delta=0.0,
            sample_peak_dbfs_delta=0.0,
            crest_factor_db_delta=0.0,
        ),
        spectrum=spectrum,
        stereo=stereo,
        warnings=[],
    )


def _crowded_report() -> ComparisonReport:
    """Build a report where all six rules fire with an ``eq`` major on each side.

    Returns:
        A report with loudness, true peak, low-mid, harshness, bass and LRA all
        outside their thresholds.
    """
    return _make_report(
        integrated_lufs_delta=2.0,
        user_true_peak_dbtp=1.0,
        user_lra_lu=1.5,
        bands=[(315.0, 7.0), (3150.0, 7.0)],
        stereo_bass_correlation=0.3,
    )


def test_perfect_report_returns_no_suggestions() -> None:
    """A report with neutral measurements must return an empty list."""
    assert generate_suggestions(_make_report()) == []


def test_loudness_mismatch_quiet_user_suggests_gain_boost() -> None:
    """A user 3.2 LUFS quieter must get a priority-2 gain boost of +3.2 dB."""
    suggestions = generate_suggestions(_make_report(integrated_lufs_delta=-3.2))

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.id == "loudness_mismatch"
    assert suggestion.priority == 2
    assert suggestion.severity == "major"
    assert suggestion.category == "loudness"
    assert suggestion.action_type == "gain"
    assert suggestion.action_params["gain_db"] == pytest.approx(3.2)
    assert suggestion.measured["integrated_lufs_delta"] == pytest.approx(-3.2)
    assert suggestion.target["integrated_lufs_delta"] == 0.0
    assert "3.2" in suggestion.title
    assert "Alza" in suggestion.title


def test_true_peak_too_high_is_critical_and_first() -> None:
    """A true peak of +0.5 dBTP must yield a critical, priority-1 limiter."""
    suggestions = generate_suggestions(_make_report(user_true_peak_dbtp=0.5))

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.id == "true_peak_too_high"
    assert suggestion.priority == 1
    assert suggestion.severity == "critical"
    assert suggestion.category == "peak"
    assert suggestion.action_type == "limiter"
    assert suggestion.action_params["ceiling_dbtp"] == pytest.approx(-1.0)
    assert suggestion.action_params["reduction_needed_db"] == pytest.approx(1.5)
    assert suggestion.measured["true_peak_dbtp"] == pytest.approx(0.5)
    assert suggestion.target["true_peak_dbtp"] == pytest.approx(-1.0)


def test_low_mid_mud_cuts_only_the_excess() -> None:
    """A +3 dB low-mid band must suggest a -2 dB cut at that band."""
    suggestions = generate_suggestions(_make_report(bands=[(315.0, 3.0)]))

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.id == "low_mid_mud"
    assert suggestion.priority == 3
    assert suggestion.severity == "minor"
    assert suggestion.category == "eq"
    assert suggestion.action_type == "eq_cut"
    assert suggestion.action_params["freq_hz"] == pytest.approx(315.0)
    assert suggestion.action_params["gain_db"] == pytest.approx(-2.0)
    assert suggestion.action_params["q"] == pytest.approx(1.2)
    assert suggestion.measured["normalized_delta_db"] == pytest.approx(3.0)


def test_spectral_rules_are_normalized_by_loudness() -> None:
    """A band that only looks loud because the user is quieter must not fire."""
    # Absolute +3.0 dB, but the user is +2.5 LUFS louder: the true tonal excess
    # is only +0.5 dB, well under the 2.0 dB low-mid threshold.
    report = _make_report(integrated_lufs_delta=2.5, bands=[(315.0, 3.0)])

    suggestions = generate_suggestions(report)

    ids = [suggestion.id for suggestion in suggestions]
    assert "low_mid_mud" not in ids
    assert ids == ["loudness_mismatch"]
    assert suggestions[0].action_params["gain_db"] == pytest.approx(-2.5)


def test_harshness_cuts_only_above_the_kept_margin() -> None:
    """A +4 dB band at 3.15 kHz must suggest a -2.5 dB cut at 3150 Hz."""
    suggestions = generate_suggestions(_make_report(bands=[(3150.0, 4.0)]))

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.id == "harshness"
    assert suggestion.priority == 3
    assert suggestion.severity == "minor"
    assert suggestion.action_type == "eq_cut"
    assert suggestion.action_params["freq_hz"] == pytest.approx(3150.0)
    assert suggestion.action_params["gain_db"] == pytest.approx(-2.5)
    assert suggestion.action_params["q"] == pytest.approx(1.0)


def test_bass_not_mono_suggests_stereo_narrowing() -> None:
    """Low bass correlation must yield a priority-4 stereo narrowing."""
    suggestions = generate_suggestions(_make_report(stereo_bass_correlation=0.4))

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.id == "bass_not_mono"
    assert suggestion.priority == 4
    assert suggestion.severity == "major"
    assert suggestion.category == "stereo"
    assert suggestion.action_type == "stereo_narrow"
    assert suggestion.action_params["below_hz"] == pytest.approx(120.0)
    assert suggestion.measured["mean_correlation"] == pytest.approx(0.4)


def test_bass_rule_ignores_silent_bands() -> None:
    """Digitally silent bass bands must not mask a genuinely wide bass.

    A ``side_to_mid_db`` of -120 dB means the side channel carries no energy, so
    the analysis layer reports a meaningless correlation of 1.0. Averaging those
    bands in would hide a wide bass whose real mean correlation is 0.2.
    """
    wide_bass_hz = (30.0, 40.0, 50.0)
    silent_bass_hz = (60.0, 70.0, 80.0, 90.0, 100.0)

    silent_bands = [
        StereoBandDelta(
            name=f"{freq_hz:.0f}Hz",
            freq_hz=freq_hz,
            user_correlation=1.0,
            reference_correlation=1.0,
            correlation_delta=0.0,
            user_side_to_mid_db=-120.0,
            reference_side_to_mid_db=0.0,
            side_to_mid_delta_db=-120.0,
            severity="ok",
        )
        for freq_hz in silent_bass_hz
    ]
    wide_bands = [
        StereoBandDelta(
            name=f"{freq_hz:.0f}Hz",
            freq_hz=freq_hz,
            user_correlation=0.2,
            reference_correlation=1.0,
            correlation_delta=-0.8,
            user_side_to_mid_db=-10.0,
            reference_side_to_mid_db=0.0,
            side_to_mid_delta_db=-10.0,
            severity="major",
        )
        for freq_hz in wide_bass_hz
    ]
    report = _make_report().model_copy(
        update={
            "stereo": StereoComparison(
                bands=silent_bands + wide_bands,
                overall_correlation_delta=0.0,
                overall_side_to_mid_delta_db=0.0,
                width_hz_delta=0.0,
                top_problems=[],
            )
        }
    )

    # Documentation of the bug this guards against: averaging every bass band,
    # silent ones included, would give (5 * 1.0 + 3 * 0.2) / 8 = 0.7, which sits
    # exactly on the 0.7 threshold and therefore produces no advice at all.
    unfiltered_mean = (len(silent_bass_hz) * 1.0 + len(wide_bass_hz) * 0.2) / (
        len(silent_bass_hz) + len(wide_bass_hz)
    )
    assert unfiltered_mean == pytest.approx(0.7)

    suggestions = generate_suggestions(report)

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.id == "bass_not_mono"
    assert suggestion.measured["mean_correlation"] == pytest.approx(0.2)


def test_over_compressed_is_last() -> None:
    """An LRA of 2.0 LU must yield a priority-5 dynamics suggestion."""
    suggestions = generate_suggestions(_make_report(user_lra_lu=2.0))

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.id == "over_compressed"
    assert suggestion.priority == 5
    assert suggestion.severity == "minor"
    assert suggestion.category == "dynamics"
    assert suggestion.action_type == "compressor"
    assert suggestion.action_params["target_lra_lu"] == pytest.approx(4.0)
    assert suggestion.measured["loudness_range_lu"] == pytest.approx(2.0)


def test_multiple_suggestions_are_sorted_by_priority() -> None:
    """Four independent problems must come back ordered [1, 2, 3, 5]."""
    report = _make_report(
        integrated_lufs_delta=-3.0,
        user_true_peak_dbtp=0.5,
        user_lra_lu=2.0,
        bands=[(315.0, 3.0)],
    )

    suggestions = generate_suggestions(report)

    assert [suggestion.id for suggestion in suggestions] == [
        "true_peak_too_high",
        "loudness_mismatch",
        "low_mid_mud",
        "over_compressed",
    ]
    assert [suggestion.priority for suggestion in suggestions] == [1, 2, 3, 5]


def test_same_priority_orders_major_before_minor() -> None:
    """Two priority-3 EQ cuts must be ordered by descending severity."""
    # Low-mid +3.0 dB is minor; harshness +5.0 dB crosses the 4.0 dB major mark.
    report = _make_report(bands=[(315.0, 3.0), (3150.0, 5.0)])

    suggestions = generate_suggestions(report)

    assert [suggestion.priority for suggestion in suggestions] == [3, 3]
    assert [suggestion.id for suggestion in suggestions] == ["harshness", "low_mid_mud"]
    assert [suggestion.severity for suggestion in suggestions] == ["major", "minor"]


def test_all_rules_fire_without_exceeding_the_cap() -> None:
    """Six firing rules must produce exactly MAX_SUGGESTIONS suggestions."""
    suggestions = generate_suggestions(_crowded_report())

    assert len(suggestions) == rule_engine.MAX_SUGGESTIONS
    assert [suggestion.priority for suggestion in suggestions] == sorted(
        suggestion.priority for suggestion in suggestions
    )
    assert {suggestion.id for suggestion in suggestions} == {
        "true_peak_too_high",
        "loudness_mismatch",
        "low_mid_mud",
        "harshness",
        "bass_not_mono",
        "over_compressed",
    }


def test_truncation_keeps_the_highest_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lowering the cap must drop the tail of the priority-sorted list."""
    # Six rules exist, so the cap is lowered to make truncation observable.
    monkeypatch.setattr(rule_engine, "MAX_SUGGESTIONS", 3)

    suggestions = generate_suggestions(_crowded_report())

    assert len(suggestions) == 3
    assert [suggestion.priority for suggestion in suggestions] == [1, 2, 3]
    assert [suggestion.id for suggestion in suggestions[:2]] == [
        "true_peak_too_high",
        "loudness_mismatch",
    ]


def test_mono_report_never_triggers_bass_rule() -> None:
    """A report without stereo data must skip the bass rule without crashing."""
    report = _make_report(
        integrated_lufs_delta=-3.0,
        user_true_peak_dbtp=0.5,
        user_lra_lu=2.0,
        stereo_bass_correlation=None,
    )
    assert report.stereo is None

    suggestions = generate_suggestions(report)

    assert suggestions
    assert all(suggestion.id != "bass_not_mono" for suggestion in suggestions)
    assert [suggestion.priority for suggestion in suggestions] == [1, 2, 5]
