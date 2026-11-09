"""Tests for the backend-side i18n message table.

The "it" locale is the source of truth; every other locale must expose exactly
the same keys. The tests also pin the fail-fast KeyError, the Italian fallback
for an unregistered locale, and str.format interpolation.
"""

from __future__ import annotations

import pytest

from master_assistant.i18n import _MESSAGES, t


def test_locales_have_identical_keys() -> None:
    """it and en must have the exact same key set."""
    it_keys = set(_MESSAGES["it"].keys())
    en_keys = set(_MESSAGES["en"].keys())
    assert it_keys == en_keys, (
        f"missing in en: {it_keys - en_keys}; missing in it: {en_keys - it_keys}"
    )


def test_missing_key_raises_keyerror() -> None:
    """A key absent from every locale must raise instead of returning a default."""
    with pytest.raises(KeyError):
        t("does.not.exist", "it")


def test_fallback_to_italian_for_unknown_lang() -> None:
    """An unregistered locale (bypassing the Literal) falls back to Italian."""
    # "fr" is deliberately outside Lang: the cast documents that the runtime
    # fallback is what this test targets, not the type checker.
    assert t("loudness_mismatch.title_boost", "fr", gain=2.5) == (  # type: ignore[arg-type]
        "Alza il gain di 2.5 dB"
    )


def test_interpolation_works() -> None:
    """Named placeholders are substituted by str.format."""
    assert t("true_peak_too_high.title", "en", ceiling=-1) == "Limit true peak to -1 dBTP"
