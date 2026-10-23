"""Figures and display images drawn from the C++ core's results (matplotlib, Agg backend). Nothing here computes
groups, fits or boundaries: curves, LUT ranges, intervals and the colour palette all come from the core's
summary.json / histogram.json."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402

LEVELS = np.arange(256)
RAW_COLOR = "#9a9a9a"
SMOOTH_COLOR = "#111111"


class Palette:
    """The core's categorical palette: index -1 = uncertain, 0.. = group/component (cycling)."""

    def __init__(self, hist: dict):
        self.rgb = [tuple(c) for c in hist["palette_rgb"]]

    def __call__(self, i: int) -> tuple:
        c = self.rgb[0] if i < 0 else self.rgb[1 + i % (len(self.rgb) - 1)]
        return tuple(v / 255 for v in c)


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


def _strip(ax, ranges, label, pal):
    """Thin band under the histogram: which group owns each gray value ({"group", "lo", "hi"} from the core)."""
    for r in ranges:
        ax.axvspan(r["lo"] - 0.5, r["hi"] + 0.5, color=pal(r["group"]), lw=0)
    ax.set_xlim(-1, 256)
    ax.set_yticks([])
    ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=8)


def histogram_gmm(summary: dict, hist: dict, log=True) -> bytes:
    """Components are coloured by their own index, matching the "component" band and the unmerged component mask; the
    "group" band uses group colours, matching the merged-group mask."""
    pal = Palette(hist)
    g, fit = summary["gmm"], summary["gmm"]["fit"]
    counts, smoothed, curves = np.array(hist["raw"]), np.array(hist["smoothed"]), np.array(hist["component_curves"])
    fig, (ax, s1, s2) = plt.subplots(3, 1, figsize=(9, 4.6), sharex=True, gridspec_kw=dict(height_ratios=[12, 1, 1]))
    _raw_bars(ax, counts, log)
    if hist["smoothing_sigma"] > 0:
        ax.plot(LEVELS, smoothed, color=SMOOTH_COLOR, lw=0.8, ls=":",
                label=f"smoothed (Gaussian, sigma {hist['smoothing_sigma']:g})")
    comp_group = {c: gi for gi, grp in enumerate(g["groups"]) for c in grp}
    for j in range(fit["k"]):
        ax.plot(LEVELS, curves[j], color=pal(j), lw=1.6,
                label=f"C{j + 1}: mean {fit['means'][j]:.1f}, sd {fit['sigmas'][j]:.1f}, w {fit['weights'][j]:.3f} "
                      f"-> G{comp_group[j] + 1}")
    ax.plot(LEVELS, curves.sum(axis=0), color="black", lw=1.0, ls="--", label="mixture (sum)")
    ax.set_title(f"GMM, K = {fit['k']}: {len(g['groups'])} intensity group(s), {g['merge_rule']} merging at D >= "
                 f"{g['threshold']:g}", fontsize=10)
    ax.legend(fontsize=7, loc="upper left", framealpha=0.85)
    _strip(s1, g["component_gray_ranges"], "component\n(no merging)", pal)
    _strip(s2, g["gray_ranges"], "group\n(merged)", pal)
    s2.set_xlabel("gray value (0-255)")
    fig.tight_layout()
    return _png(fig)


def histogram_minima(summary: dict, hist: dict, log=True) -> bytes:
    pal = Palette(hist)
    m = summary["minima"]
    counts, smoothed, sigma = np.array(hist["raw"]), np.array(hist["smoothed"]), hist["smoothing_sigma"]
    fig, (ax, strip) = plt.subplots(2, 1, figsize=(9, 4.2), sharex=True, gridspec_kw=dict(height_ratios=[12, 1]))
    _raw_bars(ax, counts, log)
    ax.plot(LEVELS, smoothed, color=SMOOTH_COLOR, lw=1.3,
            label=f"smoothed histogram (Gaussian, sigma {sigma:g} gray levels)" if sigma > 0 else "no smoothing (sigma 0)")
    floor = 1 if log else 0
    rej = [x["position"] for x in m["removed"]]
    if rej:
        ax.plot(rej, np.maximum(smoothed[np.floor(rej).astype(int)], floor), "x", color="#c00000", ms=4,
                label=f"rejected minima ({len(rej)})")
    for i, k in enumerate(m["kept"]):
        ax.axvline(k, color="#c00000", lw=1.2, label="kept minimum -> threshold" if i == 0 else None)
    ax.set_title(f"Histogram minima: {len(m['intervals'])} interval(s), min relative depth "
                 f"{m['params']['min_relative_depth']:g}", fontsize=10)
    ax.legend(fontsize=7, loc="upper left", framealpha=0.85)
    _strip(strip, [{"group": i, "lo": lo, "hi": hi} for i, (lo, hi) in enumerate(m["intervals"])], "interval", pal)
    strip.set_xlabel("gray value (0-255)")
    fig.tight_layout()
    return _png(fig)


def k_sweep(summary: dict) -> bytes:
    sw = summary["gmm"]["sweep"]
    ks = [f["k"] for f in sw]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.plot(ks, [f["bic"] for f in sw], "o-", label="BIC")
    ax.plot(ks, [f["aic"] for f in sw], "s--", label="AIC", ms=4)
    ax.axvline(summary["gmm"]["fit"]["k"], color="#888", lw=0.8, ls=":")
    ax.set_xlabel("number of components K")
    ax.set_ylabel("criterion (lower = better fit per parameter)")
    ax.set_title("GMM information criteria (indicative only)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _png(fig)


def k_grid(summary: dict, hist: dict, log=True) -> bytes:
    pal = Palette(hist)
    g = summary["gmm"]
    curves_by_k = {e["k"]: np.array(e["curves"]) for e in hist["sweep_curves"]}
    fits = [f for f in g["sweep"] if f["k"] >= 2]
    counts = np.array(hist["raw"])
    n = len(fits)
    cols = min(4, n)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.4 * cols, 2.5 * rows), squeeze=False)
    for ax, f in zip(axes.ravel(), fits):
        _raw_bars(ax, counts, log)
        curves = curves_by_k[f["k"]]
        cg = {c: gi for gi, grp in enumerate(f["groups"]) for c in grp}
        for j in range(f["k"]):
            ax.plot(LEVELS, curves[j], color=pal(cg[j]), lw=1.2)
        ax.plot(LEVELS, curves.sum(axis=0), "k--", lw=0.8)
        ax.set_title(f"K={f['k']}: {len(f['groups'])} group(s), BIC {f['bic']:.4g}", fontsize=8)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(labelsize=6)
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.suptitle(f"GMM fits for different K (groups after {g['merge_rule']} merging at D >= {g['threshold']:g})",
                 fontsize=9)
    fig.tight_layout()
    return _png(fig)


def lines_over(gray: np.ndarray, layers, dim: float = 0.45, thicken: int = 0) -> np.ndarray:
    """Display only: masks drawn in order over a dimmed copy of the image; `thicken` widens lines so they survive
    browser downscaling of large images (saved outputs use the core's 1-pixel images)."""
    rgb = np.repeat((gray.astype(np.float64) * dim)[..., None], 3, axis=2).astype(np.uint8)
    for mask, color in layers:
        if mask is None or not mask.any():
            continue
        rgb[ndimage.binary_dilation(mask, iterations=thicken) if thicken > 0 else mask] = color
    return rgb


def png_from_array(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG", optimize=False, compress_level=3)
    return buf.getvalue()
