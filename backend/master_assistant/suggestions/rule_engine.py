"""Rule engine that converts analysis deltas into prioritized mastering suggestions.

Each rule is a pure function that takes a :class:`ComparisonReport` and returns
a :class:`Suggestion` or ``None``. Suggestions carry a DAW-agnostic
``action_type`` plus ``action_params`` so a DAW adapter can translate them into a
concrete instruction without the engine knowing about any specific DAW.

Spectral rules operate on **normalized** band deltas. ``BandDelta.delta_db`` is
absolute (``user - reference``), so a user track that is 3 LUFS quieter than the
reference shows ``+3 dB`` in every band without any tonal imbalance at all.
Subtracting ``LoudnessDelta.integrated_lufs_delta`` isolates the real tonal
difference.

``priority`` answers "in which order do I apply this?" while ``severity`` answers
"how bad is it?". They intentionally differ: a true peak of +0.5 dBTP is
``critical`` but only takes ten seconds of limiter, whereas a 2 LU loudness range
is ``major`` but requires reworking the mix.
"""

from __future__ import annotations

from typing import Literal

from master_assistant.models.schemas import (
    BandDelta,
    ComparisonReport,
    Suggestion,
)

MAX_SUGGESTIONS = 6
LOUDNESS_TOLERANCE_LU = 1.0
TRUE_PEAK_CEILING_DBTP = -1.0
LOW_MID_RANGE_HZ = (200.0, 500.0)
LOW_MID_THRESHOLD_DB = 2.0
HARSH_RANGE_HZ = (2000.0, 5000.0)
HARSH_THRESHOLD_DB = 2.5
BASS_MAX_HZ = 120.0
BASS_CORR_THRESHOLD = 0.7
LRA_MIN_LU = 3.0

# Higher rank wins the tie-break when two suggestions share a priority.
_SEVERITY_RANK: dict[str, int] = {"info": 1, "minor": 2, "major": 3, "critical": 4}


def generate_suggestions(report: ComparisonReport) -> list[Suggestion]:
    """Run every rule and return the prioritized, truncated suggestions.

    Args:
        report: Comparison report produced by
            :func:`master_assistant.analysis.comparison.analyze_pair`.

    Returns:
        Up to :data:`MAX_SUGGESTIONS` suggestions ordered by ``priority``
        ascending and, within the same priority, by severity descending. An empty
        list means no rule fired, which is a valid "nothing to fix" answer rather
        than a generic reassurance.
    """
    suggestions = [
        suggestion
        for suggestion in (
            _rule_true_peak_too_high(report),
            _rule_loudness_mismatch(report),
            _rule_low_mid_mud(report),
            _rule_harshness(report),
            _rule_bass_not_mono(report),
            _rule_over_compressed(report),
        )
        if suggestion is not None
    ]
    suggestions.sort(
        key=lambda suggestion: (
            suggestion.priority,
            -_SEVERITY_RANK[suggestion.severity],
        )
    )
    return suggestions[:MAX_SUGGESTIONS]


def _normalized_delta(band: BandDelta, integrated_lufs_delta: float) -> float:
    """Remove the global loudness offset from an absolute band delta.

    Args:
        band: Band delta whose ``delta_db`` is absolute (``user - reference``).
        integrated_lufs_delta: Global ``user - reference`` integrated loudness.

    Returns:
        The tonal band delta in dB, positive when the band is too loud relative
        to the rest of the spectrum at equal loudness.
    """
    return band.delta_db - integrated_lufs_delta


def _max_normalized_band(
    report: ComparisonReport,
    freq_range: tuple[float, float],
) -> tuple[BandDelta, float] | None:
    """Find the loudest normalized band inside an inclusive frequency range.

    Args:
        report: Comparison report holding the spectral bands.
        freq_range: ``(low_hz, high_hz)`` inclusive bounds.

    Returns:
        ``(band, normalized_delta_db)`` for the band with the highest normalized
        delta, or ``None`` when no band falls inside the range.
    """
    low_hz, high_hz = freq_range
    integrated_lufs_delta = report.loudness_delta.integrated_lufs_delta
    candidates = [
        (band, _normalized_delta(band, integrated_lufs_delta))
        for band in report.spectrum.bands
        if low_hz <= band.freq_hz <= high_hz
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[1])


