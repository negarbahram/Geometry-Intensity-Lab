#include "experiment.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <stdexcept>

#include <opencv2/core/version.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include "boundaries.hpp"

#ifndef ILAB_SOURCE_DIR
#define ILAB_SOURCE_DIR "."
#endif

namespace fs = std::filesystem;

namespace ilab {

// ---------------------------------------------------------------------------------------------------------- Settings

void Settings::set(const std::string& name, const Json& v) {
  if (name == "dataset") dataset = v.is_null() ? "" : v.as_string();
  else if (name == "image") image = v.as_string();
  else if (name == "presmooth_sigma_px") presmooth_sigma_px = v.as_double();
  else if (name == "hist_smooth_sigma") hist_smooth_sigma = v.as_double();
  else if (name == "gmm_k") gmm_k = static_cast<int>(v.as_int());
  else if (name == "gmm_min_sigma") gmm_min_sigma = v.as_double();
  else if (name == "gmm_n_init") gmm_n_init = static_cast<int>(v.as_int());
  else if (name == "gmm_seed") gmm_seed = v.as_int();
  else if (name == "gmm_sweep_max_k") gmm_sweep_max_k = static_cast<int>(v.as_int());
  else if (name == "separation_threshold") separation_threshold = v.as_double();
  else if (name == "merge_rule") merge_rule = v.as_string();
  else if (name == "min_posterior") min_posterior = v.as_double();
  else if (name == "minima_min_relative_depth") minima_min_relative_depth = v.as_double();
  else if (name == "minima_min_interval_fraction") minima_min_interval_fraction = v.as_double();
  else if (name == "min_region_area_px") min_region_area_px = static_cast<int>(v.as_int());
  else if (name == "run_detector") run_detector = v.as_bool();
  else if (name == "compare_tolerance_px") compare_tolerance_px = v.as_double();
  else if (name == "histogram_log_scale") histogram_log_scale = v.as_bool();
  else throw std::invalid_argument("unknown setting: " + name);
}

Settings Settings::from_json(const Json& j) {
  const Json& obj = j.find("settings") ? j.at("settings") : j;
  Settings s;
  for (const auto& kv : obj.as_object()) s.set(kv.first, kv.second);
  return s;
}

Json Settings::to_json() const {
  Json o = Json::object();
  o.set("dataset", dataset.empty() ? Json(nullptr) : Json(dataset));
  o.set("image", image);
  o.set("presmooth_sigma_px", presmooth_sigma_px);
  o.set("hist_smooth_sigma", hist_smooth_sigma);
  o.set("gmm_k", gmm_k);
  o.set("gmm_min_sigma", gmm_min_sigma);
  o.set("gmm_n_init", gmm_n_init);
  o.set("gmm_seed", gmm_seed);
  o.set("gmm_sweep_max_k", gmm_sweep_max_k);
  o.set("separation_threshold", separation_threshold);
  o.set("merge_rule", merge_rule);
  o.set("min_posterior", min_posterior);
  o.set("minima_min_relative_depth", minima_min_relative_depth);
  o.set("minima_min_interval_fraction", minima_min_interval_fraction);
  o.set("min_region_area_px", min_region_area_px);
  o.set("run_detector", run_detector);
  o.set("compare_tolerance_px", compare_tolerance_px);
  o.set("histogram_log_scale", histogram_log_scale);
  return o;
}

// ------------------------------------------------------------------------------------------------------------ run

namespace {

using Clock = std::chrono::steady_clock;
double ms_since(Clock::time_point t) { return std::chrono::duration<double, std::milli>(Clock::now() - t).count(); }

MethodResult make_method(const std::string& name, const cv::Mat& gray, const std::array<int, 256>& lut,
                         const Settings& s) {
  MethodResult m;
  m.name = name;
  m.lut = lut;
  m.labels = apply_lut(gray, lut);
  m.regions_removed = remove_small_regions(m.labels, s.min_region_area_px);
  m.stats = group_stats(gray, m.labels);
  BoundaryMasks b = boundary_masks(m.labels);
  m.boundary = b.certain;
  m.uncertain_boundary = b.uncertain;
  m.steps = boundary_steps(gray, m.labels);
  return m;
}

}  // namespace

Result run(const Settings& s) {
  Result r;
  r.settings = s;
  auto t0 = Clock::now();
  r.image = load(resolve(s.dataset, s.image));
  r.gray = presmooth(r.image.gray, s.presmooth_sigma_px);
  r.counts = histogram(r.gray);
  r.smoothed = smooth(r.counts, s.hist_smooth_sigma);
  r.timings_ms.emplace_back("load", ms_since(t0));

  t0 = Clock::now();
  GMMOptions opt;
  opt.min_sigma = s.gmm_min_sigma;
  opt.n_init = s.gmm_n_init;
  opt.seed = static_cast<unsigned long long>(s.gmm_seed);
  r.sweep = sweep(r.counts, 1, std::max(s.gmm_sweep_max_k, s.gmm_k), opt);
  r.fit = r.sweep[s.gmm_k - 1];
  r.grouping = group_lut(r.fit, s.separation_threshold, s.min_posterior, s.merge_rule);
  r.components = component_lut(r.fit, s.min_posterior);
  r.timings_ms.emplace_back("gmm", ms_since(t0));

  t0 = Clock::now();
  r.minima = find_intervals(r.counts, r.smoothed, s.minima_min_relative_depth, s.minima_min_interval_fraction);
  r.timings_ms.emplace_back("minima", ms_since(t0));

  t0 = Clock::now();
  r.methods.push_back(make_method("gmm_components", r.gray, r.components.lut, s));
  r.methods.push_back(make_method("gmm", r.gray, r.grouping.lut, s));
  r.methods.push_back(make_method("minima", r.gray, r.minima.lut, s));
  r.timings_ms.emplace_back("masks_boundaries", ms_since(t0));
  return r;
}

// -------------------------------------------------------------------------------------------------------- summary

namespace {

Json groups_json(const std::vector<std::vector<int>>& groups) {
  Json a = Json::array();
  for (const auto& g : groups) a.push(Json::from(g));
  return a;
}

Json ranges_json(const std::vector<LutRange>& rs) {
  Json a = Json::array();
  for (const auto& r : rs) a.push(Json(Json::Object{{"group", r.group}, {"lo", r.lo}, {"hi", r.hi}}));
  return a;
}

Json fit_json(const GMMFit& f) {
  return Json(Json::Object{{"k", f.k},
                           {"weights", Json::from(f.weights)},
                           {"means", Json::from(f.means)},
                           {"sigmas", Json::from(f.sigmas)},
                           {"log_likelihood", f.log_likelihood},
                           {"n_pixels", f.n_pixels},
                           {"n_iter", f.n_iter},
                           {"converged", f.converged},
                           {"min_sigma", f.min_sigma},
                           {"bic", f.bic()},
                           {"aic", f.aic()},
                           {"n_params", f.n_params()},
                           {"best_start", f.best_start}});
}

/** numpy.percentile (linear interpolation) of the values at mask pixels. */
double percentile(std::vector<int> v, double q) {
  std::sort(v.begin(), v.end());
  double pos = q / 100.0 * (v.size() - 1);
  size_t lo = static_cast<size_t>(std::floor(pos));
  size_t hi = std::min(lo + 1, v.size() - 1);
  return v[lo] + (pos - lo) * (v[hi] - v[lo]);
}

double round3(double v) { return std::nearbyint(v * 1000.0) / 1000.0; }

}  // namespace

Json summary(const Result& r) {
  const Settings& s = r.settings;
  int first = 0, last = 255;
  while (r.counts[first] == 0) first++;
  while (r.counts[last] == 0) last--;
  int empty = 0;
  for (int v = first; v <= last; v++) empty += r.counts[v] == 0;
  long long pixels = 0;
  for (double c : r.counts) pixels += static_cast<long long>(c);

  Json d = Json::object();
  d.set("image", Json(Json::Object{{"path", r.image.path},
                                   {"sha256", r.image.sha256},
                                   {"width", r.gray.cols},
                                   {"height", r.gray.rows},
                                   {"source_mode", r.image.source_mode},
                                   {"gray_conversion", r.image.conversion},
                                   {"presmooth_sigma_px", s.presmooth_sigma_px}}));
  d.set("histogram", Json(Json::Object{{"pixels", pixels},
                                       {"min", first},
                                       {"max", last},
                                       {"empty_bins_inside_range", empty},
                                       {"count_at_0", static_cast<long long>(r.counts[0])},
                                       {"count_at_255", static_cast<long long>(r.counts[255])},
                                       {"smoothing", "Gaussian, sigma " + py_float(s.hist_smooth_sigma) +
                                                         " gray levels, zero padding"}}));
  Json sep = Json::array();
  for (const auto& row : separation_matrix(r.fit)) {
    Json jr = Json::array();
    for (double v : row) jr.push(std::isfinite(v) ? Json(round3(v)) : Json(nullptr));
    sep.push(jr);
  }
  Json gg = Json::array();
  for (const auto& g : r.grouping.groups) {
    Moments m = moment_match(r.fit, g);
    gg.push(Json(Json::Object{{"weight", m.weight}, {"mean", m.mean}, {"sigma", m.sigma}}));
  }
  int unc_g = 0, unc_c = 0;
  for (int v = 0; v < 256; v++) {
    unc_g += r.grouping.lut[v] < 0;
    unc_c += r.components.lut[v] < 0;
  }
  Json sw = Json::array();
  for (const auto& f : r.sweep) {
    auto groups = merge_groups(f, r.grouping.threshold, r.grouping.rule);
    sw.push(Json(Json::Object{{"k", f.k},
                              {"bic", f.bic()},
                              {"aic", f.aic()},
                              {"log_likelihood", f.log_likelihood},
                              {"groups_at_threshold", static_cast<int>(groups.size())},
                              {"converged", f.converged},
                              {"weights", Json::from(f.weights)},
                              {"means", Json::from(f.means)},
                              {"sigmas", Json::from(f.sigmas)},
                              {"groups", groups_json(groups)}}));
  }
  d.set("gmm", Json(Json::Object{{"fit", fit_json(r.fit)},
                                 {"separation_ashman_d", sep},
                                 {"threshold", r.grouping.threshold},
                                 {"merge_rule", r.grouping.rule},
                                 {"groups", groups_json(r.grouping.groups)},
                                 {"group_gaussians", gg},
                                 {"gray_ranges", ranges_json(lut_ranges(r.grouping.lut))},
                                 {"min_posterior", r.grouping.min_posterior},
                                 {"uncertain_gray_values", unc_g},
                                 {"component_gray_ranges", ranges_json(lut_ranges(r.components.lut))},
                                 {"uncertain_gray_values_components", unc_c},
                                 {"sweep", sw}}));
  Json removed = Json::array();
  for (const auto& m : r.minima.removed)
    removed.push(Json(Json::Object{{"position", m.position}, {"reason", m.reason}, {"value", m.value}}));
  Json intervals = Json::array();
  for (const auto& iv : r.minima.intervals) intervals.push(Json(Json::Array{iv.first, iv.second}));
  d.set("minima", Json(Json::Object{{"candidates", Json::from(r.minima.candidates)},
                                    {"kept", Json::from(r.minima.kept)},
                                    {"removed", removed},
                                    {"thresholds", Json::from(r.minima.thresholds)},
                                    {"intervals", intervals},
                                    {"interval_pixels", Json::from(r.minima.interval_pixels)},
                                    {"params", Json(Json::Object{{"min_relative_depth", r.minima.min_relative_depth},
                                                                 {"min_interval_fraction",
                                                                  r.minima.min_interval_fraction}})}}));
  Json methods = Json::object();
  for (const auto& m : r.methods) {
    Json stats = Json::array();
    int groups = 0;
    for (const auto& g : m.stats) {
      groups += g.group >= 0;
      stats.push(Json(Json::Object{{"group", g.group},
                                   {"pixels", g.pixels},
                                   {"share", g.share},
                                   {"gray_min", g.gray_min},
                                   {"gray_max", g.gray_max},
                                   {"gray_mean", g.gray_mean},
                                   {"gray_std", g.gray_std},
                                   {"connected_regions", g.connected_regions},
                                   {"largest_region_px", g.largest_region_px},
                                   {"regions_under_50px", g.regions_under_50px}}));
    }
    std::vector<int> steps;
    for (int y = 0; y < m.boundary.rows; y++) {
      const uint8_t* b = m.boundary.ptr<uint8_t>(y);
      const int16_t* st = m.steps.ptr<int16_t>(y);
      for (int x = 0; x < m.boundary.cols; x++)
        if (b[x]) steps.push_back(st[x]);
    }
    long long unc_px = 0;
    for (int y = 0; y < m.labels.rows; y++) {
      const int16_t* l = m.labels.ptr<int16_t>(y);
      for (int x = 0; x < m.labels.cols; x++) unc_px += l[x] < 0;
    }
    double n = static_cast<double>(m.labels.total());
    methods.set(m.name, Json(Json::Object{
                            {"groups", groups},
                            {"regions_removed_by_cleanup", m.regions_removed},
                            {"group_stats", stats},
                            {"boundary_px", static_cast<long long>(steps.size())},
                            {"boundary_share_of_image", steps.size() / n},
                            {"uncertain_pixels", unc_px},
                            {"uncertain_boundary_px", static_cast<long long>(cv::countNonZero(m.uncertain_boundary))},
                            {"boundary_step_median", steps.empty() ? Json(nullptr) : Json(percentile(steps, 50))},
                            {"boundary_step_p90", steps.empty() ? Json(nullptr) : Json(percentile(steps, 90))}}));
  }
  d.set("methods", methods);
  Json t = Json::object();
  for (const auto& kv : r.timings_ms) t.set(kv.first, std::round(kv.second * 10) / 10);
  d.set("timings_ms", t);
  d.set("implementation", "c++");
  return d;
}

Json histogram_data(const Result& r) {
  auto arr = [](const Hist& h) { return Json::from(std::vector<double>(h.begin(), h.end())); };
  auto lut = [](const std::array<int, 256>& l) { return Json::from(std::vector<int>(l.begin(), l.end())); };
  Json curves = Json::array(), post = Json::array(), sweep_curves = Json::array(), palette = Json::array();
  for (const auto& c : r.fit.component_curves()) curves.push(arr(c));
  for (const auto& p : r.fit.posteriors()) post.push(arr(p));
  for (const auto& f : r.sweep) {
    Json cs = Json::array();
    for (const auto& c : f.component_curves()) cs.push(arr(c));
    sweep_curves.push(Json(Json::Object{{"k", f.k}, {"curves", cs}}));
  }
  for (int g = -1; g < 12; g++) {
    cv::Vec3b c = group_color(g);
    palette.push(Json(Json::Array{c[0], c[1], c[2]}));
  }
  return Json(Json::Object{{"gray_values", "0..255 (index = gray value)"},
                           {"raw", arr(r.counts)},
                           {"smoothed", arr(r.smoothed)},
                           {"smoothing_sigma", r.settings.hist_smooth_sigma},
                           {"component_curves", curves},
                           {"component_posteriors", post},
                           {"component_lut", lut(r.components.lut)},
                           {"group_lut", lut(r.grouping.lut)},
                           {"group_certainty", arr(r.grouping.certainty)},
                           {"minima_lut", lut(r.minima.lut)},
                           {"sweep_curves", sweep_curves},
                           {"palette_rgb", palette},
                           {"palette_note", "entry 0 = uncertain (-1); entry g + 1 = group/component g, cycling every 12"}});
}

// ------------------------------------------------------------------------------------------------------------ save

namespace {

std::string git_commit() {
  std::string cmd = std::string("git -C \"") + ILAB_SOURCE_DIR + "\" rev-parse HEAD 2>/dev/null";
  FILE* p = popen(cmd.c_str(), "r");
  if (!p) return "";
  char buf[128] = {0};
  std::string out = fgets(buf, sizeof buf, p) ? std::string(buf) : "";
  pclose(p);
  while (!out.empty() && (out.back() == '\n' || out.back() == '\r')) out.pop_back();
  if (out.empty()) return out;
  cmd = std::string("git -C \"") + ILAB_SOURCE_DIR + "\" status --porcelain -- cpp/src 2>/dev/null";
  p = popen(cmd.c_str(), "r");
  if (p) {
    if (fgets(buf, sizeof buf, p)) out += "-dirty";
    pclose(p);
  }
  return out;
}

void write_text(const fs::path& p, const std::string& s) {
  std::ofstream o(p);
  o << s;
  if (!o) throw std::runtime_error("cannot write " + p.string());
}

void write_png(const fs::path& p, const cv::Mat& img) {
  cv::Mat out = img;
  if (img.channels() == 3) cv::cvtColor(img, out, cv::COLOR_RGB2BGR);   // our colour images are RGB
  if (!cv::imwrite(p.string(), out)) throw std::runtime_error("cannot write " + p.string());
}

}  // namespace

void save(const Result& r, const std::string& out_dir) {
  fs::path dir(out_dir);
  fs::create_directories(dir);
  Json software(Json::Object{{"implementation", "c++"},
                             {"lab_commit", git_commit()},
                             {"opencv", CV_VERSION},
                             {"compiler", __VERSION__},
                             {"random_starts", "start 1: quantile initialisation; starts 2..n: std::mt19937_64 seeded with gmm_seed"}});
  Json meta(Json::Object{{"settings", r.settings.to_json()},
                         {"software", software},
                         {"image_sha256", r.image.sha256},
                         {"reproduce", "intensity-lab-cli run --settings " + (dir / "settings.json").string() +
                                           " --out <new dir>"}});
  write_text(dir / "settings.json", meta.dump(2));
  write_text(dir / "summary.json", summary(r).dump(2));
  write_text(dir / "histogram.json", histogram_data(r).dump(1));
  write_png(dir / "original.png", r.gray);
  for (const auto& m : r.methods) {
    write_png(dir / ("mask_" + m.name + ".png"), overlay(r.gray, m.labels));
    write_png(dir / ("boundaries_" + m.name + ".png"),
              wireframe_image(r.gray, m.boundary, {255, 40, 40}, 0.45, 0, m.uncertain_boundary));
    cv::Mat lab;
    m.labels.convertTo(lab, CV_8U, 1, 1);                           // label + 1, so uncertain (-1) is 0
    write_png(dir / ("labels_" + m.name + ".png"), lab);
    cv::Mat b = m.boundary * 255, u = m.uncertain_boundary * 255;
    write_png(dir / ("boundary_mask_" + m.name + ".png"), b);
    write_png(dir / ("uncertain_boundary_mask_" + m.name + ".png"), u);
  }
}

}  // namespace ilab
