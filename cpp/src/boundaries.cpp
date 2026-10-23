#include "boundaries.hpp"

#include <cstdlib>

#include <opencv2/imgproc.hpp>

#include "regions.hpp"

namespace ilab {

BoundaryMasks boundary_masks(const cv::Mat& labels) {
  const int H = labels.rows, W = labels.cols;
  BoundaryMasks m{cv::Mat::zeros(H, W, CV_8U), cv::Mat::zeros(H, W, CV_8U)};
  auto mark = [&](int y, int x, int a, int b) {
    if (a == b) return;
    if (a != UNCERTAIN && b != UNCERTAIN) m.certain.at<uint8_t>(y, x) = 1;
    else m.uncertain.at<uint8_t>(y, x) = 1;
  };
  for (int y = 0; y < H; y++) {
    const int16_t* l = labels.ptr<int16_t>(y);
    const int16_t* d = y + 1 < H ? labels.ptr<int16_t>(y + 1) : nullptr;
    for (int x = 0; x < W; x++) {
      if (x + 1 < W) mark(y, x, l[x], l[x + 1]);
      if (d) mark(y, x, l[x], d[x]);
    }
  }
  m.uncertain.setTo(0, m.certain);          // a pixel that is also certain counts as certain only
  return m;
}

cv::Mat boundary_steps(const cv::Mat& gray, const cv::Mat& labels) {
  const int H = labels.rows, W = labels.cols;
  cv::Mat s = cv::Mat::zeros(H, W, CV_16SC1);
  for (int y = 0; y < H; y++) {
    const int16_t* l = labels.ptr<int16_t>(y);
    const int16_t* ld = y + 1 < H ? labels.ptr<int16_t>(y + 1) : nullptr;
    const uint8_t* g = gray.ptr<uint8_t>(y);
    const uint8_t* gd = y + 1 < H ? gray.ptr<uint8_t>(y + 1) : nullptr;
    int16_t* o = s.ptr<int16_t>(y);
    for (int x = 0; x < W; x++) {
      int v = 0;
      if (x + 1 < W && l[x] != l[x + 1] && l[x] != UNCERTAIN && l[x + 1] != UNCERTAIN) v = std::abs(g[x] - g[x + 1]);
      if (ld && l[x] != ld[x] && l[x] != UNCERTAIN && ld[x] != UNCERTAIN) v = std::max(v, std::abs(g[x] - gd[x]));
      o[x] = static_cast<int16_t>(v);
    }
  }
  return s;
}

cv::Mat wireframe_image(const cv::Mat& gray, const cv::Mat& mask, cv::Vec3b color, double dim, int thicken,
                        const cv::Mat& uncertain) {
  cv::Mat rgb(gray.size(), CV_8UC3);
  for (int y = 0; y < gray.rows; y++) {
    const uint8_t* g = gray.ptr<uint8_t>(y);
    cv::Vec3b* o = rgb.ptr<cv::Vec3b>(y);
    for (int x = 0; x < gray.cols; x++) {
      uint8_t v = static_cast<uint8_t>(g[x] * dim);      // astype(uint8) truncates
      o[x] = {v, v, v};
    }
  }
  cv::Mat cross = cv::getStructuringElement(cv::MORPH_CROSS, {3, 3});
  auto paint = [&](const cv::Mat& m, cv::Vec3b c) {
    if (m.empty() || cv::countNonZero(m) == 0) return;
    cv::Mat d = m;
    if (thicken > 0) cv::dilate(m, d, cross, {-1, -1}, thicken, cv::BORDER_CONSTANT, cv::Scalar(0));
    rgb.setTo(cv::Scalar(c[0], c[1], c[2]), d);
  };
  paint(uncertain, {255, 210, 0});
  paint(mask, color);
  return rgb;
}

}  // namespace ilab
