"""Focused checks on synthetic data with known answers."""
import numpy as np
import pytest

from intensity_lab import boundaries, compare, detector, gmm, histogram, imageio, minima, regions, synthetic
from intensity_lab.experiment import Settings, run


def scene(name):
    return synthetic.by_name(name)


def accuracy(pred, truth):
    """Best label agreement when predicted group i should equal true label i (both are ordered by intensity)."""
    return float((pred == truth).mean())


# --- histogram -------------------------------------------------------------------------------------------------------

def test_histogram_is_raw_counts_on_0_255():
    g = np.array([[0, 0, 255], [7, 7, 7]], dtype=np.uint8)
    h = histogram.histogram(g)
    assert h.shape == (256,) and h.sum() == 6
    assert h[0] == 2 and h[7] == 3 and h[255] == 1


def test_smoothing_is_separate_and_keeps_mass_inside_range():
    s = scene("three_levels")
    raw = histogram.histogram(s.gray)
    before = raw.copy()
    sm = histogram.smooth(raw, 3.0)
    assert np.array_equal(raw, before)                    # raw never modified
    assert not np.array_equal(sm, raw)
    assert sm.sum() == pytest.approx(raw.sum(), rel=1e-6)  # all levels far from 0/255, so no leakage
    assert np.array_equal(histogram.smooth(raw, 0), raw)


def test_gray_conversion_bt601_and_scale():
    rgb = np.zeros((1, 3, 3), dtype=np.uint8)
    rgb[0, 0] = (255, 0, 0)
    rgb[0, 1] = (0, 255, 0)
    rgb[0, 2] = (0, 0, 255)
    g, _ = imageio.to_gray(rgb, "RGB")
    assert g.dtype == np.uint8
    assert g.tolist() == [[76, 150, 29]]                  # round(0.299*255), round(0.587*255), round(0.114*255)


# --- GMM -------------------------------------------------------------------------------------------------------------

def test_gmm_recovers_three_levels():
    s = scene("three_levels")
    fit = gmm.fit_gmm(histogram.histogram(s.gray), 3)
    assert np.allclose(fit.means, s.levels, atol=1.5)
    assert np.all(fit.sigmas < 9)                         # noise 6 plus anti-aliased edge pixels
    grouping = gmm.group_lut(fit, 2.0)
    assert len(grouping.groups) == 3
    assert accuracy(regions.apply_lut(s.gray, grouping.lut), s.labels) > 0.99


def test_gmm_matches_sklearn_on_pixels():
    sk = pytest.importorskip("sklearn.mixture")
    s = scene("three_levels")
    fit = gmm.fit_gmm(histogram.histogram(s.gray), 3)
    ref = sk.GaussianMixture(3, random_state=0, reg_covar=1e-6, tol=1e-6).fit(s.gray.reshape(-1, 1).astype(float))
    o = np.argsort(ref.means_.ravel())
    assert np.allclose(fit.means, ref.means_.ravel()[o], atol=0.05)
    assert np.allclose(fit.sigmas, np.sqrt(ref.covariances_.ravel()[o]), atol=0.05)


def _fit(means, sigmas, weights=None):
    k = len(means)
    w = np.full(k, 1 / k) if weights is None else np.asarray(weights, float)
    return gmm.GMMFit(k=k, weights=w, means=np.asarray(means, float), sigmas=np.asarray(sigmas, float),
                      log_likelihood=0, n_pixels=1000, n_iter=0, converged=True, min_sigma=1)


def test_ashman_d_and_merge_rule():
    assert gmm.ashman_d(0, 1, 2, 1) == pytest.approx(2.0)
    fit = _fit([60, 120, 128, 200], [6, 6, 6, 6])
    d = gmm.separation_matrix(fit)
    assert d[1, 2] == pytest.approx(8 / 6)
    assert gmm.group_lut(fit, 2.0).groups == [[0], [1, 2], [3]]      # 120 and 128 merged
    assert len(gmm.group_lut(fit, 1.0).groups) == 4                  # lower threshold keeps them apart
    # chaining: A~B and B~C. Transitive merges all three although D(A, C) >= threshold; hierarchical merges A+B
    # first, and the wider merged group is then separated from C (D = 15 / sqrt((61 + 36) / 2) = 2.15).
    chain = _fit([100, 110, 120], [6, 6, 6])
    assert gmm.separation_matrix(chain)[0, 2] > 2.0
    assert gmm.merge_groups(chain, 2.0, "transitive") == [[0, 1, 2]]
    assert gmm.merge_groups(chain, 2.0, "hierarchical") == [[0, 1], [2]]


