"""One experiment = one image + one Settings object -> both grouping methods, masks, boundaries, detector comparison.

`save()` writes everything needed to reproduce the result: settings.json (re-runnable with
`python -m intensity_lab run --settings settings.json --out DIR`), summary.json and the images.
"""
from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import numpy as np
import scipy

from . import boundaries, compare, detector, gmm, histogram, imageio, minima, plots, regions

LAB_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    # image: dataset is "product-images" / "isaacsim-images", or null with `image` a full path (synthetic, other files)
    dataset: str | None = "product-images"
    image: str = ""
    # preprocessing
    presmooth_sigma_px: float = 0.0           # spatial Gaussian before everything else (0 = off)
    # histogram smoothing (used by the minima method; also drawn on the GMM plot for reference, never fitted)
    hist_smooth_sigma: float = 2.0            # gray levels
    # GMM
    gmm_k: int = 4
    gmm_min_sigma: float = 1.0                # gray levels
    gmm_n_init: int = 5
    gmm_seed: int = 0
    gmm_sweep_max_k: int = 8
    separation_threshold: float = 2.0         # Ashman's D
    merge_rule: str = "hierarchical"          # or "transitive" (see gmm.merge_groups)
    min_posterior: float = 0.0                # 0 = every gray value assigned; >0 marks low-certainty values uncertain
    # histogram minima
    minima_min_relative_depth: float = 0.2
    minima_min_interval_fraction: float = 0.001
    # masks
    min_region_area_px: int = 0               # 0 = no cleanup
    # comparison
    run_detector: bool = True
    compare_tolerance_px: float = 3.0
    # display only
    histogram_log_scale: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        names = {f.name for f in fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise ValueError(f"unknown settings: {sorted(unknown)}")
        return cls(**d)


@dataclass
class MethodResult:
    name: str
    lut: np.ndarray
    labels: np.ndarray
    regions_removed: int
    stats: list
    boundary: np.ndarray                      # certain: between two intensity groups (the wireframe)
    uncertain_boundary: np.ndarray            # edges of "uncertain" (-1) bands; never part of the wireframe
    steps: np.ndarray
    vs_detector: dict | None = None


@dataclass
class Result:
    settings: Settings
    image: imageio.LoadedImage
    gray: np.ndarray
    counts: np.ndarray
    smoothed: np.ndarray
    fit: gmm.GMMFit
    sweep: list
    grouping: gmm.GMMGrouping
    components: gmm.GMMGrouping               # the same fit without merging: one label per component
    minima: minima.MinimaResult
    methods: dict = field(default_factory=dict)
    detector_doc: dict | None = None
    detector_mask: np.ndarray | None = None
    detector_error: str | None = None
    gmm_vs_minima: dict | None = None
    timings_ms: dict = field(default_factory=dict)


def _method(name, gray, lut, s: Settings) -> MethodResult:
    labels = regions.apply_lut(gray, lut)
    labels, removed = regions.remove_small_regions(labels, s.min_region_area_px)
    certain, uncertain = boundaries.boundary_masks(labels)
    return MethodResult(name=name, lut=lut, labels=labels, regions_removed=removed,
                        stats=regions.group_stats(gray, labels), boundary=certain, uncertain_boundary=uncertain,
                        steps=boundaries.boundary_steps(gray, labels))


def run(s: Settings, loaded: imageio.LoadedImage | None = None) -> Result:
    t = {}
    t0 = time.perf_counter()
    img = loaded or imageio.load(imageio.resolve(s.dataset, s.image))
    gray = imageio.presmooth(img.gray, s.presmooth_sigma_px)
    counts = histogram.histogram(gray)
    smoothed = histogram.smooth(counts, s.hist_smooth_sigma)
    t["load"] = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    kw = dict(min_sigma=s.gmm_min_sigma, n_init=s.gmm_n_init, seed=s.gmm_seed)
    sweep = gmm.sweep(counts, range(1, max(s.gmm_sweep_max_k, s.gmm_k) + 1), **kw)
    fit = next(f for f in sweep if f.k == s.gmm_k)
    grouping = gmm.group_lut(fit, s.separation_threshold, s.min_posterior, s.merge_rule)
    components = gmm.component_lut(fit, s.min_posterior)
    t["gmm"] = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    mres = minima.find_intervals(counts, smoothed, s.minima_min_relative_depth, s.minima_min_interval_fraction)
    t["minima"] = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    r = Result(settings=s, image=img, gray=gray, counts=counts, smoothed=smoothed, fit=fit, sweep=sweep,
               grouping=grouping, components=components, minima=mres)
    # "gmm_components" is the fitted mixture as is; "gmm" is after merging. Comparing the two tells whether a missing
    # boundary was lost in the fit or in the merge.
    r.methods["gmm_components"] = _method("gmm_components", gray, components.lut, s)
    r.methods["gmm"] = _method("gmm", gray, grouping.lut, s)
    r.methods["minima"] = _method("minima", gray, mres.lut, s)
    r.gmm_vs_minima = compare.compare(r.methods["gmm"].boundary, r.methods["minima"].boundary, s.compare_tolerance_px)
    t["masks_boundaries"] = (time.perf_counter() - t0) * 1e3

    if s.run_detector:
        t0 = time.perf_counter()
        try:
            # The detector always sees the original file, never the pre-smoothed gray image.
            r.detector_doc = detector.run(img.path)
            if (r.detector_doc["image"]["width"], r.detector_doc["image"]["height"]) != gray.shape[::-1]:
                raise RuntimeError("detector image size differs from the loaded image")
            r.detector_mask = detector.rasterize(r.detector_doc, gray.shape)
            for m in r.methods.values():
                m.vs_detector = compare.compare(r.detector_mask, m.boundary, s.compare_tolerance_px)
        except Exception as e:  # report, do not hide
            r.detector_error = str(e)
        t["detector"] = (time.perf_counter() - t0) * 1e3
    r.timings_ms = {k: round(v, 1) for k, v in t.items()}
    return r


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(LAB_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
        dirty = subprocess.run(["git", "-C", str(LAB_ROOT), "status", "--porcelain", "--", "intensity_lab"],
                               capture_output=True, text=True).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "") if out.returncode == 0 else None
    except OSError:
        return None


def summary(r: Result) -> dict:
    sep = gmm.separation_matrix(r.fit)
    d = {
        "image": {"path": str(r.image.path), "sha256": r.image.sha256, "width": r.gray.shape[1],
                  "height": r.gray.shape[0], "source_mode": r.image.source_mode, "gray_conversion": r.image.conversion,
                  "presmooth_sigma_px": r.settings.presmooth_sigma_px},
        "histogram": {"pixels": int(r.counts.sum()), "min": int(np.flatnonzero(r.counts)[0]),
                      "max": int(np.flatnonzero(r.counts)[-1]), "empty_bins_inside_range": int(
                          (r.counts[np.flatnonzero(r.counts)[0]:np.flatnonzero(r.counts)[-1] + 1] == 0).sum()),
                      "count_at_0": int(r.counts[0]), "count_at_255": int(r.counts[255]),
                      "smoothing": f"Gaussian, sigma {r.settings.hist_smooth_sigma} gray levels, zero padding"},
        "gmm": {
            "fit": r.fit.summary(),
            "separation_ashman_d": [[None if not np.isfinite(v) else round(float(v), 3) for v in row] for row in sep],
            "threshold": r.grouping.threshold, "merge_rule": r.grouping.rule, "groups": r.grouping.groups,
            "group_gaussians": [dict(zip(("weight", "mean", "sigma"), gmm.moment_match(r.fit, g)))
                                for g in r.grouping.groups],
            "gray_ranges": regions.lut_ranges(r.grouping.lut), "min_posterior": r.grouping.min_posterior,
            "uncertain_gray_values": int((r.grouping.lut < 0).sum()),
            "component_gray_ranges": regions.lut_ranges(r.components.lut),
            "uncertain_gray_values_components": int((r.components.lut < 0).sum()),
            "sweep": [{"k": f.k, "bic": f.bic, "aic": f.aic, "log_likelihood": f.log_likelihood,
                       "groups_at_threshold": len(gmm.merge_groups(f, r.grouping.threshold, r.grouping.rule)),
                       "converged": f.converged} for f in r.sweep],
        },
        "minima": {"candidates": r.minima.candidates, "kept": r.minima.kept, "removed": r.minima.removed,
                   "thresholds": r.minima.thresholds, "intervals": r.minima.intervals,
                   "interval_pixels": r.minima.interval_pixels, "params": r.minima.params},
        "methods": {},
        "detector": None,
        "gmm_vs_minima_boundaries": compare.public(r.gmm_vs_minima),
        "timings_ms": r.timings_ms,
    }
    for name, m in r.methods.items():
        b = m.boundary
        d["methods"][name] = {
            "groups": sum(st["group"] >= 0 for st in m.stats), "regions_removed_by_cleanup": m.regions_removed, "group_stats": m.stats,
            "boundary_px": int(b.sum()), "boundary_share_of_image": float(b.mean()),
            "uncertain_pixels": int((m.labels < 0).sum()), "uncertain_boundary_px": int(m.uncertain_boundary.sum()),
            "boundary_step_median": float(np.median(m.steps[b])) if b.any() else None,
            "boundary_step_p90": float(np.percentile(m.steps[b], 90)) if b.any() else None,
            "vs_detector": compare.public(m.vs_detector) if m.vs_detector else None,
        }
    if r.detector_doc is not None:
        d["detector"] = detector.summary(r.detector_doc)
        d["detector"]["rasterized_px"] = int(r.detector_mask.sum())
    if r.detector_error:
        d["detector_error"] = r.detector_error
    return d


def images(r: Result, display: bool = False) -> dict[str, np.ndarray]:
    """Named RGB/gray arrays. display=True thickens 1-px lines on large images so they survive browser downscaling."""
    th = max(0, int(round(max(r.gray.shape) / 1400)) - 0) if display else 0
    out = {"original": r.gray}
    for name, m in r.methods.items():
        out[f"mask_{name}"] = regions.overlay(r.gray, m.labels)
        out[f"boundaries_{name}"] = boundaries.wireframe_image(r.gray, m.boundary, thicken=th,
                                                               uncertain=m.uncertain_boundary)
        if m.vs_detector:
            out[f"compare_{name}"] = compare.overlay(r.gray, m.vs_detector, thicken=1 + th)
    if r.detector_mask is not None:
        out["detector"] = boundaries.wireframe_image(r.gray, r.detector_mask, color=(0, 200, 255), thicken=1 + th)
    return out


def figures(r: Result) -> dict[str, bytes]:
    log = r.settings.histogram_log_scale
    return {
        "histogram_gmm": plots.histogram_gmm(r.counts, r.fit, r.grouping, log, r.smoothed, r.settings.hist_smooth_sigma,
                                             components=r.components),
        "histogram_minima": plots.histogram_minima(r.counts, r.smoothed, r.settings.hist_smooth_sigma, r.minima, log),
        "gmm_k_sweep": plots.k_sweep(r.sweep, r.fit.k),
        "gmm_k_grid": plots.k_grid(r.counts, [f for f in r.sweep if f.k >= 2], r.grouping.threshold, log,
                                   r.grouping.rule),
    }


def save(r: Result, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"settings": asdict(r.settings),
            "software": {"lab_commit": _git_commit(), "python": platform.python_version(), "numpy": np.__version__,
                         "scipy": scipy.__version__, "detector_commit": detector.DETECTOR_COMMIT,
                         "detector_cli": str(detector.CLI)},
            "image_sha256": r.image.sha256,
            "reproduce": f"python -m intensity_lab run --settings {out_dir / 'settings.json'} --out <new dir>"}
    (out_dir / "settings.json").write_text(json.dumps(meta, indent=2))
    (out_dir / "summary.json").write_text(json.dumps(summary(r), indent=2, default=float))
    for name, arr in images(r).items():
        (out_dir / f"{name}.png").write_bytes(plots.png_from_array(arr))
    for name, png in figures(r).items():
        (out_dir / f"{name}.png").write_bytes(png)
    for name, m in r.methods.items():
        (out_dir / f"labels_{name}.png").write_bytes(plots.png_from_array((m.labels + 1).astype(np.uint8)))
    if r.detector_doc is not None:
        (out_dir / "detector.json").write_text(json.dumps(r.detector_doc, indent=1))
    return out_dir


def load_settings(path: Path) -> Settings:
    d = json.loads(Path(path).read_text())
    return Settings.from_dict(d.get("settings", d))
