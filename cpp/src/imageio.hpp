// Read-only access to the replay datasets and conversion to 0-255 grayscale. Port of intensity_lab/imageio.py.
#pragma once
#include <string>
#include <vector>

#include <opencv2/core.hpp>

namespace ilab {

extern const char* const DATASET_ROOT;           // /Users/apple/Downloads/Geometry-Replay-Datasets
extern const char* const VIEWS[6];               // top, bottom, front, rear, left, right
extern const double BT601[3];                    // 0.299, 0.587, 0.114 (R, G, B)

struct LoadedImage {
  std::string path;
  cv::Mat gray;              // CV_8UC1, 0-255
  std::string source_mode;   // "L", "RGB", "RGBA" (the PIL mode names the Python reference reports)
  std::string conversion;    // how gray was obtained, same wording as the reference
  std::string sha256;
};

struct ImageEntry {
  std::string view, relpath;
};

/** All images of a dataset ("product-images" / "isaacsim-images"), view by view, sorted like Python's sorted(rglob). */
std::vector<ImageEntry> list_images(const std::string& dataset, const std::string& root = DATASET_ROOT);

/** Full path of an image; an empty dataset means `relpath` is already a path. Refuses paths outside the dataset. */
std::string resolve(const std::string& dataset, const std::string& relpath, const std::string& root = DATASET_ROOT);

/** 8-bit gray as stored, or BT.601 luma computed in double precision and rounded half-to-even (numpy.rint) -- not
 *  cv::cvtColor, whose fixed-point arithmetic differs by up to one gray level. */
LoadedImage load(const std::string& path);
cv::Mat to_gray(const cv::Mat& decoded, std::string& mode, std::string& conversion);

/** Optional spatial Gaussian smoothing (sigma in pixels), rounded back to 0-255; sigma <= 0 returns the input.
 *  Same kernel, border and order as scipy.ndimage.gaussian_filter(mode="nearest", truncate=4). */
cv::Mat presmooth(const cv::Mat& gray, double sigma_px);

}  // namespace ilab
