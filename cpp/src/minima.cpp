#include "minima.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

#include "json.hpp"

namespace ilab {

std::vector<double> local_minima(const std::vector<double>& y) {
  struct Run {
    int start, end;
    double value;
  };
  std::vector<Run> runs;
  int s = 0;
  int n = static_cast<int>(y.size());
  for (int i = 1; i <= n; i++) {
    if (i == n || y[i] != y[s]) {
      runs.push_back({s, i - 1, y[s]});
      s = i;
    }
  }
  std::vector<double> out;
  for (size_t j = 1; j + 1 < runs.size(); j++)
    if (runs[j - 1].value > runs[j].value && runs[j].value < runs[j + 1].value)
      out.push_back((runs[j].start + runs[j].end) / 2.0);
  return out;
}

namespace {

struct Depth {
  double rel, valley, peak;
};

std::vector<Depth> depths(const std::vector<double>& y, const std::vector<double>& minima) {
  std::vector<int> bounds{0};
  for (double m : minima) bounds.push_back(static_cast<int>(std::floor(m)));
  bounds.push_back(static_cast<int>(y.size()) - 1);
  std::vector<Depth> out;
  for (size_t i = 0; i < minima.size(); i++) {
    int f = static_cast<int>(std::floor(minima[i]));
    double v = y[f];
    double left = *std::max_element(y.begin() + bounds[i], y.begin() + f + 1);
    double right = *std::max_element(y.begin() + f, y.begin() + bounds[i + 2] + 1);
    double peak = std::min(left, right);
    out.push_back({peak > 0 ? (peak - v) / peak : 0.0, v, peak});
  }
  return out;
}

std::string fmt(const char* f, double v) {
  char b[64];
  std::snprintf(b, sizeof b, f, v);
  return b;
}

}  // namespace

MinimaResult find_intervals(const Hist& raw, const Hist& smoothed, double min_relative_depth,
                            double min_interval_fraction) {
  std::vector<double> y(smoothed.begin(), smoothed.end());
  MinimaResult r;
  r.min_relative_depth = min_relative_depth;
  r.min_interval_fraction = min_interval_fraction;
  r.candidates = local_minima(y);
  std::vector<double> kept = r.candidates;
  double total = 0;
  for (double c : raw) total += c;
  auto range_sum = [&](int lo, int hi) {         // inclusive
    double s = 0;
    for (int v = lo; v <= hi; v++) s += raw[v];
    return s;
  };
  while (!kept.empty()) {
    auto d = depths(y, kept);
    size_t i = 0;
    for (size_t q = 1; q < d.size(); q++)
      if (d[q].rel < d[i].rel) i = q;                                      // numpy.argmin: first minimum
    if (d[i].rel < min_relative_depth) {
      r.removed.push_back({kept[i], "relative depth " + fmt("%.3f", d[i].rel) + " < " + py_float(min_relative_depth),
                           d[i].valley});
      kept.erase(kept.begin() + static_cast<long>(i));
      continue;
    }
    std::vector<int> edges{-1};
    for (double m : kept) edges.push_back(static_cast<int>(std::floor(m)));
    edges.push_back(255);
    std::vector<double> masses;
    for (size_t j = 0; j + 1 < edges.size(); j++) masses.push_back(range_sum(edges[j] + 1, edges[j + 1]) / total);
    size_t j = 0;
    for (size_t q = 1; q < masses.size(); q++)
      if (masses[q] < masses[j]) j = q;
    if (masses[j] < min_interval_fraction) {
      std::vector<size_t> bounding;
      for (long b : {static_cast<long>(j) - 1, static_cast<long>(j)})
        if (b >= 0 && b < static_cast<long>(kept.size())) bounding.push_back(static_cast<size_t>(b));
      size_t b = bounding[0];
      for (size_t q : bounding)
        if (d[q].rel < d[b].rel) b = q;                                    // min(..., key=...): first minimum
      r.removed.push_back({kept[b], "interval " + std::to_string(j) + " holds " + fmt("%.4f", masses[j] * 100) +
                                        "% of pixels < " + fmt("%.4f", min_interval_fraction * 100) + "%",
                           d[b].valley});
      kept.erase(kept.begin() + static_cast<long>(b));
      continue;
    }
    break;
  }
  r.kept = kept;
  for (double m : kept) r.thresholds.push_back(static_cast<int>(std::floor(m)));
  std::vector<int> edges{-1};
  edges.insert(edges.end(), r.thresholds.begin(), r.thresholds.end());
  edges.push_back(255);
  for (size_t j = 0; j + 1 < edges.size(); j++) {
    int lo = edges[j] + 1, hi = edges[j + 1];
    r.intervals.emplace_back(lo, hi);
    for (int v = lo; v <= hi; v++) r.lut[v] = static_cast<int>(j);
    r.interval_pixels.push_back(static_cast<long long>(range_sum(lo, hi)));
  }
  return r;
}

}  // namespace ilab
