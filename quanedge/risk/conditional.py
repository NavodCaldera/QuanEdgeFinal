"""
Regime-conditioned risk (the brief's own example of an "innovation").

Daily losses are not independent draws: calm and turbulent periods cluster.
A full-sample VaR is therefore too high in calm markets and too low when a
crisis starts, and its breaches arrive in bunches, which Christoffersen's
independence test punishes.  Following McNeil & Frey (2000), the portfolio
return is filtered with a GJR-GARCH(1,1) (Glosten, Jagannathan & Runkle 1993:
falls raise volatility more than rises of the same size),
    r_t = mu + sigma_t z_t,
    sigma_t^2 = omega + (alpha + gamma 1[eps_{t-1} < 0]) eps_{t-1}^2 + beta sigma_{t-1}^2,
and the standardised residuals z_t, close to i.i.d., carry the tail:
  fhs        filtered historical simulation (Barone-Adesi et al. 1999):
             empirical quantiles of -z, rescaled by the next day's sigma.
  garch_evt  the EVT model fitted to -z (top 10%, as in McNeil & Frey),
             rescaled by the next day's sigma.
"Next day" means the trading day after the last observation in the data,
which is not necessarily today.  GARCH is estimated by Gaussian quasi-maximum
likelihood, which estimates the volatility consistently even though z is
fat-tailed; the tail itself is left to the empirical or EVT model.  A fit that
did not converge, or whose parameters leave the variance domain, raises
ModelFitError: suppressed optimiser warnings are not taken as success.
"""
from dataclasses import dataclass
import numpy as np
from arch import arch_model
from . import settings as S
from .evt import fit_evt
from .validation import ModelFitError, check_sample, require_n
from .var_es import Empirical, LossModel


@dataclass
class GarchFilter:
    mu: float
    omega: float
    alpha: float
    gamma: float
    beta: float
    sigma: np.ndarray        # in-sample conditional volatility, log-return units
    z: np.ndarray            # standardised residuals
    sigma_next: float = np.nan   # volatility forecast for the day after the data end
    status: str = "ok"

    @property
    def persistence(self) -> float:
        return self.alpha + self.gamma / 2 + self.beta

    def next_sigma(self, sigma_t: float, r_t: float) -> float:
        """GJR recursion: the next day's volatility from this day's volatility and return."""
        eps = r_t - self.mu
        return float(np.sqrt(self.omega + (self.alpha + self.gamma * (eps < 0)) * eps ** 2
                             + self.beta * sigma_t ** 2))


def fit_filter(r) -> GarchFilter:
    r = check_sample(r, "returns")
    require_n(len(r), S.GARCH_MIN_OBS, "a GJR-GARCH filter")
    res = arch_model(100 * r, mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="normal",
                     rescale=False).fit(disp="off", show_warning=False)   # percent returns: well-scaled optimiser
    if res.convergence_flag != 0:
        raise ModelFitError(f"GJR-GARCH optimiser did not converge (flag {res.convergence_flag})")
    p = res.params
    omega, alpha, gamma, beta = p["omega"] / 1e4, p["alpha[1]"], p["gamma[1]"], p["beta[1]"]
    tol = 1e-6                                       # boundary solutions land within solver tolerance of a constraint
    if not (omega > 0 and alpha >= -tol and beta >= -tol and alpha + gamma >= -tol):
        raise ModelFitError("GJR-GARCH parameters fall outside the valid variance domain")
    alpha, beta = max(alpha, 0.0), max(beta, 0.0)
    gamma = max(gamma, -alpha)                       # keep alpha + gamma >= 0 exactly
    sig = np.asarray(res.conditional_volatility) / 100
    if not (np.isfinite(sig).all() and (sig > 0).all()):
        raise ModelFitError("GJR-GARCH produced a non-positive or non-finite volatility path")
    mu = p["mu"] / 100
    f = GarchFilter(mu, omega, alpha, gamma, beta, sig, (r - mu) / sig)
    f.sigma_next = f.next_sigma(sig[-1], r[-1])
    if f.persistence >= 1:
        f.status = f"warning: persistence {f.persistence:.3f} >= 1, so the variance does not mean-revert"
    return f


class Conditional(LossModel):
    """Loss distribution for the day after the data end, r = mu + sigma_next z, from a loss model for -z."""

    def __init__(self, name: str, base, filt: GarchFilter):
        self.name, self.base, self.filter = name, base, filt
        self.status = next((s for s in (filt.status, base.status) if s != "ok"), "ok")
        self.params = {"mu": filt.mu, "omega": filt.omega, "alpha": filt.alpha, "gamma": filt.gamma,
                       "beta": filt.beta, "persistence": filt.persistence, "sigma_next": filt.sigma_next,
                       **{f"z_{k}": v for k, v in base.params.items()}}

    def var(self, alpha: float) -> float:
        return float(-self.filter.mu + self.filter.sigma_next * self.base.var(alpha))

    def es(self, alpha: float) -> float:
        return float(-self.filter.mu + self.filter.sigma_next * self.base.es(alpha))

    def basis(self, alpha: float) -> str:
        return self.base.basis(alpha) if hasattr(self.base, "basis") else ""

    def tail_mean(self, alpha: float, transform) -> float:
        mu, s = self.filter.mu, self.filter.sigma_next
        return self.base.tail_mean(alpha, lambda x: transform(-mu + s * x))


def fhs(filt: GarchFilter) -> Conditional:
    return Conditional("fhs", Empirical(-filt.z, "fhs_z"), filt)


def garch_evt(filt: GarchFilter, threshold_q: float = S.GARCH_EVT_THRESHOLD_Q) -> Conditional:
    return Conditional("garch_evt", fit_evt(-filt.z, threshold_q=threshold_q), filt)
