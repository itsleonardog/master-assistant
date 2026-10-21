"""Pydantic model placeholders; concrete contracts are defined in later steps."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned by the health check endpoint."""

    status: str = "ok"


class AnalysisRequest(BaseModel):
    """Placeholder for an analysis request (fields defined in Step 1)."""


class LoudnessMetrics(BaseModel):
    """ITU-R BS.1770-4 loudness and peak measurements for one audio file.

    Loudness values are expressed in LUFS, peak values in dBFS/dBTP, loudness
    range in LU, and the crest factor in dB. ``duration_s`` is the analyzed
    file duration in seconds.
    """

    integrated_lufs: float
    short_term_max_lufs: float
    momentary_max_lufs: float
    loudness_range_lu: float
    true_peak_dbtp: float
    sample_peak_dbfs: float
    crest_factor_db: float
    duration_s: float


class SegmentLoudness(BaseModel):
    """Loudness and true peak measured over a fixed analysis window."""

    start_s: float
    end_s: float
    lufs: float
    true_peak_dbtp: float


class Suggestion(BaseModel):
    """Placeholder for a single mastering suggestion (fields defined in Step 1)."""
