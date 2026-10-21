"""Loudness analysis implementing ITU-R BS.1770-4 measurements.

The module reports integrated, short-term, and momentary loudness, loudness
range, true peak, sample peak, and crest factor for an audio file. It only uses
``numpy``, ``scipy``, ``pyloudnorm``, and ``soundfile``; no streaming analysis is
performed yet.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile
from scipy.signal import resample_poly

from master_assistant.analysis.errors import AudioReadError
from master_assistant.models.schemas import LoudnessMetrics, SegmentLoudness

# ---------------------------------------------------------------------------
# BS.1770-4 constants
# ---------------------------------------------------------------------------
_SHORT_TERM_WINDOW_S = 3.0
_SHORT_TERM_HOP_S = 1.0
_MOMENTARY_WINDOW_S = 0.400
_MOMENTARY_HOP_S = 0.100
_ABSOLUTE_GATE_LUFS = -70.0
_TRUE_PEAK_OVERSAMPLE = 4
_LOUDNESS_FLOOR_LUFS = -70.0
_MIN_AMPLITUDE = 1e-12
_STREAMING_THRESHOLD_S = 10.0 * 60.0
# BS.1770-4 channel gains: L, R, C, Ls, Rs.
_CHANNEL_GAINS = np.array([1.0, 1.0, 1.0, 1.41, 1.41], dtype=np.float64)


def analyze_loudness(path: Path) -> LoudnessMetrics:
    """Measure BS.1770-4 loudness and peak values for an audio file.

    Args:
        path: Path to the audio file to analyze.

    Returns:
        LoudnessMetrics with integrated LUFS, maximum short-term and momentary
        LUFS, loudness range in LU, true peak in dBTP, sample peak in dBFS,
        crest factor in dB, and duration in seconds.

    Raises:
        AudioReadError: If the file cannot be opened or decoded.
    """
    data, sample_rate = _read_audio(path)
    duration_s = float(data.shape[0] / sample_rate)

    if duration_s > _STREAMING_THRESHOLD_S:
        # TODO: stream or chunk the analysis for files longer than 10 minutes
        # to avoid loading the whole signal and its 4x oversampled copy at once.
        pass

    integrated_lufs = _integrated_loudness(data, sample_rate)
    short_term_blocks = _blockwise_loudness(
        data,
        sample_rate,
        window_s=_SHORT_TERM_WINDOW_S,
        hop_s=_SHORT_TERM_HOP_S,
    )
    momentary_blocks = _blockwise_loudness(
        data,
        sample_rate,
        window_s=_MOMENTARY_WINDOW_S,
        hop_s=_MOMENTARY_HOP_S,
    )

    short_term_max = max(short_term_blocks) if short_term_blocks else integrated_lufs
    momentary_max = max(momentary_blocks) if momentary_blocks else integrated_lufs
    loudness_range = _loudness_range(short_term_blocks)

    sample_peak_dbfs = _sample_peak_dbfs(data)
    true_peak_dbtp = _true_peak_dbtp(data)
    rms_dbfs = _amplitude_to_db(float(np.sqrt(np.mean(np.square(data)))))
    crest_factor_db = sample_peak_dbfs - rms_dbfs

    return LoudnessMetrics(
        integrated_lufs=integrated_lufs,
        short_term_max_lufs=short_term_max,
        momentary_max_lufs=momentary_max,
        loudness_range_lu=loudness_range,
        true_peak_dbtp=true_peak_dbtp,
        sample_peak_dbfs=sample_peak_dbfs,
        crest_factor_db=crest_factor_db,
        duration_s=duration_s,
    )


def analyze_loudness_segments(path: Path, window_s: float = 3.0) -> list[SegmentLoudness]:
    """Measure integrated loudness and true peak over consecutive windows.

    Windows are non-overlapping and start at ``0``, ``window_s``, ``2 * window_s``,
    and so on. A final remainder shorter than one 400 ms gating block is skipped,
    because BS.1770-4 cannot produce a gated integrated value for it.

    Args:
        path: Path to the audio file to analyze.
        window_s: Window length in seconds. Must be positive.

    Returns:
        One SegmentLoudness per analyzed window, ordered by start time.

    Raises:
        AudioReadError: If the file cannot be opened or decoded.
        ValueError: If ``window_s`` is not positive.
    """
    if window_s <= 0.0:
        raise ValueError("window_s must be positive")

    data, sample_rate = _read_audio(path)
    window_samples = int(round(window_s * sample_rate))
    if window_samples <= 0:
        raise ValueError("window_s is too small for the file sample rate")

    minimum_samples = int(round(_MOMENTARY_WINDOW_S * sample_rate))
    total_samples = data.shape[0]
    segments: list[SegmentLoudness] = []

    for start in range(0, total_samples, window_samples):
        end = min(start + window_samples, total_samples)
        chunk = data[start:end]
        if chunk.shape[0] < minimum_samples and segments:
            break
        segments.append(
            SegmentLoudness(
                start_s=float(start / sample_rate),
                end_s=float(end / sample_rate),
                lufs=_integrated_loudness(chunk, sample_rate),
                true_peak_dbtp=_true_peak_dbtp(chunk),
            )
        )

    return segments


def _read_audio(path: Path) -> tuple[np.ndarray, int]:
    """Read an audio file as float64 samples with shape ``(frames, channels)``.

    Args:
        path: Path to the audio file.

    Returns:
        A tuple of the decoded samples and the sample rate in Hz.

    Raises:
        AudioReadError: If the file is missing, corrupt, empty, or has an
            invalid sample rate.
    """
    try:
        data, sample_rate = soundfile.read(path, dtype="float64", always_2d=True)
    except Exception as exc:  # soundfile raises several unrelated exception types
        raise AudioReadError(f"Could not read audio file '{path}': {exc}") from exc

    if data.size == 0 or data.shape[0] == 0 or sample_rate <= 0:
        raise AudioReadError(f"Audio file '{path}' contains no decodable samples")

    return data, int(sample_rate)


def _integrated_loudness(data: np.ndarray, sample_rate: int) -> float:
    """Measure gated integrated loudness according to ITU-R BS.1770-4.

    Args:
        data: Audio samples with shape ``(frames, channels)``.
        sample_rate: Sample rate in Hz.

    Returns:
        Integrated loudness in LUFS, floored at -70 LUFS when the signal is
        silent or otherwise non-finite.
    """
    if data.shape[0] < int(round(_MOMENTARY_WINDOW_S * sample_rate)):
        # BS.1770-4 gating requires at least one 400 ms block. For shorter
        # clips, use an ungated energy approximation so every metric stays
        # numeric; this path is documented as an approximation.
        return _finite_or_floor(_short_signal_loudness(data))

    try:
        loudness = float(pyloudnorm.Meter(sample_rate).integrated_loudness(data))
    except ValueError:
        # pyloudnorm only supports up to five channels (BS.1770 layout).
        if data.shape[1] > _CHANNEL_GAINS.size:
            raise ValueError(
                "pyloudnorm supports up to five channels; downmix the file before analysis"
            ) from None
        raise

    return _finite_or_floor(loudness)


def _short_signal_loudness(data: np.ndarray) -> float:
    """Approximate loudness for clips shorter than one BS.1770-4 gating block.

    K-weighting is omitted and channel gains are applied to the broadband mean
    square. This keeps extremely short files analyzable without pretending the
    result is a compliant gated measurement.

    Args:
        data: Audio samples with shape ``(frames, channels)``.

    Returns:
        Approximate loudness in LUFS.
    """
    mean_square = np.mean(np.square(data), axis=0)
    # Multi-channel layouts other than stereo and 5.1 are approximated with generic gains.
    gains = np.ones(data.shape[1], dtype=np.float64)
    gains[: min(data.shape[1], _CHANNEL_GAINS.size)] = _CHANNEL_GAINS[
        : min(data.shape[1], _CHANNEL_GAINS.size)
    ]
    energy = float(np.sum(gains * mean_square))
    if energy <= 0.0:
        return _LOUDNESS_FLOOR_LUFS
    return -0.691 + 10.0 * math.log10(energy)


def _blockwise_loudness(
    data: np.ndarray,
    sample_rate: int,
    window_s: float,
    hop_s: float,
) -> list[float]:
    """Compute ungated loudness for overlapping blocks.

    pyloudnorm 0.2.0 (the installed version) exposes only ``integrated_loudness``
    and ``loudness_range``; it has no short-term or momentary methods. A meter is
    therefore configured with the requested block size and hop, and its ungated
    ``blockwise_loudness`` list is read after ``integrated_loudness`` populates
    it. The public integrated result applies gating, but the stored per-block
    values remain ungated, which is what short-term and momentary maxima need.

    Args:
        data: Audio samples with shape ``(frames, channels)``.
        sample_rate: Sample rate in Hz.
        window_s: Block duration in seconds.
        hop_s: Block hop in seconds.

    Returns:
        Finite block loudness values in LUFS. Returns an empty list when the
        signal is shorter than one block.
    """
    if data.shape[0] < int(round(window_s * sample_rate)):
        return []

    overlap = 1.0 - (hop_s / window_s)
    meter = pyloudnorm.Meter(sample_rate, block_size=window_s, overlap=overlap)
    try:
        meter.integrated_loudness(data)
    except ValueError as exc:
        raise ValueError(
            f"blockwise loudness failed (sample_rate={sample_rate}, "
            f"shape={data.shape}, window_s={window_s}): {exc}"
        ) from exc

    blocks = getattr(meter, "blockwise_loudness", None)
    if not hasattr(blocks, "__iter__"):
        raise RuntimeError(
            "pyloudnorm meter did not expose an iterable blockwise_loudness "
            f"(sample_rate={sample_rate}, shape={data.shape}, window_s={window_s})"
        )

    return [float(value) for value in blocks if math.isfinite(value)]


def _loudness_range(short_term_blocks: list[float]) -> float:
    """Estimate loudness range from short-term block loudness values.

    The calculation is P95 - P10 after an absolute gate at -70 LUFS. This is a
    documented simplification of EBU R128: the relative gate at -20 LU is not
    applied, so the result can be slightly wider than a fully compliant meter.

    Args:
        short_term_blocks: Short-term loudness values in LUFS.

    Returns:
        Loudness range in LU, or ``0.0`` when fewer than two gated blocks exist.
    """
    gated = np.asarray(
        [value for value in short_term_blocks if value >= _ABSOLUTE_GATE_LUFS],
        dtype=np.float64,
    )
    if gated.size < 2:
        return 0.0

    return float(np.percentile(gated, 95) - np.percentile(gated, 10))


def _sample_peak_dbfs(data: np.ndarray) -> float:
    """Return the maximum absolute sample value across channels in dBFS.

    Args:
        data: Audio samples with shape ``(frames, channels)``.

    Returns:
        Sample peak in dBFS.
    """
    return _amplitude_to_db(float(np.max(np.abs(data))))


def _true_peak_dbtp(data: np.ndarray) -> float:
    """Return the oversampled true peak across channels in dBTP.

    Each channel is oversampled 4x with a polyphase FIR resampler before taking
    its absolute maximum, matching the ITU-R BS.1770-4 true-peak approach.

    Args:
        data: Audio samples with shape ``(frames, channels)``.

    Returns:
        True peak in dBTP.
    """
    channel_peaks = [
        float(np.max(np.abs(resample_poly(data[:, channel], up=_TRUE_PEAK_OVERSAMPLE, down=1))))
        for channel in range(data.shape[1])
    ]
    return _amplitude_to_db(max(channel_peaks))


def _amplitude_to_db(amplitude: float) -> float:
    """Convert a linear amplitude to dBFS with a small floor for silence.

    Args:
        amplitude: Non-negative linear amplitude.

    Returns:
        Level in dB relative to full scale.
    """
    return 20.0 * math.log10(max(amplitude, _MIN_AMPLITUDE))


def _finite_or_floor(value: float) -> float:
    """Replace non-finite loudness values with the absolute gate floor.

    Args:
        value: Loudness value in LUFS.

    Returns:
        The original value when finite, otherwise -70 LUFS.
    """
    return float(value) if math.isfinite(value) else _LOUDNESS_FLOOR_LUFS
