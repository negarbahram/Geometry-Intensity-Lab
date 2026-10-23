#include "histogram.hpp"

#include <cmath>
#include <stdexcept>

namespace ilab {

Hist histogram(const cv::Mat& gray) {
  if (gray.type() != CV_8UC1) throw std::invalid_argument("histogram expects uint8 gray values 0-255");
  std::array<long long, 256> c{};
  for (int y = 0; y < gray.rows; y++) {
    const uint8_t* p = gray.ptr<uint8_t>(y);
    for (int x = 0; x < gray.cols; x++) c[p[x]]++;
  }
  Hist h;
  for (int i = 0; i < 256; i++) h[i] = static_cast<double>(c[i]);
  return h;
}

std::vector<double> gaussian_kernel(double sigma) {
  int radius = std::max(1, static_cast<int>(std::ceil(4 * sigma)));
  std::vector<double> k(2 * radius + 1);
  double sum = 0;
  for (int i = -radius; i <= radius; i++) {
    double v = std::exp(-0.5 * (i / sigma) * (i / sigma));
    k[i + radius] = v;
    sum += v;
  }
  for (double& v : k) v /= sum;
  return k;
}

Hist smooth(const Hist& counts, double sigma) {
  if (sigma <= 0) return counts;
  std::vector<double> k = gaussian_kernel(sigma);
  int r = static_cast<int>(k.size()) / 2;
  Hist out{};
  for (int i = 0; i < 256; i++) {
    double s = 0;
    for (int j = -r; j <= r; j++) {
      int t = i + j;
      if (t >= 0 && t < 256) s += counts[t] * k[j + r];
    }
    out[i] = s;
  }
  return out;
}

}  // namespace ilab
