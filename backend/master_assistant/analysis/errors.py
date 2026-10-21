"""Exceptions raised by the audio analysis layer."""

from __future__ import annotations


class AudioReadError(Exception):
    """Raised when an audio file cannot be opened or decoded.

    The exception message always includes the offending path so callers can
    surface an actionable error to the user without inspecting the cause chain.
    """
