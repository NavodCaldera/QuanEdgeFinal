"""
"How confident are you in your risk estimates?" (brief §5)

Moving-block bootstrap: resample blocks of BOOT_BLOCK consecutive days of the
asset-return matrix (whole rows, so cross-asset dependence survives; whole
blocks, so short volatility clusters survive), refit every unconditional
model on each resampled history, and report the CI_LEVEL percentile interval
of each VaR and ES.  The EVT threshold is held at the full-sample percentile,
and Monte Carlo uses BOOT_N_SIM scenarios per resample, so the interval holds
simulation noise as well as estimation noise.  It does not measure model
risk, i.e. the cost of having picked the wrong model altogether.
"""
import numpy as np
import pandas as pd
from ..config import CONF_LEVELS, PORTFOLIO_VALUE
from . import settings as S
from .models import UNCONDITIONAL, fit_models
from .portfolio import loss_fraction


def block_bootstrap_index(n: int, block: int, rng) -> np.ndarray:
    """Row indices for one circular moving-block resample of length n."""
    starts = rng.integers(0, n, size=-(-n // block))
    return ((starts[:, None] + np.arange(block)) % n).ravel()[:n]


def bootstrap_intervals(asset_r: pd.DataFrame, weights, methods=UNCONDITIONAL, alphas=CONF_LEVELS,
                        reps: int = S.BOOT_REPS, block: int = S.BOOT_BLOCK, level: float = S.CI_LEVEL,
                        evt_threshold_q: float | None = None, seed: int = S.SEED) -> pd.DataFrame:
    """Percentile intervals of VaR and ES (log-loss units), one row per (method, alpha)."""
    if "evt" in methods and evt_threshold_q is None:
        evt_threshold_q = fit_models(asset_r, weights, ["evt"])["evt"].params["threshold_q"]
    rng = np.random.default_rng(seed)
    x = asset_r.reset_index(drop=True)
    draws = []
    for b in range(reps):
        idx = block_bootstrap_index(len(x), block, rng)
        models = fit_models(x.iloc[idx], weights, methods, n_sim=S.BOOT_N_SIM, seed=seed + 1 + b,
                            evt_threshold_q=evt_threshold_q)
        draws += [(name, a, m.var(a), m.es(a)) for name, m in models.items() for a in alphas]
    d = pd.DataFrame(draws, columns=["method", "alpha", "var", "es"])
    lo, hi = (1 - level) / 2, (1 + level) / 2
    g = d.groupby(["method", "alpha"])
    return pd.DataFrame({"var_lo": g["var"].quantile(lo), "var_hi": g["var"].quantile(hi),
                         "es_lo": g["es"].quantile(lo), "es_hi": g["es"].quantile(hi)}).reset_index()


def with_intervals(table: pd.DataFrame, intervals: pd.DataFrame, value: float = PORTFOLIO_VALUE) -> pd.DataFrame:
    """Merge bootstrap intervals into a risk_table, adding % and USD versions."""
    out = table.merge(intervals, on=["method", "alpha"], how="left")
    for col in ("var_lo", "var_hi", "es_lo", "es_hi"):
        out[f"{col}_pct"] = 100 * loss_fraction(out[col].to_numpy())
        out[f"{col}_usd"] = value * loss_fraction(out[col].to_numpy())
    return out
