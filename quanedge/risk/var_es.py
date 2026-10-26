"""
Layer 2 (VaR) and Layer 3 (Expected Shortfall).

Every model is a fitted one-day loss distribution with .var(alpha),
.es(alpha) and .es_fraction(alpha), so the dashboard can fit once and query
any confidence level.  var and es are log-return losses, positive = loss
(see portfolio.py); es_fraction is the exact ES as a fraction of NAV.

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

ES is the average loss over the worst (1 - alpha) share of outcomes.  VaR says
where the tail starts, ES how deep it goes; ES is coherent (sub-additive, so
diversification never appears to add risk) and is the measure Basel's FRTB
adopted.  For a sample (past days or scenarios) it is computed exactly, the
boundary observation taking a fractional weight, so ties and short tails are
handled consistently (Acerbi & Tasche 2002).  VaR keeps numpy's linear
interpolation (Hyndman-Fan type 7); with that pairing ES >= VaR for every sample.

Dollar ES is not the dollar value of log ES: each tail loss is converted to a
fraction of NAV, g(L) = 1 - e^{-L}, before averaging.  g is concave, so
converting log ES instead overstates dollar ES; es_fraction avoids that,
exactly for samples and the normal, by quantile integration otherwise.
"""
import numpy as np
import pandas as pd
from scipy import integrate, optimize, special, stats
from . import settings as S
from .portfolio import loss_fraction, weight_vector
from .validation import ModelFitError, check_alpha, check_returns, check_sample, require_n


def tail_integral(sorted_asc, a: float, b: float = 1.0) -> float:
    """Integral over [a, b] of the empirical step quantile of an ascending sample (each point has mass 1/n)."""
    n = len(sorted_asc)
    edges = np.arange(n + 1) / n
    return float(np.dot(sorted_asc, np.clip(edges[1:], a, b) - np.clip(edges[:-1], a, b)))


class LossModel:
    """Shared behaviour: exact dollar ES from the loss quantile integrated over the tail."""
    name = "model"
    status = "ok"

    def tail_mean(self, alpha: float, transform) -> float:
        """Average of transform(L) over the worst (1 - alpha) probability mass, for an increasing transform."""
        a = check_alpha(alpha)
        value, _ = integrate.quad(lambda p: transform(self.var(p)), a, 1, limit=200)
        return float(value / (1 - a))

    def es_fraction(self, alpha: float) -> float:
        """Exact ES as a fraction of NAV: the average of 1 - e^{-L} over the worst (1 - alpha) mass."""
        return self.tail_mean(alpha, loss_fraction)


class Empirical(LossModel):
    """Loss distribution given by a sample: past days (historical) or simulated scenarios (Monte Carlo)."""

    def __init__(self, losses, name: str = "historical", params: dict | None = None):
        self.name = name
        self.losses = check_sample(losses, f"{name} losses")     # original order: batch_se relies on it
        self._sorted = np.sort(self.losses)
        self.params = params or {"n": len(self.losses)}

    def var(self, alpha: float) -> float:
        return float(np.quantile(self._sorted, check_alpha(alpha), method=S.QUANTILE_METHOD))

    def es(self, alpha: float) -> float:
        a = check_alpha(alpha)
        return tail_integral(self._sorted, a) / (1 - a)

    def tail_mean(self, alpha: float, transform) -> float:
        a = check_alpha(alpha)
        return tail_integral(transform(self._sorted), a) / (1 - a)


def historical(r) -> Empirical:
    return Empirical(-np.asarray(r, dtype=float), "historical")


