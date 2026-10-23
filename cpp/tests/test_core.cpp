// Focused checks of the C++ core, mirroring tests/test_core.py. Synthetic scenes are read from the PNGs the Python
// evaluation wrote (examples/synthetic/<scene>/input.png), so both implementations see identical pixels.
#include <cmath>
#include <cstdio>
#include <string>

#include <opencv2/imgcodecs.hpp>

#include "boundaries.hpp"
#include "experiment.hpp"
#include "gmm.hpp"
#include "histogram.hpp"
#include "imageio.hpp"
#include "minima.hpp"
#include "regions.hpp"

using namespace ilab;

static int failures = 0, checks = 0;
#define CHECK(cond)                                                              \
  do {                                                                           \
    checks++;                                                                    \
    if (!(cond)) {                                                               \
      failures++;                                                                \
      std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);       \
    }                                                                            \
  } while (0)

static cv::Mat scene(const std::string& name) {
  return cv::imread(std::string(ILAB_EXAMPLES) + "/synthetic/" + name + "/input.png", cv::IMREAD_GRAYSCALE);
}

static GMMFit make_fit(std::vector<double> means, std::vector<double> sigmas, std::vector<double> weights = {}) {
  GMMFit f;
  f.k = static_cast<int>(means.size());
  f.means = means;
  f.sigmas = sigmas;
  f.weights = weights.empty() ? std::vector<double>(f.k, 1.0 / f.k) : weights;
  f.n_pixels = 1000;
  return f;
}

static void test_histogram() {
  cv::Mat g = (cv::Mat_<uint8_t>(2, 3) << 0, 0, 255, 7, 7, 7);
  Hist h = histogram(g);
  double sum = 0;
  for (double v : h) sum += v;
  CHECK(sum == 6 && h[0] == 2 && h[7] == 3 && h[255] == 1);
  Hist s = smooth(h, 0);
  CHECK(s == h);
  cv::Mat three = scene("three_levels");
  Hist raw = histogram(three), sm = smooth(raw, 3.0);
  double a = 0, b = 0;
  for (int i = 0; i < 256; i++) { a += raw[i]; b += sm[i]; }
  CHECK(std::fabs(a - b) < 1e-6 * a);
}

static void test_gray_bt601() {
  cv::Mat bgr(1, 3, CV_8UC3);
  bgr.at<cv::Vec3b>(0, 0) = {0, 0, 255};     // red (OpenCV stores B, G, R)
  bgr.at<cv::Vec3b>(0, 1) = {0, 255, 0};
  bgr.at<cv::Vec3b>(0, 2) = {255, 0, 0};
  std::string mode, conv;
  cv::Mat g = to_gray(bgr, mode, conv);
  CHECK(g.at<uint8_t>(0, 0) == 76 && g.at<uint8_t>(0, 1) == 150 && g.at<uint8_t>(0, 2) == 29);
  CHECK(mode == "RGB");
}

static void test_gmm_three_levels() {
  Hist c = histogram(scene("three_levels"));
  GMMFit f = fit_gmm(c, 3);
  double lv[3] = {50, 130, 210};
  for (int j = 0; j < 3; j++) CHECK(std::fabs(f.means[j] - lv[j]) < 1.5 && f.sigmas[j] < 9);
  CHECK(group_lut(f, 2.0).groups.size() == 3);
}

static void test_merge_rules() {
  CHECK(std::fabs(ashman_d(0, 1, 2, 1) - 2.0) < 1e-12);
  GMMFit f = make_fit({60, 120, 128, 200}, {6, 6, 6, 6});
  CHECK(std::fabs(separation_matrix(f)[1][2] - 8.0 / 6) < 1e-12);
  auto g = merge_groups(f, 2.0);
  CHECK(g.size() == 3 && g[1] == std::vector<int>({1, 2}));
  CHECK(merge_groups(f, 1.0).size() == 4);
  GMMFit chain = make_fit({100, 110, 120}, {6, 6, 6});
  CHECK(merge_groups(chain, 2.0, "transitive").size() == 1);
  auto h = merge_groups(chain, 2.0, "hierarchical");
  CHECK(h.size() == 2 && h[0] == std::vector<int>({0, 1}) && h[1] == std::vector<int>({2}));
  GMMFit edge = make_fit({50, 104.8, 130, 210}, {1, 41.7, 1, 1}, {0.797, 0.0065, 0.1447, 0.0518});
  auto t = merge_groups(edge, 2.0, "transitive");
  CHECK(t.size() == 2 && t[0] == std::vector<int>({0, 1, 2}));
  CHECK(merge_groups(edge, 2.0, "hierarchical").size() == 3);
  Moments m = moment_match(edge, {1, 2});
  CHECK(std::fabs(m.weight - 0.1512) < 1e-12 && m.mean > 125 && m.mean < 131 && m.sigma > 5);
  GMMFit collapse = make_fit({22, 22, 51, 108}, {4, 2, 8, 50}, {0.061, 0.071, 0.725, 0.144});
  CHECK(merge_groups(collapse, 2.0).size() == 1);
  CHECK(component_lut(collapse).groups.size() == 4);
}

