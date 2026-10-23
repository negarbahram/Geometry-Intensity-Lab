"""Read-only access to the replay datasets and conversion to 0-255 grayscale."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

DATASET_ROOT = Path("/Users/apple/Downloads/Geometry-Replay-Datasets")
DATASETS = {
    "product-images": DATASET_ROOT / "product-images",
    "isaacsim-images": DATASET_ROOT / "isaacsim-images",
}
VIEWS = ("top", "bottom", "front", "rear", "left", "right")
IMAGE_SUFFIXES = {".bmp", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

# ITU-R BT.601 luma weights; identical to OpenCV's cvtColor(BGR2GRAY), which the existing detector uses.
BT601 = (0.299, 0.587, 0.114)


@dataclass
class LoadedImage:
    path: Path
    gray: np.ndarray          # uint8, 0-255
    source_mode: str          # PIL mode of the file ("L", "RGBA", ...)
    conversion: str           # how gray was obtained
    sha256: str

    @property
    def shape(self) -> tuple[int, int]:
        return self.gray.shape


def list_images(dataset: str) -> list[dict]:
    """All images of a dataset as {view, relpath} (relpath relative to the dataset root), sorted."""
    root = DATASETS[dataset]
    out = []
    for view in VIEWS:
        for p in sorted((root / view).rglob("*")):
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not p.name.startswith("."):
                out.append({"view": view, "relpath": str(p.relative_to(root))})
    return out


def resolve(dataset: str | None, relpath: str) -> Path:
    """Path of an image; `dataset=None` means `relpath` is already a full path (synthetic or external files)."""
    if dataset is None:
        return Path(relpath)
    root = DATASETS[dataset].resolve()
    p = (root / relpath).resolve()
    if root not in p.parents:
        raise ValueError(f"{relpath!r} is outside dataset {dataset!r}")
    return p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_gray(arr: np.ndarray, mode: str) -> tuple[np.ndarray, str]:
    """uint8 grayscale on the 0-255 scale. Colour uses BT.601 weights in float, then rounds to the nearest integer."""
    if arr.ndim == 2:
        if arr.dtype != np.uint8:
            raise ValueError(f"unsupported gray dtype {arr.dtype}")
        return arr.copy(), f"stored as 8-bit gray ({mode})"
    rgb = arr[..., :3].astype(np.float64)
    note = "BT.601 luma 0.299R+0.587G+0.114B, rounded"
    if arr.shape[-1] == 4:
        a = arr[..., 3]
        note += "; alpha ignored" + (" (fully opaque)" if a.min() == 255 else f" (NOT opaque: min alpha {a.min()})")
    g = rgb @ np.array(BT601)
    return np.clip(np.rint(g), 0, 255).astype(np.uint8), note


def load(path: Path) -> LoadedImage:
    with Image.open(path) as im:
        mode = im.mode
        if mode in ("L", "RGB", "RGBA"):
            arr = np.asarray(im)
        elif mode == "P" or mode == "LA":
            arr = np.asarray(im.convert("RGBA"))
        else:
            raise ValueError(f"unsupported image mode {mode}")
    gray, note = to_gray(arr, mode)
    return LoadedImage(path=path, gray=gray, source_mode=mode, conversion=note, sha256=sha256_file(path))


def presmooth(gray: np.ndarray, sigma_px: float) -> np.ndarray:
    """Optional spatial Gaussian smoothing (sigma in pixels), rounded back to integers 0-255. sigma 0 = unchanged."""
    if sigma_px <= 0:
        return gray
    s = ndimage.gaussian_filter(gray.astype(np.float64), sigma_px, mode="nearest")
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)
