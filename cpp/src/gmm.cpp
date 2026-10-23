#include "gmm.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>

namespace ilab {

namespace {

const double LOG_2PI = std::log(2 * M_PI);

struct EMResult {
  std::vector<double> means, sigmas, weights;
  double ll = 0;
  int it = 0;
  bool converged = false;
};

/** scipy.special.logsumexp over a short vector. */
inline double logsumexp(const double* a, int n) {
  double m = -std::numeric_limits<double>::infinity();
  for (int i = 0; i < n; i++) m = std::max(m, a[i]);
  if (!std::isfinite(m)) return m;
  double s = 0;
  for (int i = 0; i < n; i++) s += std::exp(a[i] - m);
  return std::log(s) + m;
}

/** log(pi_j N(x_i | mu_j, sigma_j)) into lj[j * n + i]. */
void log_joint_into(const std::vector<double>& x, const std::vector<double>& means, const std::vector<double>& sigmas,
                    const std::vector<double>& weights, std::vector<double>& lj) {
  int k = static_cast<int>(means.size()), n = static_cast<int>(x.size());
  lj.resize(static_cast<size_t>(k) * n);
  for (int j = 0; j < k; j++) {
    double c = std::log(weights[j]) - 0.5 * LOG_2PI - std::log(sigmas[j]);
    for (int i = 0; i < n; i++) {
      double z = (x[i] - means[j]) / sigmas[j];
      lj[static_cast<size_t>(j) * n + i] = c - 0.5 * z * z;
    }
  }
}

double total_ll(const std::vector<double>& x, const std::vector<double>& w, const std::vector<double>& lj, int k,
                std::vector<double>* lse_out = nullptr) {
  int n = static_cast<int>(x.size());
  std::vector<double> col(k);
  double ll = 0;
  if (lse_out) lse_out->resize(n);
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < k; j++) col[j] = lj[static_cast<size_t>(j) * n + i];
    double l = logsumexp(col.data(), k);
    if (lse_out) (*lse_out)[i] = l;
    ll += w[i] * l;
  }
  return ll;
}

EMResult em(const std::vector<double>& x, const std::vector<double>& w, std::vector<double> means,
            std::vector<double> sigmas, std::vector<double> weights, double min_sigma, int max_iter, double tol) {
  int k = static_cast<int>(means.size()), n = static_cast<int>(x.size());
  double ntot = std::accumulate(w.begin(), w.end(), 0.0);
  double ll_prev = -std::numeric_limits<double>::infinity();
  bool converged = false;
  int it = 0;
  std::vector<double> lj, lse, r(static_cast<size_t>(k) * n), nk(k);
  for (it = 1; it <= max_iter; it++) {
    log_joint_into(x, means, sigmas, weights, lj);
    double ll = total_ll(x, w, lj, k, &lse);
    for (int j = 0; j < k; j++) {
      double s = 0;
      for (int i = 0; i < n; i++) {
        size_t q = static_cast<size_t>(j) * n + i;
        r[q] = std::exp(lj[q] - lse[i]) * w[i];       // responsibilities times bin counts
        s += r[q];
      }
      nk[j] = std::max(s, 1e-12);
    }
    for (int j = 0; j < k; j++) {
      double s = 0;
      for (int i = 0; i < n; i++) s += r[static_cast<size_t>(j) * n + i] * x[i];
      means[j] = s / nk[j];
    }
    for (int j = 0; j < k; j++) {
      double s = 0;
      for (int i = 0; i < n; i++) {
        double d = x[i] - means[j];
        s += r[static_cast<size_t>(j) * n + i] * d * d;
      }
      sigmas[j] = std::max(std::sqrt(s / nk[j]), min_sigma);
    }
    double wsum = 0;
    for (int j = 0; j < k; j++) wsum += (weights[j] = std::max(nk[j] / ntot, 1e-300));
    for (int j = 0; j < k; j++) weights[j] /= wsum;
    if (std::fabs(ll - ll_prev) <= tol * std::fabs(ll)) {
      converged = true;
      break;
    }
    ll_prev = ll;
  }
  if (it > max_iter) it = max_iter;
  log_joint_into(x, means, sigmas, weights, lj);
  double ll = total_ll(x, w, lj, k);
  return {means, sigmas, weights, ll, it, converged};
}

}  // namespace

double GMMFit::bic() const { return -2 * log_likelihood + n_params() * std::log(static_cast<double>(n_pixels)); }
double GMMFit::aic() const { return -2 * log_likelihood + 2 * n_params(); }

