// Intensity intervals from local minima of the smoothed histogram. Port of intensity_lab/minima.py.
#pragma once
#include <array>
#include <string>
#include <utility>
#include <vector>

#include "histogram.hpp"

namespace ilab {

struct RemovedMinimum {
  double position;
  std::string reason;
  double value;
};

struct MinimaResult {
  std::vector<double> candidates;                 // every local minimum (plateau -> its centre)
  std::vector<double> kept;                       // minima that survived the filters
  std::vector<RemovedMinimum> removed;            // in removal order
  std::vector<int> thresholds;                    // value <= t goes to the lower interval
  std::vector<std::pair<int, int>> intervals;     // inclusive, contiguous, covering 0..255
  std::vector<long long> interval_pixels;
  std::array<int, 256> lut{};
  double min_relative_depth = 0.2, min_interval_fraction = 0.001;
};

/** Strict local minima; a plateau of equal values counts once at its centre; the ends are never minima. */
std::vector<double> local_minima(const std::vector<double>& y);

MinimaResult find_intervals(const Hist& raw, const Hist& smoothed, double min_relative_depth = 0.2,
                            double min_interval_fraction = 0.001);

}  // namespace ilab
