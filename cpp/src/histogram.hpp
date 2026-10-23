// 256-bin gray-level histogram on the 0-255 scale, and explicit smoothing that never replaces the raw counts.
// Port of intensity_lab/histogram.py.
#pragma once
#include <array>
#include <vector>

#include <opencv2/core.hpp>

namespace ilab {

using Hist = std::array<double, 256>;    // index = gray value = bin centre

/** Raw counts per gray value 0..255 (sums to the pixel count). `gray` must be CV_8UC1. */
Hist histogram(const cv::Mat& gray);

/** Normalised Gaussian kernel, radius max(1, ceil(4 sigma)). */
std::vector<double> gaussian_kernel(double sigma);

/** Gaussian smoothing, sigma in gray levels, zero padding outside 0..255 (mass may leak past the ends; never
 *  renormalised). sigma <= 0 returns a copy. */
Hist smooth(const Hist& counts, double sigma);

}  // namespace ilab
