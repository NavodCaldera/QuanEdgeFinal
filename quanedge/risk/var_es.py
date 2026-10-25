"""
Layer 2 (VaR) and Layer 3 (Expected Shortfall).

Every model is a fitted one-day loss distribution with .var(alpha) and
.es(alpha), so the dashboard can fit once and query any confidence level.
Units: log-return loss, positive = loss (see portfolio.py).

  historical  empirical quantile of past losses.  No distributional
              assumption, but it cannot imagine a day worse than the worst
              one in the sample, and it weights every past day equally.
  normal      variance-covariance VaR: two parameters, closed form, and it
              understates fat tails by construction.
  student_t   location-scale Student-t fitted by maximum likelihood; the tail
              index nu lets the data decide how fat the tail is.
  mc_normal   Monte Carlo: scenarios for all seven assets from a multivariate
              normal (sample mean and covariance), aggregated through the
              weights one scenario at a time.
  mc_t        the same with a multivariate Student-t: identical covariance,
              tail index by profile likelihood, so assets fall together in the
              tail more often than the normal allows.

ES is the mean loss on the days VaR is breached.  VaR says where the tail
starts, ES how deep it goes; ES is coherent (sub-additive, so diversification
never appears to add risk) and is the measure Basel's FRTB adopted.
"""
import numpy as np
import pandas as pd
from scipy import optimize, special, stats
from . import settings as S
from .portfolio import weight_vector


class Empirical:
    """Loss distribution given by a sample: past days (historical) or simulated scenarios (Monte Carlo)."""

    def __init__(self, losses, name: str = "historical", params: dict | None = None):
        self.name = name
        self.losses = np.asarray(losses, dtype=float)
        self.params = params or {"n": len(self.losses)}

    def var(self, alpha: float) -> float:
        return float(np.quantile(self.losses, alpha, method=S.QUANTILE_METHOD))

    def es(self, alpha: float) -> float:
        v = self.var(alpha)
        return float(self.losses[self.losses >= v].mean())


def historical(r) -> Empirical:
    return Empirical(-np.asarray(r, dtype=float), "historical")


class Normal:
    """VaR_a = -mu + sigma z_a,  ES_a = -mu + sigma phi(z_a) / (1 - a)."""
    name = "normal"

    def __init__(self, r):
        r = np.asarray(r, dtype=float)
        self.mu, self.sigma = float(r.mean()), float(r.std(ddof=1))
        self.params = {"mu": self.mu, "sigma": self.sigma}

    def var(self, alpha: float) -> float:
        return float(-self.mu + self.sigma * stats.norm.ppf(alpha))

    def es(self, alpha: float) -> float:
        return float(-self.mu + self.sigma * stats.norm.pdf(stats.norm.ppf(alpha)) / (1 - alpha))


def fit_t(r) -> tuple[float, float, float]:
    """
    Student-t maximum likelihood (nu, loc, scale).  Fitted on data
    standardised by median and MAD so the optimiser works on numbers near 1;
    the tests check it reaches at least scipy's (much slower) likelihood.
    """
    r = np.asarray(r, dtype=float)
    m0, s0 = np.median(r), stats.median_abs_deviation(r, scale="normal")
    z = (r - m0) / s0

    def nll(th):
        nu, loc, log_s = th
        return -(len(z) * (special.gammaln((nu + 1) / 2) - special.gammaln(nu / 2)
                           - 0.5 * np.log(nu * np.pi) - log_s)
                 - (nu + 1) / 2 * np.log1p(((z - loc) / np.exp(log_s)) ** 2 / nu).sum())

    res = optimize.minimize(nll, x0=[4.0, 0.0, 0.0], method="L-BFGS-B",
                            bounds=[(1.05, 200.0), (None, None), (None, None)])   # nu > 1 so ES exists
    nu, loc, log_scale = res.x
    return float(nu), float(m0 + s0 * loc), float(s0 * np.exp(log_scale))


class StudentT:
    """
    r = loc + scale * T_nu.  For the standard t (needs nu > 1):
    ES_a = f_nu(q) / (1 - a) * (nu + q^2) / (nu - 1),  q = t_nu^{-1}(a).
    """
    name = "student_t"

    def __init__(self, r):
        self.nu, self.loc, self.scale = fit_t(r)
        self.params = {"nu": self.nu, "loc": self.loc, "scale": self.scale}

    def var(self, alpha: float) -> float:
        return float(-self.loc + self.scale * stats.t.ppf(alpha, self.nu))

    def es(self, alpha: float) -> float:
        q = stats.t.ppf(alpha, self.nu)
        es_std = stats.t.pdf(q, self.nu) / (1 - alpha) * (self.nu + q ** 2) / (self.nu - 1)
        return float(-self.loc + self.scale * es_std)


def mvt_nu(x) -> float:
    """
    Tail index of a multivariate t whose covariance equals the sample
    covariance (dispersion S = Sigma (nu-2)/nu), by profile maximum likelihood.
    """
    x = np.asarray(x, dtype=float)
    d = x.shape[1]
    dev = x - x.mean(axis=0)
    cov = np.atleast_2d(np.cov(x, rowvar=False))
    m = np.einsum("ij,jk,ik->i", dev, np.linalg.inv(cov), dev)    # Mahalanobis distances under Sigma
    logdet = np.linalg.slogdet(cov)[1]

    def nll(nu):
        c = (nu - 2) / nu
        ll = (special.gammaln((nu + d) / 2) - special.gammaln(nu / 2) - d / 2 * np.log(nu * np.pi)
              - 0.5 * (d * np.log(c) + logdet) - (nu + d) / 2 * np.log1p(m / (c * nu)))
        return -ll.sum()

    return float(optimize.minimize_scalar(nll, bounds=S.MC_T_NU_BOUNDS, method="bounded").x)


def monte_carlo(asset_r: pd.DataFrame, weights, dist: str = "normal",
                n_sim: int = S.N_SIM, seed: int = S.SEED) -> Empirical:
    """Simulate one-day log returns for every asset, aggregate each scenario in simple returns."""
    x = asset_r.to_numpy(dtype=float)
    w = weight_vector(weights, asset_r.columns)
    rng = np.random.default_rng(seed)
    chol = np.linalg.cholesky(np.atleast_2d(np.cov(x, rowvar=False)))
    sims = rng.standard_normal((n_sim, x.shape[1])) @ chol.T
    params = {"n_sim": n_sim}
    if dist == "t":
        nu = mvt_nu(x)
        sims *= np.sqrt((nu - 2) / rng.chisquare(nu, (n_sim, 1)))   # one shared shock per scenario: joint tails
        params["nu"] = nu
    elif dist != "normal":
        raise ValueError(f"dist must be 'normal' or 't', not {dist!r}")
    r_p = np.log1p(np.expm1(x.mean(axis=0) + sims) @ w)
    return Empirical(-r_p, f"mc_{dist}", params)


def batch_se(model: Empirical, alpha: float, n_batches: int = 20) -> tuple[float, float]:
    """Monte Carlo simulation error of (VaR, ES): spread of the estimate across independent batches."""
    est = np.array([(b.var(alpha), b.es(alpha)) for b in
                    (Empirical(chunk) for chunk in np.array_split(model.losses, n_batches))])
    se = est.std(axis=0, ddof=1) / np.sqrt(n_batches)
    return float(se[0]), float(se[1])
