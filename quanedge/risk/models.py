"""
Fit every risk model on one portfolio and tabulate VaR and ES side by side:
the shape the dashboard needs (brief §6: VaR, ES and the EVT estimate at the
same confidence level, so the gap between them is visible).

A model that cannot be estimated becomes an Unavailable entry: NaN numbers
with the reason in 'status', never a silent zero or a stale value.
"""
from functools import cache
import numpy as np
import pandas as pd
from ..config import CONF_LEVELS, PORTFOLIO_VALUE
from . import settings as S
from . import conditional, evt, var_es
from .portfolio import loss_fraction, portfolio_log_returns
from .validation import ModelFitError, check_alpha, check_returns

LABEL = {
    "historical": "Historical simulation",
    "normal": "Parametric (normal)",
    "student_t": "Parametric (Student-t)",
    "mc_normal": "Monte Carlo (normal)",
    "mc_t": "Monte Carlo (Student-t)",
    "evt": "EVT (POT-GPD)",
    "fhs": "Filtered HS (GARCH)",
    "garch_evt": "GARCH-EVT",
}
FAMILY = {
    "historical": "Historical", "normal": "Parametric", "student_t": "Parametric",
    "mc_normal": "Monte Carlo", "mc_t": "Monte Carlo", "evt": "EVT",
    "fhs": "Conditional", "garch_evt": "Conditional",
}
UNCONDITIONAL = ["historical", "normal", "student_t", "mc_normal", "mc_t", "evt"]
CONDITIONAL = ["fhs", "garch_evt"]          # risk for the day after the data end, given its volatility
ALL_METHODS = UNCONDITIONAL + CONDITIONAL


class Unavailable:
    """Stand-in for a model that could not be fitted: every number is NaN and the reason is kept."""

    def __init__(self, name: str, reason: str):
        self.name, self.status, self.params = name, f"failed: {reason}", {}

    def var(self, alpha: float) -> float:
        return np.nan

    def es(self, alpha: float) -> float:
        return np.nan

    def es_fraction(self, alpha: float) -> float:
        return np.nan


def fit_models(asset_log_returns: pd.DataFrame, weights, methods=None,
               n_sim: int = S.N_SIM, seed: int = S.SEED, evt_threshold_q: float | None = None) -> dict:
    """
    {method name: fitted model}; every model exposes .var(alpha), .es(alpha),
    .es_fraction(alpha), .params and .status.  evt_threshold_q fixes the EVT
    threshold percentile (the bootstrap does this); by default the threshold
    rule in evt.py picks it.  Bad inputs raise; a model that cannot be fitted
    on valid inputs comes back as Unavailable.
    """
    methods = list(methods or ALL_METHODS)
    unknown = sorted(set(methods) - set(ALL_METHODS))
    if unknown:
        raise ValueError(f"unknown methods {unknown}; choose from {ALL_METHODS}")
    check_returns(asset_log_returns, min_rows=S.MIN_OBS)
    r = portfolio_log_returns(asset_log_returns, weights)

    @cache
    def garch():                            # one filter shared by both conditional models
        return conditional.fit_filter(r)

    build = {
        "historical": lambda: var_es.historical(r),
        "normal": lambda: var_es.Normal(r),
        "student_t": lambda: var_es.StudentT(r),
        "mc_normal": lambda: var_es.monte_carlo(asset_log_returns, weights, "normal", n_sim, seed),
        "mc_t": lambda: var_es.monte_carlo(asset_log_returns, weights, "t", n_sim, seed),
        "evt": lambda: evt.fit_evt(-r.to_numpy(), threshold_q=evt_threshold_q),
        "fhs": lambda: conditional.fhs(garch()),
        "garch_evt": lambda: conditional.garch_evt(garch()),
    }
    models = {}
    for m in methods:
        try:
            models[m] = build[m]()
        except (ModelFitError, np.linalg.LinAlgError) as err:
            models[m] = Unavailable(m, str(err))
    return models


def risk_table(models: dict, alphas=CONF_LEVELS, value: float = PORTFOLIO_VALUE) -> pd.DataFrame:
    """
    One row per (method, confidence level).  var and es are log-loss units;
    *_pct are percentage points of portfolio value and *_usd dollars of
    simple loss.  ES in % and USD averages each tail loss in dollars
    (es_fraction); it is not converted from log ES.  es_over_var is in log
    units and left blank when VaR is not positive.
    """
    if not (np.isfinite(value) and value > 0):
        raise ValueError(f"portfolio value must be a positive number, got {value!r}")
    rows = []
    for name, m in models.items():
        for a in map(check_alpha, alphas):
            v, e, ef = m.var(a), m.es(a), m.es_fraction(a)
            rows.append({
                "method": name, "label": LABEL.get(name, name), "family": FAMILY.get(name, ""),
                "alpha": a, "var": v, "es": e,
                "var_pct": 100 * loss_fraction(v), "es_pct": 100 * ef,
                "var_usd": value * loss_fraction(v), "es_usd": value * ef,
                "es_over_var": e / v if v > 0 else np.nan,
                "status": getattr(m, "status", "ok"),
            })
    return pd.DataFrame(rows)
