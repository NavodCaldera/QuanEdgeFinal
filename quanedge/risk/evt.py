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
    every higher threshold, with at least EVT_STABILITY_MIN_HIGHER of them
    (so the top of the grid cannot pass by comparing with itself), and
  * the Kolmogorov-Smirnov distance between the excesses and the fitted GPD.
select_threshold takes the lowest KS distance among stable candidates, ties
to the lower threshold.  Minimising the KS distance follows Clauset, Shalizi
& Newman (2009); the stability filter is this project's own addition.  If no
candidate is stable the fallback is flagged in the rule text.  Too low a u
lets non-tail days bias the fit; too high leaves too few points.

The fitted model uses the empirical losses below u and the GPD above it, so
VaR/ES exist at every sidebar level.  Probability masses add up by
construction: (n - N_u)/n for the body, N_u/n for the tail.  Below u, VaR
follows the historical convention and ES integrates the empirical step
quantile, exactly as historical simulation does.  Once VaR lies above u they
are the POT formulas (McNeil, Frey & Embrechts 2015, ch. 5):
    VaR_a = u + sigma/xi * (((1 - a) n / N_u)^(-xi) - 1)
    ES_a  = (VaR_a + sigma - xi u) / (1 - xi)
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import integrate, optimize
from . import settings as S
from .validation import ModelFitError, check_alpha, check_sample, require_n
from .var_es import LossModel, tail_integral


@dataclass
class GPDFit:
    u: float          # threshold, in loss units
    xi: float         # shape (tail index)
    sigma: float      # scale
    n_exceed: int     # N_u
    n: int            # sample size
    nll: float = np.nan   # negative log-likelihood at the optimum

    @property
    def se(self) -> tuple[float, float]:
        """Asymptotic standard errors of (xi, sigma), valid only for xi > -0.5 (Smith 1987); NaN otherwise."""
        k, xi = self.n_exceed, self.xi
        if xi <= -0.5:
            return np.nan, np.nan
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


def gpd_ppf(p, xi: float, sigma: float):
    """GPD quantile function, the inverse of gpd_cdf."""
    p = np.asarray(p, dtype=float)
    if abs(xi) < 1e-9:
        return -sigma * np.log1p(-p)
    return sigma / xi * ((1 - p) ** (-xi) - 1)


def ks_distance(y, xi: float, sigma: float) -> float:
    """Kolmogorov-Smirnov distance between the excesses y and GPD(xi, sigma) (a distance, not a calibrated test)."""
    f = gpd_cdf(np.sort(y), xi, sigma)
    i = np.arange(1, len(f) + 1)
    return float(max((i / len(f) - f).max(), (f - (i - 1) / len(f)).max()))


