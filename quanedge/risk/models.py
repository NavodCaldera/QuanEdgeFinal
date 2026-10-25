"""
Fit every risk model on one portfolio and tabulate VaR and ES side by side:
the shape the dashboard needs (brief §6: VaR, ES and the EVT estimate at the
same confidence level, so the gap between them is visible).
"""
import pandas as pd
from ..config import CONF_LEVELS, PORTFOLIO_VALUE
from . import settings as S
from . import evt, var_es
from .portfolio import loss_fraction, portfolio_log_returns

LABEL = {
    "historical": "Historical simulation",
    "normal": "Parametric (normal)",
    "student_t": "Parametric (Student-t)",
    "mc_normal": "Monte Carlo (normal)",
    "mc_t": "Monte Carlo (Student-t)",
    "evt": "EVT (POT-GPD)",
}
FAMILY = {
    "historical": "Historical", "normal": "Parametric", "student_t": "Parametric",
    "mc_normal": "Monte Carlo", "mc_t": "Monte Carlo", "evt": "EVT",
}
UNCONDITIONAL = ["historical", "normal", "student_t", "mc_normal", "mc_t", "evt"]
ALL_METHODS = UNCONDITIONAL


def fit_models(asset_log_returns: pd.DataFrame, weights, methods=None,
               n_sim: int = S.N_SIM, seed: int = S.SEED, evt_threshold_q: float | None = None) -> dict:
    """
    {method name: fitted model}; every model exposes .var(alpha), .es(alpha)
    and .params.  evt_threshold_q fixes the EVT threshold percentile (the
    bootstrap does this); by default the threshold rule in evt.py picks it.
    """
    methods = list(methods or ALL_METHODS)
    unknown = sorted(set(methods) - set(ALL_METHODS))
    if unknown:
        raise ValueError(f"unknown methods {unknown}; choose from {ALL_METHODS}")
    r = portfolio_log_returns(asset_log_returns, weights)
    build = {
        "historical": lambda: var_es.historical(r),
        "normal": lambda: var_es.Normal(r),
        "student_t": lambda: var_es.StudentT(r),
        "mc_normal": lambda: var_es.monte_carlo(asset_log_returns, weights, "normal", n_sim, seed),
        "mc_t": lambda: var_es.monte_carlo(asset_log_returns, weights, "t", n_sim, seed),
        "evt": lambda: evt.fit_evt(-r.to_numpy(), threshold_q=evt_threshold_q),
    }
    return {m: build[m]() for m in methods}


def risk_table(models: dict, alphas=CONF_LEVELS, value: float = PORTFOLIO_VALUE) -> pd.DataFrame:
    """One row per (method, confidence level): VaR and ES as log-loss, % of portfolio value and USD."""
    rows = []
    for name, m in models.items():
        for a in alphas:
            v, e = m.var(a), m.es(a)
            rows.append({
                "method": name, "label": LABEL.get(name, name), "family": FAMILY.get(name, ""),
                "alpha": a, "var": v, "es": e,
                "var_pct": 100 * loss_fraction(v), "es_pct": 100 * loss_fraction(e),
                "var_usd": value * loss_fraction(v), "es_usd": value * loss_fraction(e),
                "es_over_var": e / v,
            })
    return pd.DataFrame(rows)
