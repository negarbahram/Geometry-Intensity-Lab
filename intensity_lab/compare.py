"""Agreement between two 1-pixel boundary masks within a distance tolerance.

Neither mask is treated as ground truth. With `reference` = detector edges and `candidate` = region boundaries:
  * reference_matched  -- share of detector edge pixels with a region boundary within `tol` px
  * candidate_matched  -- share of region boundary pixels with a detector edge within `tol` px
The unmatched parts are "detector only" (a boundary the regions miss) and "regions only" (a boundary the detector does
not report: texture, noise, gradients, or real edges the detector filters out -- the overlay must be looked at).
On synthetic images the reference is the true boundary and the two shares are recall and precision.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def distance_to(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return np.full(mask.shape, np.inf)
    return ndimage.distance_transform_edt(~mask)


def compare(reference: np.ndarray, candidate: np.ndarray, tol: float = 3.0) -> dict:
    d_ref = distance_to(reference)
    d_cand = distance_to(candidate)
    ref_hit = reference & (d_cand <= tol)
    cand_hit = candidate & (d_ref <= tol)
    nr, nc = int(reference.sum()), int(candidate.sum())
    return {
        "tolerance_px": tol,
        "reference_px": nr, "candidate_px": nc,
        "reference_matched": float(ref_hit.sum() / nr) if nr else None,
        "candidate_matched": float(cand_hit.sum() / nc) if nc else None,
        "reference_only_px": int(nr - ref_hit.sum()), "candidate_only_px": int(nc - cand_hit.sum()),
        "_masks": {"reference_hit": ref_hit, "reference_only": reference & ~ref_hit,
                   "candidate_hit": cand_hit, "candidate_only": candidate & ~cand_hit},
    }


# Colours of the comparison overlay (RGB)
MATCHED = (60, 220, 60)
REFERENCE_ONLY = (0, 200, 255)       # detector only: missing from the region wireframe
CANDIDATE_ONLY = (255, 60, 200)      # regions only: not reported by the detector


def overlay(gray: np.ndarray, result: dict, dim: float = 0.4, thicken: int = 1) -> np.ndarray:
    m = result["_masks"]
    rgb = np.repeat((gray.astype(np.float64) * dim)[..., None], 3, axis=2).astype(np.uint8)

    def draw(mask, color, it):
        if it > 0:
            mask = ndimage.binary_dilation(mask, iterations=it)
        rgb[mask] = color

    draw(m["candidate_only"], CANDIDATE_ONLY, 0)
    draw(m["candidate_hit"], MATCHED, 0)
    draw(m["reference_only"], REFERENCE_ONLY, thicken)   # detector lines thicker so they stay visible
    draw(m["reference_hit"], MATCHED, thicken)
    return rgb


def public(result: dict) -> dict:
    return {k: v for k, v in result.items() if not k.startswith("_")}
