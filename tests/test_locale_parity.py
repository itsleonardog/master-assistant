"""Parity check between the it and en locale files."""

from __future__ import annotations

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "frontend" / "src" / "locales"


def _flatten(obj: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in obj.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _flatten(value, full)
        else:
            keys.add(full)
    return keys


def test_locale_files_have_identical_keys() -> None:
    it = json.loads((LOCALES_DIR / "it.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    assert _flatten(it) == _flatten(en)
