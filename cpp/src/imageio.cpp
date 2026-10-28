#include "imageio.hpp"

#include <algorithm>
#include <cfenv>
#include <cmath>
#include <filesystem>
#include <stdexcept>

#include <opencv2/imgcodecs.hpp>

#include "sha256.hpp"

namespace fs = std::filesystem;

namespace ilab {

const char* const DATASET_ROOT = "/Users/apple/Downloads/Geometry-Replay-Datasets";
const char* const VIEWS[6] = {"top", "bottom", "front", "rear", "left", "right"};
const double BT601[3] = {0.299, 0.587, 0.114};

namespace {

bool is_image(const fs::path& p) {
  std::string s = p.extension().string();
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
  return s == ".bmp" || s == ".png" || s == ".jpg" || s == ".jpeg" || s == ".tif" || s == ".tiff";
}

/** Python's PurePath ordering: component by component. */
bool path_less(const fs::path& a, const fs::path& b) {
  auto ia = a.begin(), ib = b.begin();
  for (; ia != a.end() && ib != b.end(); ++ia, ++ib) {
    if (ia->string() != ib->string()) return ia->string() < ib->string();
  }
  return ia == a.end() && ib != b.end();
}

/** numpy.rint: round half to even (the default floating-point rounding mode). */
inline double rint_even(double v) { return std::nearbyint(v); }

}  // namespace

std::vector<ImageEntry> list_images(const std::string& dataset, const std::string& root) {
  fs::path base = fs::path(root) / dataset;
  std::vector<ImageEntry> out;
  for (const char* view : VIEWS) {
    std::vector<fs::path> files;
    if (!fs::exists(base / view)) continue;
    for (const auto& e : fs::recursive_directory_iterator(base / view))
      if (e.is_regular_file() && is_image(e.path()) && e.path().filename().string()[0] != '.') files.push_back(e.path());
    std::sort(files.begin(), files.end(), path_less);
    for (const auto& p : files) out.push_back({view, fs::relative(p, base).string()});
  }
  return out;
}

std::string resolve(const std::string& dataset, const std::string& relpath, const std::string& root) {
  if (dataset.empty()) return relpath;
  fs::path base = fs::weakly_canonical(fs::path(root) / dataset);
  fs::path p = fs::weakly_canonical(base / relpath);
  auto rel = p.lexically_relative(base);
  if (rel.empty() || *rel.begin() == "..") throw std::invalid_argument(relpath + " is outside dataset " + dataset);
  return p.string();
}

cv::Mat to_gray(const cv::Mat& img, std::string& mode, std::string& conversion) {
  if (img.depth() != CV_8U) throw std::invalid_argument("unsupported image depth (8-bit images only)");
  if (img.channels() == 1) {
    mode = "L";
    conversion = "stored as 8-bit gray (L)";
    return img.clone();
  }
  if (img.channels() != 3 && img.channels() != 4) throw std::invalid_argument("unsupported channel count");
  mode = img.channels() == 3 ? "RGB" : "RGBA";
  conversion = "BT.601 luma 0.299R+0.587G+0.114B, rounded";
  std::fesetround(FE_TONEAREST);
  cv::Mat g(img.rows, img.cols, CV_8UC1);
  int ch = img.channels();
  int min_alpha = 255;
  for (int y = 0; y < img.rows; y++) {
    const uint8_t* p = img.ptr<uint8_t>(y);
    uint8_t* q = g.ptr<uint8_t>(y);
    for (int x = 0; x < img.cols; x++, p += ch) {
      // OpenCV decodes as B, G, R(, A)
      double v = p[2] * BT601[0] + p[1] * BT601[1] + p[0] * BT601[2];
      q[x] = static_cast<uint8_t>(std::clamp(rint_even(v), 0.0, 255.0));
      if (ch == 4) min_alpha = std::min<int>(min_alpha, p[3]);
    }
  }
  if (ch == 4)
    conversion += "; alpha ignored" + (min_alpha == 255 ? std::string(" (fully opaque)")
                                                        : " (NOT opaque: min alpha " + std::to_string(min_alpha) + ")");
  return g;
}

LoadedImage load(const std::string& path) {
  cv::Mat img = cv::imread(path, cv::IMREAD_UNCHANGED);
  if (img.empty()) throw std::runtime_error("cannot decode " + path);
  LoadedImage out;
  out.path = path;
  out.gray = to_gray(img, out.source_mode, out.conversion);
  out.sha256 = sha256_file(path);
  return out;
}

cv::Mat presmooth(const cv::Mat& gray, double sigma) {
  if (sigma <= 0)
    return gray;
  // scipy _gaussian_kernel1d: radius = int(truncate * sigma + 0.5), weights exp(-0.5 x^2 / sigma^2), normalised.
  int radius = static_cast<int>(4.0 * sigma + 0.5);
  std::vector<double> w(2 * radius + 1);
  double sum = 0;
  for (int i = -radius; i <= radius; i++)
    sum += (w[i + radius] = std::exp(-0.5 / (sigma * sigma) * i * i));
  for (double& v : w)
    v /= sum;
  const double* fw = w.data() + radius;     // centre

  int H = gray.rows, W = gray.cols;
  cv::Mat src;
  gray.convertTo(src, CV_64F);
  // scipy filters axis 0 (rows) first, then axis 1, each with the symmetric-kernel summation order
  // tmp = c[0]*w[0]; for j = r..1: tmp += (c[-j] + c[+j]) * w[j], and "nearest" (replicate) borders.
  cv::Mat a(H, W, CV_64F), b(H, W, CV_64F);
  std::vector<double> line;

  line.resize(static_cast<size_t>(H + 2 * radius));
  for (int x = 0; x < W; x++) {
    for (int y = -radius; y < H + radius; y++)
        line[y + radius] = src.at<double>(std::clamp(y, 0, H - 1), x);
    for (int y = 0; y < H; y++) {
      const double* c = line.data() + y + radius;
      double t = c[0] * fw[0];
      for (int j = -radius; j < 0; j++)
        t += (c[j] + c[-j]) * fw[j];
      a.at<double>(y, x) = t;
    }
  }

  line.resize(static_cast<size_t>(W + 2 * radius));
  for (int y = 0; y < H; y++) {
    const double* row = a.ptr<double>(y);
    for (int x = -radius; x < W + radius; x++)
        line[x + radius] = row[std::clamp(x, 0, W - 1)];
    double* out = b.ptr<double>(y);
    for (int x = 0; x < W; x++) {
      const double* c = line.data() + x + radius;
      double t = c[0] * fw[0];
      for (int j = -radius; j < 0; j++)
        t += (c[j] + c[-j]) * fw[j];
      out[x] = t;
    }
  }

  std::fesetround(FE_TONEAREST);
  cv::Mat g(H, W, CV_8UC1);
  for (int y = 0; y < H; y++)
    for (int x = 0; x < W; x++)
        g.at<uint8_t>(y, x) = static_cast<uint8_t>(std::clamp(rint_even(b.at<double>(y, x)), 0.0, 255.0));
  return g;
}

}  // namespace ilab