def _eq_cut_suggestion(
    *,
    suggestion_id: str,
    band: BandDelta,
    normalized_delta_db: float,
    keep_db: float,
    q: float,
    freq_range: tuple[float, float],
    issue: str,
) -> Suggestion:
    """Build an ``eq_cut`` suggestion that trims only the band excess.

    Args:
        suggestion_id: Stable identifier of the suggestion.
        band: Band that exceeds the threshold.
        normalized_delta_db: Tonal excess of that band in dB.
        keep_db: How much of the excess to leave in place, in dB.
        q: Q factor of the suggested cut.
        freq_range: Frequency window the rule looked at, for the explanation.
        issue: Natural-language consequence of the excess.

    Returns:
        The populated suggestion, with a cut of ``-(normalized_delta_db - keep_db)``.
    """
    cut_db = -(normalized_delta_db - keep_db)
    low_hz, high_hz = freq_range
    return Suggestion(
        id=suggestion_id,
        priority=3,
        severity="major" if normalized_delta_db > 4.0 else "minor",
        category="eq",
        title=f"Riduci {band.freq_hz:.0f} Hz di {abs(cut_db):.1f} dB",
        explanation=(
            f"Hai {normalized_delta_db:.1f} dB in più tra {low_hz:.0f}-{high_hz:.0f} Hz "
            f"rispetto alla reference (a parità di loudness). {issue}"
        ),
        action_type="eq_cut",
        action_params={"freq_hz": band.freq_hz, "gain_db": cut_db, "q": q},
        measured={
            "normalized_delta_db": normalized_delta_db,
            "delta_db": band.delta_db,
        },
        target={"normalized_delta_db": 0.0},
    )


def _rule_loudness_mismatch(report: ComparisonReport) -> Suggestion | None:
    """Suggest a gain change when the integrated loudness drifts from the reference.

    Args:
        report: Comparison report to inspect.

    Returns:
        A ``gain`` suggestion when ``|integrated_lufs_delta|`` reaches
        :data:`LOUDNESS_TOLERANCE_LU`, otherwise ``None``.
    """
    delta = report.loudness_delta.integrated_lufs_delta
    if abs(delta) < LOUDNESS_TOLERANCE_LU:
        return None

    severity: Literal["minor", "major"] = "major" if abs(delta) >= 2.0 else "minor"
    gain_db = -delta
    if delta < 0.0:
        direction = "più silenzioso"
        action = "Alza"
    else:
        direction = "più forte"
        action = "Abbassa"

    return Suggestion(
        id="loudness_mismatch",
        priority=2,
        severity=severity,
        category="loudness",
        title=f"{action} il gain di {abs(gain_db):.1f} dB",
        explanation=(
            f"Il tuo master è {abs(delta):.1f} LUFS {direction} della reference. "
            f"Porta il gain di {gain_db:+.1f} dB prima del limiter."
        ),
        action_type="gain",
        action_params={"gain_db": gain_db},
        measured={"integrated_lufs_delta": delta},
        target={"integrated_lufs_delta": 0.0},
    )


def _rule_true_peak_too_high(report: ComparisonReport) -> Suggestion | None:
    """Suggest a limiter ceiling when the true peak exceeds the safe ceiling.

    Args:
        report: Comparison report to inspect.

    Returns:
        A ``critical`` limiter suggestion when ``true_peak_dbtp`` is above
        :data:`TRUE_PEAK_CEILING_DBTP`, otherwise ``None``. This rule is always
        first because lossy encoders can clip intersample peaks.
    """
    true_peak_dbtp = report.user_loudness.true_peak_dbtp
    if true_peak_dbtp <= TRUE_PEAK_CEILING_DBTP:
        return None

    return Suggestion(
        id="true_peak_too_high",
        priority=1,
        severity="critical",
        category="peak",
        title=f"Limita il true peak a {TRUE_PEAK_CEILING_DBTP:.0f} dBTP",
        explanation=(
            f"Il true peak è a {true_peak_dbtp:+.1f} dBTP. "
            f"Abbassa il ceiling a {TRUE_PEAK_CEILING_DBTP:.0f} dBTP per evitare "
            "clipping su encoding lossy (MP3, AAC, Spotify, YouTube)."
        ),
        action_type="limiter",
        action_params={
            "ceiling_dbtp": TRUE_PEAK_CEILING_DBTP,
            "reduction_needed_db": true_peak_dbtp - TRUE_PEAK_CEILING_DBTP,
        },
        measured={"true_peak_dbtp": true_peak_dbtp},
        target={"true_peak_dbtp": TRUE_PEAK_CEILING_DBTP},
    )


