"""One-dimensional Gaussian mixture on gray values, fitted by EM on the histogram.

Pixel values are integers 0..255, so the 256 histogram counts are a sufficient statistic: weighted EM over the bins
gives exactly the fit that EM over every pixel would give, in a fraction of the time.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.special import logsumexp

from .histogram import LEVELS

LOG_2PI = np.log(2 * np.pi)


@dataclass
class GMMFit:
    k: int
    weights: np.ndarray       # mixing proportions, sum 1
    means: np.ndarray         # gray levels, ascending
    sigmas: np.ndarray        # gray levels, >= min_sigma
    log_likelihood: float     # natural log, summed over all pixels
    n_pixels: int
    n_iter: int
    converged: bool
    min_sigma: float

    @property
    def n_params(self) -> int:
        return 3 * self.k - 1

    @property
    def bic(self) -> float:
        return -2 * self.log_likelihood + self.n_params * np.log(self.n_pixels)

    @property
    def aic(self) -> float:
        return -2 * self.log_likelihood + 2 * self.n_params

    def log_joint(self, x: np.ndarray) -> np.ndarray:
        """log(pi_j * N(x | mu_j, sigma_j)) with shape (k, len(x))."""
        x = np.asarray(x, dtype=np.float64)[None, :]
        m, s, w = self.means[:, None], self.sigmas[:, None], self.weights[:, None]
        return np.log(w) - 0.5 * LOG_2PI - np.log(s) - 0.5 * ((x - m) / s) ** 2

    def posteriors(self, x: np.ndarray = LEVELS) -> np.ndarray:
        lj = self.log_joint(x)
        return np.exp(lj - logsumexp(lj, axis=0, keepdims=True))

    def component_curves(self, x: np.ndarray = LEVELS) -> np.ndarray:
        """Expected pixel count per gray value for each component (pi_j * N * pdf), shape (k, len(x))."""
        return self.n_pixels * np.exp(self.log_joint(x))

    def summary(self) -> dict:
        d = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in asdict(self).items()}
        d.update(bic=self.bic, aic=self.aic, n_params=self.n_params)
        return d


def _em(x, w, means, sigmas, weights, min_sigma, max_iter, tol):
    n = w.sum()
    ll_prev = -np.inf
    converged = False
    it = 0
    for it in range(1, max_iter + 1):
        lj = (np.log(weights)[:, None] - 0.5 * LOG_2PI - np.log(sigmas)[:, None]
              - 0.5 * ((x[None, :] - means[:, None]) / sigmas[:, None]) ** 2)
        lse = logsumexp(lj, axis=0)
        ll = float(np.dot(w, lse))
        r = np.exp(lj - lse[None, :]) * w[None, :]           # responsibilities times bin counts
        nk = np.maximum(r.sum(axis=1), 1e-12)
        means = (r @ x) / nk
        var = (r * (x[None, :] - means[:, None]) ** 2).sum(axis=1) / nk
        sigmas = np.maximum(np.sqrt(var), min_sigma)
        weights = np.maximum(nk / n, 1e-300)
        weights /= weights.sum()
        if abs(ll - ll_prev) <= tol * abs(ll):
            converged = True
            break
        ll_prev = ll
    # final likelihood with the final parameters
    lj = (np.log(weights)[:, None] - 0.5 * LOG_2PI - np.log(sigmas)[:, None]
          - 0.5 * ((x[None, :] - means[:, None]) / sigmas[:, None]) ** 2)
    ll = float(np.dot(w, logsumexp(lj, axis=0)))
    return means, sigmas, weights, ll, it, converged


def fit_gmm(counts: np.ndarray, k: int, min_sigma: float = 1.0, n_init: int = 5, seed: int = 0,
            max_iter: int = 2000, tol: float = 1e-8) -> GMMFit:
    """Fit k Gaussians to the histogram. Start 0 puts the means at the (i+0.5)/k quantiles of the pixel values; the other
    n_init-1 starts draw means from the pixel distribution with a seeded generator. The highest likelihood wins."""
    counts = np.asarray(counts, dtype=np.float64)
    nz = counts > 0
    x, w = LEVELS[nz], counts[nz]
    n = w.sum()
    if n == 0:
        raise ValueError("empty histogram")
    total_mean = np.dot(w, x) / n
    total_std = max(np.sqrt(np.dot(w, (x - total_mean) ** 2) / n), min_sigma)
    cdf = np.cumsum(w) / n
    rng = np.random.default_rng(seed)
    best = None
    for start in range(max(1, n_init)):
        if start == 0:
            means = x[np.minimum(np.searchsorted(cdf, (np.arange(k) + 0.5) / k), len(x) - 1)].astype(np.float64)
        else:
            means = np.sort(rng.choice(x, size=k, replace=len(x) < k, p=w / n)).astype(np.float64)
        means = means + np.linspace(-1e-3, 1e-3, k)        # break ties between identical starts
        sigmas = np.full(k, max(total_std / k, min_sigma))
        weights = np.full(k, 1.0 / k)
        res = _em(x, w, means, sigmas, weights, min_sigma, max_iter, tol)
        if best is None or res[3] > best[3] + 1e-9 * abs(best[3]):
            best = res
    means, sigmas, weights, ll, it, conv = best
    order = np.argsort(means)
    return GMMFit(k=k, weights=weights[order], means=means[order], sigmas=sigmas[order], log_likelihood=ll,
                  n_pixels=int(n), n_iter=it, converged=conv, min_sigma=min_sigma)


def sweep(counts: np.ndarray, k_values, **kw) -> list[GMMFit]:
    return [fit_gmm(counts, k, **kw) for k in k_values]


def ashman_d(m1: float, s1: float, m2: float, s2: float) -> float:
    """Ashman's D = |m1-m2| / sqrt((s1^2+s2^2)/2). D > 2 is the usual criterion for a clean separation of two Gaussians."""
    return abs(m1 - m2) / np.sqrt((s1 * s1 + s2 * s2) / 2)


