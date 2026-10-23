# Results: histogram grouping, region masks and region boundaries vs the existing detector

> These results were produced with the Lab's earlier Python processing implementation (commit `a79e332`). The Lab now
> runs the C++ core (`cpp/`), which reproduces those computations to numerical precision from the same EM start; with
> the default 5 random EM starts it can settle on a different local optimum on some images (see `cpp/README.md`).
> Scripts named below that no longer exist (`evaluate_synthetic.py`, `check_initialisation.py`) are in Git history.

Everything below comes from `examples/` and can be regenerated with the scripts in the README.

How to read the numbers:
* **Accuracy** (recall/precision against known regions) exists only for the synthetic scenes.
* On real images there is no ground truth. "Detector edge matched" and "near detector" measure **agreement with the
  existing detector**, which is itself a heuristic, not a reference. "Missing" and "unwanted" are visual judgements and
  are labelled as such.
* Every conclusion holds for the tested settings only: one noise seed per synthetic scene, the stated K, merge rule and
  number of EM starts (default 5), and default minima parameters. None of them is a general limit of the method.

## 1. Synthetic scenes (known regions)

`examples/synthetic/results.md`; tolerance 2 px, one noise seed per scene. Recall = share of true boundary pixels found,
precision = share of predicted boundary pixels on a true boundary. "Components" = the GMM fit without merging;
"groups" = after merging (default: hierarchical, D ≥ 2). Default EM starts: 5.

| scene | GMM K=4 components | GMM K=4 groups | GMM K=4 groups, transitive | GMM K=4 groups, 20 starts | histogram minima | existing detector |
| --- | --- | --- | --- | --- | --- | --- |
| three_levels (50/130/210, noise σ 6) | 4 · R 1.00 · P 0.91 | 3 · R 1.00 · P 0.96 | same | same | 3 · R 1.00 · P 1.00 | R 0.67 · P 1.00 |
| close_levels (120 vs 128 touching, σ 6) | 4 (not the pair) · R 0.87 · P 0.99 | 3 of 4 · R 0.87 · P 1.00 | same | same | 3 of 4 · R 0.87 · P 1.00 | R 0.76 · P 1.00 |
| small_bright_spot (0.4 % of pixels) | 4 · R 1.00 · **P 0.05** | 2 of 3 · R 1.00 · P 0.99 | same | **4 · R 1.00 · P 0.97** | 4 of 3 · R 1.00 · P 1.00 | R 0.90 · P 1.00 |
| blurred_edges (σ 2 px) | 4 · R 1.00 · P 0.61 | 3 · R 0.95 · **P 0.64** | same | same | 3 · R 1.00 · P 1.00 | R 0.67 · P 1.00 |
| illumination_ramp (one region, ramp 40→130) | 4 of 2 · R 1.00 · **P 0.07** | same | same | same | 3 of 2 · R 1.00 · **P 0.15** | R 1.00 · P 1.00 |
| noise_free (anti-aliased only) | 4 · R 1.00 · P 1.00 | 3 · R 1.00 · P 1.00 | **2 of 3 · R 0.34** | same as 5 starts | 6 of 3 · R 1.00 · P 1.00 | R 0.67 · P 1.00 |

To check whether the GMM outcomes are optimisation artefacts, EM was also started at the true parameters
(`scripts/check_initialisation.py` → `examples/synthetic/initialisation_check.txt`):

| scene, K | default fit (5 starts) | started at true parameters | 20 / 100 random starts |
| --- | --- | --- | --- |
| close_levels, K=4 | LL −483 437.9, means 60 / 123.6 / 139.4 (σ 32) / 199.9 | converges to the same solution (ΔLL 0.0) | same solution |
| small_bright_spot, K=3 | LL −433 969.8, broad component instead of the spot | LL −439 429.0 (spot kept) — **lower** than the default fit | same as default |
| small_bright_spot, K=4 | LL −433 966.5, no spot component | — | **LL −433 150.8, spot at 225 kept** |
| blurred_edges, K=3 | LL −481 815.2, 50 / 129.5 / 163 (σ 53) | **LL −480 982.8, 50 / 127 / 208.5** | same as true start |

What these tests establish, and what they do not:

* **Well-separated levels** (three_levels, noise_free): both methods recovered them and the region boundaries lay on the
  true edges within 2 px. Tested at noise σ 6 and 0 only.