def _rule_low_mid_mud(report: ComparisonReport) -> Suggestion | None:
    """Suggest a cut when 200-500 Hz is tonally too loud.

    Args:
        report: Comparison report to inspect.

    Returns:
        An ``eq_cut`` suggestion when the loudest normalized band between
        :data:`LOW_MID_RANGE_HZ` exceeds :data:`LOW_MID_THRESHOLD_DB`,
        otherwise ``None``.
    """
    peak = _max_normalized_band(report, LOW_MID_RANGE_HZ)
    if peak is None:
        return None
    band, normalized_delta_db = peak
    if normalized_delta_db <= LOW_MID_THRESHOLD_DB:
        return None

    return _eq_cut_suggestion(
        suggestion_id="low_mid_mud",
        band=band,
        normalized_delta_db=normalized_delta_db,
        keep_db=1.0,
        q=1.2,
        freq_range=LOW_MID_RANGE_HZ,
        issue="È la zona che rende il mix 'impastato'.",
    )


def _rule_harshness(report: ComparisonReport) -> Suggestion | None:
    """Suggest a cut when 2-5 kHz is tonally too loud.

    Args:
        report: Comparison report to inspect.

    Returns:
        An ``eq_cut`` suggestion when the loudest normalized band between
        :data:`HARSH_RANGE_HZ` exceeds :data:`HARSH_THRESHOLD_DB`, otherwise
        ``None``.
    """
    peak = _max_normalized_band(report, HARSH_RANGE_HZ)
    if peak is None:
        return None
    band, normalized_delta_db = peak
    if normalized_delta_db <= HARSH_THRESHOLD_DB:
        return None

    return _eq_cut_suggestion(
        suggestion_id="harshness",
        band=band,
        normalized_delta_db=normalized_delta_db,
        keep_db=1.5,
        q=1.0,
        freq_range=HARSH_RANGE_HZ,
        issue="È la zona che rende il mix 'aspro' e faticoso da ascoltare.",
    )


def _rule_bass_not_mono(report: ComparisonReport) -> Suggestion | None:
    """Suggest narrowing the bass when its correlation is too low.

    Args:
        report: Comparison report to inspect.

    Returns:
        A ``stereo_narrow`` suggestion when the mean correlation below
        :data:`BASS_MAX_HZ` is under :data:`BASS_CORR_THRESHOLD`, otherwise
        ``None``. Mono input (``stereo is None``) never triggers this rule.
    """
    stereo = report.stereo
    if stereo is None:
        return None

    # ``StereoComparison`` stores deltas, so the user's own correlation lives in
    # ``user_correlation``; the reference value is not what this rule targets.
    # Bands with side_to_mid_db <= -60 dB are digitally silent and report
    # correlation=1.0; including them would mask a wide bass.
    bass_bands = [
        band
        for band in stereo.bands
        if band.freq_hz <= BASS_MAX_HZ and band.user_side_to_mid_db > -60.0
    ]
    if not bass_bands:
        return None

    mean_correlation = sum(band.user_correlation for band in bass_bands) / len(bass_bands)
    if mean_correlation >= BASS_CORR_THRESHOLD:
        return None

    severity: Literal["minor", "major"] = "major" if mean_correlation < 0.5 else "minor"
    return Suggestion(
        id="bass_not_mono",
        priority=4,
        severity=severity,
        category="stereo",
        title=f"Restringi il basso a mono sotto {BASS_MAX_HZ:.0f} Hz",
        explanation=(
            f"Sotto {BASS_MAX_HZ:.0f} Hz la correlazione media è {mean_correlation:.2f}: "
            "il basso è troppo largo e rischia di perdere energia in mono "
            "(club, telefoni, vinyl)."
        ),
        action_type="stereo_narrow",
        action_params={"below_hz": BASS_MAX_HZ},
        measured={"mean_correlation": mean_correlation},
        target={"mean_correlation": BASS_CORR_THRESHOLD},
    )


def _rule_over_compressed(report: ComparisonReport) -> Suggestion | None:
    """Suggest recovering dynamics when the loudness range is too small.

    Args:
        report: Comparison report to inspect.

    Returns:
        A ``compressor`` suggestion when the user loudness range is under
        :data:`LRA_MIN_LU`, otherwise ``None``. The engine cannot decompress, so
        the action only points at reducing compression in the mix.
    """
    loudness_range_lu = report.user_loudness.loudness_range_lu
    if loudness_range_lu >= LRA_MIN_LU:
        return None

    severity: Literal["minor", "major"] = "major" if loudness_range_lu < 2.0 else "minor"
    return Suggestion(
        id="over_compressed",
        priority=5,
        severity=severity,
        category="dynamics",
        title=f"Aumenta la dinamica (LRA {loudness_range_lu:.1f} LU)",
        explanation=(
            f"La loudness range è {loudness_range_lu:.1f} LU: il master è molto compresso. "
            "Considera di ridurre la compressione nel mix per recuperare dinamica."
        ),
        action_type="compressor",
        action_params={"target_lra_lu": 4.0},
        measured={"loudness_range_lu": loudness_range_lu},
        target={"loudness_range_lu": 4.0},
    )