def separation_matrix(fit: GMMFit) -> np.ndarray:
    k = fit.k
    d = np.full((k, k), np.inf)
    for i in range(k):
        for j in range(k):
            if i != j:
                d[i, j] = ashman_d(fit.means[i], fit.sigmas[i], fit.means[j], fit.sigmas[j])
    return d


MERGE_RULES = ("hierarchical", "transitive")


def moment_match(fit: GMMFit, comps: list[int]) -> tuple[float, float, float]:
    """(weight, mean, sigma) of the single Gaussian with the same first two moments as the given components."""
    w = fit.weights[comps]
    W = w.sum()
    m = float(np.dot(w, fit.means[comps]) / W)
    var = float(np.dot(w, fit.sigmas[comps] ** 2 + (fit.means[comps] - m) ** 2) / W)
    return float(W), m, float(np.sqrt(var))


def merge_groups(fit: GMMFit, threshold: float, rule: str = "hierarchical") -> list[list[int]]:
    """Merge components that are not separated (Ashman's D < threshold) into intensity groups.

    hierarchical (default): repeatedly merge the pair of current groups with the smallest D, where each group is
      represented by its moment-matched Gaussian, until every pair has D >= threshold. A merged group gets wider, so a
      broad low-weight component (typically edge pixels between two levels) joins one neighbour, not both.
    transitive: components linked by any pair with D < threshold form one group (union-find). Simple, but one broad
      component overlapping two separated levels chains them together.
    Groups are ordered by their weighted mean intensity."""
    if rule not in MERGE_RULES:
        raise ValueError(f"merge rule must be one of {MERGE_RULES}")
    if rule == "transitive":
        parent = list(range(fit.k))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        d = separation_matrix(fit)
        for i in range(fit.k):
            for j in range(i + 1, fit.k):
                if d[i, j] < threshold:
                    parent[find(i)] = find(j)
        by_root: dict[int, list[int]] = {}
        for i in range(fit.k):
            by_root.setdefault(find(i), []).append(i)
        out = list(by_root.values())
    else:
        out = [[i] for i in range(fit.k)]
        while len(out) > 1:
            stats = [moment_match(fit, g) for g in out]
            best, pair = np.inf, None
            for i in range(len(out)):
                for j in range(i + 1, len(out)):
                    dij = ashman_d(stats[i][1], stats[i][2], stats[j][1], stats[j][2])
                    if dij < best - 1e-9:                 # ties: the lower-intensity pair first
                        best, pair = dij, (i, j)
            if best >= threshold:
                break
            i, j = pair
            out[i] = sorted(out[i] + out[j])
            out.pop(j)
    out.sort(key=lambda g: moment_match(fit, g)[1])
    return out


@dataclass
class GMMGrouping:
    groups: list[list[int]]   # component indices per group
    lut: np.ndarray           # int16[256]: group per gray value, -1 = uncertain
    certainty: np.ndarray     # float[256]: posterior of the chosen group
    threshold: float
    min_posterior: float
    rule: str = "hierarchical"


def group_lut(fit: GMMFit, threshold: float, min_posterior: float = 0.0, rule: str = "hierarchical") -> GMMGrouping:
    """Each gray value goes to the group with the highest summed component posterior. Values whose best group posterior
    is below `min_posterior` are labelled -1 (uncertain). A group may own several non-contiguous gray ranges."""
    groups = merge_groups(fit, threshold, rule)
    post = fit.posteriors(LEVELS)                               # (k, 256)
    gpost = np.stack([post[g].sum(axis=0) for g in groups])     # (n_groups, 256)
    lut = np.argmax(gpost, axis=0).astype(np.int16)
    certainty = gpost.max(axis=0)
    if min_posterior > 0:
        lut[certainty < min_posterior] = -1
    return GMMGrouping(groups=groups, lut=lut, certainty=certainty, threshold=threshold, min_posterior=min_posterior,
                       rule=rule)
