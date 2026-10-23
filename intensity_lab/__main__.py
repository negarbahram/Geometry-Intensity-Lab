"""Command line: run one experiment (C++ core + detector comparison) and save it.

  python -m intensity_lab run --settings outputs/<run>/settings.json --out outputs/<new>
  python -m intensity_lab run --dataset product-images --image "top/.../Pic.bmp" --out outputs/x [--set gmm_k=5 ...]
"""
from __future__ import annotations

import argparse
import json
import sys

from . import engine, experiment


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
    try:
        d = experiment.load_settings(a.settings) if a.settings else experiment.make_settings()
        if a.dataset:
            d["dataset"] = None if a.dataset == "none" else a.dataset
        if a.image:
            d["image"] = a.image
        for kv in a.set:
            k, _, v = kv.partition("=")
            if k not in d:
                p.error(f"unknown setting {k}")
            try:
                d[k] = json.loads(v)
            except json.JSONDecodeError:
                d[k] = v                                 # bare word, e.g. --set merge_rule=transitive
        out = experiment.save(experiment.run(d), a.out)
    except engine.EngineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
