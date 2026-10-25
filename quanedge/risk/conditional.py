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
             empirical quantiles of -z, rescaled by tomorrow's sigma.
  garch_evt  the EVT model fitted to -z (top 10%, as in McNeil & Frey),
             rescaled by tomorrow's sigma.
GARCH is estimated by Gaussian quasi-maximum likelihood, which estimates the
volatility consistently even though z is fat-tailed; the tail itself is left
to the empirical or EVT model rather than assumed.
"""
from dataclasses import dataclass
import numpy as np
from arch import arch_model
from . import settings as S
from .evt import fit_evt
from .var_es import Empirical


@dataclass
class GarchFilter:
    mu: float
    omega: float
    alpha: float
    gamma: float
    beta: float
    sigma: np.ndarray        # in-sample conditional volatility, log-return units
    z: np.ndarray            # standardised residuals
    sigma_next: float = np.nan   # one-day-ahead volatility forecast

    def next_sigma(self, sigma_t: float, r_t: float) -> float:
        """GJR recursion: tomorrow's volatility from today's volatility and return."""
        eps = r_t - self.mu
        return float(np.sqrt(self.omega + (self.alpha + self.gamma * (eps < 0)) * eps ** 2
                             + self.beta * sigma_t ** 2))


def fit_filter(r) -> GarchFilter:
    r = np.asarray(r, dtype=float)
    res = arch_model(100 * r, mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="normal",
                     rescale=False).fit(disp="off", show_warning=False)   # percent returns: well-scaled optimiser
    p = res.params
    sig = np.asarray(res.conditional_volatility) / 100
    mu = p["mu"] / 100
    f = GarchFilter(mu, p["omega"] / 1e4, p["alpha[1]"], p["gamma[1]"], p["beta[1]"], sig, (r - mu) / sig)
    f.sigma_next = f.next_sigma(sig[-1], r[-1])
    return f


class Conditional:
    """Tomorrow's loss distribution, r = mu + sigma_next z, built from a loss model for -z."""

    def __init__(self, name: str, base, filt: GarchFilter):
        self.name, self.base, self.filter = name, base, filt
        self.params = {"mu": filt.mu, "omega": filt.omega, "alpha": filt.alpha, "gamma": filt.gamma,
                       "beta": filt.beta, "sigma_next": filt.sigma_next,
                       **{f"z_{k}": v for k, v in base.params.items()}}

    def var(self, alpha: float) -> float:
        return float(-self.filter.mu + self.filter.sigma_next * self.base.var(alpha))

    def es(self, alpha: float) -> float:
        return float(-self.filter.mu + self.filter.sigma_next * self.base.es(alpha))


def fhs(filt: GarchFilter) -> Conditional:
    return Conditional("fhs", Empirical(-filt.z, "fhs_z"), filt)


def garch_evt(filt: GarchFilter, threshold_q: float = S.GARCH_EVT_THRESHOLD_Q) -> Conditional:
    return Conditional("garch_evt", fit_evt(-filt.z, threshold_q=threshold_q), filt)
