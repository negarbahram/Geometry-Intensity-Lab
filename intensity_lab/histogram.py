"""256-bin gray-level histogram on the 0-255 scale, and explicit smoothing that never replaces the raw counts."""
from __future__ import annotations

import numpy as np

LEVELS = np.arange(256, dtype=np.float64)   # bin centres: the gray values themselves


def histogram(gray: np.ndarray) -> np.ndarray:
    """Raw counts per gray value 0..255 (float64, sums to the pixel count)."""
    if gray.dtype != np.uint8:
        raise ValueError("histogram expects uint8 gray values 0-255")
    return np.bincount(gray.ravel(), minlength=256).astype(np.float64)


def gaussian_kernel(sigma: float) -> np.ndarray:
    radius = max(1, int(np.ceil(4 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    return k / k.sum()


def smooth(counts: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing with sigma in gray levels. Bins outside 0..255 are treated as empty (zero padding), so the
    smoothed curve can leak a little mass past the ends; it is never renormalised. sigma 0 returns a copy."""
    counts = np.asarray(counts, dtype=np.float64)
    if sigma <= 0:
        return counts.copy()
    k = gaussian_kernel(sigma)
    r = len(k) // 2
    padded = np.concatenate([np.zeros(r), counts, np.zeros(r)])
    return np.convolve(padded, k, mode="valid")
