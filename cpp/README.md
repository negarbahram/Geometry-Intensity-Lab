# Geometry Intensity Lab — C++ core

The Lab's processing engine: a C++17 / OpenCV port of the reviewed Python processing core (commit `a79e332`), which it
replaces. The Lab's interface and command line (`intensity_lab/engine.py`) run this CLI for every experiment; no Python
is needed to run it on its own. Original porting plan and tolerances: `PORTING_PLAN.md`.

Ported: histogram and explicit smoothing; histogram-weighted GMM fitting and the K = 1…8 comparison (BIC/AIC);
Ashman's D separation and the `hierarchical` / `transitive` / `none` merge rules; unmerged component and merged group
assignments (with the optional minimum posterior); histogram-minimum intervals; region masks and small-region cleanup;
certain boundaries and uncertainty-band boundaries kept separate. The detector comparison, plots and web UI are in the
Python layer, which draws them from this core's outputs.

## Build

Requirements: CMake ≥ 3.16, a C++17 compiler, curl. Nothing is installed system-wide.

```bash
cd /Users/apple/Downloads/Geometry-Intensity-Lab-CPP/cpp
scripts/build_opencv.sh                      # once: OpenCV 4.11.0 (core, imgproc, imgcodecs) into third_party/, SHA-256 checked
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 8
build/intensity-core-tests                   # 35 checks
```

`-DOpenCV_DIR=<install>/lib/cmake/opencv4` uses another OpenCV 4 build instead.

## Run

```bash
build/intensity-lab-cli run --dataset product-images --image "top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp" --out out/x
build/intensity-lab-cli run --dataset none --image /path/to/image.png --set gmm_k=5 --set merge_rule=transitive --out out/y
build/intensity-lab-cli run --settings out/x/settings.json --out out/x2      # reproduce (also accepts Python settings.json)
build/intensity-lab-cli summary --dataset isaacsim-images --image "front/isaacsim-samples/rgb_0046.png"   # summary.json to stdout
build/intensity-lab-cli list --dataset isaacsim-images                      # view, relative path, full path
build/intensity-lab-cli defaults                                            # default settings (used by the interface)
```

The core defines the settings (`--set name=value`, JSON values; `defaults` prints them) with the same names, defaults
and meaning as before. `run_detector`, `compare_tolerance_px` and `histogram_log_scale` are accepted and written back
for the Python layer, but unused here. Settings files saved by the interface, by this CLI or by the earlier Python
implementation are interchangeable. A failure exits with status 1 and an `error: ...` line on stderr, which the
interface shows as it is.

Outputs in `--out`:

| File | Content |
| --- | --- |
| `settings.json` | settings + software (C++, OpenCV version, lab commit) — re-runnable |
| `summary.json` | same structure as the Python summary for the ported parts (image, histogram, gmm, minima, methods) plus `implementation: "c++"`; `gmm.fit.best_start` says which EM start won |
| `histogram.json` | raw and smoothed histogram, component curves and posteriors (selected K and every K of the sweep), component / group / minima LUTs, the colour palette — the data behind the interface's plots |
| `original.png` | the gray image processed (after optional pre-smoothing) |
| `mask_<m>.png`, `boundaries_<m>.png`, `labels_<m>.png` | as in Python, for `m` = `gmm_components`, `gmm`, `minima`; labels are stored as label + 1 (0 = uncertain) |
| `boundary_mask_<m>.png`, `uncertain_boundary_mask_<m>.png` | the certain wireframe and the uncertainty-band edges as 0/255 masks |

Conventions are unchanged: gray values 0–255 (8-bit gray as stored; colour → BT.601 luma in double precision, rounded
half-to-even like `numpy.rint`); pixel (x, y) with the origin at the top-left; a label change between a pixel and its
right or lower neighbour marks that pixel; label −1 = uncertain.

## Parity with the earlier Python implementation (validation record)

Before the Python processing was removed, a harness (`cpp/parity/compare.py` at commit `cfe9933`, removed afterwards
with the Python processing it compared against) ran both implementations on the same image and the same settings file
and compared every stage. 62 cases: the six synthetic scenes and ten product / Isaac Sim images (every view group), with
the default settings and with one EM start; the synthetic scenes and four real images also with transitive merging,
minimum posterior 0.8, and pre-smoothing σ 1 px plus cleanup of regions < 50 px. Full table: `parity/results.md`.

**Result: 62 / 62 within tolerance.**

