# Geometry Intensity Lab — implementation plan

Standalone prototype for three experiments: histogram-based intensity grouping, intensity region masks, and region-boundary
"wireframes" compared with the existing AIxAM detector. Nothing in the AIxAM repository is modified.

## What the data looks like (inspected before planning)

| Dataset | Groups | Format | Histogram character |
| --- | --- | --- | --- |
| product-images | 990x550 (top/left, 16), 1000x550 (bottom/right, 10), 1200x670 (front, 9), 6144x550 line-scan (rear, 18) | 8-bit grayscale BMP | 2–4 broad, overlapping modes; clipped spike at 255 (holes/glare); comb gaps (empty bins) in some images; rear images are ~60 % black background |
| isaacsim-images | overhead (top/bottom, 15), side (front/rear/left/right, 7) | RGBA PNG, 2592x1942, alpha always 255, not gray (R≠G≠B) | overhead: one huge background peak plus a long low tail; side: many narrow peaks from flat-shaded surfaces |

Camera folders reuse the same files (top=left, bottom=right, etc.), so the effective set is 4 product groups + 2 Isaac groups.

## Architecture

```
intensity_lab/          processing core: numpy/scipy only, no UI code, no I/O side effects except explicit save()
  imageio.py            dataset discovery, read-only loading, grayscale conversion, sha256
  histogram.py          256-bin histogram + explicit Gaussian smoothing (raw and smoothed kept separately)
  gmm.py                1-D Gaussian mixture by EM on the histogram, BIC/AIC sweep, separation (Ashman's D), grouping
  minima.py             intervals from local minima of the (smoothed) histogram, with a depth filter
  regions.py            value→group lookup table, label map, optional small-region cleanup, coloured overlays
  boundaries.py         label-change boundaries (the "wireframe")
  detector.py           runs the existing geometry-detect CLI (built from AIxAM commit 4ca9cf5), caches its JSON, rasterises it
  compare.py            boundary vs detector agreement within a pixel tolerance
  synthetic.py          synthetic images with known regions
  experiment.py         Settings → run both methods → Result; save()/load settings for reproduction
  plots.py              matplotlib figures (shared by UI and saved outputs)
app/server.py           tiny local web UI (Python standard library http.server + one HTML page)
scripts/                build_detector.sh, make_examples.py, evaluate_synthetic.py
tests/                  pytest, synthetic only
```

## Methods

1. **Grayscale**: 8-bit gray files are used as stored. RGB(A) is converted with ITU-R BT.601 weights
   (0.299 R + 0.587 G + 0.114 B, the same as OpenCV's `cvtColor`, which the detector uses) and rounded to integers 0–255.
   Optional spatial Gaussian pre-smoothing (σ in pixels, default off) is rounded back to integers 0–255.
2. **Histogram**: 256 unit bins centred on 0…255, raw counts. Smoothing is a Gaussian kernel with σ in gray levels,
   always drawn as a separate line labelled with σ; the raw histogram is never replaced.
3. **GMM**: weighted EM on the raw histogram (equivalent to EM on all pixels, since pixel values are integers). Deterministic
   quantile initialisation plus seeded restarts; σ floor (default 1 gray level) so a clipped spike (e.g. 255) does not
   collapse to zero variance. BIC/AIC computed for K = 1…10 as information, not as an automatic choice.
4. **Separation and overlap**: Ashman's D = |μ₁−μ₂| / √((σ₁²+σ₂²)/2) for every pair of components; D ≥ threshold
   (default 2.0) counts as separated. Components linked by any pair below the threshold are merged into one intensity group
   (transitive). Each gray value goes to the group with the highest summed posterior; optionally values whose best group
   posterior is below a minimum are labelled "uncertain". A group may therefore own non-contiguous intensity ranges.
5. **Histogram minima**: local minima of the smoothed histogram (linear or log(1+count) scale), plateau → its centre;
   minima are removed shallowest-first while their relative depth (min(neighbouring peaks) − value) / min(peaks) is below
   a threshold. Thresholds split 0…255 into contiguous intervals.
6. **Masks**: label map from a 256-entry lookup table; optional removal of connected regions smaller than N pixels
   (re-filled from the nearest remaining region). Per-group statistics include the number of connected regions.
7. **Boundaries**: a pixel is on a boundary when its right or lower 4-neighbour has a different label.
8. **Detector comparison**: detector line polylines and circles rasterised (1 px); distance transforms both ways;
   tolerance default 3 px. Reported: detector edge length matched by region boundaries, region boundary length near a
   detector edge, and overlays of matched / detector-only (missing from regions) / regions-only (extra) boundaries.

## Ambiguities and assumptions

* **"Correct" grouping is undefined on real images.** There is no ground truth for intensity groups or boundaries in
  either dataset. Quantitative accuracy is measured only on synthetic images; real images get descriptive statistics and
  visual review. The detector is a reference, not ground truth: "missing" and "unwanted" are stated relative to it and
  then judged visually, with the judgement labelled as such.
* **The detector and region boundaries are different kinds of output.** The detector reports at most ~40 straight lines and
  a few verified circles after filtering texture and soft edges; region boundaries are every label change. Region-only
  boundaries are expected to dominate; the comparison is asymmetric by construction.
* **Detector input**: it accepts PNG/JPEG only. BMP files are converted losslessly to PNG in `cache/` (pixel-identical,
  originals untouched). Isaac PNGs are passed as-is. Its default pipeline (version 2) and parameters are used unchanged.
* **Colour** in Isaac images is discarded by the gray conversion; two differently coloured surfaces can map to the same gray.
* **The GMM models the gray-value distribution, not objects.** Components are not assumed to be objects or connected regions;
  bright groups are not called reflections and dark groups are not called background.
* **Whole-image histogram**: no ROI. Large uniform areas (rear background, Isaac floor) dominate the fit.
* **Dependencies**: PyPI is unreachable from this machine, so the venv is layered on the existing miniconda Python 3.12
  (numpy, scipy, matplotlib, pillow, pytest). No OpenCV-Python and no web framework are needed.
