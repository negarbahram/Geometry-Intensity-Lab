"""Figures shared by the interface and the saved outputs (matplotlib, Agg backend)."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from .gmm import GMMFit, GMMGrouping, merge_groups  # noqa: E402
from .histogram import LEVELS  # noqa: E402
from .minima import MinimaResult  # noqa: E402
from .regions import group_color, lut_ranges  # noqa: E402

RAW_COLOR = "#9a9a9a"
SMOOTH_COLOR = "#111111"


def _rgb(i):
    return tuple(c / 255 for c in group_color(i))


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return buf.getvalue()


def _raw_bars(ax, counts, log):
    ax.bar(LEVELS, counts, width=1.0, color=RAW_COLOR, edgecolor="none", label="raw histogram (counts)")
    ax.set_xlim(-1, 256)
    ax.set_xlabel("gray value (0-255)")
    ax.set_ylabel("pixels" + (" (log scale)" if log else ""))
    if log:
        ax.set_yscale("log")
        ax.set_ylim(0.8, max(counts.max(), 1) * 2)


def _lut_strip(ax, lut, label):
    """Thin band under the histogram: which group owns each gray value."""
    for r in lut_ranges(lut):
        ax.axvspan(r["lo"] - 0.5, r["hi"] + 0.5, color=_rgb(r["group"]), lw=0)
    ax.set_xlim(-1, 256)
    ax.set_yticks([])
    ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=8)


def histogram_gmm(counts, fit: GMMFit, grouping: GMMGrouping, log=True, smoothed=None, smooth_sigma=None,
                  components: GMMGrouping | None = None) -> bytes:
    """Components are coloured by their own index (C1 = first palette colour, ...), matching the "component" band and
    the unmerged component mask; the "group" band uses group colours, matching the merged-group mask."""
    fig, axes = plt.subplots(3 if components is not None else 2, 1, figsize=(9, 4.6), sharex=True,
                             gridspec_kw=dict(height_ratios=[12, 1, 1] if components is not None else [12, 1]))
    ax, strips = axes[0], axes[1:]
    _raw_bars(ax, counts, log)
    if smoothed is not None and smooth_sigma:
        ax.plot(LEVELS, smoothed, color=SMOOTH_COLOR, lw=0.8, ls=":", label=f"smoothed (Gaussian, sigma {smooth_sigma:g})")
    curves = fit.component_curves(LEVELS)
    comp_group = {c: gi for gi, g in enumerate(grouping.groups) for c in g}
    for j in range(fit.k):
        ax.plot(LEVELS, curves[j], color=_rgb(j if components is not None else comp_group[j]), lw=1.6,
                label=f"C{j + 1}: mean {fit.means[j]:.1f}, sd {fit.sigmas[j]:.1f}, w {fit.weights[j]:.3f} -> G{comp_group[j] + 1}")
    ax.plot(LEVELS, curves.sum(axis=0), color="black", lw=1.0, ls="--", label="mixture (sum)")
    ax.set_title(f"GMM, K = {fit.k}: {len(grouping.groups)} intensity group(s), {grouping.rule} merging at D >= "
                 f"{grouping.threshold:g}",
                 fontsize=10)
    ax.legend(fontsize=7, loc="upper left", framealpha=0.85)
    if components is not None:
        _lut_strip(strips[0], components.lut, "component\n(no merging)")
    _lut_strip(strips[-1], grouping.lut, "group\n(merged)")
    strips[-1].set_xlabel("gray value (0-255)")
    fig.tight_layout()
    return _png(fig)


def histogram_minima(counts, smoothed, sigma, res: MinimaResult, log=True) -> bytes:
    fig, (ax, strip) = plt.subplots(2, 1, figsize=(9, 4.2), sharex=True, gridspec_kw=dict(height_ratios=[12, 1]))
    _raw_bars(ax, counts, log)
    ax.plot(LEVELS, smoothed, color=SMOOTH_COLOR, lw=1.3,
            label=f"smoothed histogram (Gaussian, sigma {sigma:g} gray levels)" if sigma > 0 else "no smoothing (sigma 0)")
    floor = 1 if log else 0
    rej = [m for m in res.candidates if m not in res.kept]
    if rej:
        ax.plot(rej, np.maximum(smoothed[np.floor(rej).astype(int)], floor), "x", color="#c00000", ms=4,
                label=f"rejected minima ({len(rej)})")
    for i, m in enumerate(res.kept):
        ax.axvline(m, color="#c00000", lw=1.2, label="kept minimum -> threshold" if i == 0 else None)
    ax.set_title(f"Histogram minima: {len(res.intervals)} interval(s), min relative depth {res.params['min_relative_depth']:g}",
                 fontsize=10)
    ax.legend(fontsize=7, loc="upper left", framealpha=0.85)
    _lut_strip(strip, res.lut, "interval")
    strip.set_xlabel("gray value (0-255)")
    fig.tight_layout()
    return _png(fig)


def k_sweep(fits: list[GMMFit], chosen_k: int) -> bytes:
    ks = [f.k for f in fits]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.plot(ks, [f.bic for f in fits], "o-", label="BIC")
    ax.plot(ks, [f.aic for f in fits], "s--", label="AIC", ms=4)
    ax.axvline(chosen_k, color="#888", lw=0.8, ls=":")
    ax.set_xlabel("number of components K")
    ax.set_ylabel("criterion (lower = better fit per parameter)")
    ax.set_title("GMM information criteria (indicative only)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _png(fig)


def k_grid(counts, fits: list[GMMFit], threshold: float, log=True, rule="hierarchical") -> bytes:
    n = len(fits)
    cols = min(4, n)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.4 * cols, 2.5 * rows), squeeze=False)
    for ax, f in zip(axes.ravel(), fits):
        _raw_bars(ax, counts, log)
        curves = f.component_curves(LEVELS)
        groups = merge_groups(f, threshold, rule)
        cg = {c: gi for gi, g in enumerate(groups) for c in g}
        for j in range(f.k):
            ax.plot(LEVELS, curves[j], color=_rgb(cg[j]), lw=1.2)
        ax.plot(LEVELS, curves.sum(axis=0), "k--", lw=0.8)
        ax.set_title(f"K={f.k}: {len(groups)} group(s), BIC {f.bic:.4g}", fontsize=8)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(labelsize=6)
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.suptitle(f"GMM fits for different K (groups after {rule} merging at D >= {threshold:g})", fontsize=9)
    fig.tight_layout()
    return _png(fig)


def png_from_array(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG", optimize=False, compress_level=3)
    return buf.getvalue()
