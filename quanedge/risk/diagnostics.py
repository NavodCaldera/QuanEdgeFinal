"""
Evidence for or against each model's assumptions: the brief asks teams to
test the assumptions behind their risk models, not apply formulas blindly.
A test can reject its null hypothesis; failing to reject is not proof that
the assumption holds, and the conclusions are worded accordingly.
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.stattools import adfuller
from ..config import PORTFOLIO_VALUE, TRADING_DAYS
from .portfolio import loss_fraction, weight_vector

LAGS = 10


def describe(r: pd.Series) -> dict:
    x = r.to_numpy(dtype=float)
    return {"start": r.index[0].date(), "end": r.index[-1].date(), "n_days": len(x),
            "mean_daily": x.mean(), "vol_daily": x.std(ddof=1),
            "vol_annual": x.std(ddof=1) * np.sqrt(TRADING_DAYS),
            "skewness": stats.skew(x), "excess_kurtosis": stats.kurtosis(x),
            "worst_day": x.min(), "worst_day_date": r.idxmin().date(), "best_day": x.max()}


def _ljung_box(x, lags):
    lb = acorr_ljungbox(x, lags=[lags]).iloc[0]
    return float(lb["lb_stat"]), float(lb["lb_pvalue"])


def assumption_checks(r, z=None, lags: int = LAGS, level: float = 0.05) -> pd.DataFrame:
    """One row per assumption: the test, its null hypothesis, statistic, p-value and what that shows."""
    x = np.asarray(r, dtype=float)
    d = x - x.mean()
    jb = stats.jarque_bera(x)
    lm, lm_p, _, _ = het_arch(d, nlags=lags)
    adf_stat, adf_p = adfuller(x, autolag="AIC")[:2]
    # (assumption, used by, test, null hypothesis, statistic, p-value, is the null the assumption itself?)
    rows = [
        ("Returns are normal", "normal, mc_normal", "Jarque-Bera", "returns are normal",
         jb.statistic, jb.pvalue, True),
        ("No autocorrelation in returns", "all unconditional models", f"Ljung-Box Q({lags}) on r",
         f"no autocorrelation up to lag {lags}", *_ljung_box(x, lags), True),
        ("Constant volatility (no clustering)", "all unconditional models", f"Ljung-Box Q({lags}) on r^2",
         f"no autocorrelation in squared returns up to lag {lags}", *_ljung_box(d ** 2, lags), True),
        ("Constant volatility (no clustering)", "all unconditional models", f"ARCH-LM({lags})",
         "no ARCH effects", lm, lm_p, True),
        ("Returns are stationary", "all models", "ADF", "unit root (non-stationary)", adf_stat, adf_p, False),
    ]
    if z is not None:
        z = np.asarray(z, dtype=float)
        jbz = stats.jarque_bera(z)
        rows += [
            ("GARCH filter removed the clustering", "fhs, garch_evt", f"Ljung-Box Q({lags}) on z^2",
             f"no autocorrelation in squared residuals up to lag {lags}", *_ljung_box(z ** 2, lags), True),
            ("GARCH residuals are normal", "(why fhs/garch_evt model the residual tail)", "Jarque-Bera on z",
             "residuals are normal", jbz.statistic, jbz.pvalue, True),
        ]
    out = pd.DataFrame(rows, columns=["assumption", "used_by", "test", "null_hypothesis", "statistic",
                                      "p_value", "null_is_assumption"])
    rejected, is_assumption = out["p_value"] < level, out.pop("null_is_assumption")
    out["conclusion"] = np.select(
        [rejected & is_assumption, ~rejected & is_assumption, rejected & ~is_assumption],
        [f"null rejected at {level:.0%}: evidence against the assumption",
         f"null not rejected at {level:.0%}: no evidence against it (not proof)",
         f"null rejected at {level:.0%}: supports the assumption"],
        default=f"null not rejected at {level:.0%}: assumption not supported")
    return out


def worst_days(r: pd.Series, asset_r: pd.DataFrame | None = None, weights=None, n: int = 10,
               value: float = PORTFOLIO_VALUE) -> pd.DataFrame:
    """
    The n largest daily portfolio losses as simple losses (% of NAV and USD).
    With asset returns: the asset with the lowest return that day.  With
    weights as well: the asset that contributed most to the loss (weight x
    simple return), which differs from the lowest return when weights differ.
    """
    idx = r.nsmallest(n).index
    out = pd.DataFrame({"date": idx.date, "loss_pct": 100 * loss_fraction(-r[idx].to_numpy()),
                        "loss_usd": value * loss_fraction(-r[idx].to_numpy())})
    if asset_r is not None:
        a = asset_r.loc[idx]
        out["lowest_return_asset"] = a.idxmin(axis=1).to_numpy()
        out["lowest_asset_return_pct"] = 100 * np.expm1(a.min(axis=1).to_numpy())
        if weights is not None:
            contrib = np.expm1(a) * weight_vector(weights, a.columns)
            out["top_loss_contributor"] = contrib.idxmin(axis=1).to_numpy()
            out["top_contribution_pct"] = 100 * contrib.min(axis=1).to_numpy()
    return out


def in_sample_breaches(r, models: dict, alphas) -> pd.DataFrame:
    """
    How often the full-sample VaR of each unconditional model was exceeded
    inside the same sample.  A sanity check of fit, NOT a backtest (the
    out-of-sample tests are Person 4's, on rolling forecasts).  A model with
    no VaR gets blanks, not zero breaches.
    """
    losses = -np.asarray(r, dtype=float)
    rows = []
    for name, m in models.items():
        for a in alphas:
            v = m.var(a)
            hits = losses > v if np.isfinite(v) else None
            rows.append({"method": name, "alpha": a, "expected_pct": 100 * (1 - a),
                         "breach_pct": 100 * hits.mean() if hits is not None else np.nan,
                         "breaches": int(hits.sum()) if hits is not None else np.nan})
    return pd.DataFrame(rows)
