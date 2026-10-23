"""Synthetic images with known intensity regions, for checking grouping and boundary extraction.

Shapes are rendered with 4x4 supersampling (area anti-aliasing); the true label of a pixel is the shape covering its
centre. Gray noise is Gaussian and seeded; values are rounded and clipped to 0-255.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

SS = 4


@dataclass
class Scene:
    name: str
    gray: np.ndarray            # uint8
    labels: np.ndarray          # int16, true region per pixel (by shape, not by intensity)
    levels: list[float]         # nominal intensity of each label (before noise / ramps)
    description: str
    notes: dict = field(default_factory=dict)


def _grid(h, w, ss):
    ys = (np.arange(h * ss) + 0.5) / ss
    xs = (np.arange(w * ss) + 0.5) / ss
    return np.meshgrid(xs, ys)


def _rot_rect(X, Y, cx, cy, w, h, deg):
    a = np.deg2rad(deg)
    u = (X - cx) * np.cos(a) + (Y - cy) * np.sin(a)
    v = -(X - cx) * np.sin(a) + (Y - cy) * np.cos(a)
    return (np.abs(u) <= w / 2) & (np.abs(v) <= h / 2)


def _disk(X, Y, cx, cy, r):
    return (X - cx) ** 2 + (Y - cy) ** 2 <= r * r


def render(h, w, shapes, levels, noise=0.0, seed=0, blur=0.0, ramp=None):
    """shapes: list of (label, fn(X, Y) -> bool) painted in order onto label 0. ramp: callable(X, Y) -> offset added to
    label 0 only (illumination gradient on the background)."""
    X, Y = _grid(h, w, SS)
    lab_hi = np.zeros(X.shape, dtype=np.int16)
    for lab, fn in shapes:
        lab_hi[fn(X, Y)] = lab
    val_hi = np.asarray(levels, dtype=np.float64)[lab_hi]
    if ramp is not None:
        val_hi = np.where(lab_hi == 0, val_hi + ramp(X, Y), val_hi)
    val = val_hi.reshape(h, SS, w, SS).mean(axis=(1, 3))
    labels = lab_hi[SS // 2::SS, SS // 2::SS].copy()
    if blur > 0:
        val = ndimage.gaussian_filter(val, blur, mode="nearest")
    if noise > 0:
        val = val + np.random.default_rng(seed).normal(0, noise, val.shape)
    return np.clip(np.rint(val), 0, 255).astype(np.uint8), labels


def scenes() -> list[Scene]:
    H, W = 300, 400
    out = []
    shapes = [(1, lambda X, Y: _rot_rect(X, Y, 150, 150, 160, 110, 17)), (2, lambda X, Y: _disk(X, Y, 300, 120, 45))]
    g, l = render(H, W, shapes, [50, 130, 210], noise=6, seed=1)
    out.append(Scene("three_levels", g, l, [50, 130, 210], "Three well-separated levels (50/130/210), noise sigma 6"))

    shapes2 = [(1, lambda X, Y: _rot_rect(X, Y, 120, 150, 140, 160, 0)),
               (2, lambda X, Y: _rot_rect(X, Y, 250, 150, 120, 160, 0)),
               (3, lambda X, Y: _disk(X, Y, 340, 60, 30))]
    g, l = render(H, W, shapes2, [60, 120, 128, 200], noise=6, seed=2)
    out.append(Scene("close_levels", g, l, [60, 120, 128, 200],
                     "Two touching rectangles at 120 and 128 (D = 8/6 = 1.33 < 2), plus 60 and 200; noise sigma 6",
                     notes={"inseparable_pair": [1, 2]}))

    shapes3 = [(1, lambda X, Y: _rot_rect(X, Y, 200, 170, 220, 120, -8)), (2, lambda X, Y: _disk(X, Y, 60, 60, 12))]
    g, l = render(H, W, shapes3, [40, 140, 225], noise=5, seed=3)
    out.append(Scene("small_bright_spot", g, l, [40, 140, 225],
                     "Large dark background, medium block, small bright disk (~0.4 % of pixels); noise sigma 5"))

    g, l = render(H, W, shapes, [50, 130, 210], noise=6, seed=4, blur=2.0)
    out.append(Scene("blurred_edges", g, l, [50, 130, 210],
                     "three_levels blurred with sigma 2 px before noise: edge pixels take intermediate values"))

    g, l = render(H, W, [(1, lambda X, Y: _rot_rect(X, Y, 220, 150, 150, 120, 10))], [40, 170], noise=4, seed=5,
                  ramp=lambda X, Y: 90.0 * X / W)
    out.append(Scene("illumination_ramp", g, l, [40, 170],
                     "Background with a left-to-right ramp 40->130, block at 170: one region, but a wide gray range"))

    g, l = render(H, W, shapes, [50, 130, 210], noise=0, seed=0)
    out.append(Scene("noise_free", g, l, [50, 130, 210], "three_levels without noise (anti-aliased edges only)"))
    return out


def by_name(name: str) -> Scene:
    for s in scenes():
        if s.name == name:
            return s
    raise KeyError(name)