| | cases | result |
| --- | ---: | --- |
| gray image, raw histogram | 62 | identical (0 differing pixels) |
| smoothed histogram | 62 | max relative difference 6.3e-16 |
| GMM from the same start (one-start variants) | 46 | means/σ within 1e-11, weights 1e-13, log-likelihood 2e-15 relative, **identical EM iteration counts**; every K = 1…8 of the sweep within 4e-15 |
| separation matrix, merged groups, component / group / minima LUTs | 46 | identical |
| minima candidates, kept minima, thresholds, removal reasons | 62 | identical |
| label maps, certain and uncertain boundary masks, group statistics | 46 | identical, including 645 357 uncertainty-band edge pixels and 15 614 small regions removed by cleanup |
| default settings (5 EM starts) | 16 | 3 identical, 10 same optimum, 3 different optimum (below) |

Speed (same machine, default settings, median per image): synthetic 0.20 s vs 1.23 s, product photographs 0.47 s vs
1.40 s, Isaac Sim 0.75 s vs 1.63 s (C++ CLI including process start, decoding and writing every output, vs the Python
core in-process without plots or saving).

## Remaining differences

1. **Random EM starts (by design).** Start 1 (quantile initialisation) is identical. Starts 2…n use `std::mt19937_64`
   instead of NumPy's PCG64 `Generator.choice`, so with `gmm_n_init > 1` the two implementations try different
   starting points. Over the 16 default-settings cases:
   * 3 picked the same start: identical results.
   * 10 picked different starts that reached the **same optimum**: log-likelihood within 9e-8 relative, parameters within
     0.03 gray levels (EM stops at a relative change of 1e-8 along different paths, e.g. 753 vs 115 iterations).
     Groups, LUTs, labels and boundaries are identical in 9; in one synthetic scene (small_bright_spot) two gray values
     change component, so 3 616 pixels of the *unmerged component* map differ (merged groups identical).
   * 3 found **different local optima** (`parity/more_starts.txt`): product top/RHS_NG/125226_3 (Python's fit better by
     1.2e-4), Isaac rgb_0046 (Python's better by 6.3e-4) and Isaac rgb_0137 (C++'s better by 2.6e-3). Downstream outputs
     then differ substantially (e.g. on rgb_0046 Python's merged groups have 21 112 boundary pixels, C++'s collapse to
     one group with none). With more starts the first two converge to the same fit (20 and 50 starts). On rgb_0137 the
     C++ starts keep finding better maxima (50 starts: LL −19 524 980 vs Python's −19 622 720); Python scores the C++
     parameters at the same likelihood (2e-16) and its EM restarted from them stays there, so it is a genuine maximum
     the Python starts did not reach, not a porting error.
   This is the same initialisation sensitivity documented for the Python lab (5 starts are too few on some images); it
   is not a numerical difference between the implementations. For bit-for-bit comparable runs use `gmm_n_init = 1`.
2. **Ties in small-region cleanup.** Small regions are refilled from the nearest certain pixel; scipy and the C++ exact
   distance transform may choose different pixels when two sources of different labels are exactly equidistant. In the
   ten cleanup cases this never changed a pixel; it remains possible in principle.
3. **Last-bit floating-point differences** (summation order in smoothing, logsumexp and EM sums) are at the 1e-16–1e-11
   level. They could in principle flip a strict comparison between two nearly equal smoothed-histogram values or a
   posterior exactly at the minimum-posterior threshold; this did not occur in any case.
4. **Outside the core**: detector comparison, matplotlib figures (drawn from `histogram.json` and `summary.json`) and
   the web UI live in the Python layer, which adds `vs_detector`, `gmm_vs_minima_boundaries`, detector and engine fields
   to the saved `summary.json`.
5. **Other small differences**: PNG files are written by OpenCV rather than Pillow, so file bytes differ while pixels are
   identical. Palette images report mode `RGB` (OpenCV) where Pillow reports `P`. Separation values in `summary.json`
   are rounded to 3 decimals as `nearbyint(v·1000)/1000`, while Python's `round` rounds the exact decimal value, so the
   last digit can differ in rare half-way cases (not observed).

## Layout

```
cpp/src/        json, sha256, histogram, imageio, gmm, minima, regions, boundaries, experiment (Settings -> Result -> save)
cpp/cli/        intensity-lab-cli
cpp/tests/      C++ unit tests (synthetic scenes read from examples/synthetic/*/input.png)
cpp/parity/     results.md, more_starts.txt: the parity record (the harness is in Git history, commit cfe9933)
cpp/scripts/    build_opencv.sh
cpp/third_party/, cpp/build/   (git-ignored) OpenCV build and the CMake build
```
