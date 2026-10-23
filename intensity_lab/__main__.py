"""Command line: re-run a saved experiment, or run one image with default settings.

  python -m intensity_lab run --settings outputs/<run>/settings.json --out outputs/<new>
  python -m intensity_lab run --dataset product-images --image "top/.../Pic.bmp" --out outputs/x [--set gmm_k=5 ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, fields

from . import experiment


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="intensity_lab")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--settings")
    r.add_argument("--dataset")
    r.add_argument("--image")
    r.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    r.add_argument("--out", required=True)
    a = p.parse_args(argv)

    s = experiment.load_settings(a.settings) if a.settings else experiment.Settings()
    d = asdict(s)
    if a.dataset:
        d["dataset"] = None if a.dataset == "none" else a.dataset
    if a.image:
        d["image"] = a.image
    types = {f.name: f.type for f in fields(experiment.Settings)}
    for kv in a.set:
        k, _, v = kv.partition("=")
        if k not in types:
            p.error(f"unknown setting {k}")
        d[k] = json.loads(v) if v not in ("", None) else v
    res = experiment.run(experiment.Settings.from_dict(d))
    out = experiment.save(res, a.out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
