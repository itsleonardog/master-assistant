"""Pydantic model placeholders; concrete contracts are defined in later steps."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned by the health check endpoint."""

    status: str = "ok"


class AnalysisRequest(BaseModel):
    """Placeholder for an analysis request (fields defined in Step 1)."""


class LoudnessMetrics(BaseModel):
    """Placeholder for loudness measurements (fields defined in Step 1)."""


class Suggestion(BaseModel):
    """Placeholder for a single mastering suggestion (fields defined in Step 1)."""
