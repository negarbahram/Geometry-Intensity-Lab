"""Are GMM outcomes on the synthetic scenes optimisation artefacts? Compares the default fit (5 starts) with EM started at
the true parameters and with 20 / 100 random starts. Writes examples/synthetic/initialisation_check.txt.

  .venv/bin/python scripts/check_initialisation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intensity_lab import gmm, histogram, synthetic  # noqa: E402
from intensity_lab.histogram import LEVELS  # noqa: E402

CASES = [("close_levels", 6, (4,)), ("small_bright_spot", 5, (3, 4)), ("blurred_edges", 6, (3,))]


def main():
    lines = ["LL = log-likelihood (higher is better). True-parameter start: true levels, the scene's noise sigma, true weights.", ""]
    for name, noise, ks in CASES:
        s = synthetic.by_name(name)
        c = histogram.histogram(s.gray)
        for k in ks:
            f = gmm.fit_gmm(c, k)
            lines.append(f"{name} K={k}, 5 starts (default): LL {f.log_likelihood:.1f}  means {f.means.round(1).tolist()}"
                         f"  sd {f.sigmas.round(1).tolist()}")
            if k == len(s.levels):
                lv = np.array(s.levels, float)
                w = np.bincount(s.labels.ravel(), minlength=len(lv)) / s.labels.size
                nz = c > 0
                m, sd, _, ll, _, _ = gmm._em(LEVELS[nz], c[nz], lv.copy(), np.full(len(lv), float(noise)), w, 1.0,
                                             5000, 1e-10)
                o = np.argsort(m)
                lines.append(f"    started at true parameters: LL {ll:.1f}  means {m[o].round(1).tolist()}"
                             f"  sd {sd[o].round(1).tolist()}  (difference {ll - f.log_likelihood:+.1f})")
            for n in (20, 100):
                g = gmm.fit_gmm(c, k, n_init=n)
                lines.append(f"    {n} starts: LL {g.log_likelihood:.1f}  means {g.means.round(1).tolist()}")
        lines.append("")
    out = ROOT / "examples" / "synthetic" / "initialisation_check.txt"
    out.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
