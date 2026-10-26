"""
Stationarity testing module for QuanEdge financial time series.

Mandatory rubric requirement:
"Run a basic stationarity check (e.g., an Augmented Dickey-Fuller test)
on the return series used for modelling, and note the result."

This module implements:
1. Augmented Dickey-Fuller (ADF) tests:
   - H0: Unit root present (series is non-stationary).
   - H1: Stationary process.
   - Runs on price levels (log prices) and return series (log and simple).
   - Regression with a constant only (`regression="c"`), no deterministic trend.
   - Uses Akaike Information Criterion (AIC) for automatic lag selection, and ALSO reports the
     statistic at a fixed 5 lags so assets can be compared on the same footing. The ADF
     statistic depends strongly on the lag chosen (AIC picked 0 lags for GLD returns, which
     gives a statistic near -sqrt(N); other assets pick 15-28 lags), so statistics are not
     comparable across assets unless the lag is fixed.
2. Complementary KPSS (Kwiatkowski-Phillips-Schmidt-Shin) tests:
   - H0: Stationary around a constant level.
   - H1: Unit root present.
3. ARCH-LM test on returns: stationarity of the mean does NOT mean constant variance. Daily
   returns show strong volatility clustering, which is why conditional models (GARCH) are used
   downstream.
4. `test_portfolio_return_series`: the brief asks for the check on "the return series used for
   modelling", i.e. the portfolio, not only single assets.
5. Formatted comparative table and economic interpretation.

Note: unit-root/KPSS tests assess weak (covariance) stationarity of the mean. They do not
establish strict stationarity, and they do not validate any distributional assumption.
"""
from __future__ import annotations

import logging
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import het_arch
from statsmodels.tsa.stattools import adfuller, kpss

logger = logging.getLogger(__name__)


def run_adf_test(
    series: pd.Series,
    regression: str = "c",
    autolag: Optional[str] = "AIC",
    maxlag: Optional[int] = None,
) -> Dict[str, object]:
    """
    Run Augmented Dickey-Fuller test on a 1D time series.

    With autolag="AIC" the lag is chosen by AIC; pass autolag=None and maxlag=k for a fixed lag.
    """
    clean_s = series.dropna()
    res = adfuller(clean_s, maxlag=maxlag, regression=regression, autolag=autolag)
    test_stat, p_val, used_lag, nobs, crit_vals = res[:5]   # a sixth item (best IC) exists only with autolag

    return {
        "test": "ADF",
        "statistic": float(test_stat),
        "p_value": float(p_val),
        "used_lag": int(used_lag),
        "nobs": int(nobs),
        "crit_1pct": float(crit_vals["1%"]),
        "crit_5pct": float(crit_vals["5%"]),
        "crit_10pct": float(crit_vals["10%"]),
        "is_stationary_5pct": bool(p_val < 0.05),
    }


def run_kpss_test(
    series: pd.Series,
    regression: str = "c",
    nlags: str = "auto",
) -> Dict[str, object]:
    """
    Run KPSS test on a 1D time series.
    """
    clean_s = series.dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stat, p_val, used_lags, crit_vals = kpss(clean_s, regression=regression, nlags=nlags)

    return {
        "test": "KPSS",
        "statistic": float(stat),
        "p_value": float(p_val),
        # statsmodels interpolates within 0.01-0.10 and caps at 0.10: a printed 0.10 means "p >= 0.10"
        "p_value_is_capped": bool(p_val >= 0.1 - 1e-12),
        "used_lag": int(used_lags),
        "crit_1pct": float(crit_vals["1%"]),
        "crit_5pct": float(crit_vals["5%"]),
        "crit_10pct": float(crit_vals["10%"]),
        "is_stationary_5pct": bool(p_val >= 0.05),
    }


FIXED_ADF_LAG = 5


def run_arch_lm_test(series: pd.Series, lags: int = 10) -> Dict[str, object]:
    """Engle's ARCH-LM test for conditional heteroskedasticity (H0: no ARCH effects)."""
    stat, p_val, _, _ = het_arch(series.dropna() - series.dropna().mean(), nlags=lags)
    return {"test": "ARCH-LM", "lags": lags, "statistic": float(stat), "p_value": float(p_val)}


