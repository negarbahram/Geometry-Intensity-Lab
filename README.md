# Geometry Intensity Lab

Standalone prototype for testing histogram-based intensity grouping, intensity region masks and region-boundary
"wireframes" on the Geometry replay images, compared with the existing AIxAM detector. Not integrated with AIxAM; the
AIxAM repository and the image datasets are only read.

All intensity processing runs in the **C++ core** (`cpp/`, `intensity-lab-cli`): gray conversion, histogram and
smoothing, GMM fitting and the K comparison, separation and merging, histogram minima, masks, small-region cleanup and
valid / uncertainty-band boundaries. The Python layer (`intensity_lab/`, `app/`) starts the core, draws its results,
runs the existing detector and compares boundaries with it. There is no Python fallback: if the core is missing or
fails, the interface and the command line say so.

* `PLAN.md`: the plan, methods, ambiguities and assumptions.
* `REPORT.md`: results, the comparison of the two grouping methods and the existing detector, and limitations.
* `cpp/README.md`: the C++ core, its CLI, and the parity record against the earlier Python implementation.
* `examples/`: saved outputs (synthetic scenes, selected product and Isaac Sim images, an aggregate over all images).

## Setup (once)

```bash
cd /Users/apple/Downloads/Geometry-Intensity-Lab

# 1. C++ core: OpenCV 4.11 (skipped if cpp/third_party/opencv-install exists), then the core and its tests
cpp/scripts/build_opencv.sh
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j 8
cpp/build/intensity-core-tests

# 2. Python layer (server, plots, detector comparison): numpy, scipy, matplotlib, pillow
/Users/apple/miniconda3/bin/python -m venv --system-site-packages .venv

# 3. Existing detector, for the comparison (built from AIxAM commit 4ca9cf5 without modifying AIxAM)
scripts/build_detector.sh
```

PyPI was not reachable from this machine, so the virtual environment reuses miniconda's packages; with network access
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` works too. `build_opencv.sh` downloads the official
OpenCV 4.11.0 archive (SHA-256 checked) and builds core, imgproc and imgcodecs into `cpp/third_party/` (a few minutes,
nothing system-wide); `-DOpenCV_DIR=<install>/lib/cmake/opencv4` uses another OpenCV 4 build. Without the detector,
everything except the detector comparison still works. `INTENSITY_LAB_CLI=<path>` points the Python layer at another
build of the core.

## Run the interface

```bash
.venv/bin/python app/server.py
```

Then open http://127.0.0.1:8765. The header shows the processing engine ("Processing: C++ core (intensity-lab-cli) ·
OpenCV 4.11.0"); it turns red and Run is disabled when the core is not built. Choose a dataset, camera folder and
image, adjust the settings, and press **Run experiment**. The tabs show:

1. **Image and histogram**: the grayscale image, the raw histogram (gray bars) and the explicitly smoothed one (black line).
2. **GMM components**: fitted components, the Ashman's D separation matrix, the resulting groups and their gray ranges,
   and BIC/AIC and fits for K = 1…8.
3. **Histogram-minimum intervals**: smoothed histogram, kept and rejected minima, and the intervals.
4. **Region masks**: coloured overlays for the GMM components (no merging), the GMM groups (after merging) and the
   minima intervals, with per-group statistics including the number of connected regions.
5. **Boundaries vs detector**: region boundaries for all three labellings (edges of "uncertain" bands in yellow, kept
   out of the wireframe), the detector's edges, and overlays of matched (green), detector-only (cyan) and regions-only
   (magenta) boundaries.

Click an image to open it at full resolution. **Save settings and outputs** writes `outputs/<time>_<image>[_label]/`
with `settings.json` (settings as the core read them, plus engine, OpenCV and commit), `summary.json`, the core's own
images, label maps, boundary masks and `histogram.json`, the plots, and the detector JSON and comparison images. To
reproduce a run, pick it under **Load settings from a saved run** and press Run, or use the command line:

```bash
.venv/bin/python -m intensity_lab run --settings outputs/<run>/settings.json --out outputs/<new>
.venv/bin/python -m intensity_lab run --dataset product-images --image "top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp" --set gmm_k=5 --out outputs/k5
cpp/build/intensity-lab-cli run --settings outputs/<run>/settings.json --out outputs/<new>      # processing only, no detector
```

Settings files from earlier versions of the Lab load unchanged (same names and meaning). A run takes about 0.3–1 s in
the core; the detector adds 0.2–0.9 s (cached per image).

## Checks and evaluation

```bash
cpp/build/intensity-core-tests                       # C++ unit tests (synthetic scenes from examples/synthetic/)
.venv/bin/python scripts/make_examples.py examples   # examples/<dataset>/: saved outputs of selected images
.venv/bin/python scripts/make_examples.py aggregate  # examples/aggregate.{csv,md}: every distinct image
```

The results in `REPORT.md` and `examples/` were produced with the earlier Python implementation (commit `a79e332`). The
C++ core reproduces it to numerical precision when both use the same EM start; with the default 5 random starts the
starts differ, which can select a different local optimum on some images (`cpp/README.md`).

## Layout

```
cpp/             C++ core: src/ (histogram, gmm, minima, regions, boundaries, experiment, ...), cli/, tests/, scripts/
intensity_lab/   Python layer: engine (runs the core), experiment (settings -> core -> detector comparison -> save),
                 plots (figures from the core's data), detector (runs the existing detector CLI), compare
app/             server.py (standard-library HTTP server, 127.0.0.1 only) and static/index.html
scripts/         build_detector.sh, make_examples.py
cache/           detector inputs and cached detector JSON — safe to delete
```
