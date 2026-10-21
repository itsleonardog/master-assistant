"""Tests for ITU-R BS.1770-4 loudness and peak analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyloudnorm
import pytest
import soundfile as sf

from master_assistant.analysis.errors import AudioReadError
from master_assistant.analysis.loudness import analyze_loudness, analyze_loudness_segments

SAMPLE_RATE = 48_000


def _write_sine(
    path: Path,
    duration_s: float,
    amplitude: float,
    frequency_hz: float = 1000.0,
    channels: int = 1,
    phase_rad: float = 0.0,
) -> None:
    """Write a float WAV sine wave and return its path."""
    time = np.arange(int(round(duration_s * SAMPLE_RATE))) / SAMPLE_RATE
    signal = amplitude * np.sin(2.0 * np.pi * frequency_hz * time + phase_rad)
    data = signal[:, np.newaxis] if channels == 1 else np.column_stack([signal] * channels)
    sf.write(path, data, SAMPLE_RATE, subtype="FLOAT")


def test_mono_sine_reports_expected_integrated_loudness(tmp_path: Path) -> None:
    """A 1 kHz sine at -20 dBFS RMS should read about -20 LUFS.

    BS.1770 K-weighting is approximately 0 dB at 1 kHz and the standard's
    -0.691 dB offset is small, so integrated loudness tracks RMS closely.
    """
    path = tmp_path / "mono_sine.wav"
    _write_sine(path, duration_s=5.0, amplitude=np.sqrt(2.0) * 10.0 ** (-20.0 / 20.0))

    metrics = analyze_loudness(path)

    assert metrics.integrated_lufs == pytest.approx(-20.0, abs=0.5)
    assert metrics.duration_s == pytest.approx(5.0)


def test_stereo_identical_channels_sum_to_three_db_higher_lufs(tmp_path: Path) -> None:
    """Two identical -23 dBFS channels should read about -20 LUFS combined."""
    path = tmp_path / "stereo_sine.wav"
    _write_sine(
        path,
        duration_s=5.0,
        amplitude=np.sqrt(2.0) * 10.0 ** (-23.0 / 20.0),
        channels=2,
    )

    metrics = analyze_loudness(path)

    assert metrics.integrated_lufs == pytest.approx(-20.0, abs=0.5)


def test_true_peak_exceeds_sample_peak_for_intersample_peaks(tmp_path: Path) -> None:
    """A phase-shifted Fs/4 sine must reveal intersample peaks."""
    path = tmp_path / "intersample.wav"
    _write_sine(
        path,
        duration_s=5.0,
        amplitude=0.99,
        frequency_hz=SAMPLE_RATE / 4.0,
        phase_rad=np.pi / 4.0,
    )

    metrics = analyze_loudness(path)

    assert metrics.true_peak_dbtp > metrics.sample_peak_dbfs


def test_loudness_range_reflects_two_loudness_levels(tmp_path: Path) -> None:
    """30 s at -14 LUFS followed by 30 s at -23 LUFS should yield about 9 LU."""
    path = tmp_path / "range.wav"
    total_samples = int(60.0 * SAMPLE_RATE)
    time = np.arange(total_samples) / SAMPLE_RATE
    loud = np.sqrt(2.0) * 10.0 ** (-14.0 / 20.0)
    quiet = np.sqrt(2.0) * 10.0 ** (-23.0 / 20.0)
    amplitude = np.where(time < 30.0, loud, quiet)
    signal = amplitude * np.sin(2.0 * np.pi * 1000.0 * time)
    sf.write(path, signal, SAMPLE_RATE, subtype="FLOAT")

    metrics = analyze_loudness(path)

    assert 7.0 <= metrics.loudness_range_lu <= 11.0
    assert metrics.loudness_range_lu > 0.0


def test_blockwise_loudness_non_empty(tmp_path: Path) -> None:
    """A two-level signal must populate per-block loudness values."""
    path = tmp_path / "blockwise.wav"
    total_samples = int(60.0 * SAMPLE_RATE)
    time = np.arange(total_samples) / SAMPLE_RATE
    loud = np.sqrt(2.0) * 10.0 ** (-14.0 / 20.0)
    quiet = np.sqrt(2.0) * 10.0 ** (-23.0 / 20.0)
    amplitude = np.where(time < 30.0, loud, quiet)
    signal = amplitude * np.sin(2.0 * np.pi * 1000.0 * time)
    sf.write(path, signal, SAMPLE_RATE, subtype="FLOAT")

    metrics = analyze_loudness(path)

    assert metrics.loudness_range_lu > 5.0

    noise = np.random.default_rng(0).standard_normal(int(10.0 * SAMPLE_RATE)) * 0.1
    meter = pyloudnorm.Meter(SAMPLE_RATE, block_size=3.0, overlap=2.0 / 3.0)
    meter.integrated_loudness(noise)

    assert len(meter.blockwise_loudness) > 0


def test_segments_split_a_six_second_file(tmp_path: Path) -> None:
    """A 6 s file must yield at least two valid 3 s segments."""
    path = tmp_path / "segments.wav"
    _write_sine(path, duration_s=6.0, amplitude=0.2)

    segments = analyze_loudness_segments(path, window_s=3.0)

    assert len(segments) >= 2
    assert segments[0].lufs == pytest.approx(segments[1].lufs, abs=0.1)
    for segment in segments:
        assert segment.start_s < segment.end_s
        assert np.isfinite(segment.lufs)
        assert np.isfinite(segment.true_peak_dbtp)


def test_missing_and_corrupt_files_raise_audio_read_error(tmp_path: Path) -> None:
    """Unreadable inputs must surface as AudioReadError."""
    with pytest.raises(AudioReadError):
        analyze_loudness(tmp_path / "missing.wav")

    corrupt = tmp_path / "corrupt.wav"
    corrupt.write_bytes(b"this is not an audio file")
    with pytest.raises(AudioReadError):
        analyze_loudness(corrupt)