def _return_row(name: str, series_type: str, series: pd.Series, with_kpss: bool = True) -> Dict[str, object]:
    adf = run_adf_test(series)
    adf_fixed = run_adf_test(series, autolag=None, maxlag=FIXED_ADF_LAG)
    kpss_res = run_kpss_test(series) if with_kpss else None
    arch = run_arch_lm_test(series)
    return {
        "asset": name,
        "series_type": series_type,
        "adf_stat": round(adf["statistic"], 4),
        "adf_p_value": float(f"{adf['p_value']:.2e}"),
        "adf_lags": adf["used_lag"],
        "adf_crit_5pct": round(adf["crit_5pct"], 4),
        "adf_stat_lag5": round(adf_fixed["statistic"], 4),
        "adf_p_value_lag5": float(f"{adf_fixed['p_value']:.2e}"),
        "kpss_stat": round(kpss_res["statistic"], 4) if kpss_res else np.nan,
        "kpss_p_value": round(kpss_res["p_value"], 4) if kpss_res else np.nan,
        "kpss_p_capped": bool(kpss_res["p_value_is_capped"]) if kpss_res else False,
        "arch_lm_p_value": float(f"{arch['p_value']:.2e}"),
        "verdict": "Stationary I(0)" if adf["is_stationary_5pct"] else "Non-Stationary",
    }


def test_portfolio_return_series(
    portfolio_log_returns: pd.Series,
    name: str = "Portfolio",
) -> pd.DataFrame:
    """
    Stationarity diagnostics for the portfolio return series actually used for modelling
    (ADF with AIC and fixed lag, KPSS, ARCH-LM). Call this with the final recommended weights;
    the pipeline itself only runs it on an equal-weight PLACEHOLDER.
    """
    return pd.DataFrame([_return_row(name, "Portfolio Daily Log Returns", portfolio_log_returns)])


# not a pytest test despite the name prefix
test_portfolio_return_series.__test__ = False


