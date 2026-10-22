"""Tests for stereo analysis and reference comparison."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from master_assistant.analysis.errors import AudioReadError
from master_assistant.analysis.stereo import analyze_stereo, compare_stereo

SAMPLE_RATE = 48_000
DURATION_S = 5.0
AMPLITUDE = 0.1
SPLIT_HZ = 500.0


def _samples() -> int:
    """Return the number of samples in the shared fixture duration."""
    return int(DURATION_S * SAMPLE_RATE)


def _write_wav(path: Path, data: np.ndarray) -> None:
    """Write float64 audio data to a WAV file at the shared sample rate."""
    sf.write(path, data, SAMPLE_RATE, subtype="FLOAT")


def _sine(
    frequency_hz: float,
    amplitude: float,
    phase_rad: float = 0.0,
    channels: int = 2,
) -> np.ndarray:
    """Generate a sine wave, optionally duplicated across channels."""
    time = np.arange(_samples()) / SAMPLE_RATE
    signal = amplitude * np.sin(2.0 * np.pi * frequency_hz * time + phase_rad)
    return np.column_stack([signal] * channels)


def _independent_noise(seed_left: int, seed_right: int) -> np.ndarray:
    """Generate two fully independent white-noise channels."""
    left = AMPLITUDE * np.random.default_rng(seed_left).standard_normal(_samples())
    right = AMPLITUDE * np.random.default_rng(seed_right).standard_normal(_samples())
    return np.column_stack([left, right])


def _bandlimited(white: np.ndarray, cutoff_hz: float, keep_below: bool) -> np.ndarray:
    """Keep only the FFT bins below or above ``cutoff_hz``."""
    spectrum = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(white.size, d=1.0 / SAMPLE_RATE)
    if keep_below:
        spectrum[freqs >= cutoff_hz] = 0.0
    else:
        spectrum[freqs < cutoff_hz] = 0.0
    return np.fft.irfft(spectrum, n=white.size)


def _split_band_stereo(seed: int) -> np.ndarray:
    """Build a file that is mono below 500 Hz and wide above 500 Hz.

    Both channels share the same low-frequency noise, so below the crossover the
    side signal is empty; above it each channel gets independent noise, so the
    side carries full-band energy.
    """
    rng = np.random.default_rng(seed)
    common = _bandlimited(rng.standard_normal(_samples()), SPLIT_HZ, keep_below=True)
    left_high = _bandlimited(rng.standard_normal(_samples()), SPLIT_HZ, keep_below=False)
    right_high = _bandlimited(rng.standard_normal(_samples()), SPLIT_HZ, keep_below=False)
    data = np.column_stack([common + left_high, common + right_high])
    rms = float(np.sqrt(np.mean(np.square(data))))
    return data * (AMPLITUDE / rms)


def test_mono_file_is_rejected(tmp_path: Path) -> None:
    """A single-channel file must raise a descriptive ValueError."""
    path = tmp_path / "mono.wav"
    _write_wav(path, _sine(frequency_hz=1000.0, amplitude=0.5, channels=1))

    with pytest.raises(ValueError) as excinfo:
        analyze_stereo(path)

    message = str(excinfo.value).lower()
    assert "stereo" in message
    assert "mono" in message


def test_correlated_sine_is_perfectly_mono(tmp_path: Path) -> None:
    """Identical channels must read as fully correlated with zero side energy."""
    path = tmp_path / "mono_correlated.wav"
    _write_wav(path, _sine(frequency_hz=1000.0, amplitude=0.5))

    metrics = analyze_stereo(path)

    assert metrics.overall_correlation == pytest.approx(1.0, abs=0.02)
    assert metrics.overall_side_to_mid_db < -60.0
    assert metrics.width_hz == 20000.0
    band_1k = next(band for band in metrics.bands if band.freq_hz == 1000.0)
    assert band_1k.correlation == pytest.approx(1.0, abs=0.01)
    # Silent bands must not be averaged in as "no correlation".
    assert all(band.correlation == 1.0 for band in metrics.bands if band.freq_hz < 500.0)


def test_independent_noise_is_uncorrelated(tmp_path: Path) -> None:
    """Independent channels must read as uncorrelated with a wide image."""
    path = tmp_path / "decorrelated.wav"
    _write_wav(path, _independent_noise(seed_left=30, seed_right=31))

    metrics = analyze_stereo(path)

    assert -0.1 <= metrics.overall_correlation <= 0.1
    assert -3.0 <= metrics.overall_side_to_mid_db <= 3.0
    assert metrics.width_hz < 500.0


def test_width_tracks_where_side_content_starts(tmp_path: Path) -> None:
    """Mono below 500 Hz and wide above must yield a width near the crossover."""
    path = tmp_path / "split_band.wav"
    _write_wav(path, _split_band_stereo(seed=40))

    metrics = analyze_stereo(path)

    assert 400.0 <= metrics.width_hz <= 700.0
    low_bands = [band for band in metrics.bands if band.freq_hz <= 250.0]
    assert low_bands
    assert all(band.correlation > 0.9 for band in low_bands)
    high_bands = [band for band in metrics.bands if band.freq_hz >= 2000.0]
    assert high_bands
    assert all(band.correlation < 0.5 for band in high_bands)


def test_two_correlated_files_have_no_deltas(tmp_path: Path) -> None:
    """Both files are mono despite different phase, so every delta is zero."""
    user_path = tmp_path / "user.wav"
    reference_path = tmp_path / "reference.wav"
    _write_wav(user_path, _sine(frequency_hz=1000.0, amplitude=0.5))
    _write_wav(reference_path, _sine(frequency_hz=1000.0, amplitude=0.5, phase_rad=0.7))

    comparison = compare_stereo(user_path, reference_path)

    assert comparison.bands
    for band in comparison.bands:
        assert band.correlation_delta == pytest.approx(0.0, abs=1e-12)
        assert band.severity == "ok"
    assert comparison.overall_correlation_delta == pytest.approx(0.0, abs=1e-12)
    assert comparison.width_hz_delta == pytest.approx(0.0, abs=1e-12)
    assert comparison.top_problems == []


def test_decorrelated_user_reports_major_deltas(tmp_path: Path) -> None:
    """A wide user track against a mono reference must flag major problems."""
    user_path = tmp_path / "user.wav"
    reference_path = tmp_path / "reference.wav"
    _write_wav(user_path, _independent_noise(seed_left=50, seed_right=51))
    _write_wav(reference_path, _sine(frequency_hz=1000.0, amplitude=0.5))

    comparison = compare_stereo(user_path, reference_path)

    assert comparison.overall_correlation_delta == pytest.approx(-1.0, abs=0.15)
    assert any(band.severity == "major" for band in comparison.bands)
    assert comparison.top_problems
    assert len(comparison.top_problems) <= 3
    assert all(problem.severity != "ok" for problem in comparison.top_problems)


def test_missing_file_raises_audio_read_error(tmp_path: Path) -> None:
    """A nonexistent path must surface the shared AudioReadError."""
    missing = tmp_path / "does_not_exist.wav"

    with pytest.raises(AudioReadError):
        analyze_stereo(missing)