class Normal(LossModel):
    """VaR_a = -mu + sigma z_a,  ES_a = -mu + sigma phi(z_a) / (1 - a), for normal log returns."""
    name = "normal"

    def __init__(self, r):
        r = check_sample(r, "returns", min_n=2)
        self.mu, self.sigma = float(r.mean()), float(r.std(ddof=1))
        self.params = {"mu": self.mu, "sigma": self.sigma}

    def var(self, alpha: float) -> float:
        return float(-self.mu + self.sigma * stats.norm.ppf(check_alpha(alpha)))

    def es(self, alpha: float) -> float:
        a = check_alpha(alpha)
        return float(-self.mu + self.sigma * stats.norm.pdf(stats.norm.ppf(a)) / (1 - a))

    def es_fraction(self, alpha: float) -> float:
        """1 - exp(mu + sigma^2/2) Phi(-z_a - sigma) / (1 - a), evaluated in logs for extreme tails."""
        a = check_alpha(alpha)
        z = stats.norm.ppf(a)
        return float(-np.expm1(self.mu + self.sigma ** 2 / 2 + stats.norm.logcdf(-z - self.sigma) - np.log1p(-a)))


def fit_t(r) -> tuple[float, float, float]:
    """
    Student-t maximum likelihood (nu, loc, scale).  Fitted on data
    standardised by median and MAD so the optimiser works on numbers near 1;
    the tests check it reaches at least scipy's (much slower) likelihood.
    """
    r = check_sample(r, "returns")
    require_n(len(r), 10, "a Student-t fit")
    m0, s0 = np.median(r), stats.median_abs_deviation(r, scale="normal")
    if s0 == 0:                                  # over half the days identical: standardise by the sd instead
        s0 = r.std(ddof=1)
    if s0 == 0:
        raise ModelFitError("returns are constant, so a Student-t scale cannot be estimated")
    z = (r - m0) / s0

    def nll(th):
        nu, loc, log_s = th
        return -(len(z) * (special.gammaln((nu + 1) / 2) - special.gammaln(nu / 2)
                           - 0.5 * np.log(nu * np.pi) - log_s)
                 - (nu + 1) / 2 * np.log1p(((z - loc) / np.exp(log_s)) ** 2 / nu).sum())

    with np.errstate(over="ignore", invalid="ignore"):     # a collapsing scale overflows before it is rejected
        res = optimize.minimize(nll, x0=[4.0, 0.0, 0.0], method="L-BFGS-B",
                                bounds=[S.T_NU_BOUNDS, (None, None), (None, None)])
    if not (res.success and np.isfinite(res.fun)):
        raise ModelFitError(f"Student-t likelihood did not converge: {res.message}")
    nu, loc, log_scale = res.x
    if np.exp(log_scale) < 1e-6:                 # many identical returns let the likelihood collapse onto them
        raise ModelFitError("Student-t fit collapsed onto a point mass (too many identical returns)")
    return float(nu), float(m0 + s0 * loc), float(s0 * np.exp(log_scale))


class StudentT(LossModel):
    """
    r = loc + scale * T_nu.  For the standard t (needs nu > 1):
    ES_a = f_nu(q) / (1 - a) * (nu + q^2) / (nu - 1),  q = t_nu^{-1}(a).
    The scale is not the standard deviation (that is scale * sqrt(nu / (nu - 2)), for nu > 2).
    """
    name = "student_t"

    def __init__(self, r):
        self.nu, self.loc, self.scale = fit_t(r)
        lo, hi = S.T_NU_BOUNDS
        if min(self.nu - lo, hi - self.nu) < 1e-3:
            self.status = f"warning: nu = {self.nu:.3g} sits at its bound"
        self.params = {"nu": self.nu, "loc": self.loc, "scale": self.scale}

    def var(self, alpha: float) -> float:
        return float(-self.loc + self.scale * stats.t.ppf(check_alpha(alpha), self.nu))

    def es(self, alpha: float) -> float:
        a = check_alpha(alpha)
        q = stats.t.ppf(a, self.nu)
        es_std = stats.t.pdf(q, self.nu) / (1 - a) * (self.nu + q ** 2) / (self.nu - 1)
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
    try:
        m = np.einsum("ij,jk,ik->i", dev, np.linalg.inv(cov), dev)    # Mahalanobis distances under Sigma
    except np.linalg.LinAlgError:
        raise ModelFitError("sample covariance is singular") from None
    logdet = np.linalg.slogdet(cov)[1]

    def nll(nu):
        c = (nu - 2) / nu
        ll = (special.gammaln((nu + d) / 2) - special.gammaln(nu / 2) - d / 2 * np.log(nu * np.pi)
              - 0.5 * (d * np.log(c) + logdet) - (nu + d) / 2 * np.log1p(m / (c * nu)))
        return -ll.sum()

    res = optimize.minimize_scalar(nll, bounds=S.MC_T_NU_BOUNDS, method="bounded")
    if not (res.success and np.isfinite(res.fun)):
        raise ModelFitError(f"multivariate t tail index did not converge: {res.message}")
    return float(res.x)