std::vector<Hist> GMMFit::log_joint() const {
  std::vector<Hist> out(k);
  for (int j = 0; j < k; j++) {
    double c = std::log(weights[j]) - 0.5 * LOG_2PI - std::log(sigmas[j]);
    for (int v = 0; v < 256; v++) {
      double z = (v - means[j]) / sigmas[j];
      out[j][v] = c - 0.5 * z * z;
    }
  }
  return out;
}

std::vector<Hist> GMMFit::posteriors() const {
  std::vector<Hist> lj = log_joint(), out(k);
  std::vector<double> col(k);
  for (int v = 0; v < 256; v++) {
    for (int j = 0; j < k; j++) col[j] = lj[j][v];
    double l = logsumexp(col.data(), k);
    for (int j = 0; j < k; j++) out[j][v] = std::exp(lj[j][v] - l);
  }
  return out;
}

std::vector<Hist> GMMFit::component_curves() const {
  std::vector<Hist> lj = log_joint();
  for (auto& h : lj)
    for (double& v : h) v = static_cast<double>(n_pixels) * std::exp(v);
  return lj;
}

GMMFit fit_gmm(const Hist& counts, int k, const GMMOptions& opt) {
  if (k < 1) throw std::invalid_argument("k must be >= 1");
  std::vector<double> x, w;
  for (int v = 0; v < 256; v++)
    if (counts[v] > 0) { x.push_back(v); w.push_back(counts[v]); }
  int n = static_cast<int>(x.size());
  double ntot = std::accumulate(w.begin(), w.end(), 0.0);
  if (ntot == 0) throw std::invalid_argument("empty histogram");
  double mean = 0;
  for (int i = 0; i < n; i++) mean += w[i] * x[i];
  mean /= ntot;
  double var = 0;
  for (int i = 0; i < n; i++) var += w[i] * (x[i] - mean) * (x[i] - mean);
  double total_std = std::max(std::sqrt(var / ntot), opt.min_sigma);
  std::vector<double> cdf(n);
  double c = 0;
  for (int i = 0; i < n; i++) cdf[i] = (c += w[i]) / ntot;

  std::mt19937_64 rng(opt.seed);
  std::uniform_real_distribution<double> uni(0.0, 1.0);
  bool have = false;
  EMResult best;
  int best_start = 0;
  for (int start = 0; start < std::max(1, opt.n_init); start++) {
    std::vector<double> means(k);
    if (start == 0) {
      for (int i = 0; i < k; i++) {
        double q = (i + 0.5) / k;
        int idx = static_cast<int>(std::lower_bound(cdf.begin(), cdf.end(), q) - cdf.begin());   // searchsorted(left)
        means[i] = x[std::min(idx, n - 1)];
      }
    } else {
      bool replace = n < k;
      std::vector<double> p = w;
      for (int i = 0; i < k; i++) {
        double tot = std::accumulate(p.begin(), p.end(), 0.0);
        double u = uni(rng) * tot, acc = 0;
        int pick = n - 1;
        for (int q = 0; q < n; q++) {
          acc += p[q];
          if (u < acc && p[q] > 0) { pick = q; break; }
        }
        means[i] = x[pick];
        if (!replace) p[pick] = 0;
      }
      std::sort(means.begin(), means.end());
    }
    // numpy.linspace(-1e-3, 1e-3, k): break ties between identical starts
    if (k == 1) means[0] += -1e-3;
    else {
      double step = 2e-3 / (k - 1);
      for (int i = 0; i < k; i++) means[i] += (i == k - 1) ? 1e-3 : -1e-3 + i * step;
    }
    std::vector<double> sigmas(k, std::max(total_std / k, opt.min_sigma)), weights(k, 1.0 / k);
    EMResult res = em(x, w, means, sigmas, weights, opt.min_sigma, opt.max_iter, opt.tol);
    if (!have || res.ll > best.ll + 1e-9 * std::fabs(best.ll)) {
      best = res;
      best_start = start;
      have = true;
    }
  }
  std::vector<int> order(k);
  std::iota(order.begin(), order.end(), 0);
  std::stable_sort(order.begin(), order.end(), [&](int a, int b) { return best.means[a] < best.means[b]; });
  GMMFit f;
  f.k = k;
  for (int j : order) {
    f.weights.push_back(best.weights[j]);
    f.means.push_back(best.means[j]);
    f.sigmas.push_back(best.sigmas[j]);
  }
  f.log_likelihood = best.ll;
  f.n_pixels = static_cast<long long>(ntot);
  f.n_iter = best.it;
  f.converged = best.converged;
  f.min_sigma = opt.min_sigma;
  f.best_start = best_start;
  return f;
}

std::vector<GMMFit> sweep(const Hist& counts, int k_min, int k_max, const GMMOptions& opt) {
  std::vector<GMMFit> out;
  for (int k = k_min; k <= k_max; k++) out.push_back(fit_gmm(counts, k, opt));
  return out;
}

