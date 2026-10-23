"""Parity of the C++ port against the reviewed Python reference (intensity_lab at a79e332).

Runs the Python core in-process and the C++ CLI on the same image and the same settings file, then compares every
stage. Writes cpp/parity/results.json and cpp/parity/results.md.

  .venv/bin/python cpp/parity/compare.py [--quick]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from intensity_lab import experiment, gmm  # noqa: E402

CLI = ROOT / "cpp" / "build" / "intensity-lab-cli"
OUT = ROOT / "cpp" / "parity"

# Tolerances (cpp/PORTING_PLAN.md)
TOL = {"param": 0.01, "weight": 1e-4, "ll_rel": 1e-8, "iter": 2, "sep": 1e-3, "smooth_rel": 1e-9, "stat": 1e-6,
       "cleanup_px_share": 1e-4,
       # Same optimum reached from different starts (default 5 starts; random starts differ by design): EM stops at a
       # relative log-likelihood change of 1e-8, so parameters can differ by more than numerical noise.
       "path_param": 0.05, "path_ll_rel": 1e-7,
       # numerical-noise agreement (observed ~1e-13 when the same start wins)
       "noise_param": 1e-6, "noise_ll_rel": 1e-12}

SYNTHETIC = ["three_levels", "close_levels", "small_bright_spot", "blurred_edges", "illumination_ramp", "noise_free"]
REAL = [
    ("product-images", "top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp"),
    ("product-images", "top/RHS_NG/RHS_10-15/Pic_2026_10_15_125226_3.bmp"),
    ("product-images", "bottom/Good Parts/Good Parts10-8(2)/Pic_2026_10_08_115202_10.bmp"),
    ("product-images", "bottom/Rust-1/Rust-1 10-8(2)/Pic_2026_10_08_113300_3.bmp"),
    ("product-images", "front/RHS_NG/RHS_NG-10-6(2)/Pic_2026_10_06_154528_2.bmp"),
    ("product-images", "rear/Good Parts/Good Parts 10-6(1)/Pic_2026_10_06_125715_14.bmp"),
    ("isaacsim-images", "top/isaacsim-samples/rgb_0143.png"),
    ("isaacsim-images", "top/isaacsim-samples/rgb_0317.png"),
    ("isaacsim-images", "front/isaacsim-samples/rgb_0046.png"),
    ("isaacsim-images", "front/isaacsim-samples/rgb_0137.png"),
]
VARIANTS = {
    "default": {},
    "one_start": {"gmm_n_init": 1},
    "transitive": {"gmm_n_init": 1, "merge_rule": "transitive"},
    "uncertain": {"gmm_n_init": 1, "min_posterior": 0.8},
    "cleanup": {"gmm_n_init": 1, "presmooth_sigma_px": 1.0, "min_region_area_px": 50},
}


def cases(quick: bool):
    for s in SYNTHETIC:
        for v in VARIANTS:
            yield f"synthetic/{s}", None, str(ROOT / "examples" / "synthetic" / s / "input.png"), v
    for i, (ds, rel) in enumerate(REAL):
        names = list(VARIANTS) if (i in (1, 3, 6, 8) and not quick) else ["default", "one_start"]
        for v in names:
            yield f"{ds}/{rel}", ds, rel, v


def run_cpp(settings: experiment.Settings, tmp: Path):
    sf = tmp / "settings.json"
    sf.write_text(json.dumps({"settings": asdict(settings)}))
    out = tmp / "out"
    t0 = time.perf_counter()
    res = subprocess.run([str(CLI), "run", "--settings", str(sf), "--out", str(out)], capture_output=True, text=True)
    wall = time.perf_counter() - t0
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    summ = json.loads((out / "summary.json").read_text())
    hist = json.loads((out / "histogram.json").read_text())
    png = lambda n: np.asarray(Image.open(out / f"{n}.png"))  # noqa: E731
    return summ, hist, png, wall


def gap_of(fit: gmm.GMMFit, groups, v: int) -> float:
    """Posterior gap between the best and second-best group at gray value v (Python side): a near-tie explains a flip."""
    post = fit.posteriors()
    g = sorted((post[grp][:, v].sum() for grp in groups), reverse=True)
    return float(g[0] - g[1]) if len(g) > 1 else 1.0


def compare_case(name, dataset, image, variant):
    s = experiment.Settings(dataset=dataset, image=image, run_detector=False, **VARIANTS[variant])
    t0 = time.perf_counter()
    py = experiment.run(s)
    py_time = time.perf_counter() - t0
    with tempfile.TemporaryDirectory() as td:
        cs, ch, png, cpp_time = run_cpp(s, Path(td))
        cpp_gray = png("original")
        labels = {m: png(f"labels_{m}").astype(np.int16) - 1 for m in ("gmm_components", "gmm", "minima")}
        bmask = {m: png(f"boundary_mask_{m}") > 0 for m in labels}
        umask = {m: png(f"uncertain_boundary_mask_{m}") > 0 for m in labels}

    r = {"case": name, "variant": variant, "settings": {k: v for k, v in VARIANTS[variant].items()},
         "python_s": round(py_time, 3), "cpp_s": round(cpp_time, 3), "issues": [], "notes": []}
    issue = r["issues"].append
    note = r["notes"].append

    # --- image and histogram
    r["gray_pixels_differing"] = int((cpp_gray != py.gray).sum())
    if r["gray_pixels_differing"]:
        issue(f"gray image differs in {r['gray_pixels_differing']} px")
    raw_c, sm_c = np.array(ch["raw"]), np.array(ch["smoothed"])
    if not np.array_equal(raw_c, py.counts):
        issue("raw histogram differs")
    r["smoothed_max_rel_diff"] = float(np.abs(sm_c - py.smoothed).max() / max(py.counts.max(), 1))
    if r["smoothed_max_rel_diff"] > TOL["smooth_rel"]:
        issue(f"smoothed histogram differs by {r['smoothed_max_rel_diff']:.2e} (relative)")

    # --- GMM fit (selected K) and the K sweep
    cf = cs["gmm"]["fit"]
    pf = py.fit
    dm = float(np.max(np.abs(np.array(cf["means"]) - pf.means)))
    ds_ = float(np.max(np.abs(np.array(cf["sigmas"]) - pf.sigmas)))
    dw = float(np.max(np.abs(np.array(cf["weights"]) - pf.weights)))
    dll = abs(cf["log_likelihood"] - pf.log_likelihood) / abs(pf.log_likelihood)
    r["fit"] = {"max_mean_diff": dm, "max_sigma_diff": ds_, "max_weight_diff": dw, "ll_rel_diff": dll,
                "iter_python": pf.n_iter, "iter_cpp": cf["n_iter"], "converged": [pf.converged, cf["converged"]],
                "ll_python": pf.log_likelihood, "ll_cpp": cf["log_likelihood"], "cpp_best_start": cf["best_start"]}
    same_fit = dm <= TOL["param"] and ds_ <= TOL["param"] and dw <= TOL["weight"] and dll <= TOL["ll_rel"]
    same_optimum = dm <= TOL["path_param"] and ds_ <= TOL["path_param"] and dll <= TOL["path_ll_rel"]
    # tier: "identical" (same start, numerical noise only), "same optimum" (different starts, same maximum, EM stopped
    # at different points), "different optimum" (the random starts led to different local maxima).
    # With one start both sides start identically, so the plan's tolerances apply. With several starts Python's winning
    # start is unknown; only agreement at numerical-noise level shows that the same start won.
    noise = dm <= TOL["noise_param"] and ds_ <= TOL["noise_param"] and dll <= TOL["noise_ll_rel"]
    if s.gmm_n_init <= 1:
        r["fit_tier"] = "identical" if same_fit else "different optimum"
    elif noise:
        r["fit_tier"] = "identical"
    elif same_optimum:
        r["fit_tier"] = "same optimum"
    else:
        r["fit_tier"] = "different optimum"
    strict = r["fit_tier"] == "identical"
    r["same_fit"] = strict
    if r["fit_tier"] != "identical":
        better = "C++" if cf["log_likelihood"] > pf.log_likelihood else "Python"
        msg = (f"{r['fit_tier']}: K={pf.k} fit differs (means {dm:.3g}, sigmas {ds_:.3g}, LL rel {dll:.2e}, "
               f"EM iterations {pf.n_iter}/{cf['n_iter']}); higher likelihood: {better}; C++ winning start "
               f"{cf['best_start']}")
        (note if s.gmm_n_init > 1 else issue)(msg)
    same_fit = strict
    sweep_rows = []
    for pfk, cfk in zip(py.sweep, cs["gmm"]["sweep"]):
        rel = abs(cfk["log_likelihood"] - pfk.log_likelihood) / abs(pfk.log_likelihood)
        sweep_rows.append({"k": pfk.k, "ll_rel_diff": rel, "cpp_better": cfk["log_likelihood"] > pfk.log_likelihood,
                           "groups": [len(gmm.merge_groups(pfk, s.separation_threshold, s.merge_rule)),
                                      cfk["groups_at_threshold"]]})
    r["sweep"] = sweep_rows
    r["sweep_k_differing"] = [x["k"] for x in sweep_rows if x["ll_rel_diff"] > TOL["ll_rel"]]
    if r["sweep_k_differing"]:
        (note if s.gmm_n_init > 1 else issue)(f"K sweep: different fits at K = {r['sweep_k_differing']}")

    # --- separation, groups, LUTs (only meaningful to require when the fits agree)
    sep_c = np.array([[np.inf if v is None else v for v in row] for row in cs["gmm"]["separation_ashman_d"]])
    sep_p = np.round(gmm.separation_matrix(pf), 3)
    finite = np.isfinite(sep_p)
    r["separation_max_diff"] = float(np.abs(sep_c[finite] - sep_p[finite]).max()) if finite.any() else 0.0
    r["groups_equal"] = cs["gmm"]["groups"] == [list(map(int, g)) for g in py.grouping.groups]
    lut_c = {"gmm_components": np.array(ch["component_lut"]), "gmm": np.array(ch["group_lut"]),
             "minima": np.array(ch["minima_lut"])}
    lut_p = {"gmm_components": py.components.lut, "gmm": py.grouping.lut, "minima": py.minima.lut}
    r["lut_values_differing"] = {m: int((lut_c[m] != lut_p[m]).sum()) for m in lut_c}
    if not same_fit:
        note(f"downstream of the {r['fit_tier']}: separation max diff {r['separation_max_diff']:.3g}, groups "
             f"{'equal' if r['groups_equal'] else 'differ'}, LUT values differing {r['lut_values_differing']}")
    if same_fit:
        if r["separation_max_diff"] > TOL["sep"]:
            issue(f"separation matrix differs by {r['separation_max_diff']:.3g}")
        if not r["groups_equal"]:
            issue("merged groups differ")
        for m, grouping in (("gmm_components", py.components), ("gmm", py.grouping)):
            for v in np.flatnonzero(lut_c[m] != lut_p[m]):
                gap = gap_of(pf, grouping.groups, int(v))
                near_threshold = (grouping.min_posterior > 0 and
                                  abs(grouping.certainty[v] - grouping.min_posterior) < 1e-6)
                if gap >= 1e-6 and not near_threshold:
                    issue(f"{m} LUT differs at gray {v} (posterior gap {gap:.2e})")
                else:
                    note(f"{m} LUT differs at gray {v}: near-tie (gap {gap:.1e})")

    # --- minima
    mc, mp = cs["minima"], py.minima
    r["minima_equal"] = {"candidates": mc["candidates"] == [float(x) for x in mp.candidates],
                         "kept": mc["kept"] == [float(x) for x in mp.kept],
                         "thresholds": mc["thresholds"] == mp.thresholds,
                         "removed_reasons": [x["reason"] for x in mc["removed"]] == [x["reason"] for x in mp.removed]}
    for k, ok in r["minima_equal"].items():
        if not ok:
            issue(f"minima {k} differ")
    if r["lut_values_differing"]["minima"]:
        issue("minima LUT differs")

    # --- label maps, boundaries, statistics
    r["methods"] = {}
    for m in ("gmm_components", "gmm", "minima"):
        pm = py.methods[m]
        lab_diff = int((labels[m] != pm.labels).sum())
        b_diff = int((bmask[m] != pm.boundary).sum())
        u_diff = int((umask[m] != pm.uncertain_boundary).sum())
        sp = {x["group"]: x for x in pm.stats}
        sc = {x["group"]: x for x in cs["methods"][m]["group_stats"]}
        stats_ok = sp.keys() == sc.keys() and all(
            sp[g][k] == sc[g][k] for g in sp for k in ("pixels", "gray_min", "gray_max", "connected_regions",
                                                       "largest_region_px", "regions_under_50px")) and all(
            abs(sp[g][k] - sc[g][k]) <= TOL["stat"] * max(1, abs(sp[g][k])) for g in sp
            for k in ("share", "gray_mean", "gray_std"))
        removed = [pm.regions_removed, cs["methods"][m]["regions_removed_by_cleanup"]]
        r["methods"][m] = {"label_px_differing": lab_diff, "boundary_px_differing": b_diff,
                           "uncertain_boundary_px_differing": u_diff, "stats_equal": stats_ok,
                           "regions_removed": removed, "boundary_px": [int(pm.boundary.sum()),
                                                                       cs["methods"][m]["boundary_px"]],
                           "uncertain_boundary_px": [int(pm.uncertain_boundary.sum()),
                                                     cs["methods"][m]["uncertain_boundary_px"]]}
        lut_same = r["lut_values_differing"][m] == 0
        if lut_same and (same_fit or m == "minima"):
            share = lab_diff / pm.labels.size
            cleanup = s.min_region_area_px > 1
            if lab_diff and not (cleanup and share <= TOL["cleanup_px_share"] and removed[0] == removed[1]):
                issue(f"{m}: {lab_diff} label px differ with identical LUTs")
            elif lab_diff:
                note(f"{m}: {lab_diff} px ({share:.2e}) differ after cleanup (equidistant fill sources)")
            if (b_diff or u_diff) and not cleanup:
                issue(f"{m}: boundary masks differ ({b_diff} certain, {u_diff} uncertain px)")
            if not stats_ok and not lab_diff:
                issue(f"{m}: group statistics differ")
    r["status"] = "pass" if not r["issues"] else "FAIL"
    if r["status"] == "pass" and r["fit_tier"] != "identical":
        r["status"] = f"pass ({r['fit_tier']})"
    return r


def write_report(rows):
    (OUT / "results.json").write_text(json.dumps(rows, indent=1, default=float))
    lines = ["# Parity results: C++ port vs Python reference (a79e332)", "",
             "Status `pass` = every comparison within the tolerances of cpp/PORTING_PLAN.md. "
             "With the default 5 EM starts the random starts differ by design (NumPy PCG64 vs std::mt19937_64): "
             "`pass (same optimum)` = a different start won but reached the same maximum (LL within 1e-7, parameters "
             "within 0.05); `pass (different optimum)` = the starts found different local maxima. In both cases the "
             "downstream outputs are reported, not required to match.", "",
             "| case | variant | status | gray px diff | fit Δmean / Δσ | LL rel diff | EM iter Py/C++ | LUT diffs comp/grp/min "
             "| label px diff comp/grp/min | boundary px diff comp/grp/min | Python s | C++ s |",
             "| --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | ---: | ---: |"]
    for r in rows:
        f, m, l_ = r["fit"], r["methods"], r["lut_values_differing"]
        trio = lambda key: " / ".join(str(m[x][key]) for x in ("gmm_components", "gmm", "minima"))  # noqa: E731
        lines.append(
            f"| {r['case'].replace('product-images/', 'product/').replace('isaacsim-images/', 'isaac/')} | "
            f"{r['variant']} | {r['status']} | {r['gray_pixels_differing']} | "
            f"{f['max_mean_diff']:.2g} / {f['max_sigma_diff']:.2g} | {f['ll_rel_diff']:.1e} | "
            f"{f['iter_python']}/{f['iter_cpp']} | {l_['gmm_components']}/{l_['gmm']}/{l_['minima']} | "
            f"{trio('label_px_differing')} | {trio('boundary_px_differing')} | {r['python_s']} | {r['cpp_s']} |")
    issues = [(r["case"], r["variant"], i) for r in rows for i in r["issues"]]
    notes = [(r["case"], r["variant"], i) for r in rows for i in r["notes"]]
    lines += ["", f"## Issues ({len(issues)})", ""] + [f"* {c} [{v}]: {i}" for c, v, i in issues]
    lines += ["", f"## Notes ({len(notes)})", ""] + [f"* {c} [{v}]: {i}" for c, v, i in notes]
    py_t = sum(r["python_s"] for r in rows)
    cpp_t = sum(r["cpp_s"] for r in rows)
    lines += ["", f"Total time over {len(rows)} cases: Python {py_t:.1f} s (in-process, no detector), "
                  f"C++ {cpp_t:.1f} s (CLI including process start, PNG and JSON writing)."]
    (OUT / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-(len(issues) + len(notes) + 8):]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer variants on the real images")
    a = ap.parse_args()
    if not CLI.exists():
        sys.exit(f"build the CLI first: {CLI}")
    rows = []
    for name, ds, img, v in cases(a.quick):
        r = compare_case(name, ds, img, v)
        print(f"{r['status']:28s} {v:11s} {name}", flush=True)
        rows.append(r)
    write_report(rows)
    return 0 if all(r["status"].startswith("pass") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
