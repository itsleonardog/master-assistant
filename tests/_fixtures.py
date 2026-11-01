"""Shared audio fixtures for the API tests.

The signals are constructed so the rule engine stays quiet on an
identical-file comparison: the dynamic envelope keeps the loudness range above
``LRA_MIN_LU`` and the left and right channels carry the same noise, so the bass
correlation stays at 1.0 and the "bass not mono" rule never fires. That makes
"identical uploads produce no suggestions" a meaningful assertion instead of an
accident of the fixture.

``_write_wav`` targets a path while ``_wav_bytes`` returns the encoded WAV in
memory, which is what multipart uploads need.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 48_000
AMPLITUDE = 0.05
# Segment levels of the dynamic envelope, one per third of the signal. A flat
# noise burst has a loudness range near 0 LU and would trip the over-compression
# rule even when user and reference are identical.
_ENVELOPE_SEGMENTS_DB = (0.0, -10.0, -20.0)


def _dynamic_envelope(samples: int) -> np.ndarray:
    """Build a piecewise-constant amplitude envelope with a wide loudness range.

    Args:
        samples: Number of samples to generate.

    Returns:
        A ``(samples,)`` gain array stepping through :data:`_ENVELOPE_SEGMENTS_DB`,
        each segment spanning an equal share of the signal.
    """
    t = np.arange(samples) / SAMPLE_RATE
    duration_s = samples / SAMPLE_RATE
    segment = np.minimum((t / duration_s * len(_ENVELOPE_SEGMENTS_DB)).astype(int), 2)
    levels_db = np.asarray(_ENVELOPE_SEGMENTS_DB)[segment]
    return 10.0 ** (levels_db / 20.0)


def _stereo_noise(
    duration_s: float,
    seed: int,
    amplitude: float = AMPLITUDE,
) -> np.ndarray:
    """Generate stereo noise with identical channels and a dynamic envelope.

    Args:
        duration_s: Signal length in seconds.
        seed: Seed for the random generator, so tests stay deterministic.
        amplitude: Peak amplitude of the loudest segment.

    Returns:
        A ``(samples, 2)`` float64 array whose channels are identical.
    """
    rng = np.random.default_rng(seed)
    samples = int(duration_s * SAMPLE_RATE)
    noise = rng.standard_normal(samples)
    channel = amplitude * _dynamic_envelope(samples) * noise
    return np.column_stack((channel, channel))


def _mono_noise(
    duration_s: float,
    seed: int,
    amplitude: float = AMPLITUDE,
) -> np.ndarray:
    """Generate single-channel noise with the same dynamic envelope as the stereo fixture.

    Args:
        duration_s: Signal length in seconds.
        seed: Seed for the random generator, so tests stay deterministic.
        amplitude: Peak amplitude of the loudest segment.

    Returns:
        A ``(samples, 1)`` float64 array, the shape ``soundfile`` treats as mono.
    """
    rng = np.random.default_rng(seed)
    samples = int(duration_s * SAMPLE_RATE)
    signal = amplitude * _dynamic_envelope(samples) * rng.standard_normal(samples)
    return signal[:, np.newaxis]


def _write_wav(path: Path, data: np.ndarray) -> None:
    """Write float64 audio data to a WAV file at the shared sample rate.

    Args:
        path: Destination path.
        data: Samples, either mono ``(samples,)`` or ``(samples, channels)``.
    """
    sf.write(path, data, SAMPLE_RATE, subtype="FLOAT")


def _wav_bytes(data: np.ndarray) -> bytes:
    """Encode audio data as in-memory WAV bytes for multipart uploads.

    Args:
        data: Samples, either mono ``(samples,)`` or ``(samples, channels)``.

    Returns:
        The complete WAV file content.
    """
    buffer = io.BytesIO()
    sf.write(buffer, data, SAMPLE_RATE, format="WAV", subtype="FLOAT")
    return buffer.getvalue()
