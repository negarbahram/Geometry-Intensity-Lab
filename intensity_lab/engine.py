"""The C++ processing core (cpp/, `intensity-lab-cli`) as seen from Python.

All intensity processing (gray conversion, histogram, GMM, merging, minima, masks, cleanup, boundaries) runs in the C++
CLI. This module only starts it, reads what it wrote, and raises EngineError when it cannot: there is no Python
fallback.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

LAB_ROOT = Path(__file__).resolve().parent.parent
CLI = Path(os.environ.get("INTENSITY_LAB_CLI", LAB_ROOT / "cpp" / "build" / "intensity-lab-cli"))
DATASETS = ("product-images", "isaacsim-images")
METHODS = ("gmm_components", "gmm", "minima")
NAME = "C++ core (intensity-lab-cli)"


class EngineError(RuntimeError):
    """The C++ core is missing or failed; the message says why."""


def available() -> bool:
    return CLI.is_file() and os.access(CLI, os.X_OK)


def _call(args: list[str], timeout: float = 600) -> str:
    if not available():
        raise EngineError(f"C++ core not built: {CLI} is missing. Build it with the commands in README.md "
                          "(cpp/scripts/build_opencv.sh, then cmake).")
    try:
        res = subprocess.run([str(CLI), *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise EngineError(f"C++ core timed out after {timeout:.0f} s") from e
    except OSError as e:
        raise EngineError(f"C++ core could not be started: {e}") from e
    if res.returncode != 0:
        msg = res.stderr.strip() or f"exit code {res.returncode}"
        raise EngineError(f"C++ core failed: {msg.removeprefix('error: ')}")
    return res.stdout


@lru_cache(maxsize=1)
def defaults() -> dict:
    """Default settings, as defined by the C++ core (the single source of names, defaults and types)."""
    return json.loads(_call(["defaults"]))


def list_images(dataset: str) -> list[dict]:
    """[{"view", "relpath", "path"}] in the order the core lists them."""
    rows = []
    for line in _call(["list", "--dataset", dataset]).splitlines():
        view, rel, path = line.split("\t")
        rows.append({"view": view, "relpath": rel, "path": path})
    return rows


@dataclass
class EngineResult:
    out_dir: Path                         # everything the C++ core wrote
    settings_doc: dict                    # its settings.json (settings + software)
    summary: dict                         # its summary.json
    hist: dict                            # its histogram.json
    gray: np.ndarray                      # the processed gray image
    labels: dict = field(default_factory=dict)       # method -> int16 label map (-1 = uncertain)
    boundary: dict = field(default_factory=dict)     # method -> bool, certain boundaries (the wireframe)
    uncertain: dict = field(default_factory=dict)    # method -> bool, edges of uncertainty bands
    wall_s: float = 0.0

    @property
    def software(self) -> dict:
        return self.settings_doc.get("software", {})


def run(settings: dict, work_dir: Path) -> EngineResult:
    """Run one experiment in the C++ core; outputs go to work_dir/cpp."""
    import time
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    sf = work_dir / "settings_in.json"
    sf.write_text(json.dumps({"settings": settings}))
    out = work_dir / "cpp"
    t0 = time.perf_counter()
    _call(["run", "--settings", str(sf), "--out", str(out)])
    wall = time.perf_counter() - t0

    def png(name: str) -> np.ndarray:
        p = out / f"{name}.png"
        if not p.exists():
            raise EngineError(f"C++ core did not write {p.name}")
        return np.asarray(Image.open(p))

    r = EngineResult(out_dir=out, settings_doc=json.loads((out / "settings.json").read_text()),
                     summary=json.loads((out / "summary.json").read_text()),
                     hist=json.loads((out / "histogram.json").read_text()), gray=png("original"), wall_s=wall)
    for m in METHODS:
        r.labels[m] = png(f"labels_{m}").astype(np.int16) - 1
        r.boundary[m] = png(f"boundary_mask_{m}") > 0
        r.uncertain[m] = png(f"uncertain_boundary_mask_{m}") > 0
    return r
