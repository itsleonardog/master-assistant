"""Tests for spectral analysis and reference comparison."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from master_assistant.analysis.errors import AudioReadError
from master_assistant.analysis.spectrum import analyze_spectrum, compare_spectra

SAMPLE_RATE = 48_000
DURATION_S = 5.0
AMPLITUDE = 0.1


def _write_wav(path: Path, data: np.ndarray) -> None:
    """Write float64 audio data to a WAV file at the shared sample rate."""
    sf.write(path, data, SAMPLE_RATE, subtype="FLOAT")


def _white_noise(seed: int, channels: int = 2) -> np.ndarray:
    """Generate independent white noise channels with a fixed seed."""
    rng = np.random.default_rng(seed)
    samples = int(DURATION_S * SAMPLE_RATE)
    return AMPLITUDE * rng.standard_normal((samples, channels))


def _pink_noise(seed: int, channels: int = 2) -> np.ndarray:
    """Generate pink (-3 dB/octave) noise via FFT-domain amplitude shaping.

    Each FFT bin is scaled by ``1 / sqrt(max(f, 1))`` before the inverse
    transform, so the resulting PSD falls as ``1 / f``. The signal is then
    normalized to the same RMS as the white noise fixtures so absolute band
    comparisons are meaningful.
    """
    rng = np.random.default_rng(seed)
    samples = int(DURATION_S * SAMPLE_RATE)
    freqs = np.fft.rfftfreq(samples, d=1.0 / SAMPLE_RATE)
    shape = 1.0 / np.sqrt(np.maximum(freqs, 1.0))

    channels_data = np.empty((samples, channels), dtype=np.float64)
    for channel in range(channels):
        white = rng.standard_normal(samples)
        shaped = np.fft.irfft(np.fft.rfft(white) * shape, n=samples)
        channels_data[:, channel] = shaped

    rms = float(np.sqrt(np.mean(np.square(channels_data))))
    return channels_data * (AMPLITUDE / rms)


def _sine(frequency_hz: float, amplitude: float, channels: int = 1) -> np.ndarray:
    """Generate a pure sine wave at the shared sample rate."""
    time = np.arange(int(DURATION_S * SAMPLE_RATE)) / SAMPLE_RATE
    signal = amplitude * np.sin(2.0 * np.pi * frequency_hz * time)
    if channels == 1:
        return signal[:, np.newaxis]
    return np.column_stack([signal] * channels)


def test_white_noise_is_flat_and_broadband(tmp_path: Path) -> None:
    """White noise must be flat, untilted, and centered near fs/4."""
    path = tmp_path / "white.wav"
    _write_wav(path, _white_noise(seed=1))

    metrics = analyze_spectrum(path)

    assert metrics.flatness > 0.7
    assert -1.0 <= metrics.tilt_db_per_octave <= 1.0
    assert 3000.0 <= metrics.spectral_centroid_hz <= 15000.0


def test_pink_noise_has_negative_tilt(tmp_path: Path) -> None:
    """Pink noise must measure roughly -3 dB per octave."""
    path = tmp_path / "pink.wav"
    _write_wav(path, _pink_noise(seed=2))

    metrics = analyze_spectrum(path)

    assert -4.0 <= metrics.tilt_db_per_octave <= -2.0


def test_pure_sine_is_tonal_at_its_frequency(tmp_path: Path) -> None:
    """A 1 kHz sine must have a 1 kHz centroid and near-zero flatness."""
    path = tmp_path / "sine.wav"
    _write_wav(path, _sine(frequency_hz=1000.0, amplitude=0.5))

    metrics = analyze_spectrum(path)

    assert metrics.spectral_centroid_hz == pytest.approx(1000.0, abs=100.0)
    assert metrics.flatness < 0.1


def test_independent_white_noise_files_compare_as_equivalent(tmp_path: Path) -> None:
    """Two independent white-noise files must differ by less than 2 dB per band."""
    user_path = tmp_path / "user_white.wav"
    reference_path = tmp_path / "reference_white.wav"
    _write_wav(user_path, _white_noise(seed=10))
    _write_wav(reference_path, _white_noise(seed=11))

    comparison = compare_spectra(user_path, reference_path)

    assert comparison.bands
    for band in comparison.bands:
        assert abs(band.delta_db) < 2.0
    assert all(problem.severity == "minor" for problem in comparison.top_problems)


def test_pink_noise_is_darker_than_white_noise(tmp_path: Path) -> None:
    """Pink noise must tilt below white noise and lose high-frequency energy."""
    pink_path = tmp_path / "pink.wav"
    white_path = tmp_path / "white.wav"
    _write_wav(pink_path, _pink_noise(seed=20))
    _write_wav(white_path, _white_noise(seed=21))

    # The user track is pink, the reference is white, so the tilt delta is
    # negative (pink is steeper) and high bands are quieter in the user track.
    comparison = compare_spectra(pink_path, white_path)

    assert comparison.tilt_delta_db_per_octave < -2.0
    high_bands = [band for band in comparison.bands if band.freq_hz >= 8000.0]
    assert high_bands
    assert any(band.delta_db < -3.0 for band in high_bands)


def test_missing_file_raises_audio_read_error(tmp_path: Path) -> None:
    """A nonexistent path must surface the shared AudioReadError."""
    missing = tmp_path / "does_not_exist.wav"

    with pytest.raises(AudioReadError):
        analyze_spectrum(missing)
