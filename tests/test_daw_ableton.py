"""Tests for the Ableton Live adapter.

Suggestions are built directly instead of running the rule engine: the adapter
is a pure formatter, so hand-built payloads keep every case explicit and let us
cover action types the engine does not produce yet (``eq_boost``,
``stereo_widen``, ``deesser``, ``saturation``).

``Suggestion.model_construct`` bypasses Pydantic validation, which is what lets
the unsupported-action-type test pass an invalid ``action_type`` without a
``cast`` or a hacked subclass.
"""

from __future__ import annotations

import pytest

from master_assistant.daw.ableton import AbletonAdapter
from master_assistant.models.schemas import Suggestion


@pytest.fixture()
def adapter() -> AbletonAdapter:
    """Return a fresh adapter for each test."""
    return AbletonAdapter()


def _suggestion(action_type: str, **action_params: float) -> Suggestion:
    """Build a minimal suggestion without going through the rule engine.

    Args:
        action_type: Action type to render, valid or deliberately invalid.
        **action_params: Values placed in ``action_params``.

    Returns:
        A suggestion carrying only the fields the adapter reads.
    """
    return Suggestion.model_construct(
        id=f"test_{action_type}",
        priority=1,
        severity="info",
        category="eq",
        title="Test suggestion",
        explanation="Built by the adapter test suite.",
        action_type=action_type,
        action_params=action_params,
        measured={},
        target={},
    )


def _assert_single_line(text: str) -> None:
    """Assert the rendered instruction is a trimmed, single Ableton line."""
    assert text.startswith("Ableton: ")
    assert "\n" not in text
    assert text == text.strip()


# --- Action types produced by the Step 5 rule engine -------------------------


def test_gain_renders_utility_before_limiter(adapter: AbletonAdapter) -> None:
    """A gain suggestion maps to Utility with a signed dB value."""
    text = adapter.render(_suggestion("gain", gain_db=-2.0))

    _assert_single_line(text)
    assert "Utility" in text
    assert "-2.0 dB" in text
    assert "prima del limiter" in text


def test_gain_without_gain_db_raises(adapter: AbletonAdapter) -> None:
    """``gain_db`` is mandatory because there is no sensible default."""
    with pytest.raises(ValueError, match="gain_db"):
        adapter.render(_suggestion("gain"))


def test_limiter_renders_ceiling_and_reduction(adapter: AbletonAdapter) -> None:
    """A limiter suggestion exposes ceiling and required reduction."""
    text = adapter.render(_suggestion("limiter", ceiling_dbtp=-1.0, reduction_needed_db=2.0))

    _assert_single_line(text)
    assert "Limiter" in text
    assert "-1.0 dB" in text
    assert "2.0 dB" in text


def test_limiter_uses_documented_defaults(adapter: AbletonAdapter) -> None:
    """Missing limiter parameters fall back to -1.0 dB and 0.0 dB."""
    text = adapter.render(_suggestion("limiter"))

    assert "-1.0 dB" in text
    assert "0.0 dB" in text


def test_eq_cut_renders_bell_band(adapter: AbletonAdapter) -> None:
    """An EQ cut maps to EQ Eight band 1 with frequency, gain, and Q."""
    text = adapter.render(_suggestion("eq_cut", freq_hz=315.0, gain_db=-3.5, q=1.2))

    _assert_single_line(text)
    assert "EQ Eight" in text
    assert "315 Hz" in text
    assert "-3.5 dB" in text
    assert "Q = 1.2" in text


def test_eq_cut_defaults_to_q_of_one(adapter: AbletonAdapter) -> None:
    """A missing Q renders the documented default of 1.0."""
    text = adapter.render(_suggestion("eq_cut", freq_hz=400.0, gain_db=-2.0))

    assert "Q = 1.0" in text


def test_eq_requires_frequency_and_gain(adapter: AbletonAdapter) -> None:
    """A bell band without frequency or gain is rejected instead of guessed."""
    with pytest.raises(ValueError, match="freq_hz"):
        adapter.render(_suggestion("eq_cut", gain_db=-2.0))
    with pytest.raises(ValueError, match="gain_db"):
        adapter.render(_suggestion("eq_cut", freq_hz=400.0))


def test_stereo_narrow_renders_bass_mono(adapter: AbletonAdapter) -> None:
    """A stereo_narrow suggestion maps to Utility Bass Mono at the cutoff."""
    text = adapter.render(_suggestion("stereo_narrow", below_hz=120.0))

    _assert_single_line(text)
    assert "Utility" in text
    assert "Bass Mono" in text
    assert "120 Hz" in text


def test_stereo_narrow_defaults_to_120_hz(adapter: AbletonAdapter) -> None:
    """A missing cutoff uses the documented 120 Hz default."""
    text = adapter.render(_suggestion("stereo_narrow"))

    assert "120 Hz" in text


def test_compressor_renders_lra_target(adapter: AbletonAdapter) -> None:
    """A compressor suggestion names Glue Compressor and the LRA target."""
    text = adapter.render(_suggestion("compressor", target_lra_lu=4.0))

    _assert_single_line(text)
    assert "Glue Compressor" in text
    assert "Compressor" in text
    assert "4.0 LU" in text
    assert "mix" in text


def test_compressor_defaults_to_four_lu(adapter: AbletonAdapter) -> None:
    """A missing LRA target uses the documented 4.0 LU default."""
    text = adapter.render(_suggestion("compressor"))

    assert "4.0 LU" in text


# --- Action types defined by the schema but not produced yet -----------------


def test_eq_boost_renders_bell_band(adapter: AbletonAdapter) -> None:
    """An EQ boost uses the same EQ Eight rendering as a cut."""
    text = adapter.render(_suggestion("eq_boost", freq_hz=8000.0, gain_db=2.5, q=0.7))

    _assert_single_line(text)
    assert "EQ Eight" in text
    assert "8000 Hz" in text
    assert "+2.5 dB" in text
    assert "Q = 0.7" in text


def test_stereo_widen_renders_utility_width(adapter: AbletonAdapter) -> None:
    """A stereo_widen suggestion maps to Utility Width above 100%."""
    text = adapter.render(_suggestion("stereo_widen"))

    _assert_single_line(text)
    assert "Utility" in text
    assert "Width" in text


def test_deesser_renders_eq_eight_high_shelf(adapter: AbletonAdapter) -> None:
    """A deesser suggestion maps to an EQ Eight high shelf cut."""
    text = adapter.render(_suggestion("deesser"))

    _assert_single_line(text)
    assert "EQ Eight" in text
    assert "High Shelf" in text


def test_saturation_renders_saturator(adapter: AbletonAdapter) -> None:
    """A saturation suggestion maps to Saturator with a conservative mix."""
    text = adapter.render(_suggestion("saturation"))

    _assert_single_line(text)
    assert "Saturator" in text
    assert "20–30%" in text


# --- Unsupported action types ----------------------------------------------


def test_unknown_action_type_raises(adapter: AbletonAdapter) -> None:
    """An action type the adapter does not know is a programming error."""
    with pytest.raises(ValueError, match="Unsupported action_type for Ableton"):
        adapter.render(_suggestion("reverse_polarity"))


def test_unknown_action_type_error_names_the_type(adapter: AbletonAdapter) -> None:
    """The error message includes the offending action type for debugging."""
    with pytest.raises(ValueError, match="reverse_polarity"):
        adapter.render(_suggestion("reverse_polarity"))
