"""Shared third-octave band geometry and Welch PSD helpers.

This module is internal (leading underscore). It holds the pieces that both
:mod:`master_assistant.analysis.spectrum` and
:mod:`master_assistant.analysis.stereo` need: the ISO band center table, band
naming, band bin selection, and the Welch estimator parameters.

It exists because ``stereo.py`` needs exactly the same band layout and Welch
setup as ``spectrum.py``. The alternative was importing the underscore-prefixed
helpers straight out of ``spectrum.py``, which would couple stereo analysis to
another module's private API; a tiny shared module is the cleaner (and only
slightly more invasive) option. ``spectrum.py`` imports from here, so the
extraction does not change any public behavior.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import welch

# Welch parameters. 8192 samples at 48 kHz gives ~5.9 Hz resolution, fine
# enough to resolve the lowest third-octave band while keeping enough segments
# for a stable estimate on a 5 s clip.
NPERSEG = 8192
OVERLAP_NUMERATOR = 3
OVERLAP_DENOMINATOR = 4

# Floor used when a band has no measurable energy (silence or out-of-range).
SILENCE_DB = -120.0

# A third-octave band spans center / 2**(1/6) to center * 2**(1/6).
BAND_EDGE_RATIO = 2.0 ** (1.0 / 6.0)

# ISO 266 third-octave band centers in Hz.
BAND_CENTERS_HZ: tuple[float, ...] = (
    20.0,
    25.0,
    31.5,
    40.0,
    50.0,
    63.0,
    80.0,
    100.0,
    125.0,
    160.0,
    200.0,
    250.0,
    315.0,
    400.0,
    500.0,
    630.0,
    800.0,
    1000.0,
    1250.0,
    1600.0,
    2000.0,
    2500.0,
    3150.0,
    4000.0,
    5000.0,
    6300.0,
    8000.0,
    10000.0,
    12500.0,
    16000.0,
    20000.0,
)


def welch_psd(signal: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    """Estimate the one-sided power spectral density with Welch's method.

    Args:
        signal: One-dimensional audio signal.
        sample_rate: Sample rate in Hz.

    Returns:
        A tuple of frequency bins in Hz and the PSD in units of power per Hz.
    """
    freqs, psd = welch(
        signal,
        fs=sample_rate,
        window="hann",
        nperseg=NPERSEG,
        noverlap=NPERSEG * OVERLAP_NUMERATOR // OVERLAP_DENOMINATOR,
        scaling="density",
        detrend=False,
        return_onesided=True,
    )
    return freqs, psd


def band_name(center_hz: float) -> str:
    """Format a band center frequency as a stable, human-readable name.

    Args:
        center_hz: Band center frequency in Hz.

    Returns:
        A name such as ``"1kHz"`` for integer kilohertz or ``"31.5Hz"``.
    """
    if center_hz >= 1000.0 and center_hz % 1000.0 == 0.0:
        return f"{center_hz / 1000.0:g}kHz"
    return f"{center_hz:g}Hz"


def band_mask(freqs: np.ndarray, center_hz: float) -> np.ndarray:
    """Select the frequency bins that fall inside one third-octave band.

    Args:
        freqs: Frequency bins in Hz.
        center_hz: Band center frequency in Hz.

    Returns:
        A boolean mask aligned with ``freqs``. Bands entirely above the Nyquist
        frequency, or too narrow to contain a bin, yield an all-``False`` mask.
    """
    f_lo = center_hz / BAND_EDGE_RATIO
    f_hi = center_hz * BAND_EDGE_RATIO
    if f_lo >= freqs[-1]:
        return np.zeros(freqs.shape, dtype=bool)
    return (freqs >= f_lo) & (freqs < f_hi)


def band_power(freqs: np.ndarray, psd: np.ndarray, center_hz: float) -> float:
    """Sum the PSD bins inside one third-octave band.

    Band power (rather than mean density) is the natural quantity for energy
    ratios such as mid/side balance.

    Args:
        freqs: Frequency bins in Hz.
        psd: Power spectral density aligned with ``freqs``.
        center_hz: Band center frequency in Hz.

    Returns:
        The summed band power, or ``0.0`` when the band is unmeasurable.
    """
    mask = band_mask(freqs, center_hz)
    if not np.any(mask):
        return 0.0
    value = float(np.sum(psd[mask]))
    return value if np.isfinite(value) else 0.0


def band_energy_db(freqs: np.ndarray, psd: np.ndarray, center_hz: float) -> float:
    """Integrate the PSD over one third-octave band and convert it to dB.

    The band spans ``center / 2**(1/6)`` to ``center * 2**(1/6)``. Because the
    PSD is already a density, the mean of the bins inside the interval is used
    as the band energy. Bands entirely above the Nyquist frequency, bands with
    no bins, and silent bands return ``-120.0``.

    Args:
        freqs: Frequency bins in Hz.
        psd: Power spectral density aligned with ``freqs``.
        center_hz: Band center frequency in Hz.

    Returns:
        Mean band power in dB, or ``-120.0`` when the band is unmeasurable.
    """
    mask = band_mask(freqs, center_hz)
    if not np.any(mask):
        return SILENCE_DB

    mean_power = float(np.mean(psd[mask]))
    if not np.isfinite(mean_power) or mean_power <= 0.0:
        return SILENCE_DB

    return float(10.0 * np.log10(mean_power))
