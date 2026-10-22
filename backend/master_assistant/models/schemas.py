"""Pydantic model placeholders; concrete contracts are defined in later steps."""

from __future__ import annotations

from typing import Literal

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


class SpectralBand(BaseModel):
    """Energy measured in one third-octave band.

    ``freq_hz`` is the ISO band center frequency and ``energy_db`` is the mean
    power spectral density inside the band expressed in dB.
    """

    name: str
    freq_hz: float
    energy_db: float


class SpectralMetrics(BaseModel):
    """Spectral balance and timbre descriptors for one audio file.

    Band energies are in dB, the tilt is in dB per octave, centroid and rolloff
    are in Hz, and flatness is a dimensionless ratio between 0 and 1.
    """

    bands: list[SpectralBand]
    tilt_db_per_octave: float
    spectral_centroid_hz: float
    rolloff_85_hz: float
    flatness: float


class BandDelta(BaseModel):
    """Difference between the user band energy and the reference band energy.

    ``delta_db`` is ``user_db - reference_db`` and ``severity`` classifies its
    magnitude as ``ok``, ``minor``, or ``major``.
    """

    name: str
    freq_hz: float
    user_db: float
    reference_db: float
    delta_db: float
    severity: Literal["ok", "minor", "major"]


class SpectralComparison(BaseModel):
    """Per-band comparison of a user track against a reference master.

    ``top_problems`` holds up to three bands whose severity is not ``ok``,
    ordered by descending absolute difference.
    """

    bands: list[BandDelta]
    tilt_delta_db_per_octave: float
    top_problems: list[BandDelta]