def monte_carlo(asset_r: pd.DataFrame, weights, dist: str = "normal",
                n_sim: int = S.N_SIM, seed: int = S.SEED) -> Empirical:
    """
    Simulate one-day log returns for every asset and aggregate each scenario
    in simple returns.  The per-asset scenarios stay on the result
    (.scenarios, columns in .assets order) for risk attribution.
    """
    if dist not in ("normal", "t"):
        raise ValueError(f"dist must be 'normal' or 't', not {dist!r}")
    x = check_returns(asset_r, min_rows=S.MIN_OBS).to_numpy(dtype=float)
    w = weight_vector(weights, asset_r.columns)
    try:
        chol = np.linalg.cholesky(np.atleast_2d(np.cov(x, rowvar=False)))
    except np.linalg.LinAlgError:
        raise ModelFitError("sample covariance is not positive definite (a constant or collinear asset); "
                            "no jitter is added") from None
    rng = np.random.default_rng(seed)
    sims = rng.standard_normal((n_sim, x.shape[1])) @ chol.T
    params = {"n_sim": n_sim, "seed": seed}
    if dist == "t":
        nu = mvt_nu(x)
        sims *= np.sqrt((nu - 2) / rng.chisquare(nu, (n_sim, 1)))   # one shared shock per scenario: joint tails
        params["nu"] = nu
    scenarios = x.mean(axis=0) + sims
    with np.errstate(over="ignore"):
        simple = np.expm1(scenarios) @ w
    if not np.isfinite(simple).all() or np.any(simple <= -1):
        raise ModelFitError("a simulated portfolio value overflowed or fell to zero; scenarios are not clipped")
    model = Empirical(-np.log1p(simple), f"mc_{dist}", params)
    model.scenarios, model.assets = scenarios, list(asset_r.columns)
    return model


def batch_se(model: Empirical, alpha: float, n_batches: int = 20) -> tuple[float, float]:
    """Monte Carlo simulation error of (VaR, ES): spread of the estimate across independent batches."""
    a = check_alpha(alpha)
    size = len(model.losses) // n_batches
    if n_batches < 2 or size * (1 - a) < 10:
        raise ValueError(f"{n_batches} batches of {size} scenarios leave under 10 tail points each at {a:.1%}")
    est = np.array([(b.var(a), b.es(a)) for b in
                    (Empirical(chunk) for chunk in np.array_split(model.losses, n_batches))])
    se = est.std(axis=0, ddof=1) / np.sqrt(n_batches)
    return float(se[0]), float(se[1])


def mc_convergence(asset_r: pd.DataFrame, weights, sizes=S.MC_CONVERGENCE_SIZES,
                   n_seeds: int = S.MC_CONVERGENCE_SEEDS, alphas=(0.95, 0.99)) -> pd.DataFrame:
    """Monte Carlo VaR/ES across simulation sizes and independent seeds, one row per run and level."""
    rows = []
    for dist in ("normal", "t"):
        for n in sizes:
            for seed in range(S.SEED, S.SEED + n_seeds):
                m = monte_carlo(asset_r, weights, dist, n, seed)
                rows += [{"method": f"mc_{dist}", "n_sim": n, "seed": seed, "alpha": a, "var": m.var(a),
                          "es": m.es(a), "es_fraction": m.es_fraction(a)} for a in alphas]
    return pd.DataFrame(rows)
