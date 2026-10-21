"""Abstract interface implemented by every DAW adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from master_assistant.models.schemas import Suggestion


class DawAdapter(ABC):
    """Base class for DAW-specific suggestion exporters."""

    @abstractmethod
    def render(self, suggestion: Suggestion) -> str:
        """Return a DAW-specific textual instruction for a single suggestion."""
