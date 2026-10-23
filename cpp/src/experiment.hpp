// One experiment = one image + one Settings object -> GMM components, GMM groups and histogram-minimum intervals,
// their masks and boundaries. Port of the processing part of intensity_lab/experiment.py (the detector comparison,
// matplotlib figures and the web UI are not part of the port).
#pragma once
#include <map>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "gmm.hpp"
#include "imageio.hpp"
#include "json.hpp"
#include "minima.hpp"
#include "regions.hpp"

namespace ilab {

/** Same fields, defaults and meaning as intensity_lab.experiment.Settings. The last three are accepted and written
 *  back unchanged so settings files stay interchangeable, but the port does not use them (no detector, no plots). */
struct Settings {
  std::string dataset = "product-images";   // empty = `image` is a full path (Python: null)
  std::string image;
  double presmooth_sigma_px = 0.0;
  double hist_smooth_sigma = 2.0;
  int gmm_k = 4;
  double gmm_min_sigma = 1.0;
  int gmm_n_init = 5;
  long long gmm_seed = 0;
  int gmm_sweep_max_k = 8;
  double separation_threshold = 2.0;
  std::string merge_rule = "hierarchical";
  double min_posterior = 0.0;
  double minima_min_relative_depth = 0.2;
  double minima_min_interval_fraction = 0.001;
  int min_region_area_px = 0;
  bool run_detector = true;                  // not used by the port
  double compare_tolerance_px = 3.0;         // not used by the port
  bool histogram_log_scale = true;           // not used by the port

  /** From a settings object or a saved settings.json ({"settings": {...}, ...}); unknown keys are an error. */
  static Settings from_json(const Json& j);
  /** Set one field from JSON text (CLI --set name=value). */
  void set(const std::string& name, const Json& value);
  Json to_json() const;
};

struct MethodResult {
  std::string name;
  std::array<int, 256> lut{};
  cv::Mat labels;            // CV_16SC1, -1 = uncertain
  int regions_removed = 0;
  std::vector<GroupStats> stats;
  cv::Mat boundary;          // certain boundaries (the wireframe), CV_8U 0/1
  cv::Mat uncertain_boundary;
  cv::Mat steps;             // CV_16SC1
};

struct Result {
  Settings settings;
  LoadedImage image;
  cv::Mat gray;              // after optional pre-smoothing
  Hist counts{}, smoothed{};
  GMMFit fit;
  std::vector<GMMFit> sweep;
  GMMGrouping grouping, components;
  MinimaResult minima;
  std::vector<MethodResult> methods;    // gmm_components, gmm, minima (in this order, like the reference)
  std::vector<std::pair<std::string, double>> timings_ms;
};

Result run(const Settings& s);
Json summary(const Result& r);
/** Histogram, smoothed histogram, component curves, posteriors and LUTs: the data behind the reference's plots. */
Json histogram_data(const Result& r);
/** settings.json, summary.json, histogram.json and the PNGs (original, mask_*, boundaries_*, labels_*). */
void save(const Result& r, const std::string& out_dir);

}  // namespace ilab
