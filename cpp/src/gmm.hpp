// One-dimensional Gaussian mixture on gray values, fitted by EM on the 256-bin histogram (a sufficient statistic for
// integer pixel values). Port of intensity_lab/gmm.py: same initialisation, update order, stopping rule, constants,
// merge rules and assignment. Only the random starts 2..n differ (std::mt19937_64 instead of NumPy's PCG64).
#pragma once
#include <string>
#include <vector>

#include "histogram.hpp"

namespace ilab {

struct GMMFit {
  int k = 0;
  std::vector<double> weights, means, sigmas;   // ascending means; sigmas >= min_sigma
  double log_likelihood = 0;                    // natural log, summed over all pixels
  long long n_pixels = 0;
  int n_iter = 0;
  bool converged = false;
  double min_sigma = 1.0;
  int best_start = 0;                           // which start won (0 = quantile start); diagnostic only

  int n_params() const { return 3 * k - 1; }
  double bic() const;
  double aic() const;
  /** log(pi_j N(x | mu_j, sigma_j)) for x = 0..255, as [j][x]. */
  std::vector<Hist> log_joint() const;
  std::vector<Hist> posteriors() const;
  /** Expected pixel count per gray value for each component (pi_j * N * pdf). */
  std::vector<Hist> component_curves() const;
};

struct GMMOptions {
  double min_sigma = 1.0;
  int n_init = 5;
  unsigned long long seed = 0;
  int max_iter = 2000;
  double tol = 1e-8;
};

/** Start 0: means at the (i+0.5)/k quantiles of the pixel values; starts 1..n_init-1: means drawn from the pixel
 *  distribution (weighted, without replacement unless there are fewer distinct values than k). Highest likelihood wins. */
GMMFit fit_gmm(const Hist& counts, int k, const GMMOptions& opt = {});
std::vector<GMMFit> sweep(const Hist& counts, int k_min, int k_max, const GMMOptions& opt = {});

/** Ashman's D = |m1-m2| / sqrt((s1^2+s2^2)/2). */
double ashman_d(double m1, double s1, double m2, double s2);
/** k x k; the diagonal is +infinity. */
std::vector<std::vector<double>> separation_matrix(const GMMFit& fit);

struct Moments {
  double weight, mean, sigma;
};
/** The single Gaussian with the same first two moments as the given components. */
Moments moment_match(const GMMFit& fit, const std::vector<int>& comps);

/** "hierarchical" (default), "transitive" or "none". See gmm.py for the definitions. */
std::vector<std::vector<int>> merge_groups(const GMMFit& fit, double threshold, const std::string& rule = "hierarchical");

struct GMMGrouping {
  std::vector<std::vector<int>> groups;    // component indices per group
  std::array<int, 256> lut{};               // group per gray value, -1 = uncertain
  Hist certainty{};                         // posterior of the chosen group
  double threshold = 0, min_posterior = 0;
  std::string rule = "hierarchical";
};

GMMGrouping group_lut(const GMMFit& fit, double threshold, double min_posterior = 0.0,
                      const std::string& rule = "hierarchical");
/** The unmerged assignment: each gray value goes to its most probable component. */
GMMGrouping component_lut(const GMMFit& fit, double min_posterior = 0.0);

}  // namespace ilab