def test_broad_edge_component_does_not_chain_levels_hierarchically():
    # parameters EM finds on the noise-free scene with K=4: a broad low-weight component for anti-aliased edge pixels
    fit = _fit([50, 104.8, 130, 210], [1, 41.7, 1, 1], [0.797, 0.0065, 0.1447, 0.0518])
    assert gmm.merge_groups(fit, 2.0, "transitive") == [[0, 1, 2], [3]]      # 50 and 130 chained via the broad one
    assert len(gmm.merge_groups(fit, 2.0, "hierarchical")) == 3
    w, m, s = gmm.moment_match(fit, [1, 2])
    assert w == pytest.approx(0.1512) and 125 < m < 131 and s > 5


def test_close_levels_scene_is_not_separated():
    """120 vs 128 with noise sigma 6 (D = 1.33): EM does not recover the two levels as separate components (one
    component sits between them and another is spent on edge pixels), and the grouping must not split the pair."""
    s = scene("close_levels")
    fit = gmm.fit_gmm(histogram.histogram(s.gray), 4)
    lab = regions.apply_lut(s.gray, gmm.group_lut(fit, 2.0).lut)
    in1, in2 = lab[s.labels == 1], lab[s.labels == 2]
    g1 = np.bincount(in1[in1 >= 0]).argmax()
    assert np.bincount(in2[in2 >= 0]).argmax() == g1
    truth = s.labels.copy()
    truth[truth == 2] = 1
    # the broad 4th component (edge pixels) is merged with the 120/128 group and also claims the 200-disc rim
    assert (lab[truth == 0] != g1).mean() > 0.99 and (lab[truth == 3] != g1).mean() > 0.95


def test_broad_component_can_own_non_contiguous_ranges():
    # a narrow component inside a broad one: the broad one wins on both tails
    fit = _fit([100, 101], [3, 40])
    g = gmm.group_lut(fit, threshold=0.0)                  # threshold 0: never merge
    ranges = regions.lut_ranges(g.lut)
    assert [r["group"] for r in ranges] == [1, 0, 1]


def test_min_posterior_marks_uncertain_values():
    fit = _fit([60, 120, 128, 200], [6, 6, 6, 6])
    g = gmm.group_lut(fit, 0.0, min_posterior=0.9)         # no merging, so the 120/128 overlap is uncertain
    assert (g.lut[118:132] == -1).any()
    assert g.lut[60] >= 0 and g.lut[200] >= 0


def test_sigma_floor_on_a_spike():
    counts = np.zeros(256)
    counts[255] = 1000
    counts[100:140] = 50
    fit = gmm.fit_gmm(counts, 2, min_sigma=1.0)
    assert fit.sigmas.min() >= 1.0 and np.isfinite(fit.log_likelihood)


# --- histogram minima ------------------------------------------------------------------------------------------------

def test_local_minima_plateau_and_ends():
    y = np.array([5, 3, 3, 3, 6, 2, 9, 1], dtype=float)
    assert minima.local_minima(y) == [2.0, 5.0]           # plateau centre; last bin (an end) is never a minimum


def test_minima_split_three_levels():
    s = scene("three_levels")
    raw = histogram.histogram(s.gray)
    res = minima.find_intervals(raw, histogram.smooth(raw, 2.0), 0.2, 0.001)
    assert len(res.thresholds) == 2
    assert 50 < res.thresholds[0] < 130 < res.thresholds[1] < 210
    assert accuracy(regions.apply_lut(s.gray, res.lut), s.labels) > 0.99
    assert res.intervals[0][0] == 0 and res.intervals[-1][1] == 255


def test_minima_depth_filter_and_unsmoothed_noise():
    s = scene("three_levels")
    raw = histogram.histogram(s.gray)
    noisy = minima.find_intervals(raw, raw, 0.0, 0.0)      # no smoothing, no filters: many spurious minima
    assert len(noisy.thresholds) > 5
    filtered = minima.find_intervals(raw, histogram.smooth(raw, 2.0), 0.2, 0.001)
    assert len(filtered.thresholds) == 2