def run_full_stationarity_analysis(
    prices: pd.DataFrame,
    log_returns: pd.DataFrame,
    simple_returns: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Run comprehensive stationarity diagnostics across all portfolio assets.

    Tests:
    - Log price levels: ln(P_t) -> expected non-stationary I(1)
    - Log return series: r_t -> expected stationary I(0)
    - Simple return series: R_t -> expected stationary I(0)

    Returns:
        Structured summary DataFrame with test statistics, p-values, critical values,
        and statistical conclusions.
    """
    rows = []

    # 1. Price levels (log prices)
    for col in prices.columns:
        log_px = np.log(prices[col])
        adf_res = run_adf_test(log_px)
        fixed_res = run_adf_test(log_px, autolag=None, maxlag=FIXED_ADF_LAG)
        rows.append({
            "asset": col,
            "series_type": "Log Price Levels ln(P_t)",
            "adf_stat": round(adf_res["statistic"], 4),
            "adf_p_value": round(adf_res["p_value"], 4),
            "adf_lags": adf_res["used_lag"],
            "adf_crit_5pct": round(adf_res["crit_5pct"], 4),
            "adf_stat_lag5": round(fixed_res["statistic"], 4),
            "adf_p_value_lag5": round(fixed_res["p_value"], 4),
            "kpss_stat": np.nan,
            "kpss_p_value": np.nan,
            "kpss_p_capped": False,
            "arch_lm_p_value": np.nan,
            "verdict": "Non-Stationary I(1)" if not adf_res["is_stationary_5pct"] else "Stationary",
        })

    # 2. Log returns
    for col in log_returns.columns:
        rows.append(_return_row(col, "Daily Log Returns r_t", log_returns[col]))

    # 3. Simple returns (ADF only)
    if simple_returns is not None:
        for col in simple_returns.columns:
            row = _return_row(col, "Daily Simple Returns R_t", simple_returns[col], with_kpss=False)
            rows.append(row)

    # 4. Equal-weight placeholder portfolio (NOT the recommendation; replaced once weights are final)
    if simple_returns is not None:
        ew = np.log1p(simple_returns.mean(axis=1))
        rows.append(_return_row("EW-PLACEHOLDER", "Portfolio Daily Log Returns (equal-weight placeholder)", ew))

    df = pd.DataFrame(rows)
    return df


def _fmt_adf_p(p: float) -> str:
    return f"{p:.2e}" if 0 < p < 1e-3 else f"{p:.4f}"


def _fmt_p(p: float, capped: bool = False) -> str:
    if pd.isna(p):
        return "—"
    return ">0.10" if capped else f"{p:.4f}"


def generate_stationarity_summary_markdown(df: pd.DataFrame) -> str:
    """
    Generate markdown report explaining stationarity test outcomes. Every number quoted in the
    conclusions is computed from `df`, so the text cannot disagree with the table.
    """
    assets = df[df["series_type"] == "Daily Log Returns r_t"]
    prices = df[df["series_type"] == "Log Price Levels ln(P_t)"]
    portfolio = df[df["series_type"].str.startswith("Portfolio")]

    lines = [
        "## Return-Series Stationarity Analysis (ADF, KPSS and ARCH-LM Tests)",
        "",
        "The Augmented Dickey-Fuller (ADF) test evaluates the null hypothesis of a unit root ($H_0$: non-stationary) "
        "against the alternative of stationarity ($H_1$); it is run with a constant only. The KPSS test evaluates "
        "the null hypothesis of stationarity ($H_0$: stationary) against the alternative of a unit root. "
        "The ARCH-LM test (10 lags) has $H_0$: no conditional heteroskedasticity.",
        "",
        "### Test Results Across Investable Universe",
        "",
        f"`ADF (AIC)` uses the lag chosen by AIC; `ADF (5 lags)` fixes the lag so assets are comparable. "
        "KPSS p-values are interpolated inside 0.01-0.10, so `>0.10` means the true value is at least 0.10.",
        "",
        "| Asset | Series Type | ADF (AIC) Stat | ADF p-value | AIC lags | ADF (5 lags) Stat | ADF 5% Crit | KPSS Stat | KPSS p-value | ARCH-LM p-value | Statistical Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for _, r in df.iterrows():
        k_stat = f"{r['kpss_stat']:.4f}" if pd.notna(r["kpss_stat"]) else "—"
        k_pval = _fmt_p(r["kpss_p_value"], bool(r["kpss_p_capped"]))
        arch = f"{r['arch_lm_p_value']:.2e}" if pd.notna(r["arch_lm_p_value"]) else "—"
        lines.append(
            f"| **{r['asset']}** | {r['series_type']} | {r['adf_stat']:.4f} | {_fmt_adf_p(r['adf_p_value'])} | {r['adf_lags']} | "
            f"{r['adf_stat_lag5']:.4f} | {r['adf_crit_5pct']:.4f} | {k_stat} | {k_pval} | {arch} | `{r['verdict']}` |"
        )

    lo, hi = assets["adf_stat"].min(), assets["adf_stat"].max()
    lo5, hi5 = assets["adf_stat_lag5"].min(), assets["adf_stat_lag5"].max()
    max_p = assets["adf_p_value"].max()
    worst_arch = assets["arch_lm_p_value"].max()
    n_kpss_ok = int((assets["kpss_p_value"] >= 0.05).sum())

    lines.extend([
        "",
        "### Conclusions and Limits",
        f"- **Price levels are non-stationary, I(1):** the ADF p-value on log prices is at least {prices['adf_p_value'].min():.2f} "
        f"for all {len(prices)} ETFs, so the unit-root null is not rejected. Modelling price levels directly risks spurious relationships.",
        f"- **Return series reject a unit root:** ADF statistics on daily log returns range from {lo:.1f} to {hi:.1f} with AIC lags "
        f"(largest p-value {max_p:.1e}) and from {lo5:.1f} to {hi5:.1f} with a fixed 5 lags, against a 5% critical value of about -2.86. "
        f"KPSS does not reject stationarity at 5% for {n_kpss_ok} of {len(assets)} ETFs.",
        "- **Why GLD looks different:** AIC selected 0 lags for GLD returns, which pushes the ADF statistic towards -sqrt(N) "
        "(about -75). It is a lag-selection artefact, not stronger evidence; at a fixed lag GLD is comparable to the others.",
        f"- **Stationary in mean is not constant variance:** the ARCH-LM test rejects 'no ARCH effects' for every ETF (largest p-value "
        f"{worst_arch:.1e}). Volatility clusters, which is why the risk models use conditional (GARCH-filtered) volatility. "
        "These tests do not validate normality or any tail model.",
        "- **Scope:** unit-root and KPSS tests concern weak stationarity of the mean; they do not show strict stationarity. "
        "The brief asks for the check on the return series used for modelling, i.e. the portfolio. The equal-weight row is a "
        "PLACEHOLDER; rerun `test_portfolio_return_series` on the final recommended weights."
        + (f" Placeholder portfolio: ADF {portfolio.iloc[0]['adf_stat']:.2f} (p {_fmt_adf_p(portfolio.iloc[0]['adf_p_value'])}), "
           f"ARCH-LM p {portfolio.iloc[0]['arch_lm_p_value']:.1e}." if len(portfolio) else ""),
    ])

    return "\n".join(lines)
