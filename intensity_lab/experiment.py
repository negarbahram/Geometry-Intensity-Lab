"""One experiment = one image + one settings dict -> GMM components, GMM groups and histogram-minimum intervals with
masks and boundaries (all computed by the C++ core, see engine.py), plus the comparison with the existing detector.

`save()` writes everything needed to reproduce the result: settings.json (re-runnable with
`python -m intensity_lab run --settings settings.json --out DIR`, or directly with the C++ CLI), summary.json and the
images.
"""
from __future__ import annotations

import copy
import json
import platform
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import compare, detector, engine, plots

LAB_ROOT = Path(__file__).resolve().parent.parent
METHODS = engine.METHODS
RED, YELLOW, CYAN = (255, 40, 40), (255, 210, 0), (0, 200, 255)   # display colours, same as the core's images


def make_settings(overrides: dict | None = None) -> dict:
    """The core's defaults updated with `overrides`; unknown names are an error (the core checks values and types)."""
    s = copy.deepcopy(engine.defaults())
    unknown = set(overrides or {}) - set(s)
    if unknown:
        raise ValueError(f"unknown settings: {sorted(unknown)}")
    s.update(overrides or {})
    return s


def load_settings(path: Path) -> dict:
    """Settings from a saved settings.json ({"settings": {...}, ...}) or a plain settings object."""
    d = json.loads(Path(path).read_text())
    return make_settings(d.get("settings", d))


@dataclass
class Result:
    settings: dict                         # as the core read them (echoed in its settings.json)
    core: engine.EngineResult
    work: tempfile.TemporaryDirectory      # keeps the core's output files alive until the result is dropped
    detector_doc: dict | None = None
    detector_mask: np.ndarray | None = None
    detector_error: str | None = None
    vs_detector: dict = field(default_factory=dict)
    gmm_vs_minima: dict | None = None
    timings_ms: dict = field(default_factory=dict)

    @property
    def gray(self) -> np.ndarray:
        return self.core.gray


def run(settings: dict) -> Result:
    """Process one image in the C++ core, then compare its boundaries with the existing detector. Raises
    engine.EngineError when the core is missing or fails."""
    s = make_settings(settings)
    work = tempfile.TemporaryDirectory(prefix="intensity-lab-")
    core = engine.run(s, Path(work.name))
    r = Result(settings=core.settings_doc["settings"], core=core, work=work)
    r.timings_ms = dict(core.summary.get("timings_ms", {}))
    r.timings_ms["cpp_process_total"] = round(core.wall_s * 1e3, 1)
    tol = r.settings["compare_tolerance_px"]
    r.gmm_vs_minima = compare.compare(core.boundary["gmm"], core.boundary["minima"], tol)
    if r.settings["run_detector"]:
        t0 = time.perf_counter()
        try:
            # The detector always sees the original file, never the pre-smoothed gray image.
            r.detector_doc = detector.run(Path(core.summary["image"]["path"]))
            if (r.detector_doc["image"]["width"], r.detector_doc["image"]["height"]) != r.gray.shape[::-1]:
                raise RuntimeError("detector image size differs from the loaded image")
            r.detector_mask = detector.rasterize(r.detector_doc, r.gray.shape)
            for m in METHODS:
                r.vs_detector[m] = compare.compare(r.detector_mask, core.boundary[m], tol)
        except Exception as e:  # report, do not hide
            r.detector_error = str(e)
        r.timings_ms["detector"] = round((time.perf_counter() - t0) * 1e3, 1)
    return r


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(LAB_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
        dirty = subprocess.run(["git", "-C", str(LAB_ROOT), "status", "--porcelain", "--", "intensity_lab", "cpp/src",
                                "cpp/cli"], capture_output=True, text=True).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "") if out.returncode == 0 else None
    except OSError:
        return None


