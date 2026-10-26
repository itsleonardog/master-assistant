"""Tests for the combined loudness/spectrum/stereo comparison orchestrator."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from master_assistant.analysis.comparison import analyze_pair
from master_assistant.analysis.errors import AudioReadError

SAMPLE_RATE = 48_000
AMPLITUDE = 0.1


def _write_wav(path: Path, data: np.ndarray) -> None:
    """Write float64 audio data to a WAV file at the shared sample rate."""
    sf.write(path, data, SAMPLE_RATE, subtype="FLOAT")


def _stereo_noise(duration_s: float, seed: int, amplitude: float = AMPLITUDE) -> np.ndarray:
    """Generate independent white-noise left and right channels."""
    rng = np.random.default_rng(seed)
    samples = int(duration_s * SAMPLE_RATE)
    return amplitude * rng.standard_normal((samples, 2))


def _mono_noise(duration_s: float, seed: int, amplitude: float = AMPLITUDE) -> np.ndarray:
    """Generate a single-channel white-noise signal."""
    rng = np.random.default_rng(seed)
    samples = int(duration_s * SAMPLE_RATE)
    return amplitude * rng.standard_normal((samples, 1))


def test_identical_files_produce_zero_deltas(tmp_path: Path) -> None:
    """The same file as user and reference must yield all-zero deltas."""
    path = tmp_path / "same.wav"
    _write_wav(path, _stereo_noise(duration_s=5.0, seed=1))

    report = analyze_pair(path, path)

    delta = report.loudness_delta
    assert delta.integrated_lufs_delta == pytest.approx(0.0, abs=1e-9)
    assert delta.short_term_max_lufs_delta == pytest.approx(0.0, abs=1e-9)
    assert delta.momentary_max_lufs_delta == pytest.approx(0.0, abs=1e-9)
    assert delta.loudness_range_lu_delta == pytest.approx(0.0, abs=1e-9)
    assert delta.true_peak_dbtp_delta == pytest.approx(0.0, abs=1e-9)
    assert delta.sample_peak_dbfs_delta == pytest.approx(0.0, abs=1e-9)
    assert delta.crest_factor_db_delta == pytest.approx(0.0, abs=1e-9)
    assert all(abs(band.delta_db) < 1e-9 for band in report.spectrum.bands)
    assert report.stereo is not None
    assert all(abs(band.correlation_delta) < 1e-9 for band in report.stereo.bands)
    assert report.warnings == []


def test_gainer_user_shows_uniform_gain_deltas(tmp_path: Path) -> None:
    """A +6 dB user version must show +6 dB in loudness and every band."""
    reference_path = tmp_path / "reference.wav"
    user_path = tmp_path / "user.wav"
    reference = _stereo_noise(duration_s=5.0, seed=2)
    _write_wav(reference_path, reference)
    _write_wav(user_path, reference * 10.0 ** (6.0 / 20.0))

    report = analyze_pair(user_path, reference_path)

    assert report.loudness_delta.integrated_lufs_delta == pytest.approx(6.0, abs=0.5)
    assert report.loudness_delta.true_peak_dbtp_delta == pytest.approx(6.0, abs=0.5)
    # The 20 Hz band falls between two Welch bins (5.86 Hz spacing at 48 kHz
    # with nperseg=8192), so both files are floored at -120 dB and its delta is
    # 0 rather than the gain. Every measurable band must still show +6.02 dB.
    measurable_bands = [band for band in report.spectrum.bands if band.user_db > -120.0]
    assert len(measurable_bands) == len(report.spectrum.bands) - 1
    for band in measurable_bands:
        assert abs(band.delta_db - 6.02) < 1.0
    assert report.stereo is not None
    for band in report.stereo.bands:
        assert abs(band.correlation_delta) < 0.01
        assert abs(band.side_to_mid_delta_db) < 0.5


def test_mono_user_skips_stereo_with_warning(tmp_path: Path) -> None:
    """A mono user file against a stereo reference must skip stereo analysis."""
    user_path = tmp_path / "user.wav"
    reference_path = tmp_path / "reference.wav"
    _write_wav(user_path, _mono_noise(duration_s=5.0, seed=3))
    _write_wav(reference_path, _stereo_noise(duration_s=5.0, seed=4))

    report = analyze_pair(user_path, reference_path)

    assert report.stereo is None
    assert any(
        "mono" in warning.lower() or "stereo" in warning.lower() for warning in report.warnings
    )


def test_both_mono_files_skip_stereo_with_warning(tmp_path: Path) -> None:
    """Two mono files must also skip stereo analysis and warn about it."""
    user_path = tmp_path / "user.wav"
    reference_path = tmp_path / "reference.wav"
    _write_wav(user_path, _mono_noise(duration_s=5.0, seed=5))
    _write_wav(reference_path, _mono_noise(duration_s=5.0, seed=6))

    report = analyze_pair(user_path, reference_path)

    assert report.stereo is None
    assert any(
        "mono" in warning.lower() or "stereo" in warning.lower() for warning in report.warnings
    )


def test_missing_user_file_raises_audio_read_error(tmp_path: Path) -> None:
    """A nonexistent user path must propagate AudioReadError."""
    reference_path = tmp_path / "reference.wav"
    _write_wav(reference_path, _stereo_noise(duration_s=5.0, seed=7))

    with pytest.raises(AudioReadError):
        analyze_pair(tmp_path / "does_not_exist.wav", reference_path)


def test_missing_reference_file_raises_audio_read_error(tmp_path: Path) -> None:
    """A nonexistent reference path must propagate AudioReadError."""
    user_path = tmp_path / "user.wav"
    _write_wav(user_path, _stereo_noise(duration_s=5.0, seed=8))

    with pytest.raises(AudioReadError):
        analyze_pair(user_path, tmp_path / "does_not_exist.wav")


def test_very_different_durations_emit_warning(tmp_path: Path) -> None:
    """A 4x duration ratio must add a warning that mentions duration."""
    user_path = tmp_path / "user.wav"
    reference_path = tmp_path / "reference.wav"
    _write_wav(user_path, _stereo_noise(duration_s=5.0, seed=9))
    _write_wav(reference_path, _stereo_noise(duration_s=20.0, seed=10))

    report = analyze_pair(user_path, reference_path)

    assert any("duration" in warning.lower() for warning in report.warnings)


def test_similar_durations_emit_no_duration_warning(tmp_path: Path) -> None:
    """A 1.2x duration ratio must not add a duration warning."""
    user_path = tmp_path / "user.wav"
    reference_path = tmp_path / "reference.wav"
    _write_wav(user_path, _stereo_noise(duration_s=5.0, seed=11))
    _write_wav(reference_path, _stereo_noise(duration_s=6.0, seed=12))

    report = analyze_pair(user_path, reference_path)

    assert not any("duration" in warning.lower() for warning in report.warnings)