double ashman_d(double m1, double s1, double m2, double s2) {
  return std::fabs(m1 - m2) / std::sqrt((s1 * s1 + s2 * s2) / 2);
}

std::vector<std::vector<double>> separation_matrix(const GMMFit& fit) {
  std::vector<std::vector<double>> d(fit.k, std::vector<double>(fit.k, std::numeric_limits<double>::infinity()));
  for (int i = 0; i < fit.k; i++)
    for (int j = 0; j < fit.k; j++)
      if (i != j) d[i][j] = ashman_d(fit.means[i], fit.sigmas[i], fit.means[j], fit.sigmas[j]);
  return d;
}

Moments moment_match(const GMMFit& fit, const std::vector<int>& comps) {
  double W = 0, m = 0, var = 0;
  for (int c : comps) W += fit.weights[c];
  for (int c : comps) m += fit.weights[c] * fit.means[c];
  m /= W;
  for (int c : comps) var += fit.weights[c] * (fit.sigmas[c] * fit.sigmas[c] + (fit.means[c] - m) * (fit.means[c] - m));
  var /= W;
  return {W, m, std::sqrt(var)};
}

std::vector<std::vector<int>> merge_groups(const GMMFit& fit, double threshold, const std::string& rule) {
  std::vector<std::vector<int>> out;
  if (rule == "none") {
    for (int i = 0; i < fit.k; i++) out.push_back({i});        // component order (= ascending mean) is the label order
    return out;
  }
  if (rule == "transitive") {
    std::vector<int> parent(fit.k);
    std::iota(parent.begin(), parent.end(), 0);
    auto find = [&](int a) {
      while (parent[a] != a) {
        parent[a] = parent[parent[a]];
        a = parent[a];
      }
      return a;
    };
    auto d = separation_matrix(fit);
    for (int i = 0; i < fit.k; i++)
      for (int j = i + 1; j < fit.k; j++)
        if (d[i][j] < threshold) parent[find(i)] = find(j);
    std::vector<int> roots;                                    // insertion order of the Python dict
    for (int i = 0; i < fit.k; i++) {
      int r = find(i);
      auto it = std::find(roots.begin(), roots.end(), r);
      if (it == roots.end()) {
        roots.push_back(r);
        out.push_back({i});
      } else {
        out[it - roots.begin()].push_back(i);
      }
    }
  } else if (rule == "hierarchical") {
    for (int i = 0; i < fit.k; i++) out.push_back({i});
    while (out.size() > 1) {
      std::vector<Moments> st;
      for (const auto& g : out) st.push_back(moment_match(fit, g));
      double best = std::numeric_limits<double>::infinity();
      int bi = -1, bj = -1;
      for (size_t i = 0; i < out.size(); i++)
        for (size_t j = i + 1; j < out.size(); j++) {
          double dij = ashman_d(st[i].mean, st[i].sigma, st[j].mean, st[j].sigma);
          if (dij < best - 1e-9) {                             // ties: the lower-intensity pair first
            best = dij;
            bi = static_cast<int>(i);
            bj = static_cast<int>(j);
          }
        }
      if (best >= threshold) break;
      out[bi].insert(out[bi].end(), out[bj].begin(), out[bj].end());
      std::sort(out[bi].begin(), out[bi].end());
      out.erase(out.begin() + bj);
    }
  } else {
    throw std::invalid_argument("merge rule must be one of hierarchical, transitive, none");
  }
  std::stable_sort(out.begin(), out.end(), [&](const std::vector<int>& a, const std::vector<int>& b) {
    return moment_match(fit, a).mean < moment_match(fit, b).mean;
  });
  return out;
}

GMMGrouping group_lut(const GMMFit& fit, double threshold, double min_posterior, const std::string& rule) {
  GMMGrouping g;
  g.groups = merge_groups(fit, threshold, rule);
  g.threshold = threshold;
  g.min_posterior = min_posterior;
  g.rule = rule;
  std::vector<Hist> post = fit.posteriors();
  for (int v = 0; v < 256; v++) {
    int best = 0;
    double bp = -1;
    for (size_t gi = 0; gi < g.groups.size(); gi++) {
      double p = 0;
      for (int c : g.groups[gi]) p += post[c][v];
      if (p > bp) {                                            // numpy.argmax: first maximum
        bp = p;
        best = static_cast<int>(gi);
      }
    }
    g.lut[v] = best;
    g.certainty[v] = bp;
    if (min_posterior > 0 && bp < min_posterior) g.lut[v] = -1;
  }
  return g;
}

GMMGrouping component_lut(const GMMFit& fit, double min_posterior) {
  return group_lut(fit, 0.0, min_posterior, "none");
}

}  // namespace ilab
