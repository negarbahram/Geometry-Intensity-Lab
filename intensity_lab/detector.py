"""The existing AIxAM detector (services/geometry-detect, commit 4ca9cf5), run unchanged through its own CLI.

The CLI is built from an exported copy of that commit by scripts/build_detector.sh. It accepts PNG/JPEG only, so BMP files
are converted losslessly to PNG in cache/ first (pixel-identical; the dataset files are never touched). Results are cached
by the SHA-256 of the bytes the detector saw plus the parameter overrides.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

LAB_ROOT = Path(__file__).resolve().parent.parent
CLI = LAB_ROOT / "third_party" / "geometry-detect-build" / "geometry-detect-cli"
CACHE = LAB_ROOT / "cache" / "detector"
DETECTOR_COMMIT = "4ca9cf58e9cc73f3c8bde9b64aab69b38c9f077c"
DETECTOR_SOURCE = "AIxAM services/geometry-detect (branch Geometry-Studio)"


def available() -> bool:
    return CLI.exists()


def _png_input(path: Path) -> Path:
    """The file to hand to the detector: PNG/JPEG as-is, anything else as a lossless PNG copy in the cache."""
    if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return path
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    out = CACHE / "inputs" / f"{digest}.png"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(path) as im:
            im.save(out, format="PNG")
    return out


def run(path: Path, overrides: dict | None = None) -> dict:
    """Detection JSON (aixam.geometry.detection.v1) for an image file, with optional `--set name=value` overrides."""
    if not available():
        raise RuntimeError(f"detector CLI not built: run scripts/build_detector.sh ({CLI})")
    src = _png_input(Path(path))
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    key = digest + ("-" + hashlib.sha1(json.dumps(overrides, sort_keys=True).encode()).hexdigest()[:10]
                    if overrides else "")
    cached = CACHE / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    args = [str(CLI)]
    for k, v in sorted((overrides or {}).items()):
        args += ["--set", f"{k}={v}"]
    args.append(str(src))
    res = subprocess.run(args, capture_output=True, text=True, timeout=300)
    if res.returncode != 0:
        raise RuntimeError(f"detector failed: {res.stderr.strip()}")
    doc = json.loads(res.stdout.strip().splitlines()[-1])
    doc["_lab"] = {"detector_input": str(src), "cli": str(CLI), "commit": DETECTOR_COMMIT, "overrides": overrides or {}}
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(doc))
    return doc


def run_array(gray: np.ndarray, name: str) -> dict:
    """Run the detector on an in-memory gray image (synthetic tests): saved as PNG in the cache first."""
    out = CACHE / "arrays" / f"{name}-{hashlib.sha256(gray.tobytes()).hexdigest()[:16]}.png"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(gray).save(out)
    return run(out)


def _draw_polyline(mask: np.ndarray, pts, step: float = 0.25) -> None:
    h, w = mask.shape
    pts = np.asarray(pts, dtype=np.float64)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(2, int(np.ceil(np.hypot(x1 - x0, y1 - y0) / step)) + 1)
        xs = np.floor(np.linspace(x0, x1, n)).astype(int)        # outer-corner convention: pixel index = floor
        ys = np.floor(np.linspace(y0, y1, n)).astype(int)
        ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
        mask[ys[ok], xs[ok]] = True


def rasterize(doc: dict, shape: tuple[int, int]) -> np.ndarray:
    """1-pixel mask of every detector edge (lines via their polyline, circles via centre and radius)."""
    mask = np.zeros(shape, dtype=bool)
    for e in doc.get("edges", []):
        if e.get("type") == "circle" and "radius_px" in e:
            cx, cy = e["center"] if isinstance(e["center"], list) else (e["center"]["x"], e["center"]["y"])
            r = e["radius_px"]
            t = np.linspace(0, 2 * np.pi, max(64, int(2 * np.pi * r / 0.25)))
            _draw_polyline(mask, np.c_[cx + r * np.cos(t), cy + r * np.sin(t)])
        elif e.get("polyline"):
            _draw_polyline(mask, e["polyline"])
    return mask


def summary(doc: dict) -> dict:
    edges = doc.get("edges", [])
    return {
        "status": doc.get("status"), "points": len(doc.get("points", [])),
        "lines": sum(e.get("type") == "line" for e in edges), "circles": sum(e.get("type") == "circle" for e in edges),
        "line_length_px": float(sum(e.get("length_px", 0) for e in edges if e.get("type") == "line")),
        "resized_for_detection": doc.get("transforms", {}).get("resized_for_detection"),
        "processing_size": doc.get("transforms", {}).get("processing_size"),
        "version": doc.get("detector", {}).get("version"), "commit": DETECTOR_COMMIT,
    }
