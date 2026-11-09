"""Backend-side i18n for user-facing strings (suggestions, DAW instructions).

Strings live in a flat dict keyed by dotted identifiers. Interpolation uses
str.format with named placeholders. Missing keys raise KeyError (fail fast
during tests); the "it" locale is the source of truth, "en" must have exactly
the same keys (verified by tests/test_i18n.py).
"""

from __future__ import annotations

from typing import Literal

Lang = Literal["it", "en"]

_MESSAGES: dict[Lang, dict[str, str]] = {
    "it": {
        "loudness_mismatch.title_boost": "Alza il gain di {gain} dB",
        "loudness_mismatch.title_cut": "Abbassa il gain di {gain} dB",
        "loudness_mismatch.explanation_boost": (
            "Il tuo master è {delta} LUFS più silenzioso della reference. "
            "Porta il gain di {gain} dB prima del limiter."
        ),
        "loudness_mismatch.explanation_cut": (
            "Il tuo master è {delta} LUFS più forte della reference. "
            "Porta il gain di {gain} dB prima del limiter."
        ),
        "true_peak_too_high.title": "Limita il true peak a {ceiling} dBTP",
        "true_peak_too_high.explanation": (
            "Il true peak è a {tp} dBTP. "
            "Abbassa il ceiling a {ceiling} dBTP per evitare "
            "clipping su encoding lossy (MP3, AAC, Spotify, YouTube)."
        ),
        "low_mid_mud.title": "Riduci {freq} Hz di {gain} dB",
        "low_mid_mud.explanation": (
            "Hai {delta} dB in più tra {low}-{high} Hz rispetto alla reference "
            "(a parità di loudness). È la zona che rende il mix 'impastato'."
        ),
        "harshness.title": "Riduci {freq} Hz di {gain} dB",
        "harshness.explanation": (
            "Hai {delta} dB in più tra {low}-{high} Hz rispetto alla reference "
            "(a parità di loudness). È la zona che rende il mix 'aspro' e "
            "faticoso da ascoltare."
        ),
        "bass_not_mono.title": "Restringi il basso a mono sotto {max} Hz",
        "bass_not_mono.explanation": (
            "Sotto {max} Hz la correlazione media è {corr}. "
            "Il basso è troppo largo e rischia di perdere energia in mono "
            "(club, telefoni, vinyl)."
        ),
        "over_compressed.title": "Aumenta la dinamica (LRA {lra} LU)",
        "over_compressed.explanation": (
            "La loudness range è {lra} LU: il master è molto compresso. "
            "Considera di ridurre la compressione nel mix per recuperare dinamica."
        ),
        "ableton.gain": "Ableton: Utility — Gain: {gain} dB (prima del limiter).",
        "ableton.limiter": (
            "Ableton: Limiter — Ceiling: {ceiling} dB, poi verifica il True Peak "
            "con un meter. Riduzione necessaria: {reduction} dB."
        ),
        "ableton.eq": (
            "Ableton: EQ Eight — Band 1: Bell, Frequency = {freq} Hz, Gain = {gain} dB, Q = {q}."
        ),
        "ableton.stereo_narrow": "Ableton: Utility — Bass Mono: On, Frequency = {hz} Hz.",
        "ableton.stereo_widen": "Ableton: Utility — Width: >100% (oppure Mid/Side plugin).",
        "ableton.compressor": (
            "Ableton: Glue Compressor / Compressor — riduci Ratio e/o alza Threshold; "
            "target LRA {lra} LU. È un intervento sul mix, non sul master."
        ),
        "ableton.deesser": (
            "Ableton: EQ Eight — High Shelf cut 6–8 kHz (oppure de-esser third-party)."
        ),
        "ableton.saturation": "Ableton: Saturator — Drive basso, Dry/Wet 20–30%.",
    },
    "en": {
        "loudness_mismatch.title_boost": "Raise gain by {gain} dB",
        "loudness_mismatch.title_cut": "Lower gain by {gain} dB",
        "loudness_mismatch.explanation_boost": (
            "Your master is {delta} LUFS quieter than the reference. "
            "Add {gain} dB of gain before the limiter."
        ),
        "loudness_mismatch.explanation_cut": (
            "Your master is {delta} LUFS louder than the reference. "
            "Reduce gain by {gain} dB before the limiter."
        ),
        "true_peak_too_high.title": "Limit true peak to {ceiling} dBTP",
        "true_peak_too_high.explanation": (
            "True peak is at {tp} dBTP. "
            "Lower the ceiling to {ceiling} dBTP to avoid clipping on lossy "
            "encoding (MP3, AAC, Spotify, YouTube)."
        ),
        "low_mid_mud.title": "Cut {freq} Hz by {gain} dB",
        "low_mid_mud.explanation": (
            "You have {delta} dB too much between {low}-{high} Hz compared to the "
            "reference (at equal loudness). This is the region that makes the mix "
            "sound muddy."
        ),
        "harshness.title": "Cut {freq} Hz by {gain} dB",
        "harshness.explanation": (
            "You have {delta} dB too much between {low}-{high} Hz compared to the "
            "reference (at equal loudness). This is the region that makes the mix "
            "harsh and fatiguing."
        ),
        "bass_not_mono.title": "Narrow the bass to mono below {max} Hz",
        "bass_not_mono.explanation": (
            "Below {max} Hz the average correlation is {corr}. "
            "The bass is too wide and risks losing energy in mono "
            "(clubs, phones, vinyl)."
        ),
        "over_compressed.title": "Increase dynamics (LRA {lra} LU)",
        "over_compressed.explanation": (
            "The loudness range is {lra} LU: the master is heavily compressed. "
            "Consider reducing compression in the mix to recover dynamics."
        ),
        "ableton.gain": "Ableton: Utility — Gain: {gain} dB (before the limiter).",
        "ableton.limiter": (
            "Ableton: Limiter — Ceiling: {ceiling} dB, then verify True Peak with a "
            "meter. Required reduction: {reduction} dB."
        ),
        "ableton.eq": (
            "Ableton: EQ Eight — Band 1: Bell, Frequency = {freq} Hz, Gain = {gain} dB, Q = {q}."
        ),
        "ableton.stereo_narrow": "Ableton: Utility — Bass Mono: On, Frequency = {hz} Hz.",
        "ableton.stereo_widen": "Ableton: Utility — Width: >100% (or a Mid/Side plugin).",
        "ableton.compressor": (
            "Ableton: Glue Compressor / Compressor — reduce Ratio and/or raise "
            "Threshold; target LRA {lra} LU. This is a mix-level fix, not a master fix."
        ),
        "ableton.deesser": (
            "Ableton: EQ Eight — High Shelf cut 6–8 kHz (or a third-party de-esser)."
        ),
        "ableton.saturation": "Ableton: Saturator — Low Drive, Dry/Wet 20–30%.",
    },
}


def t(key: str, lang: Lang, /, **params: object) -> str:
    """Return the localized string for `key`, formatted with `params`.

    Args:
        key: Dotted identifier, e.g. "low_mid_mud.title".
        lang: Target locale.
        **params: Values for the {placeholder}s in the template.

    Returns:
        The formatted string.

    Raises:
        KeyError: If `key` is missing in both `lang` and the "it" fallback.
    """
    template = _MESSAGES.get(lang, {}).get(key) or _MESSAGES["it"][key]
    return template.format(**params)
