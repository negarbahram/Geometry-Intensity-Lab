"""Synthetic scenes with known regions: grouping accuracy and boundary recall/precision for both methods and the
existing detector. Writes examples/synthetic/<scene>/ (full experiment outputs) and examples/synthetic/results.{json,md}.

  .venv/bin/python scripts/evaluate_synthetic.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intensity_lab import boundaries, compare, detector, experiment, synthetic  # noqa: E402

OUT = ROOT / "examples" / "synthetic"
TOL = 2.0


def majority_accuracy(pred: np.ndarray, truth: np.ndarray) -> float:
    """Each predicted group is mapped to the true label it overlaps most; share of pixels then correct.
    Over-segmentation is not penalised by this number, so the group count is reported next to it."""
    correct = 0
    for g in np.unique(pred):
        t = truth[pred == g]
        correct += np.bincount(t - t.min()).max()
    return correct / truth.size


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for sc in synthetic.scenes():
        d = OUT / sc.name
        d.mkdir(exist_ok=True)
        p = d / "input.png"
        Image.fromarray(sc.gray).save(p)
        truth_b = boundaries.boundary_mask(sc.labels)
        Image.fromarray(np.where(truth_b, 255, 0).astype(np.uint8)).save(d / "true_boundaries.png")
        n_true = len(np.unique(sc.labels))
        for k_label, k, rule in (("K=true", max(n_true, 2), "hierarchical"), ("K=4 transitive", 4, "transitive"),
                                 ("K=4", 4, "hierarchical")):
            s = experiment.Settings(dataset=None, image=str(p), gmm_k=k, gmm_sweep_max_k=6, merge_rule=rule)
            r = experiment.run(s)
            if k_label == "K=4":
                experiment.save(r, d / "experiment_default")
            for name, m in r.methods.items():
                if name == "minima" and k_label != "K=4":
                    continue                                  # minima does not depend on K
                c = compare.compare(truth_b, m.boundary, TOL)
                rows.append({"scene": sc.name, "method": "GMM " + k_label if name == "gmm" else "histogram minima",
                             "groups": len(m.stats), "true_regions": n_true,
                             "label_accuracy": majority_accuracy(m.labels, sc.labels),
                             "boundary_recall": c["reference_matched"], "boundary_precision": c["candidate_matched"]})
        det = r.detector_doc
        if det is not None:
            dm = detector.rasterize(det, sc.gray.shape)
            c = compare.compare(truth_b, dm, TOL)
            rows.append({"scene": sc.name, "method": "existing detector", "groups": None, "true_regions": n_true,
                         "label_accuracy": None, "boundary_recall": c["reference_matched"],
                         "boundary_precision": c["candidate_matched"],
                         "detector": detector.summary(det)})
        print(sc.name, "done")
    (OUT / "results.json").write_text(json.dumps(rows, indent=1, default=float))
    fmt = lambda x: "—" if x is None else f"{x:.3f}"  # noqa: E731
    lines = [f"Boundary recall/precision: share of true / predicted boundary pixels within {TOL:g} px of the other.",
             "Label accuracy: each predicted group mapped to its majority true region (does not penalise extra groups).",
             "", "| scene | method | groups / true | label accuracy | boundary recall | boundary precision |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for r in rows:
        g = "—" if r["groups"] is None else f"{r['groups']} / {r['true_regions']}"
        lines.append(f"| {r['scene']} | {r['method']} | {g} | {fmt(r['label_accuracy'])} | {fmt(r['boundary_recall'])} "
                     f"| {fmt(r['boundary_precision'])} |")
    (OUT / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
