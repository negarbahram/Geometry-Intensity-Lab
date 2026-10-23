# Geometry Intensity Lab

Standalone prototype for testing histogram-based intensity grouping, intensity region masks and region-boundary
"wireframes" on the Geometry replay images, compared with the existing AIxAM detector. Not integrated with AIxAM; the
AIxAM repository and the image datasets are only read.

* `PLAN.md`: the plan, methods, ambiguities and assumptions.
* `REPORT.md`: results, the comparison of the two grouping methods and the existing detector, and limitations.
* `examples/`: saved outputs (synthetic scenes, selected product and Isaac Sim images, an aggregate over all images).

## Setup (once)

PyPI was not reachable from this machine, so the virtual environment reuses the packages of the existing miniconda
Python 3.12 (numpy, scipy, matplotlib, pillow, pytest). Nothing is installed into miniconda itself.

```bash
cd /Users/apple/Downloads/Geometry-Intensity-Lab
/Users/apple/miniconda3/bin/python -m venv --system-site-packages .venv
```

With network access a clean environment works too: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

The comparison needs the existing detector's command-line tool, built from AIxAM commit `4ca9cf5`
(`services/geometry-detect`) into `third_party/` with the OpenCV build that the AIxAM checkout already has:

```bash
scripts/build_detector.sh
```

The CLI built this way gives byte-identical detection JSON (apart from timing) to the binary already in the AIxAM
checkout. Without it, everything except the detector comparison still works.

## Run the interface

```bash
.venv/bin/python app/server.py
```

Then open http://127.0.0.1:8765. Choose a dataset, camera folder and image, adjust the settings, and press
**Run experiment**. The tabs show:

1. **Image and histogram**: the grayscale image, the raw histogram (gray bars) and the explicitly smoothed one (black line).
2. **GMM components**: fitted components, the Ashman's D separation matrix, the resulting groups and their gray ranges,
   and BIC/AIC and fits for K = 1…8.
3. **Histogram-minimum intervals**: smoothed histogram, kept and rejected minima, and the intervals.
4. **Region masks**: coloured overlays for both methods, with per-group statistics including the number of connected regions.
5. **Boundaries vs detector**: region boundaries for both methods, the detector's edges, and overlays of matched
   (green), detector-only (cyan, missing from the regions) and regions-only (magenta) boundaries.

Click an image to open it at full resolution. **Save settings and outputs** writes `outputs/<time>_<image>[_label]/`
with `settings.json`, `summary.json`, every image, the label maps and the detector JSON. To reproduce a run, pick it
under **Load settings from a saved run** and press Run, or use the command line:

```bash
.venv/bin/python -m intensity_lab run --settings outputs/<run>/settings.json --out outputs/<new>
.venv/bin/python -m intensity_lab run --dataset product-images --image "top/Good Parts/Good Parts10-15/Pic_2026_10_15_151035_21.bmp" --set gmm_k=5 --out outputs/k5
```

Large Isaac Sim images (2592x1942) take about 5 s per run; product images 2–4 s.

## Tests and evaluation

```bash
.venv/bin/python -m pytest                          # 22 focused checks on synthetic data (about 5 s)
.venv/bin/python scripts/evaluate_synthetic.py      # examples/synthetic/: accuracy against known regions
.venv/bin/python scripts/make_examples.py examples  # examples/<dataset>/: saved outputs of selected images
.venv/bin/python scripts/make_examples.py aggregate # examples/aggregate.{csv,md}: every distinct image (~10 min)
```

## Layout

```
intensity_lab/   processing core (numpy/scipy, no UI): imageio, histogram, gmm, minima, regions, boundaries,
                 detector (runs the existing CLI), compare, synthetic, experiment (Settings -> Result -> save), plots
app/             server.py (standard-library HTTP server, 127.0.0.1 only) and static/index.html
scripts/         build_detector.sh, evaluate_synthetic.py, make_examples.py
tests/           pytest
cache/           detector inputs (lossless PNG copies of BMPs) and cached detector JSON — safe to delete
```

For integration later, `intensity_lab.experiment.run(Settings)` is the entry point; the modules below it are pure
functions of arrays and parameters.
