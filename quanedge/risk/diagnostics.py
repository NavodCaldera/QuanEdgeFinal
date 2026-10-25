"""
Evidence for or against each model's assumptions: the brief asks teams to
test the assumptions behind their risk models, not apply formulas blindly.
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.stattools import adfuller
from ..config import PORTFOLIO_VALUE, TRADING_DAYS
from .portfolio import loss_fraction

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
    """One row per assumption: the test, its statistic and p-value, and whether the data support it."""
    x = np.asarray(r, dtype=float)
    d = x - x.mean()
    jb = stats.jarque_bera(x)
    lm, lm_p, _, _ = het_arch(d, nlags=lags)
    adf_stat, adf_p = adfuller(x, autolag="AIC")[:2]
    # (assumption, used by, test, statistic, p-value, does a small p-value mean the assumption FAILS?)
    rows = [
        ("Returns are normal", "normal, mc_normal", "Jarque-Bera", jb.statistic, jb.pvalue, True),
        ("No autocorrelation in returns", "all unconditional models", f"Ljung-Box Q({lags}) on r",
         *_ljung_box(x, lags), True),
        ("Constant volatility (no clustering)", "all unconditional models", f"Ljung-Box Q({lags}) on r^2",
         *_ljung_box(d ** 2, lags), True),
        ("Constant volatility (no clustering)", "all unconditional models", f"ARCH-LM({lags})", lm, lm_p, True),
        ("Returns are stationary", "all models", "ADF (H0: unit root)", adf_stat, adf_p, False),
    ]
    if z is not None:
        z = np.asarray(z, dtype=float)
        jbz = stats.jarque_bera(z)
        rows += [
            ("GARCH filter removed the clustering", "fhs, garch_evt", f"Ljung-Box Q({lags}) on z^2",
             *_ljung_box(z ** 2, lags), True),
            ("GARCH residuals are normal", "(why fhs/garch_evt model the residual tail)", "Jarque-Bera on z",
             jbz.statistic, jbz.pvalue, True),
        ]
    out = pd.DataFrame(rows, columns=["assumption", "used_by", "test", "statistic", "p_value", "small_p_rejects"])
    rejected = out["p_value"] < level
    out["supported"] = np.where(rejected == out.pop("small_p_rejects"), "no", "yes")
    return out


def worst_days(r: pd.Series, asset_r: pd.DataFrame | None = None, n: int = 10,
               value: float = PORTFOLIO_VALUE) -> pd.DataFrame:
    """The n largest daily portfolio losses, in % and USD, with the asset that fell most that day."""
    idx = r.nsmallest(n).index
    out = pd.DataFrame({"date": idx.date, "loss_pct": 100 * loss_fraction(-r[idx].to_numpy()),
                        "loss_usd": value * loss_fraction(-r[idx].to_numpy())})
    if asset_r is not None:
        a = asset_r.loc[idx]
        out["worst_asset"] = a.idxmin(axis=1).to_numpy()
        out["worst_asset_return_pct"] = 100 * np.expm1(a.min(axis=1).to_numpy())
    return out


def in_sample_breaches(r, models: dict, alphas) -> pd.DataFrame:
    """
    How often the full-sample VaR of each unconditional model was exceeded
    inside the same sample.  A sanity check of fit, NOT a backtest (the
    out-of-sample tests are Person 4's, on rolling forecasts).
    """
    losses = -np.asarray(r, dtype=float)
    rows = [{"method": name, "alpha": a, "expected_pct": 100 * (1 - a),
             "breach_pct": 100 * np.mean(losses > m.var(a)), "breaches": int(np.sum(losses > m.var(a)))}
            for name, m in models.items() for a in alphas]
    return pd.DataFrame(rows)
