// Boundaries between intensity regions (the "wireframe"). Port of intensity_lab/boundaries.py.
// Coordinates: a label change between pixel (x, y) and its right or lower 4-neighbour marks pixel (x, y), i.e. a
// 1-pixel line on the upper/left side of the change, offset by half a pixel from the true edge.
#pragma once
#include <opencv2/core.hpp>

namespace ilab {

struct BoundaryMasks {
  cv::Mat certain;     // CV_8U 0/1: change between two intensity groups (both labels >= 0) -- the wireframe
  cv::Mat uncertain;   // CV_8U 0/1: change with -1 on one side (edge of an uncertainty band); never also certain
};

BoundaryMasks boundary_masks(const cv::Mat& labels);

/** Absolute gray step across each certain boundary pixel (max over its right and lower group changes); 0 elsewhere.
 *  CV_16SC1. */
cv::Mat boundary_steps(const cv::Mat& gray, const cv::Mat& labels);

/** Boundary pixels over a dimmed copy of the image, RGB CV_8UC3; uncertainty-band edges (if given) in yellow
 *  underneath; `thicken` dilates with a 3x3 cross, like scipy's binary_dilation default. */
cv::Mat wireframe_image(const cv::Mat& gray, const cv::Mat& mask, cv::Vec3b color = {255, 40, 40}, double dim = 0.45,
                        int thicken = 0, const cv::Mat& uncertain = cv::Mat());

}  // namespace ilab
