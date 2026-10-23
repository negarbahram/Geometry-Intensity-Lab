# Results: histogram grouping, region masks and region boundaries vs the existing detector

Everything below comes from `examples/` and can be regenerated with the scripts in the README. There is no ground truth
for the real images, so numbers on them describe *agreement with the detector* and *how much boundary is produced*,
not accuracy. Accuracy is measured only on synthetic scenes.

## 1. Synthetic scenes (known regions)

`examples/synthetic/results.md`; tolerance 2 px. Recall = share of true boundary pixels found, precision = share of
predicted boundary pixels on a true boundary. "K=4" uses the default settings.

| scene | GMM K=4 (default) | GMM K=4, transitive merge | histogram minima | existing detector |
| --- | --- | --- | --- | --- |
| three_levels (50/130/210, noise 6) | 3 groups · R 1.00 · P 0.96 | same | 3 · R 1.00 · P 1.00 | R 0.67 · P 1.00 (disc missed) |
| close_levels (120 vs 128 touching) | 3 of 4 · R 0.87 · P 1.00 | same | 3 of 4 · R 0.87 · P 1.00 | R 0.76 · P 1.00 |
| small_bright_spot (0.4 % of pixels) | 2 of 3 (spot not a group) · R 1.00 · P 0.99 | same | 4 of 3 · R 1.00 · P 1.00 | R 0.90 · P 1.00 |
| blurred_edges (σ 2 px) | 3 · R 0.95 · **P 0.64** | same | 3 · R 1.00 · P 1.00 | R 0.67 · P 1.00 |
| illumination_ramp (one region, ramp 40→130) | 4 of 2 · R 1.00 · **P 0.07** | same | 3 of 2 · R 1.00 · **P 0.15** | R 1.00 · P 1.00 |
| noise_free (anti-aliased only) | 3 · R 1.00 · P 1.00 | **2 of 3 · R 0.34** | 6 of 3 · R 1.00 · P 1.00 | R 0.67 · P 1.00 |

What this shows:

* Both methods recover well-separated levels exactly, and region boundaries then land on the true edges (≤ 2 px).
* **Neither method can separate levels closer than about 2σ of the noise** (120 vs 128 at σ 6). With K = 4 the GMM did
  not even place two components there; it put one between them and spent the fourth on edge pixels. That is the
  maximum-likelihood answer, not a bug.
* **Small modes**: the GMM missed a bright spot holding 0.4 % of the pixels (EM preferred a broad component); the minima
  method found it, plus one extra interval from the anti-aliased rim.
* **Blurred edges**: intermediate gray values along an edge form their own GMM component; it becomes a thin extra band
  with a second boundary next to the real one (precision 0.64). The minima method was not affected here because the
  valley stayed deep.
* **Illumination gradients** are the main failure of both: a single surface with a ramp is cut into iso-intensity bands
  (precision 0.07 / 0.15). Intensity grouping has no notion of spatial continuity.
* **Overlap handling matters**: with transitive merging, one broad low-weight "edge pixel" component that overlaps two
  separated levels chains them into one group (noise_free, recall 0.34). The default hierarchical rule avoids that case
  — but see the real-image failure in §3, where it does worse.
* **The detector** is precise (every reported line is on a true edge) but reports **no circles for bright discs** in any
  scene; its circle verification expects a dark interior (`max_inner_mean = 80` in its parameters). Its recall is lower
  for that reason, not because lines are missed.

The 22 unit tests (`tests/test_core.py`) cover the same mechanisms at a smaller scale: histogram on 0–255, smoothing kept
separate, EM equal to scikit-learn's on all pixels (±0.05 gray levels), Ashman's D, both merge rules, non-contiguous gray
ranges, the σ floor on a 255 spike, minima with plateaus, exact boundaries on a label map, small-region cleanup,
comparison tolerance, and an end-to-end run with the real detector.

## 2. How the separation criterion and overlaps are handled

* **Criterion**: Ashman's D = |μ₁−μ₂| / √((σ₁²+σ₂²)/2) between components; D ≥ 2 (default) counts as separated.
* **Overlap handling (default, hierarchical)**: repeatedly merge the pair of current groups with the lowest D, replacing
  them by their moment-matched Gaussian (same weight, mean and variance), until every pair has D ≥ threshold.
  *Transitive* (option): any linked pair joins one group.
* **Assignment**: each gray value goes to the group with the highest summed posterior, so a group can own several
  non-contiguous gray ranges (seen on real images: a broad component owning both tails of a narrow one). Optional
  "minimum posterior" marks low-certainty gray values as *uncertain* instead.
* A component is a shape in the gray-value distribution. Per-group statistics in every output count the **connected
  regions** of each group: on real images a group is typically tens to hundreds of separate regions, never "one object".

## 3. Real images

### Aggregate over every distinct image