def test_minima_cannot_separate_close_levels():
    s = scene("close_levels")                              # 120 vs 128 with noise 6: no valley between them
    raw = histogram.histogram(s.gray)
    res = minima.find_intervals(raw, histogram.smooth(raw, 2.0), 0.2, 0.001)
    assert not any(120 <= t < 128 for t in res.thresholds)


# --- regions and boundaries ------------------------------------------------------------------------------------------

def test_boundary_on_noise_free_labels_is_exact():
    lab = np.zeros((6, 8), dtype=np.int16)
    lab[2:4, 3:6] = 1
    b = boundaries.boundary_mask(lab)
    expected = np.zeros_like(b)
    expected[1, 3:6] = True          # above the block (label change to the lower neighbour)
    expected[3, 3:6] = True          # bottom row of the block
    expected[2:4, 2] = True          # left of the block
    expected[2:4, 5] = True          # right column of the block
    assert np.array_equal(b, expected)


def test_noise_free_scene_boundaries_match_truth():
    s = scene("noise_free")
    raw = histogram.histogram(s.gray)
    res = minima.find_intervals(raw, histogram.smooth(raw, 2.0), 0.2, 0.0005)
    lab = regions.apply_lut(s.gray, res.lut)
    c = compare.compare(boundaries.boundary_mask(s.labels), boundaries.boundary_mask(lab), tol=1.0)
    assert c["reference_matched"] > 0.99 and c["candidate_matched"] > 0.97


def test_group_is_not_one_region():
    s = scene("close_levels")                              # two separate objects can share a group
    labels = s.labels.copy()
    labels[labels == 2] = 1
    st = {x["group"]: x for x in regions.group_stats(s.gray, labels)}
    assert st[1]["connected_regions"] == 1                 # touching rectangles -> one region
    lab2 = np.zeros((10, 10), dtype=np.int16)
    lab2[1:3, 1:3] = 1
    lab2[6:8, 6:8] = 1
    assert {x["group"]: x for x in regions.group_stats(np.zeros((10, 10), np.uint8), lab2)}[1]["connected_regions"] == 2


def test_small_region_cleanup():
    lab = np.zeros((20, 20), dtype=np.int16)
    lab[5:15, 5:15] = 1
    lab[0, 0] = 2                                          # 1-pixel speck
    out, removed = regions.remove_small_regions(lab, 4)
    assert removed == 1 and out[0, 0] == 0 and (out[5:15, 5:15] == 1).all()


# --- comparison ------------------------------------------------------------------------------------------------------

def test_compare_tolerance():
    ref = np.zeros((50, 50), bool)
    ref[25, 5:45] = True
    cand = np.zeros_like(ref)
    cand[27, 5:25] = True                                  # 2 px off, half the length
    cand[5, 5:45] = True                                   # far away
    c = compare.compare(ref, cand, tol=3)
    assert c["reference_matched"] == pytest.approx(22 / 40)   # tolerance disc reaches 2 px past the segment end
    assert c["candidate_matched"] == pytest.approx(20 / 60)


def test_detector_rasterize_line_and_circle():
    doc = {"edges": [{"type": "line", "polyline": [[0.5, 10.5], [20.5, 10.5]]},
                     {"type": "circle", "center": [30, 30], "radius_px": 5, "polyline": []}]}
    m = detector.rasterize(doc, (50, 50))
    assert m[10, 0:21].all()
    assert m[30, 35] or m[30, 34]


@pytest.mark.skipif(not detector.available(), reason="detector CLI not built")
def test_end_to_end_with_detector_on_synthetic(tmp_path):
    from PIL import Image
    s = scene("three_levels")
    p = tmp_path / "three.png"
    Image.fromarray(s.gray).save(p)
    r = run(Settings(dataset=None, image=str(p), gmm_k=3, gmm_sweep_max_k=4))
    assert r.detector_error is None
    assert len(r.methods["gmm"].stats) == 3 and len(r.methods["minima"].stats) == 3
    assert r.methods["gmm"].vs_detector["reference_matched"] > 0.8
