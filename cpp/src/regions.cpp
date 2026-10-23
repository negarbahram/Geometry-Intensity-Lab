#include "regions.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <set>

#include <opencv2/imgproc.hpp>

namespace ilab {

namespace {

const cv::Vec3b PALETTE[12] = {
    {31, 119, 180}, {255, 127, 14}, {44, 160, 44}, {214, 39, 40}, {148, 103, 189}, {140, 86, 75},
    {227, 119, 194}, {23, 190, 207}, {188, 189, 34}, {127, 127, 127}, {174, 199, 232}, {255, 187, 120}};
const cv::Vec3b UNCERTAIN_RGB(40, 40, 40);

std::vector<int> unique_labels(const cv::Mat& labels) {
  std::set<int> s;
  for (int y = 0; y < labels.rows; y++) {
    const int16_t* p = labels.ptr<int16_t>(y);
    for (int x = 0; x < labels.cols; x++) s.insert(p[x]);
  }
  return {s.begin(), s.end()};
}

/** 8-connected components of (labels == g): component id per pixel (0 = not in g) and the number of components. */
int components_of(const cv::Mat& labels, int g, cv::Mat& cc) {
  cv::Mat mask = labels == g;
  return cv::connectedComponents(mask, cc, 8, CV_32S) - 1;
}

}  // namespace

cv::Vec3b group_color(int group) { return group < 0 ? UNCERTAIN_RGB : PALETTE[group % 12]; }

cv::Mat apply_lut(const cv::Mat& gray, const std::array<int, 256>& lut) {
  cv::Mat out(gray.size(), CV_16SC1);
  for (int y = 0; y < gray.rows; y++) {
    const uint8_t* p = gray.ptr<uint8_t>(y);
    int16_t* q = out.ptr<int16_t>(y);
    for (int x = 0; x < gray.cols; x++) q[x] = static_cast<int16_t>(lut[p[x]]);
  }
  return out;
}

std::vector<int> nearest_source(const cv::Mat& source) {
  const int H = source.rows, W = source.cols;
  const double INF = std::numeric_limits<double>::infinity();
  // pass 1, per column: nearest source row above/below
  std::vector<int> row_of(static_cast<size_t>(H) * W, -1);
  for (int x = 0; x < W; x++) {
    int last = -1;
    for (int y = 0; y < H; y++) {
      if (source.at<uint8_t>(y, x)) last = y;
      row_of[static_cast<size_t>(y) * W + x] = last;
    }
    last = -1;
    for (int y = H - 1; y >= 0; y--) {
      if (source.at<uint8_t>(y, x)) last = y;
      int& r = row_of[static_cast<size_t>(y) * W + x];
      if (last >= 0 && (r < 0 || last - y < y - r)) r = last;
    }
  }
  // pass 2, per row: lower envelope of parabolas f(q) + (x - q)^2 with f(q) = (y - row_of(q))^2
  std::vector<int> out(static_cast<size_t>(H) * W, -1);
  std::vector<double> f(W), z(W + 1);
  std::vector<int> v(W);
  for (int y = 0; y < H; y++) {
    for (int q = 0; q < W; q++) {
      int r = row_of[static_cast<size_t>(y) * W + q];
      f[q] = r < 0 ? INF : double(y - r) * double(y - r);
    }
    int k = -1;
    for (int q = 0; q < W; q++) {
      if (!std::isfinite(f[q])) continue;
      while (true) {
        if (k < 0) {
          k = 0;
          v[0] = q;
          z[0] = -INF;
          z[1] = INF;
          break;
        }
        double s = ((f[q] + double(q) * q) - (f[v[k]] + double(v[k]) * v[k])) / (2.0 * q - 2.0 * v[k]);
        if (s <= z[k]) {
          k--;
          continue;
        }
        k++;
        v[k] = q;
        z[k] = s;
        z[k + 1] = INF;
        break;
      }
    }
    if (k < 0) continue;                                   // no source anywhere in the image
    int j = 0;
    for (int x = 0; x < W; x++) {
      while (z[j + 1] < x) j++;
      int q = v[j];
      out[static_cast<size_t>(y) * W + x] = row_of[static_cast<size_t>(y) * W + q] * W + q;
    }
  }
  return out;
}

int remove_small_regions(cv::Mat& labels, int min_area) {
  if (min_area <= 1) return 0;
  cv::Mat small = cv::Mat::zeros(labels.size(), CV_8U);
  int removed = 0;
  for (int g : unique_labels(labels)) {
    if (g == UNCERTAIN) continue;
    cv::Mat cc;
    int n = components_of(labels, g, cc);
    if (n == 0) continue;
    std::vector<long long> sizes(n + 1, 0);
    for (int y = 0; y < cc.rows; y++) {
      const int* p = cc.ptr<int>(y);
      for (int x = 0; x < cc.cols; x++) sizes[p[x]]++;
    }
    std::vector<uint8_t> bad(n + 1, 0);
    for (int c = 1; c <= n; c++)
      if (sizes[c] < min_area) { bad[c] = 1; removed++; }
    for (int y = 0; y < cc.rows; y++) {
      const int* p = cc.ptr<int>(y);
      uint8_t* s = small.ptr<uint8_t>(y);
      for (int x = 0; x < cc.cols; x++)
        if (bad[p[x]]) s[x] = 1;
    }
  }
  if (cv::countNonZero(small) == 0) return 0;
  cv::Mat source = (labels != UNCERTAIN) & (small == 0);
  if (cv::countNonZero(source) == 0) return 0;               // nothing large enough to fill from: leave unchanged
  std::vector<int> nearest = nearest_source(source);
  cv::Mat orig = labels.clone();
  const int W = labels.cols;
  for (int y = 0; y < labels.rows; y++) {
    const uint8_t* s = small.ptr<uint8_t>(y);
    int16_t* l = labels.ptr<int16_t>(y);
    for (int x = 0; x < W; x++)
      if (s[x]) {
        int idx = nearest[static_cast<size_t>(y) * W + x];
        l[x] = orig.at<int16_t>(idx / W, idx % W);
      }
  }
  return removed;
}

cv::Mat overlay(const cv::Mat& gray, const cv::Mat& labels, double alpha) {
  cv::Mat out(gray.size(), CV_8UC3);
  for (int y = 0; y < gray.rows; y++) {
    const uint8_t* g = gray.ptr<uint8_t>(y);
    const int16_t* l = labels.ptr<int16_t>(y);
    cv::Vec3b* o = out.ptr<cv::Vec3b>(y);
    for (int x = 0; x < gray.cols; x++) {
      cv::Vec3b c = group_color(l[x]);
      for (int ch = 0; ch < 3; ch++) {
        double v = (1 - alpha) * g[x] + alpha * c[ch];
        o[x][ch] = static_cast<uint8_t>(std::clamp(v, 0.0, 255.0));   // astype(uint8) truncates
      }
    }
  }
  return out;
}

std::vector<GroupStats> group_stats(const cv::Mat& gray, const cv::Mat& labels) {
  std::vector<GroupStats> out;
  const double n = static_cast<double>(labels.total());
  for (int g : unique_labels(labels)) {
    GroupStats s{};
    s.group = g;
    s.gray_min = 255;
    s.gray_max = 0;
    long double sum = 0;
    for (int y = 0; y < gray.rows; y++) {
      const uint8_t* p = gray.ptr<uint8_t>(y);
      const int16_t* l = labels.ptr<int16_t>(y);
      for (int x = 0; x < gray.cols; x++)
        if (l[x] == g) {
          s.pixels++;
          sum += p[x];
          s.gray_min = std::min<int>(s.gray_min, p[x]);
          s.gray_max = std::max<int>(s.gray_max, p[x]);
        }
    }
    long double mean = sum / s.pixels, ss = 0;
    for (int y = 0; y < gray.rows; y++) {
      const uint8_t* p = gray.ptr<uint8_t>(y);
      const int16_t* l = labels.ptr<int16_t>(y);
      for (int x = 0; x < gray.cols; x++)
        if (l[x] == g) ss += (p[x] - mean) * (p[x] - mean);
    }
    s.share = s.pixels / n;
    s.gray_mean = static_cast<double>(mean);
    s.gray_std = static_cast<double>(std::sqrt(ss / s.pixels));
    cv::Mat cc;
    int ncc = components_of(labels, g, cc);
    std::vector<long long> sizes(ncc + 1, 0);
    for (int y = 0; y < cc.rows; y++) {
      const int* p = cc.ptr<int>(y);
      for (int x = 0; x < cc.cols; x++) sizes[p[x]]++;
    }
    s.connected_regions = ncc;
    for (int c = 1; c <= ncc; c++) {
      s.largest_region_px = std::max(s.largest_region_px, sizes[c]);
      if (sizes[c] < 50) s.regions_under_50px++;
    }
    out.push_back(s);
  }
  return out;
}

std::vector<LutRange> lut_ranges(const std::array<int, 256>& lut) {
  std::vector<LutRange> out;
  int s = 0;
  for (int v = 1; v <= 256; v++)
    if (v == 256 || lut[v] != lut[s]) {
      out.push_back({lut[s], s, v - 1});
      s = v;
    }
  return out;
}

}  // namespace ilab