static void test_non_contiguous_and_uncertain() {
  GMMFit f = make_fit({100, 101}, {3, 40});
  auto r = lut_ranges(group_lut(f, 0.0, 0.0, "none").lut);
  CHECK(r.size() == 3 && r[0].group == 1 && r[1].group == 0 && r[2].group == 1);
  GMMFit c = make_fit({60, 120, 128, 200}, {6, 6, 6, 6});
  GMMGrouping g = group_lut(c, 0.0, 0.9);
  bool any = false;
  for (int v = 118; v < 132; v++) any |= g.lut[v] == -1;
  CHECK(any && g.lut[60] >= 0 && g.lut[200] >= 0);
}

static void test_minima() {
  std::vector<double> y = {5, 3, 3, 3, 6, 2, 9, 1};
  auto m = local_minima(y);
  CHECK(m.size() == 2 && m[0] == 2.0 && m[1] == 5.0);
  Hist raw = histogram(scene("three_levels"));
  MinimaResult res = find_intervals(raw, smooth(raw, 2.0), 0.2, 0.001);
  CHECK(res.thresholds.size() == 2 && res.thresholds[0] > 50 && res.thresholds[0] < 130 && res.thresholds[1] > 130 &&
        res.thresholds[1] < 210);
  MinimaResult noisy = find_intervals(raw, raw, 0.0, 0.0);
  CHECK(noisy.thresholds.size() > 5);
}

static void test_boundaries() {
  cv::Mat lab = cv::Mat::zeros(6, 8, CV_16SC1);
  lab(cv::Rect(3, 2, 3, 2)).setTo(1);
  BoundaryMasks b = boundary_masks(lab);
  cv::Mat expected = cv::Mat::zeros(6, 8, CV_8U);
  expected(cv::Rect(3, 1, 3, 1)).setTo(1);
  expected(cv::Rect(3, 3, 3, 1)).setTo(1);
  expected(cv::Rect(2, 2, 1, 2)).setTo(1);
  expected(cv::Rect(5, 2, 1, 2)).setTo(1);
  CHECK(cv::countNonZero(b.certain != expected) == 0 && cv::countNonZero(b.uncertain) == 0);

  cv::Mat band = cv::Mat::zeros(4, 9, CV_16SC1);
  band(cv::Rect(3, 0, 3, 4)).setTo(-1);
  band(cv::Rect(6, 0, 3, 4)).setTo(1);
  BoundaryMasks u = boundary_masks(band);
  CHECK(cv::countNonZero(u.certain) == 0 && cv::countNonZero(u.uncertain) == 8);
  cv::Mat g(4, 9, CV_8U, cv::Scalar(9));
  CHECK(cv::countNonZero(boundary_steps(g, band)) == 0);

  cv::Mat mix = (cv::Mat_<int16_t>(3, 4) << 0, 0, 1, 1, 0, 0, 1, 1, -1, -1, -1, -1);
  BoundaryMasks mm = boundary_masks(mix);
  CHECK(mm.certain.at<uint8_t>(0, 1) && mm.certain.at<uint8_t>(1, 1) && !mm.uncertain.at<uint8_t>(1, 1));
  CHECK(mm.uncertain.at<uint8_t>(1, 0) && mm.uncertain.at<uint8_t>(1, 2) && mm.uncertain.at<uint8_t>(1, 3));
}

static void test_cleanup() {
  cv::Mat lab = cv::Mat::zeros(20, 20, CV_16SC1);
  lab(cv::Rect(5, 5, 10, 10)).setTo(1);
  lab.at<int16_t>(0, 0) = 2;
  CHECK(remove_small_regions(lab, 4) == 1 && lab.at<int16_t>(0, 0) == 0);

  cv::Mat u = cv::Mat::zeros(20, 20, CV_16SC1);
  u(cv::Rect(10, 0, 10, 20)).setTo(1);
  u.at<int16_t>(5, 5) = -1;
  u.at<int16_t>(12, 11) = 0;
  u(cv::Rect(9, 0, 3, 3)).setTo(-1);
  u.at<int16_t>(1, 12) = 0;
  cv::Mat before = u.clone();
  int removed = remove_small_regions(u, 4);
  CHECK(removed == 2);
  CHECK(cv::countNonZero((before == -1) != (u == -1)) == 0);
  CHECK(u.at<int16_t>(12, 11) == 1 && u.at<int16_t>(1, 12) == 1);
}

static void test_nearest_source_exact() {
  cv::Mat src = cv::Mat::zeros(30, 40, CV_8U);
  src.at<uint8_t>(3, 4) = 1;
  src.at<uint8_t>(25, 33) = 1;
  src.at<uint8_t>(10, 30) = 1;
  auto idx = nearest_source(src);
  int bad = 0;
  for (int y = 0; y < 30; y++)
    for (int x = 0; x < 40; x++) {
      double best = 1e9;
      for (auto p : {cv::Point(4, 3), cv::Point(33, 25), cv::Point(30, 10)})
        best = std::min(best, std::hypot(p.x - x, p.y - y));
      int i = idx[y * 40 + x];
      if (std::fabs(std::hypot(i % 40 - x, i / 40 - y) - best) > 1e-12) bad++;
    }
  CHECK(bad == 0);
}

int main() {
  test_histogram();
  test_gray_bt601();
  test_gmm_three_levels();
  test_merge_rules();
  test_non_contiguous_and_uncertain();
  test_minima();
  test_boundaries();
  test_cleanup();
  test_nearest_source_exact();
  std::printf("%d checks, %d failed\n", checks, failures);
  return failures ? 1 : 0;
}
