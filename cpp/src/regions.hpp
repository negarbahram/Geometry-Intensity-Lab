// Label maps from gray-value lookup tables, optional small-region cleanup, overlays and per-group statistics.
// Port of intensity_lab/regions.py. Label maps are CV_16SC1; -1 = uncertain.
#pragma once
#include <array>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

namespace ilab {

constexpr int UNCERTAIN = -1;

/** Categorical palette (RGB), indexed by group; uncertain is dark gray. Same colours as the reference. */
cv::Vec3b group_color(int group);

cv::Mat apply_lut(const cv::Mat& gray, const std::array<int, 256>& lut);

/** Connected regions (8-connectivity, per label) smaller than `min_area` take the label of the nearest pixel that is
 *  certain and belongs to a large-enough region. Uncertain pixels are never relabelled and never used as a source.
 *  Returns the number of regions removed. min_area <= 1 = off. */
int remove_small_regions(cv::Mat& labels, int min_area);

/** For every pixel, the linear index (y * cols + x) of the nearest nonzero pixel of `source` (exact Euclidean
 *  distance; Felzenszwalb-Huttenlocher). Ties between equidistant sources are broken differently from scipy. */
std::vector<int> nearest_source(const cv::Mat& source);

/** Coloured groups blended over the gray image, as RGB (not BGR) CV_8UC3. */
cv::Mat overlay(const cv::Mat& gray, const cv::Mat& labels, double alpha = 0.55);

struct GroupStats {
  int group;
  long long pixels;
  double share;
  int gray_min, gray_max;
  double gray_mean, gray_std;
  int connected_regions;
  long long largest_region_px;
  int regions_under_50px;
};
std::vector<GroupStats> group_stats(const cv::Mat& gray, const cv::Mat& labels);

struct LutRange {
  int group, lo, hi;
};
std::vector<LutRange> lut_ranges(const std::array<int, 256>& lut);

}  // namespace ilab
