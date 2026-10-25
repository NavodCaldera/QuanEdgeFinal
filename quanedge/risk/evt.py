"""
Layer 4: Extreme Value Theory, peaks over threshold (POT).

Above a high threshold u, excess losses Y = L - u are approximately
Generalized Pareto, GPD(xi, sigma), whatever the parent distribution
(Pickands 1975; Balkema & de Haan 1974).  The shape xi is the tail index:
xi > 0 is a power-law tail, xi < 0.5 means finite variance, xi < 1 means ES
exists.  This lets the model extrapolate beyond the worst observed day
instead of imposing one shape (normal or t) on the whole distribution.

Threshold choice is the judgement call the brief asks us to justify.  For
every candidate u (80th-98.5th loss percentile) threshold_scan records
  * the mean excess e(u) = E[L - u | L > u]: linear in u once the GPD holds,
  * xi-hat and the modified scale sigma* = sigma - xi u: flat once it holds,
  * a stability flag: xi-hat(u) lies inside the 95% interval of xi-hat at
    every higher threshold, and
  * the Kolmogorov-Smirnov distance between the excesses and the fitted GPD.
select_threshold takes the lowest KS distance among stable candidates with at
least EVT_MIN_EXCEED exceedances (the KS rule of Clauset, Shalizi & Newman
2009).  Too low a u lets non-tail days bias the fit; too high leaves too few.

The fitted model uses the empirical losses below u and the GPD above it, so
VaR/ES exist at every sidebar level; once VaR lies above u they are the POT
formulas (McNeil, Frey & Embrechts 2015, ch. 5), with N_u exceedances in n:
    VaR_a = u + sigma/xi * (((1 - a) n / N_u)^(-xi) - 1)
    ES_a  = (VaR_a + sigma - xi u) / (1 - xi)
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import optimize
from . import settings as S


@dataclass
class GPDFit:
    u: float          # threshold, in loss units
    xi: float         # shape (tail index)
    sigma: float      # scale
    n_exceed: int     # N_u
    n: int            # sample size

    @property
    def se(self) -> tuple[float, float]:
        """Asymptotic standard errors of (xi, sigma), valid for xi > -0.5 (Smith 1987)."""
        k, xi = self.n_exceed, self.xi
        return float((1 + xi) / np.sqrt(k)), float(self.sigma * np.sqrt(2 * (1 + xi) / k))


def gpd_nll(theta, y) -> float:
    xi, log_sigma = theta
    if abs(xi) < 1e-9:                       # exponential limit xi -> 0
        return len(y) * log_sigma + y.sum() / np.exp(log_sigma)
    t = 1 + xi * y / np.exp(log_sigma)
    if np.any(t <= 0):
        return np.inf
    return len(y) * log_sigma + (1 + 1 / xi) * np.log(t).sum()


def gpd_cdf(y, xi: float, sigma: float):
    if abs(xi) < 1e-9:
        return -np.expm1(-np.asarray(y) / sigma)
    return 1 - np.maximum(1 + xi * np.asarray(y) / sigma, 0) ** (-1 / xi)


def ks_distance(y, xi: float, sigma: float) -> float:
    """Kolmogorov-Smirnov distance between the excesses y and GPD(xi, sigma)."""
    f = gpd_cdf(np.sort(y), xi, sigma)
    i = np.arange(1, len(f) + 1)
    return float(max((i / len(f) - f).max(), (f - (i - 1) / len(f)).max()))


def fit_gpd(losses, u: float) -> GPDFit:
    """Maximum-likelihood GPD for the excesses over u, started at the method of moments (Hosking & Wallis 1987)."""
    losses = np.asarray(losses, dtype=float)
    y = losses[losses > u] - u
    m, v = y.mean(), y.var()
    xi0 = float(np.clip(0.5 * (1 - m * m / v), -0.4, 0.45))
    res = optimize.minimize(gpd_nll, [xi0, np.log(m * (1 - xi0))], args=(y,), method="Nelder-Mead",
                            options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
    return GPDFit(float(u), float(res.x[0]), float(np.exp(res.x[1])), len(y), len(losses))


class EVT:
    """Loss distribution: empirical below the threshold, GPD above it."""
    name = "evt"

    def __init__(self, losses, fit: GPDFit, scan: pd.DataFrame | None = None):
        self.losses = np.sort(np.asarray(losses, dtype=float))
        self.n, self.fit, self.scan = len(self.losses), fit, scan
        self.zeta = fit.n_exceed / self.n            # P(L > u)
        self.params = {"u": fit.u, "threshold_q": 1 - self.zeta, "n_exceed": fit.n_exceed,
                       "xi": fit.xi, "xi_se": fit.se[0], "sigma": fit.sigma}

    def var(self, alpha: float) -> float:
        p, f = 1 - alpha, self.fit
        if p > self.zeta:                            # VaR below the threshold: the data speak for themselves
            return float(np.quantile(self.losses, alpha, method=S.QUANTILE_METHOD))
        if abs(f.xi) < 1e-9:
            return float(f.u + f.sigma * np.log(self.zeta / p))
        return float(f.u + f.sigma / f.xi * ((p / self.zeta) ** (-f.xi) - 1))

    def es(self, alpha: float) -> float:
        f, v = self.fit, self.var(alpha)
        if f.xi >= 1:
            return np.inf                            # the tail is too heavy for a finite mean
        if 1 - alpha <= self.zeta:
            return float((v + f.sigma - f.xi * f.u) / (1 - f.xi))
        body = self.losses[(self.losses >= v) & (self.losses <= f.u)]
        tail_mean = f.u + f.sigma / (1 - f.xi)       # E[L | L > u] under the GPD
        return float((body.sum() / self.n + self.zeta * tail_mean) / (len(body) / self.n + self.zeta))


def threshold_scan(losses, grid=S.EVT_THRESHOLD_GRID, min_exceed: int = S.EVT_MIN_EXCEED,
                   alphas=(0.99,)) -> pd.DataFrame:
    """Diagnostics for every candidate threshold (see module docstring); one row per percentile q."""
    losses = np.asarray(losses, dtype=float)
    rows = []
    for q in grid:
        u = float(np.quantile(losses, q, method=S.QUANTILE_METHOD))
        y = losses[losses > u] - u
        if len(y) < min_exceed:
            continue
        fit = fit_gpd(losses, u)
        model = EVT(losses, fit)
        row = {"q": float(q), "u": u, "n_exceed": fit.n_exceed, "mean_excess": y.mean(),
               "xi": fit.xi, "xi_se": fit.se[0], "sigma": fit.sigma, "sigma_star": fit.sigma - fit.xi * u,
               "ks": ks_distance(y, fit.xi, fit.sigma)}
        for a in alphas:
            row[f"var_{a:g}"], row[f"es_{a:g}"] = model.var(a), model.es(a)
        rows.append(row)
    scan = pd.DataFrame(rows)
    xi, se = scan["xi"].to_numpy(), scan["xi_se"].to_numpy()
    scan["stable"] = [bool(np.all(np.abs(xi[i:] - xi[i]) <= S.EVT_STABILITY_Z * se[i:]))
                      for i in range(len(scan))]
    return scan


def select_threshold(scan: pd.DataFrame) -> pd.Series:
    """Lowest KS distance among stable thresholds (all candidates if none is stable)."""
    pool = scan[scan["stable"]] if scan["stable"].any() else scan
    return scan.loc[pool["ks"].idxmin()]


def fit_evt(losses, u: float | None = None, threshold_q: float | None = None) -> EVT:
    """EVT model.  Give u or threshold_q to fix the threshold; otherwise the scan rule chooses it."""
    losses = np.asarray(losses, dtype=float)
    scan = None
    if u is None:
        if threshold_q is None:
            scan = threshold_scan(losses)
            threshold_q = float(select_threshold(scan)["q"])
        u = float(np.quantile(losses, threshold_q, method=S.QUANTILE_METHOD))
    return EVT(losses, fit_gpd(losses, u), scan)