Medians over distinct images (camera folders that reuse the same file are counted once).
detector matched = share of rasterised detector edge pixels with a region boundary within 3 px;
near detector = share of region boundary pixels within 3 px of a detector edge.

| dataset | group | variant | images | groups GMM / minima | boundary share of image GMM / minima | detector matched GMM / minima | near detector GMM / minima |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| isaacsim-images | 2592x1942 | cleanup | 22 | 2 / 1 | 0.8 % / 0.0 % | 6.1 % / 0.0 % | 0.2 % / 49.0 % |
| isaacsim-images | 2592x1942 | default | 22 | 2 / 1.5 | 0.8 % / 0.4 % | 14.9 % / 0.0 % | 0.4 % / 42.9 % |
| product-images | 1000x550 | cleanup | 10 | 3 / 4.5 | 1.0 % / 1.2 % | 42.5 % / 63.6 % | 14.1 % / 16.4 % |
| product-images | 1000x550 | default | 10 | 3 / 4 | 1.5 % / 1.7 % | 60.1 % / 77.4 % | 13.3 % / 14.6 % |
| product-images | 1200x670 | cleanup | 9 | 3 / 5 | 0.5 % / 2.1 % | 43.1 % / 87.6 % | 39.0 % / 26.1 % |
| product-images | 1200x670 | default | 9 | 3 / 4 | 1.6 % / 2.6 % | 52.1 % / 83.0 % | 12.5 % / 20.3 % |
| product-images | 6144x550 | cleanup | 18 | 4 / 8 | 1.0 % / 1.6 % | 65.5 % / 77.8 % | 4.5 % / 2.0 % |
| product-images | 6144x550 | default | 18 | 4 / 6 | 1.9 % / 2.3 % | 73.5 % / 82.2 % | 3.1 % / 1.8 % |
| product-images | 990x550 | cleanup | 16 | 3 / 4.5 | 1.2 % / 1.7 % | 50.2 % / 70.2 % | 13.4 % / 11.2 % |
| product-images | 990x550 | default | 16 | 3 / 4 | 2.1 % / 2.1 % | 54.0 % / 76.4 % | 10.3 % / 9.2 % |

Separated by Isaac view (default settings): overhead (15 images) — groups GMM 2 / minima 1, detector edge matched 0 % /
0 %; side (7 images) — groups 2 / 9, detector edge matched 47 % / 99 %.

Failures across all 75 distinct images (default settings), not visible in the hand-picked examples alone:

* **Minima method gives a single interval — no boundaries at all — on 11 of the 15 Isaac overhead images.** The dial
  and floor produce one dominant peak with a long tail, and the only valley is shallower than the 0.2 depth threshold.
  (The two overhead examples in the table below happen to be among the 4 that kept one threshold.)