def fit_gpd(losses, u: float) -> GPDFit:
    """
    Maximum-likelihood GPD for the excesses over u, started at the method of
    moments (Hosking & Wallis 1987).  Raises ModelFitError rather than return
    a fit the optimiser did not actually find.
    """
    losses = check_sample(losses, "losses")
    y = losses[losses > u] - u
    require_n(len(y), S.GPD_MIN_FIT, f"a GPD fit above u = {u:.4g}")
    if len(np.unique(y)) < 3:
        raise ModelFitError(f"excesses above u = {u:.4g} take fewer than 3 distinct values")
    m, v = y.mean(), y.var()
    xi0 = float(np.clip(0.5 * (1 - m * m / v), -0.4, 0.45))
    res = optimize.minimize(gpd_nll, [xi0, np.log(m * (1 - xi0))], args=(y,), method="Nelder-Mead",
                            options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
    xi, sigma = float(res.x[0]), float(np.exp(res.x[1]))
    if not (res.success and np.isfinite(res.fun) and np.isfinite(xi) and 0 < sigma < np.inf):
        raise ModelFitError(f"GPD likelihood did not converge at u = {u:.4g}: {res.message}")
    if np.any(1 + xi * y / sigma <= 0):
        raise ModelFitError(f"the GPD fitted at u = {u:.4g} does not cover the observed excesses")
    return GPDFit(float(u), xi, sigma, len(y), len(losses), float(res.fun))


class EVT(LossModel):
    """Loss distribution: empirical below the threshold u, GPD above it."""
    name = "evt"

    def __init__(self, losses, fit: GPDFit, scan: pd.DataFrame | None = None, rule: str = "fixed threshold u"):
        self.losses = np.sort(check_sample(losses, "losses"))
        self.n, self.fit, self.scan, self.rule = len(self.losses), fit, scan, rule
        self.zeta = fit.n_exceed / self.n            # P(L > u)
        if fit.xi >= 1:
            self.status = f"warning: xi = {fit.xi:.2f} >= 1, so log ES is infinite (dollar ES stays finite)"
        self.params = {"u": fit.u, "threshold_q": 1 - self.zeta, "n_exceed": fit.n_exceed,
                       "xi": fit.xi, "xi_se": fit.se[0], "sigma": fit.sigma, "threshold_rule": rule}

    def basis(self, alpha: float) -> str:
        """Which part of the model answers at this level: the label the dashboard shows beside the EVT number."""
        return "GPD tail" if 1 - check_alpha(alpha) <= self.zeta else "empirical body below the EVT threshold"

    def _tail_var(self, p: float) -> float:
        """GPD quantile for an exceedance probability p <= zeta."""
        f = self.fit
        if abs(f.xi) < 1e-9:
            return f.u + f.sigma * np.log(self.zeta / p)
        return f.u + f.sigma / f.xi * ((p / self.zeta) ** (-f.xi) - 1)

    def var(self, alpha: float) -> float:
        a = check_alpha(alpha)
        if 1 - a > self.zeta:                        # below the threshold: the data speak for themselves
            return float(np.quantile(self.losses, a, method=S.QUANTILE_METHOD))
        return float(self._tail_var(1 - a))

    def es(self, alpha: float) -> float:
        a, f = check_alpha(alpha), self.fit
        if f.xi >= 1:
            return np.inf                            # the tail is too heavy for a finite mean
        if 1 - a <= self.zeta:
            return float((self._tail_var(1 - a) + f.sigma - f.xi * f.u) / (1 - f.xi))
        tail = self.zeta * (f.u + f.sigma / (1 - f.xi))       # mass zeta times E[L | L > u] under the GPD
        return float((tail_integral(self.losses, a, 1 - self.zeta) + tail) / (1 - a))

    def tail_mean(self, alpha: float, transform) -> float:
        """Body: exact empirical integral; tail: quadrature over the GPD quantile (bounded for dollar losses)."""
        a = check_alpha(alpha)
        tail, _ = integrate.quad(lambda p: transform(self._tail_var(1 - p)), max(a, 1 - self.zeta), 1, limit=200)
        body = tail_integral(transform(self.losses), a, 1 - self.zeta) if a < 1 - self.zeta else 0.0
        return float((body + tail) / (1 - a))


def threshold_scan(losses, grid=S.EVT_THRESHOLD_GRID, min_exceed: int = S.EVT_MIN_EXCEED,
                   alphas=(0.99,), dollar_es: bool = False) -> pd.DataFrame:
    """
    Diagnostics for every candidate threshold with at least min_exceed
    exceedances; one row per percentile q.  Failed fits stay in the table
    (fit_ok False, reason in 'note') and are never selected.  dollar_es adds
    the exact dollar ES as a fraction of NAV for each candidate.
    """
    losses = check_sample(losses, "losses")
    cols = ["q", "u", "n_exceed", "fit_ok", "note", "mean_excess", "xi", "xi_se", "sigma", "sigma_star", "ks"]
    cols += [f"{m}_{a:g}" for a in alphas for m in (("var", "es", "es_fraction") if dollar_es else ("var", "es"))]
    rows = []
    for q in grid:
        u = float(np.quantile(losses, q, method=S.QUANTILE_METHOD))
        y = losses[losses > u] - u
        if len(y) < min_exceed:
            continue
        row = {"q": float(q), "u": u, "n_exceed": len(y), "mean_excess": float(y.mean())}
        try:
            fit = fit_gpd(losses, u)
        except ModelFitError as err:
            rows.append({**row, "fit_ok": False, "note": str(err)})
            continue
        model = EVT(losses, fit)
        row.update(fit_ok=True, note="", xi=fit.xi, xi_se=fit.se[0], sigma=fit.sigma,
                   sigma_star=fit.sigma - fit.xi * u, ks=ks_distance(y, fit.xi, fit.sigma))
        for a in alphas:
            row[f"var_{a:g}"], row[f"es_{a:g}"] = model.var(a), model.es(a)
            if dollar_es:
                row[f"es_fraction_{a:g}"] = model.es_fraction(a)
        rows.append(row)
    scan = pd.DataFrame(rows, columns=cols)
    scan["fit_ok"] = scan["fit_ok"].astype(bool)
    ok = np.flatnonzero(scan["fit_ok"].to_numpy())
    xi, se = scan["xi"].to_numpy(dtype=float), scan["xi_se"].to_numpy(dtype=float)
    stable = np.zeros(len(scan), dtype=bool)
    for k, i in enumerate(ok):
        higher = ok[k + 1:]
        stable[i] = len(higher) >= S.EVT_STABILITY_MIN_HIGHER and bool(
            np.all(np.abs(xi[higher] - xi[i]) <= S.EVT_STABILITY_Z * se[higher]))
    scan["stable"] = stable
    return scan


def select_threshold(scan: pd.DataFrame) -> pd.Series:
    """
    Lowest KS distance among stable thresholds, ties to the lower threshold.
    With no stable candidate it falls back to the lowest KS distance among
    valid fits and says so in the returned row's 'rule'.
    """
    valid = scan[scan["fit_ok"]]
    if valid.empty:
        raise ModelFitError("no candidate threshold has enough exceedances and a valid GPD fit")
    stable = valid[valid["stable"]]
    pool, rule = ((stable, "lowest KS distance among stable thresholds") if len(stable) else
                  (valid, "FALLBACK: no stable threshold, so lowest KS distance among valid fits"))
    row = scan.loc[pool["ks"].idxmin()].copy()
    row["rule"] = rule
    return row


def fit_evt(losses, u: float | None = None, threshold_q: float | None = None) -> EVT:
    """EVT model.  Give u or threshold_q to fix the threshold; otherwise the scan rule chooses it."""
    losses = check_sample(losses, "losses")
    require_n(len(losses), S.EVT_MIN_EXCEED, "an EVT fit")
    scan, rule = None, "fixed threshold u"
    if u is None:
        if threshold_q is None:
            scan = threshold_scan(losses)
            chosen = select_threshold(scan)
            threshold_q, rule = float(chosen["q"]), str(chosen["rule"])
        else:
            rule = f"fixed percentile q = {threshold_q:.4g}"
        u = float(np.quantile(losses, threshold_q, method=S.QUANTILE_METHOD))
    return EVT(losses, fit_gpd(losses, u), scan, rule)
