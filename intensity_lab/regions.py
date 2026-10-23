"""Label maps from gray-value lookup tables, optional small-region cleanup, overlays and per-group statistics."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

UNCERTAIN = -1
EIGHT = np.ones((3, 3), dtype=bool)

# Categorical palette (RGB). Order is the group index, which is sorted by intensity; the colours carry no meaning.
PALETTE = np.array([
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75),
    (227, 119, 194), (23, 190, 207), (188, 189, 34), (127, 127, 127), (174, 199, 232), (255, 187, 120),
], dtype=np.uint8)
UNCERTAIN_RGB = np.array((40, 40, 40), dtype=np.uint8)


def group_color(i: int) -> tuple[int, int, int]:
    return tuple(int(c) for c in (UNCERTAIN_RGB if i < 0 else PALETTE[i % len(PALETTE)]))


def apply_lut(gray: np.ndarray, lut: np.ndarray) -> np.ndarray:
    return np.asarray(lut, dtype=np.int16)[gray]


def remove_small_regions(labels: np.ndarray, min_area: int) -> tuple[np.ndarray, int]:
    """Connected regions (8-connectivity, per label) smaller than `min_area` pixels are given the label of the nearest
    pixel that belongs to a large-enough region. Returns the new map and the number of regions removed. 0 = off."""
    if min_area <= 1:
        return labels, 0
    small = np.zeros(labels.shape, dtype=bool)
    removed = 0
    for g in np.unique(labels):
        cc, n = ndimage.label(labels == g, structure=EIGHT)
        if n == 0:
            continue
        sizes = np.bincount(cc.ravel())
        bad = np.flatnonzero(sizes < min_area)
        bad = bad[bad > 0]
        if len(bad):
            small |= np.isin(cc, bad)
            removed += len(bad)
    if not small.any():
        return labels, 0
    if small.all():
        return labels, 0                                   # nothing large enough to fill from: leave unchanged
    _, (iy, ix) = ndimage.distance_transform_edt(small, return_indices=True)
    return labels[iy, ix], removed


def overlay(gray: np.ndarray, labels: np.ndarray, alpha: float = 0.55) -> np.ndarray:
    """Coloured groups blended over the gray image (RGB uint8). Uncertain pixels are dark gray."""
    base = np.repeat(gray[..., None], 3, axis=2).astype(np.float64)
    colors = np.zeros(labels.shape + (3,), dtype=np.float64)
    for g in np.unique(labels):
        colors[labels == g] = group_color(int(g))
    return np.clip((1 - alpha) * base + alpha * colors, 0, 255).astype(np.uint8)


def group_stats(gray: np.ndarray, labels: np.ndarray) -> list[dict]:
    """Per label: pixel share, gray range/mean/std of the pixels it actually holds, and its number of connected regions
    (8-connectivity) -- a group is a set of gray values, not one object."""
    out = []
    n = labels.size
    for g in np.unique(labels):
        m = labels == g
        v = gray[m].astype(np.float64)
        cc, ncc = ndimage.label(m, structure=EIGHT)
        sizes = np.bincount(cc.ravel())[1:]
        out.append({
            "group": int(g), "pixels": int(m.sum()), "share": float(m.sum() / n),
            "gray_min": int(v.min()), "gray_max": int(v.max()), "gray_mean": float(v.mean()), "gray_std": float(v.std()),
            "connected_regions": int(ncc), "largest_region_px": int(sizes.max()) if len(sizes) else 0,
            "regions_under_50px": int((sizes < 50).sum()),
        })
    return out


def lut_ranges(lut: np.ndarray) -> list[dict]:
    """Runs of equal labels in a 256-entry LUT: {"group", "lo", "hi"} (inclusive)."""
    out = []
    s = 0
    for v in range(1, 257):
        if v == 256 or lut[v] != lut[s]:
            out.append({"group": int(lut[s]), "lo": s, "hi": v - 1})
            s = v
    return out
