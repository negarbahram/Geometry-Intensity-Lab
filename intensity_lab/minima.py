"""Intensity intervals from local minima of the smoothed histogram."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class MinimaResult:
    candidates: list[float]            # every local minimum of the smoothed histogram (plateau -> its centre)
    kept: list[float]                  # minima that survived the filters
    removed: list[dict]                # {"position", "reason", "value"} in removal order
    thresholds: list[int]              # value <= t goes to the lower interval
    intervals: list[tuple[int, int]]   # inclusive gray ranges, contiguous, covering 0..255
    interval_pixels: list[int]
    lut: np.ndarray                    # int16[256]
    params: dict = field(default_factory=dict)


def local_minima(y: np.ndarray) -> list[float]:
    """Positions of strict local minima; a plateau of equal values counts once, at its centre. The ends of the range
    are never minima (a minimum needs higher values on both sides)."""
    runs = []                                         # (start, end, value) of runs of equal values
    s = 0
    for i in range(1, len(y) + 1):
        if i == len(y) or y[i] != y[s]:
            runs.append((s, i - 1, y[s]))
            s = i
    out = []
    for j in range(1, len(runs) - 1):
        if runs[j - 1][2] > runs[j][2] < runs[j + 1][2]:
            out.append((runs[j][0] + runs[j][1]) / 2)
    return out


def _depths(y: np.ndarray, minima: list[float]) -> list[tuple[float, float, float]]:
    """(relative depth, valley value, lower neighbouring peak) for each minimum, given the other minima kept."""
    out = []
    bounds = [0] + [int(np.floor(m)) for m in minima] + [len(y) - 1]
    for i, m in enumerate(minima):
        v = y[int(np.floor(m))]
        left = y[bounds[i]: int(np.floor(m)) + 1].max()
        right = y[int(np.floor(m)): bounds[i + 2] + 1].max()
        peak = min(left, right)
        out.append(((peak - v) / peak if peak > 0 else 0.0, v, peak))
    return out


def find_intervals(raw: np.ndarray, smoothed: np.ndarray, min_relative_depth: float = 0.2,
                   min_interval_fraction: float = 0.001) -> MinimaResult:
    """Minima of `smoothed` split 0..255 into intervals. Filters, applied one minimum at a time:
      1. a minimum whose valley is not at least `min_relative_depth` below the lower of its two neighbouring peaks
         (relative depth = 1 - valley/peak, on the smoothed counts) is removed, shallowest first;
      2. then an interval holding less than `min_interval_fraction` of the pixels (raw counts) is merged into a neighbour
         by removing the shallower of its bounding minima.
    After every removal the depths are recomputed, since the neighbouring peaks change."""
    y = np.asarray(smoothed, dtype=np.float64)
    raw = np.asarray(raw, dtype=np.float64)
    candidates = local_minima(y)
    kept = list(candidates)
    removed = []
    total = raw.sum()
    while kept:
        d = _depths(y, kept)
        i = int(np.argmin([x[0] for x in d]))
        if d[i][0] < min_relative_depth:
            removed.append({"position": kept[i], "reason": f"relative depth {d[i][0]:.3f} < {min_relative_depth}",
                            "value": float(d[i][1])})
            kept.pop(i)
            continue
        th = [int(np.floor(m)) for m in kept]
        edges = [-1] + th + [255]
        masses = [raw[edges[j] + 1: edges[j + 1] + 1].sum() / total for j in range(len(edges) - 1)]
        j = int(np.argmin(masses))
        if masses[j] < min_interval_fraction:
            bounding = [b for b in (j - 1, j) if 0 <= b < len(kept)]
            b = min(bounding, key=lambda q: d[q][0])
            removed.append({"position": kept[b], "reason": f"interval {j} holds {masses[j]:.4%} of pixels "
                                                           f"< {min_interval_fraction:.4%}", "value": float(d[b][1])})
            kept.pop(b)
            continue
        break
    thresholds = [int(np.floor(m)) for m in kept]
    edges = [-1] + thresholds + [255]
    intervals = [(edges[j] + 1, edges[j + 1]) for j in range(len(edges) - 1)]
    lut = np.zeros(256, dtype=np.int16)
    for g, (lo, hi) in enumerate(intervals):
        lut[lo:hi + 1] = g
    pixels = [int(raw[lo:hi + 1].sum()) for lo, hi in intervals]
    return MinimaResult(candidates=candidates, kept=kept, removed=removed, thresholds=thresholds, intervals=intervals,
                        interval_pixels=pixels, lut=lut,
                        params={"min_relative_depth": min_relative_depth,
                                "min_interval_fraction": min_interval_fraction})
