"""Boundaries between intensity regions: the "wireframe" of this prototype."""
from __future__ import annotations

import numpy as np


def boundary_mask(labels: np.ndarray) -> np.ndarray:
    """True on a pixel whose right or lower 4-neighbour has a different label. Each label change therefore marks exactly
    one pixel (on its upper/left side), giving a 1-pixel-wide line with a systematic offset of half a pixel."""
    b = np.zeros(labels.shape, dtype=bool)
    b[:, :-1] |= labels[:, :-1] != labels[:, 1:]
    b[:-1, :] |= labels[:-1, :] != labels[1:, :]
    return b


def boundary_steps(gray: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Absolute gray step across each boundary pixel (max over its right and lower label changes); 0 elsewhere."""
    g = gray.astype(np.int16)
    s = np.zeros(labels.shape, dtype=np.int16)
    h = labels[:, :-1] != labels[:, 1:]
    s[:, :-1] = np.where(h, np.abs(g[:, :-1] - g[:, 1:]), 0)
    v = labels[:-1, :] != labels[1:, :]
    s[:-1, :] = np.maximum(s[:-1, :], np.where(v, np.abs(g[:-1, :] - g[1:, :]), 0))
    return s


def wireframe_image(gray: np.ndarray, mask: np.ndarray, color=(255, 40, 40), dim: float = 0.45,
                    thicken: int = 0) -> np.ndarray:
    """Boundary pixels drawn over a dimmed copy of the image (RGB uint8). `thicken` dilates the line for display only."""
    if thicken > 0:
        from scipy import ndimage
        mask = ndimage.binary_dilation(mask, iterations=thicken)
    rgb = np.repeat((gray.astype(np.float64) * dim)[..., None], 3, axis=2).astype(np.uint8)
    rgb[mask] = color
    return rgb