def engine_info(r: Result | None = None) -> dict:
    info = {"engine": "c++", "name": engine.NAME, "cli": str(engine.CLI)}
    if r is not None:
        sw = r.core.software
        info.update(opencv=sw.get("opencv"), compiler=sw.get("compiler"), random_starts=sw.get("random_starts"))
    return info


def summary(r: Result) -> dict:
    """The core's summary.json, plus the engine identity, the detector comparison and timings."""
    d = copy.deepcopy(r.core.summary)
    d["engine"] = engine_info(r)
    for m in METHODS:
        d["methods"][m]["vs_detector"] = compare.public(r.vs_detector[m]) if m in r.vs_detector else None
    d["detector"] = None
    if r.detector_doc is not None:
        d["detector"] = detector.summary(r.detector_doc)
        d["detector"]["rasterized_px"] = int(r.detector_mask.sum())
    if r.detector_error:
        d["detector_error"] = r.detector_error
    d["gmm_vs_minima_boundaries"] = compare.public(r.gmm_vs_minima)
    d["timings_ms"] = r.timings_ms
    return d


def _core_png(r: Result, name: str) -> np.ndarray:
    return np.asarray(Image.open(r.core.out_dir / f"{name}.png"))


def images(r: Result, display: bool = False) -> dict[str, np.ndarray]:
    """Named RGB/gray arrays. The masks and 1-pixel boundary images are the core's own; display=True redraws the
    core's boundary masks with thicker lines so they survive browser downscaling of large images."""
    th = int(round(max(r.gray.shape) / 1400)) if display else 0
    out = {"original": r.gray}
    for m in METHODS:
        out[f"mask_{m}"] = _core_png(r, f"mask_{m}")
        out[f"boundaries_{m}"] = (plots.lines_over(r.gray, [(r.core.uncertain[m], YELLOW), (r.core.boundary[m], RED)],
                                                   thicken=th) if display else _core_png(r, f"boundaries_{m}"))
        if m in r.vs_detector:
            out[f"compare_{m}"] = compare.overlay(r.gray, r.vs_detector[m], thicken=1 + th)
    if r.detector_mask is not None:
        out["detector"] = plots.lines_over(r.gray, [(r.detector_mask, CYAN)], thicken=1 + th)
    return out


def figures(r: Result) -> dict[str, bytes]:
    log = bool(r.settings["histogram_log_scale"])
    s, h = r.core.summary, r.core.hist
    return {"histogram_gmm": plots.histogram_gmm(s, h, log), "histogram_minima": plots.histogram_minima(s, h, log),
            "gmm_k_sweep": plots.k_sweep(s), "gmm_k_grid": plots.k_grid(s, h, log)}


def save(r: Result, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    software = {**engine_info(r), "lab_commit": _git_commit(), "python": platform.python_version(),
                "detector_commit": detector.DETECTOR_COMMIT, "detector_cli": str(detector.CLI)}
    meta = {"settings": r.settings, "software": software, "image_sha256": r.core.summary["image"]["sha256"],
            "reproduce": f"python -m intensity_lab run --settings {out_dir / 'settings.json'} --out <new dir>   "
                         f"(processing only: cpp/build/intensity-lab-cli run --settings ... --out ...)"}
    (out_dir / "settings.json").write_text(json.dumps(meta, indent=2))
    (out_dir / "summary.json").write_text(json.dumps(summary(r), indent=2, default=float))
    # the core's own outputs, unchanged
    for p in r.core.out_dir.iterdir():
        if p.suffix == ".png" or p.name == "histogram.json":
            shutil.copy2(p, out_dir / p.name)
    for name, arr in images(r).items():
        if name.startswith("compare_") or name == "detector":
            (out_dir / f"{name}.png").write_bytes(plots.png_from_array(arr))
    for name, png in figures(r).items():
        (out_dir / f"{name}.png").write_bytes(png)
    if r.detector_doc is not None:
        (out_dir / "detector.json").write_text(json.dumps(r.detector_doc, indent=1))
    return out_dir
