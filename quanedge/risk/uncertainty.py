"""
"How confident are you in your risk estimates?" (brief §5)

Moving-block bootstrap: resample blocks of BOOT_BLOCK consecutive days of the
asset-return matrix (whole rows, so cross-asset dependence survives; whole
blocks, so short volatility clusters survive; blocks wrap around the sample
end), refit every unconditional model on each resampled history, and report
the CI_LEVEL percentile interval of each VaR and ES.  Dollar ES is recomputed
exactly inside every resample, never converted from a log-ES bound.

What the interval covers: estimation noise, plus simulation noise for Monte
Carlo (BOOT_N_SIM scenarios per resample).  What it leaves out: the EVT
threshold is held at the full-sample percentile (no re-selection), and model
risk, i.e. having picked the wrong model altogether.  Resamples in which a
model cannot be fitted are counted (reps_failed), never silently dropped.
"""
import numpy as np
import pandas as pd
from ..config import CONF_LEVELS, PORTFOLIO_VALUE
from . import settings as S
from .models import UNCONDITIONAL, Unavailable, fit_models
from .portfolio import loss_fraction
from .validation import check_alpha


def block_bootstrap_index(n: int, block: int, rng) -> np.ndarray:
    """Row indices for one circular moving-block resample of length n."""
    starts = rng.integers(0, n, size=-(-n // block))
    return ((starts[:, None] + np.arange(block)) % n).ravel()[:n]


def _percentile(values: pd.Series, p: float) -> float:
    """Linear percentile; the nearest draw instead when infinite draws make interpolation undefined."""
    x = values.to_numpy(dtype=float)
    return float(np.quantile(x, p, method="linear" if np.isfinite(x).all() else "inverted_cdf"))


def bootstrap_intervals(asset_r: pd.DataFrame, weights, methods=UNCONDITIONAL, alphas=CONF_LEVELS,
                        reps: int = S.BOOT_REPS, block: int = S.BOOT_BLOCK, level: float = S.CI_LEVEL,
                        evt_threshold_q: float | None = None, seed: int = S.SEED) -> pd.DataFrame:
    """
    One row per (method, alpha): percentile intervals of VaR and ES in log
    units (var_lo/var_hi, es_lo/es_hi), of exact dollar ES as a fraction of
    NAV (es_frac_lo/es_frac_hi), and how many resamples succeeded or failed.
    """
    methods, alphas = list(methods), [check_alpha(a) for a in alphas]
    fitted = list(methods)
    if "evt" in methods and evt_threshold_q is None:
        full = fit_models(asset_r, weights, ["evt"])["evt"]
        if isinstance(full, Unavailable):
            fitted.remove("evt")             # no full-sample threshold to hold fixed: reported as all failed
        else:
            evt_threshold_q = full.params["threshold_q"]
    rng = np.random.default_rng(seed)
    x = asset_r.reset_index(drop=True)
    draws = []
    for b in range(reps):
        idx = block_bootstrap_index(len(x), block, rng)
        models = fit_models(x.iloc[idx], weights, fitted, n_sim=S.BOOT_N_SIM, seed=seed + 1 + b,
                            evt_threshold_q=evt_threshold_q)
        draws += [(name, a, m.var(a), m.es(a), m.es_fraction(a))
                  for name, m in models.items() if not isinstance(m, Unavailable) for a in alphas]
    d = pd.DataFrame(draws, columns=["method", "alpha", "var", "es", "es_frac"])
    g = d.groupby(["method", "alpha"])
    keys = pd.MultiIndex.from_product([methods, alphas], names=["method", "alpha"])
    lo, hi = (1 - level) / 2, (1 + level) / 2
    out = pd.DataFrame({f"{col}_{tag}": g[col].agg(_percentile, p)
                        for col in ("var", "es", "es_frac") for tag, p in (("lo", lo), ("hi", hi))}).reindex(keys)
    out["reps_ok"] = g.size().reindex(keys).fillna(0).astype(int)
    out["reps_failed"] = reps - out["reps_ok"]
    return out.reset_index()


def with_intervals(table: pd.DataFrame, intervals: pd.DataFrame, value: float = PORTFOLIO_VALUE) -> pd.DataFrame:
    """Merge bootstrap intervals into a risk_table: VaR bounds converted from log loss, ES bounds from the dollar draws."""
    out = table.merge(intervals, on=["method", "alpha"], how="left")
    for col in ("var_lo", "var_hi"):
        out[f"{col}_pct"] = 100 * loss_fraction(out[col].to_numpy())
        out[f"{col}_usd"] = value * loss_fraction(out[col].to_numpy())
    for col in ("es_lo", "es_hi"):
        frac = out[col.replace("es_", "es_frac_")].to_numpy()
        out[f"{col}_pct"], out[f"{col}_usd"] = 100 * frac, value * frac
    return out
