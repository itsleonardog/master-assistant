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


class StereoBandMetrics(BaseModel):
    """Stereo descriptors measured in one third-octave band.

    ``correlation`` is the goniometer ratio ``(M² - S²) / (M² + S²)`` in the
    ``[-1, 1]`` range: 1.0 for fully mono content, 0.0 for uncorrelated content
    and -1.0 for fully out-of-phase content. ``side_to_mid_db`` is the side
    power relative to the mid power in dB.
    """

    name: str
    freq_hz: float
    correlation: float
    side_to_mid_db: float


class StereoMetrics(BaseModel):
    """Stereo width, correlation, and mid/side balance for one audio file.

    ``width_hz`` is the frequency below which the signal is essentially mono,
    that is the highest band center for which the side stays more than 20 dB
    under the mid.
    """

    bands: list[StereoBandMetrics]
    overall_correlation: float
    overall_side_to_mid_db: float
    width_hz: float


class StereoBandDelta(BaseModel):
    """Difference between the user and reference stereo metrics in one band.

    Deltas are ``user - reference``. ``severity`` classifies the magnitude of
    ``correlation_delta`` as ``ok``, ``minor``, or ``major``.
    """

    name: str
    freq_hz: float
    user_correlation: float
    reference_correlation: float
    correlation_delta: float
    user_side_to_mid_db: float
    reference_side_to_mid_db: float
    side_to_mid_delta_db: float
    severity: Literal["ok", "minor", "major"]


class StereoComparison(BaseModel):
    """Per-band comparison of a user stereo image against a reference master.

    ``top_problems`` holds up to three bands whose severity is not ``ok``,
    ordered by descending absolute correlation difference.
    """

    bands: list[StereoBandDelta]
    overall_correlation_delta: float
    overall_side_to_mid_delta_db: float
    width_hz_delta: float
    top_problems: list[StereoBandDelta]


class LoudnessDelta(BaseModel):
    """Difference between user and reference for every loudness metric.

    Every field is ``user - reference``. ``duration_s`` is intentionally absent
    because the two files may have different durations, which makes a delta
    meaningless for it.
    """

    integrated_lufs_delta: float
    short_term_max_lufs_delta: float
    momentary_max_lufs_delta: float
    loudness_range_lu_delta: float
    true_peak_dbtp_delta: float
    sample_peak_dbfs_delta: float
    crest_factor_db_delta: float


class ComparisonReport(BaseModel):
    """Combined user versus reference report ready for the rule engine.

    ``stereo`` is ``None`` when either file is mono, because mid/side metrics
    are only defined for a stereo pair. ``warnings`` collects non-fatal caveats
    such as a skipped stereo comparison or very different file durations.
    """

    user_loudness: LoudnessMetrics
    reference_loudness: LoudnessMetrics
    loudness_delta: LoudnessDelta
    spectrum: SpectralComparison
    stereo: StereoComparison | None
    warnings: list[str]