* **GMM collapses to one group on 5 of the 16 product top-view (990x550) images** (four RHS_NG and one "Nick on the
  Flange"): a broad component (σ ≈ 50) overlaps everything at D < 2.
* Across all images the minima method matched more of the detector's edge length on 48, the GMM on 15 (the rest tie).
* The cleanup variant (pre-smoothing σ 1 px, regions < 50 px removed) reduced the boundary length by a median of 39 %
  (GMM) / 33 % (minima), and lowered agreement with the detector on most groups — it removes short true edges along with
  speckle. On some images it changed the grouping itself (one minima case gained boundary).
* The detector reported 0 circles on all 75 images.

### Selected examples (`examples/<dataset>/<image>/default/`)

| image | GMM K=4 groups | minima intervals | detector | detector edge matched GMM / minima | boundary near detector GMM / minima |
| --- | --- | --- | --- | --- | --- |
| product top Good 151035_21 | 3 | 4 | 11 lines | 0.76 / 0.73 | 0.12 / 0.11 |
| product top RHS_NG 125226_3 | **1 (no boundaries)** | 3 | 8 lines | **0.00** / 0.69 | — / 0.17 |
| product bottom Good 115202_10 | 3 | 4 | 11 lines | 0.41 / 0.45 | 0.09 / 0.13 |
| product bottom Rust-1 113300_3 | 4 | 5 | 24 lines | 0.79 / 0.91 | 0.21 / 0.15 |
| product front RHS_NG 154528_2 | 3 | 4 | 14 lines | 0.69 / 0.83 | 0.10 / 0.08 |
| product rear Good 125715_14 (6144 px) | 4 | 7 | 5 lines | 0.65 / 0.98 | 0.03 / 0.04 |
| Isaac overhead rgb_0143 | 2 | 2 | 5 lines | 0.02 / 0.00 | 0.00 / 0.00 |
| Isaac overhead rgb_0317 | 2 | 2 | 5 lines | 0.00 / 0.00 | 0.00 / 0.00 |
| Isaac side rgb_0046 | 3 | 9 | 23 lines | 0.51 / 0.99 | 0.53 / 0.50 |
| Isaac side rgb_0137 | 2 | 9 | 21 lines | 0.46 / 0.99 | 0.41 / 0.44 |

### What the overlays show (visual review, labelled as such)

**Product photographs**

* *Found by regions, not reported by the detector* (magenta, but real boundaries by visual inspection): the outlines of
  the two through-holes on every top/bottom/front image (clipped at 255; the detector reports no circles there), the
  silhouette of the bright housing on the left, and the slot outlines.
* *Unwanted region boundaries*: speckle and short closed contours in the dark textured areas (right-hand side of top/
  front, rear background), where the gray values straddle an interval threshold; ragged contours along machining marks
  and the striped band on the front image; contours of shading bands inside the slots. This is most of the "regions
  only" length: only 3–21 % of region boundary pixels lie near a detector edge.
* *Missing from region boundaries* (cyan): edges between surfaces that fall into the same intensity group, e.g. the
  vertical step at x≈155 and the inner slot shoulders on bottom/115202_10 (only 41–45 % of detector edge length matched).
  An edge with a real but small gray step inside one group cannot appear by construction.
* Pre-smoothing (σ 1 px) plus removal of regions < 50 px cuts boundary pixels (median 33–39 % over all images) and removes most specks
  (compare `default/` and `cleanup/`), at the cost of a few short true edges.

**Isaac Sim**

* *Side views*: shading is flat, so the minima intervals reproduce 99 % of the detector's lines; they also add
  iso-intensity bands across the shaded floor and the cylinder (the ramp failure from §1). The GMM (K = 4) groups the
  many narrow peaks too coarsely and misses about half of the detector's edges.
* *Overhead dial*: both methods outline the ~100 tick marks and the hub (the detector reports neither; presumably its
  cluster rule for parallel short strokes suppresses the ticks — not verified) but **both miss the dial rim**, which the detector partly finds: plate and floor
  have nearly the same gray value. The detector's 5 lines and the region boundaries do not overlap at all.

## 4. Comparison of the two grouping methods

| | GMM (+ Ashman's D merging) | Local histogram minima |
| --- | --- | --- |
| Separated levels | exact | exact |
| Levels closer than ~2σ | not separated | not separated |
| Small modes (< 1 % of pixels) | often absorbed by a broad component | found if a valley exists |
| Edge (mixed) pixels | can form their own component → double boundaries | only if they produce a valley |
| Stability | **sensitive to K and merge rule**: 125226_3 gives 1 group at K = 4 (hierarchical), 2 (transitive), 4 at K = 5 | sensitive to smoothing σ and depth threshold; minima positions are stable |
| Choosing the count | BIC was lowest at the largest K tried (8) on 9 of 10 examples (hundreds of thousands of pixels): no usable optimum | follows the histogram's own valleys; on flat-shaded Isaac side views this means 9 intervals |
| Interpretability | components, σ and D per pair; non-contiguous gray ranges possible | contiguous thresholds, easy to read |
| Cost | ~0.3–1 s (sweep of 8 K × 5 starts) | < 1 ms |

Neither is better overall. Each has a whole-image failure mode at default settings: the GMM merges everything into one
group on 5/16 product top views, the minima method finds no valley on 11/15 Isaac overhead images. On the examples the minima method agreed with the detector more often (higher "detector
edge matched" on 7 of 10 examples, GMM on 2, one tie) mainly because it produces more groups and therefore more boundary; the share of its
boundary that is near a detector edge is no higher. The GMM had the single worst failure (a whole image as one group).

## 5. Region boundaries vs the existing detector

* They are different kinds of output: the detector reports ≤ 40 filtered straight lines and dark verified circles;
  region boundaries are every label change, closed contours, at full resolution.
* Region boundaries add real closed outlines the detector omits (bright holes, curved silhouettes, tick marks) but
  also much more clutter (texture, noise, shading bands). Without a filter on contrast, length or shape they are not
  usable as measurement landmarks directly.
* The detector finds low-contrast straight edges inside one intensity group that grouping cannot see.
* On the 6144x550 rear line-scan images the detector runs on a 1280x115 downscaled copy (its `processing_max_side`),
  then refines on the full image; region boundaries work at full resolution.

## 6. Limitations

* No ground truth for real images; "missing"/"unwanted" are judgements against the detector and by eye.
* Whole-image histograms: large uniform areas (rear background, Isaac floor) dominate both fits; no ROI support.
* Isaac colour is reduced to BT.601 gray; surfaces differing only in hue can merge.
* Clipped pixels (0 and 255) are fitted like any other value (a narrow component at 255 with the σ floor of 1).
* Boundaries are label changes at pixel resolution with a ½-pixel offset; no sub-pixel position, no contrast filter.
* The detector comparison uses a 3 px tolerance and rasterised detector geometry; detector points are not compared.
* Only default detector parameters were used. Example images were picked to cover every view group, not at random;
  the aggregate covers all distinct images.
* The environment reuses miniconda's packages because PyPI was unreachable; versions are pinned in requirements.txt.
