# C++ port of the Geometry Intensity Lab core — plan

Baseline: the reviewed Python implementation at commit `a79e332` (`intensity_lab/`), which stays in this repository
unchanged as the reference. The port lives in `cpp/`, builds without Python, and is validated against the Python code by a
comparison harness that runs both.

## Scope

Ported (same settings, same 0–255 scale, same pixel grid and label meaning):

| Python | C++ | Notes |
| --- | --- | --- |
| `imageio.load`, `to_gray`, `presmooth`, `list_images`, `resolve` | `imageio.{hpp,cpp}` | decode with OpenCV; gray conversion in double precision (not `cv::cvtColor`, which is fixed-point) |
| `histogram.histogram`, `smooth` | `histogram.{hpp,cpp}` | 256 bins, Gaussian kernel radius ⌈4σ⌉, zero padding |
| `gmm.*` (EM, sweep, BIC/AIC, Ashman's D, merge rules, `group_lut`, `component_lut`) | `gmm.{hpp,cpp}` | identical algorithm and constants |
| `minima.*` | `minima.{hpp,cpp}` | identical removal order and tie rules |
| `regions.*` (LUT, small-region cleanup, overlay, stats, `lut_ranges`) | `regions.{hpp,cpp}` | OpenCV connected components; own exact nearest-source distance transform |
| `boundaries.*` (certain / uncertainty-band masks, steps, wireframe image) | `boundaries.{hpp,cpp}` | |
| `experiment.Settings`, `run`, `summary`, `save` (ported parts) | `experiment.{hpp,cpp}`, `cli/main.cpp` | |

Not ported (outside the requested core): the detector wrapper and detector comparison, matplotlib figures, the web UI.
The CLI writes the histogram, smoothed histogram, component curves and LUTs as JSON instead of plots.

## Where exact parity is impossible, and what is done instead

1. **Random EM starts.** Python draws starts 2…n from NumPy's PCG64 `Generator.choice`; reproducing that stream is not
   worthwhile. Start 1 (quantile initialisation) is deterministic and identical. C++ uses `std::mt19937_64` seeded with
   `gmm_seed` and the same sampling rule (weighted, without replacement unless fewer distinct values than K).
   *Validation*: with `gmm_n_init = 1` the fits must agree within the tolerances below; with the default 5 starts the
   selected fits are compared by log-likelihood, and any case where the two pick a different optimum is listed.
2. **Floating-point summation order** (logsumexp, dot products, convolution). Results differ in the last bits, which
   can shift the EM stopping iteration by one and flip strict comparisons between nearly equal smoothed-histogram values.
3. **Nearest-source ties in small-region cleanup.** scipy's `distance_transform_edt(return_indices=True)` breaks ties
   between equidistant source pixels in its own way; the C++ exact transform (Felzenszwalb–Huttenlocher, separable)
   breaks them differently. Only pixels with two equidistant sources of different labels can differ.

## Tolerances (per case)

| Quantity | Tolerance |
| --- | --- |
| histogram counts, gray image | identical |
| smoothed histogram | max abs diff ≤ 1e-9 × max count |
| GMM (same start): means, sigmas | ≤ 0.01 gray levels |
| GMM weights | ≤ 1e-4 |
| log-likelihood | relative ≤ 1e-8 |
| EM iterations | ±2 (reported) |
| separation matrix | ≤ 1e-3 |
| merged groups, LUTs (component, group, minima) | identical; any gray value whose label differs must have a near-tie (posterior gap < 1e-6) |
| minima candidates, kept minima, thresholds | identical |
| label maps, certain and uncertain boundary masks | identical when LUTs are identical; with cleanup, differing pixels ≤ 0.01 % and only at equidistant ties |
| group statistics | counts identical; mean/std ≤ 1e-6 |

## Validation

* `cpp/tests/test_core.cpp`: C++ unit tests mirroring the Python ones (histogram, EM on synthetic data, Ashman's D, merge
  rules incl. chaining, non-contiguous ranges, minima plateaus, boundaries, uncertain bands, cleanup never touching −1).
* `cpp/parity/compare.py`: runs the Python reference in-process and the C++ CLI on the same files and settings, and
  compares everything in the table above. Cases: the six synthetic scenes (`examples/synthetic/*/input.png`) and the ten
  selected product / Isaac Sim images, each with the default settings, `gmm_n_init = 1`, and variants exercising
  transitive / no merging, minimum posterior (uncertain bands), pre-smoothing and small-region cleanup. Results go to
  `cpp/parity/results.{json,md}`; differences are investigated and written up in `cpp/README.md`.
