"""Boundaries between intensity regions: the "wireframe" of this prototype."""
from __future__ import annotations

import numpy as np


UNCERTAIN = -1


def boundary_masks(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(certain, uncertain) boundary pixels. A pixel is marked when its right or lower 4-neighbour has a different label,
    so each label change marks exactly one pixel (on its upper/left side): a 1-pixel line offset by half a pixel.
    certain: the change is between two intensity groups (both labels >= 0). This is the wireframe.
    uncertain: one side is the "uncertain" label (-1, gray values below the minimum posterior). Such a change is the edge
    of an uncertainty band, not a boundary between groups; a pixel that is also certain counts as certain only."""
    certain = np.zeros(labels.shape, dtype=bool)
    uncertain = np.zeros(labels.shape, dtype=bool)
    for a, b, sl in ((labels[:, :-1], labels[:, 1:], (slice(None), slice(None, -1))),
                     (labels[:-1, :], labels[1:, :], (slice(None, -1), slice(None)))):
        change = a != b
        sure = (a != UNCERTAIN) & (b != UNCERTAIN)
        certain[sl] |= change & sure
        uncertain[sl] |= change & ~sure
    return certain, uncertain & ~certain


def boundary_mask(labels: np.ndarray) -> np.ndarray:
    """Certain boundaries only (see boundary_masks); identical to "any label change" when no label is -1."""
    return boundary_masks(labels)[0]


def boundary_steps(gray: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Absolute gray step across each certain boundary pixel (max over its right and lower label changes between two
    groups); 0 elsewhere."""
    g = gray.astype(np.int16)
    s = np.zeros(labels.shape, dtype=np.int16)
    sure = labels != UNCERTAIN
    h = (labels[:, :-1] != labels[:, 1:]) & sure[:, :-1] & sure[:, 1:]
    s[:, :-1] = np.where(h, np.abs(g[:, :-1] - g[:, 1:]), 0)
    v = (labels[:-1, :] != labels[1:, :]) & sure[:-1, :] & sure[1:, :]
    s[:-1, :] = np.maximum(s[:-1, :], np.where(v, np.abs(g[:-1, :] - g[1:, :]), 0))
    return s


UNCERTAIN_COLOR = (255, 210, 0)


def wireframe_image(gray: np.ndarray, mask: np.ndarray, color=(255, 40, 40), dim: float = 0.45,
                    thicken: int = 0, uncertain: np.ndarray | None = None) -> np.ndarray:
    """Boundary pixels drawn over a dimmed copy of the image (RGB uint8); edges of uncertainty bands, if given, in yellow
    underneath. `thicken` dilates the lines for display only."""
    from scipy import ndimage
    rgb = np.repeat((gray.astype(np.float64) * dim)[..., None], 3, axis=2).astype(np.uint8)
    for m, c in ((uncertain, UNCERTAIN_COLOR), (mask, color)):
        if m is None or not m.any():
            continue
        rgb[ndimage.binary_dilation(m, iterations=thicken) if thicken > 0 else m] = c
    return rgb