* **The 120 vs 128 pair (Δ = 8 at noise σ 6, Ashman's D ≈ 1.3)** was not separated by either method in this one scene.
  For the GMM with K = 4 the evidence is that EM started at the true parameters converges to the same solution and 100
  random starts find nothing better: within these tests it is the best K = 4 fit found, with one component between the
  two levels and one broad component for edge pixels. That is not a proof of a global maximum, and no other separations,
  noise levels or region sizes were tested, so no general "≈ 2σ" limit is claimed. For the minima method it only shows that
  the smoothed histogram (σ 2) had no valley there.
* **The small bright spot** is lost by the default GMM partly through **initialisation**: at K = 4, 20 starts find a fit
  with higher likelihood that keeps the spot, and it survives merging (4 groups, precision 0.97). At K = 3 the broad
  solution genuinely has the higher likelihood. The minima method found the spot with default settings (plus one extra
  interval from the anti-aliased rim).
* **Blurred edges**: with K = 3 the default fit is a local optimum (the true-parameter start reaches a higher likelihood
  with all three levels). With K = 4 the extra component models intermediate edge values and produces a second boundary
  beside the real one (precision 0.61–0.64). The minima valley stayed deep enough in this scene.
* **Illumination ramp**: in the one ramp scene, both methods cut the single surface into iso-intensity bands (precision
  0.07 / 0.15). Intensity grouping uses no spatial information, so this is expected wherever a ramp spans a threshold.
* **Merge rule**: in noise_free the unmerged components are correct (recall 1.00); transitive merging chains two levels
  through a broad edge-pixel component (recall 0.34); hierarchical merging does not. On real images hierarchical merging
  fails differently (§3).
* **The detector** placed every reported line on a true edge (precision 1.00 in every scene) and reported **no circle**
  in any scene. Its circle check requires the inside to be at least 35 gray levels darker than the ring and at most 80
  (`pipeline.cpp:538`, `min_inside_contrast`, `max_inner_mean`), so bright discs cannot pass. Its lower recall is
  consistent with that: e.g. in three_levels the rectangle is 66 % of the true boundary length and recall is 0.665.

The 27 unit tests (`tests/test_core.py`) cover: histogram on 0–255, smoothing kept separate, EM equal to scikit-learn's
on all pixels (±0.05 gray levels), Ashman's D, all merge rules, non-contiguous gray ranges, the σ floor on a 255 spike,
minima with plateaus, exact boundaries on a label map, uncertain-band boundaries kept out of the wireframe, small-region
cleanup that never touches uncertain pixels, unmerged components surviving a merge collapse, comparison tolerance, and an
end-to-end run with the real detector.

## 2. How the separation criterion and overlaps are handled

* **Criterion**: Ashman's D = |μ₁−μ₂| / √((σ₁²+σ₂²)/2) between components; D ≥ 2 (default) counts as separated.
* **Overlap handling (default, hierarchical)**: repeatedly merge the pair of current groups with the lowest D, replacing
  them by their moment-matched Gaussian (same weight, mean and variance), until every pair has D ≥ threshold.
  *Transitive* (option): any linked pair joins one group.
* **Assignment**: each gray value goes to the group with the highest summed posterior, so a group can own several
  non-contiguous gray ranges (seen on real images: a broad component owning both tails of a narrow one).
* **Fit vs merge are shown separately**: every run also labels pixels by their most probable component without merging
  ("GMM components"), with its own mask, boundaries and detector comparison, so a missing boundary can be traced to the
  fit or to the merge. The merge rule and threshold are experimental choices of this prototype, not requirements.
* **Uncertain values**: an optional minimum posterior labels gray values whose best posterior is lower as *uncertain*
  (−1). A label change with −1 on one side is the edge of an uncertainty band, not a boundary between two groups: it is
  drawn in yellow, counted separately and excluded from the wireframe, the gray-step statistics and every comparison.
  Small-region cleanup never relabels uncertain pixels and never fills from them. (Before this was fixed, such edges were
  drawn as ordinary wireframe edges: on product top/RHS_NG/125226_3 with default settings and minimum posterior 0.8,
  24 324 of the 25 360 unmerged-component boundary pixels are uncertainty-band edges.) The default is off (0), so the default results are unaffected.
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
* **GMM groups collapse to one group on 5 of the 16 product top-view (990x550) images** (four RHS_NG and one "Nick on
  the Flange"). `examples/gmm_collapse_check.txt` traces the cause: in all 5 the unmerged fit has 4 components and
  12 000–89 000 boundary pixels, so **the collapse happens in the merge**: a broad component (σ ≈ 43–56) is within D < 2
  of its neighbours and hierarchical merging absorbs everything (transitive merging leaves 2–3 groups). In 3 of the 5,
  20 EM starts also find a higher-likelihood fit (with a component at the clipped value 255) that merges to 3–4 groups,
  so the 5-start fit is a local optimum as well. Both factors contribute.
* Across all images the minima boundaries agreed with more of the detector's edge length on 48, the GMM groups on 15
  (the rest tie). This is agreement with the detector, not accuracy.
* The cleanup variant (pre-smoothing σ 1 px, regions < 50 px removed) reduced the boundary length by a median of 39 %
  (GMM) / 33 % (minima), and lowered agreement with the detector on most groups — it removes short true edges along with
  speckle (visual check). On some images it changed the grouping itself (one minima case gained boundary).
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
* *Probably unwanted region boundaries* (visual judgement): speckle and short closed contours in the dark textured areas
  (right-hand side of top/front, rear background), where the gray values straddle an interval threshold; ragged contours
  along machining marks and the striped band on the front image; contours of shading bands inside the slots. Only 3–21 %
  of region boundary pixels lie near a detector edge; how much of the rest is clutter versus real edges the detector
  omits was not measured.
* *Detector-only edges* (cyan) that look real: edges between surfaces that fall into the same intensity group, e.g. the
  vertical step at x≈155 and the inner slot shoulders on bottom/115202_10 (41–45 % of detector edge length matched).
  An edge whose gray step lies inside one group cannot appear by construction.
* Pre-smoothing (σ 1 px) plus removal of regions < 50 px cuts boundary pixels (median 33–39 % over all images) and removes most specks
  (compare `default/` and `cleanup/`), at the cost of a few short true edges.

**Isaac Sim**

* *Side views*: the minima boundaries lie within 3 px of 99 % of the detector's line length; they also add iso-intensity
  bands across the shaded floor and the cylinder (like the ramp scene in §1). The GMM groups (K = 4) cover about half of
  the detector's line length; the histogram has many narrow peaks and four components group them coarsely.
* *Overhead dial*: both methods outline the ~100 tick marks and the hub (the detector reports neither; presumably its
  cluster rule for parallel short strokes suppresses the ticks — not verified) but **both miss the dial rim**, which the detector partly finds: plate and floor
  have nearly the same gray value. The detector's 5 lines and the region boundaries do not overlap at all.

## 4. Comparison of the two grouping methods

| | GMM (+ Ashman's D merging) | Local histogram minima |
| --- | --- | --- |
| Well-separated levels (tested σ 0 and 6) | recovered | recovered |
| One close pair (Δ 8, σ 6) | not separated (best fit found at K = 4) | not separated (no valley at σ 2) |
| Small mode (0.4 % of pixels, one scene) | lost with 5 starts, kept with 20 starts at K = 4 | found |
| Edge (mixed) pixels | can form their own component → double boundaries | only if they produce a valley |
| Stability | **sensitive to K, EM starts and merge rule**: 125226_3 gives 1 group at K = 4 (hierarchical), 2 (transitive), 4 with K = 5 or with 20 starts | depends on smoothing σ and depth threshold (sensitivity not swept) |
| Choosing the count | BIC was lowest at the largest K tried (8) on 9 of 10 examples (hundreds of thousands of pixels): no usable optimum | follows the histogram's own valleys; on flat-shaded Isaac side views this means 9 intervals |
| Interpretability | components, σ and D per pair; non-contiguous gray ranges possible | contiguous thresholds, easy to read |
| Cost | ~0.3–1 s (sweep of 8 K × 5 starts) | < 1 ms |

Neither is better overall in these tests. Each has a whole-image failure at default settings: GMM merging collapses
5/16 product top views to one group, and the minima method finds no valley on 11/15 Isaac overhead images. The minima
boundaries agreed with the detector more often (7 of 10 examples, 48 of 75 images). That is agreement, not accuracy,
and it is consistent with the minima method producing more groups and more boundary: the share of its boundary near a
detector edge is no higher than the GMM's.

## 5. Region boundaries vs the existing detector

* They are different kinds of output: the detector reports ≤ 40 filtered straight lines and dark verified circles;
  region boundaries are every label change, closed contours, at full resolution.
* By visual inspection, region boundaries add closed outlines the detector omits (bright holes, curved silhouettes,
  tick marks) but also much more clutter (texture, noise, shading bands). Without a filter on contrast, length or shape they are not
  usable as measurement landmarks directly.
* The detector reports low-contrast straight edges that fall inside one intensity group, which grouping cannot
  produce by construction.
* On the 6144x550 rear line-scan images the detector runs on a 1280x115 downscaled copy (its `processing_max_side`),
  then refines on the full image; region boundaries work at full resolution.

## 6. Limitations

* No ground truth for real images; "missing"/"unwanted" are judgements against the detector and by eye, and detector
  agreement is not accuracy.
* Synthetic conclusions rest on one noise seed per scene and a handful of level spacings; no parameter sweeps.
* The default of 5 EM starts is too few for some images (§1, §3); 20 starts changed the result on 3 of 5 collapsed images.
  The default was not changed, so the aggregate stays comparable; raise "EM starts" in the interface when checking a
  GMM failure.
* The aggregate table was not re-run after adding the unmerged-component view; the GMM and minima outputs it reports are
  unchanged (verified on a regenerated example), and the component view was checked only on the 5 collapsed images.
* Whole-image histograms: large uniform areas (rear background, Isaac floor) dominate both fits; no ROI support.
* Isaac colour is reduced to BT.601 gray; surfaces differing only in hue can merge.
* Clipped pixels (0 and 255) are fitted like any other value (a narrow component at 255 with the σ floor of 1).
* Boundaries are label changes at pixel resolution with a ½-pixel offset; no sub-pixel position, no contrast filter.
* The detector comparison uses a 3 px tolerance and rasterised detector geometry; detector points are not compared.
* Only default detector parameters were used. Example images were picked to cover every view group, not at random;
  the aggregate covers all distinct images.
* The environment reuses miniconda's packages because PyPI was unreachable; versions are pinned in requirements.txt.
