"""Saved example outputs and an aggregate over every distinct image of both datasets.

  .venv/bin/python scripts/make_examples.py examples     # selected images -> examples/<dataset>/<name>/{default,cleanup}/
  .venv/bin/python scripts/make_examples.py aggregate    # all distinct images, numbers only -> examples/aggregate.{csv,md}

Processing runs in the C++ core (intensity_lab.engine); the detector comparison as in the interface.
"default" = the core's default settings. "cleanup" = the same plus spatial pre-smoothing sigma 1 px and removal of regions
under 50 px, to show how much of the boundary count is pixel-level fragmentation.
"""
from __future__ import annotations

import csv
import hashlib
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intensity_lab import engine, experiment  # noqa: E402

OUT = ROOT / "examples"
SELECTED = [
    ("product-images", "top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp", True),
    ("product-images", "top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp", False),
    ("product-images", "bottom/Good Parts/Good Parts10-8(2)/Pic_2026_10_08_115202_10.bmp", True),
    ("product-images", "bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp", False),
    ("product-images", "front/RHS_NG/RHS_NG-10-6(2)/Pic_2026_10_06_154528_2.bmp", False),
    ("product-images", "rear/Good Parts/Good Parts 10-6(1)/Pic_2026_10_06_125715_14.bmp", False),
    ("isaacsim-images", "top/isaacsim-samples/rgb_0143.png", True),
    ("isaacsim-images", "top/isaacsim-samples/rgb_0317.png", False),
    ("isaacsim-images", "front/isaacsim-samples/rgb_0046.png", True),
    ("isaacsim-images", "front/isaacsim-samples/rgb_0137.png", False),
]
VARIANTS = {"default": {}, "cleanup": {"presmooth_sigma_px": 1.0, "min_region_area_px": 50}}


def name_of(dataset, rel):
    parts = rel.split("/")
    return f"{parts[0]}_{Path(parts[-1]).stem.replace(' ', '_').replace('(', '').replace(')', '')}"


def row(dataset, rel, variant, r):
    s = experiment.summary(r)
    out = {"dataset": dataset, "image": rel, "view": rel.split("/")[0], "variant": variant,
           "width": s["image"]["width"], "height": s["image"]["height"],
           "detector_lines": s["detector"]["lines"] if s["detector"] else None,
           "detector_circles": s["detector"]["circles"] if s["detector"] else None,
           "detector_resized": s["detector"]["resized_for_detection"] if s["detector"] else None,
           "gmm_groups": s["methods"]["gmm"]["groups"], "minima_groups": s["methods"]["minima"]["groups"]}
    for m in ("gmm", "minima"):
        sm = s["methods"][m]
        out[f"{m}_boundary_share"] = sm["boundary_share_of_image"]
        out[f"{m}_step_median"] = sm["boundary_step_median"]
        v = sm["vs_detector"] or {}
        out[f"{m}_detector_matched"] = v.get("reference_matched")
        out[f"{m}_near_detector"] = v.get("candidate_matched")
    return out


def examples():
    for dataset, rel, with_cleanup in SELECTED:
        for variant, over in VARIANTS.items():
            if variant != "default" and not with_cleanup:
                continue
            r = experiment.run({"dataset": dataset, "image": rel, **over})
            experiment.save(r, OUT / dataset / name_of(dataset, rel) / variant)
            print(dataset, rel, variant, "saved")


def distinct_images():
    seen = set()
    for dataset in engine.DATASETS:
        for it in engine.list_images(dataset):
            h = hashlib.sha256(Path(it["path"]).read_bytes()).hexdigest()
            if h not in seen:                    # camera folders reuse the same files
                seen.add(h)
                yield dataset, it["relpath"]


def aggregate():
    rows = []
    for dataset, rel in distinct_images():
        for variant, over in VARIANTS.items():
            r = experiment.run({"dataset": dataset, "image": rel, **over})
            rows.append(row(dataset, rel, variant, r))
        print(len(rows) // 2, dataset, rel, flush=True)
    with open(OUT / "aggregate.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def med(rs, k):
        v = [x[k] for x in rs if x[k] is not None]
        return statistics.median(v) if v else None

    lines = ["Medians over distinct images (camera folders that reuse the same file are counted once).",
             "detector matched = share of rasterised detector edge pixels with a region boundary within 3 px;",
             "near detector = share of region boundary pixels within 3 px of a detector edge.", "",
             "| dataset | group | variant | images | groups GMM / minima | boundary share of image GMM / minima "
             "| detector matched GMM / minima | near detector GMM / minima |", "| --- | --- | --- | ---: | --- | --- | --- | --- |"]
    groups = {}
    for x in rows:
        key = (x["dataset"], f"{x['width']}x{x['height']}", x["variant"])
        groups.setdefault(key, []).append(x)
    for (ds, size, var), rs in sorted(groups.items()):
        p = lambda k: "—" if med(rs, k) is None else f"{100 * med(rs, k):.1f} %"  # noqa: E731
        lines.append(f"| {ds} | {size} | {var} | {len(rs)} | {med(rs, 'gmm_groups'):g} / {med(rs, 'minima_groups'):g} "
                     f"| {p('gmm_boundary_share')} / {p('minima_boundary_share')} "
                     f"| {p('gmm_detector_matched')} / {p('minima_detector_matched')} "
                     f"| {p('gmm_near_detector')} / {p('minima_near_detector')} |")
    (OUT / "aggregate.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    {"examples": examples, "aggregate": aggregate}[sys.argv[1]]()
