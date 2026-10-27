# Data Data Engineering & Provenance Report

Generated on 2026-10-27 07:57:38 UTC by `python -m quanedge.data.run`.

## Overview & Compliance
- **Investable Universe:** SPY, EFA, EEM, AGG, GLD, XLE, XLK (7 permitted ETFs, strict rubric compliance).
- **Sample Period:** 2005-01-03 to 2026-09-30 (5,470 trading days).
- **Adjustment Method:** Auto-adjusted close prices via yfinance (dividends and splits incorporated).
- **Data Sources:** Yahoo Finance (core universe), FRED (risk-free DTB3, Treasury DGS10, CPI, Fed Funds, VIX), World Bank (US GDP/Inflation).
- **Price snapshot:** `prices_dev.csv` (5,470 dates; 0 dropped by the common-calendar filter; SHA-256 `76bac76cbc98b5ce...`). Retrieval time and library version: see `data/clean/price_provenance.json`. Do not `--refresh` after the report numbers are frozen: adjusted history changes with every dividend.
- **Risk-free rate:** FRED DTB3 (discount basis) converted to a bond-equivalent yield before use.
- **Deleted Observations:** 0. Every flagged observation is retained and logged.

## Return-Series Stationarity Analysis (ADF, KPSS and ARCH-LM Tests)

The Augmented Dickey-Fuller (ADF) test evaluates the null hypothesis of a unit root ($H_0$: non-stationary) against the alternative of stationarity ($H_1$); it is run with a constant only. The KPSS test evaluates the null hypothesis of stationarity ($H_0$: stationary) against the alternative of a unit root. The ARCH-LM test (10 lags) has $H_0$: no conditional heteroskedasticity.

### Test Results Across Investable Universe

`ADF (AIC)` uses the lag chosen by AIC; `ADF (5 lags)` fixes the lag so assets are comparable. KPSS p-values are interpolated inside 0.01-0.10, so `>0.10` means the true value is at least 0.10.

| Asset | Series Type | ADF (AIC) Stat | ADF p-value | AIC lags | ADF (5 lags) Stat | ADF 5% Crit | KPSS Stat | KPSS p-value | ARCH-LM p-value | Statistical Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **SPY** | Log Price Levels ln(P_t) | 0.6438 | 0.9886 | 20 | 0.6602 | -2.8621 | — | — | — | `Non-Stationary I(1)` |
| **EFA** | Log Price Levels ln(P_t) | -0.6818 | 0.8514 | 20 | -0.6781 | -2.8621 | — | — | — | `Non-Stationary I(1)` |
| **EEM** | Log Price Levels ln(P_t) | -2.0014 | 0.2859 | 20 | -2.0895 | -2.8621 | — | — | — | `Non-Stationary I(1)` |
| **AGG** | Log Price Levels ln(P_t) | -1.9054 | 0.3295 | 22 | -1.9570 | -2.8621 | — | — | — | `Non-Stationary I(1)` |
| **GLD** | Log Price Levels ln(P_t) | -0.9736 | 0.7628 | 0 | -1.0381 | -2.8621 | — | — | — | `Non-Stationary I(1)` |
| **XLE** | Log Price Levels ln(P_t) | -1.2277 | 0.6616 | 29 | -1.5573 | -2.8621 | — | — | — | `Non-Stationary I(1)` |
| **XLK** | Log Price Levels ln(P_t) | 1.2438 | 0.9963 | 16 | 1.3047 | -2.8621 | — | — | — | `Non-Stationary I(1)` |
| **SPY** | Daily Log Returns r_t | -16.6255 | 1.68e-29 | 19 | -32.9557 | -2.8621 | 0.1989 | >0.10 | 0.00e+00 | `Stationary I(0)` |
| **EFA** | Daily Log Returns r_t | -16.1484 | 4.60e-29 | 19 | -32.2822 | -2.8621 | 0.0689 | >0.10 | 1.03e-297 | `Stationary I(0)` |
| **EEM** | Daily Log Returns r_t | -16.2109 | 3.99e-29 | 19 | -33.3350 | -2.8621 | 0.0638 | >0.10 | 0.00e+00 | `Stationary I(0)` |
| **AGG** | Daily Log Returns r_t | -15.6546 | 1.58e-28 | 21 | -31.6660 | -2.8621 | 0.3102 | >0.10 | 2.99e-145 | `Stationary I(0)` |
| **GLD** | Daily Log Returns r_t | -75.0381 | 0.0000 | 0 | -31.2263 | -2.8621 | 0.1604 | >0.10 | 1.42e-74 | `Stationary I(0)` |
| **XLE** | Daily Log Returns r_t | -14.4164 | 8.05e-27 | 28 | -30.7093 | -2.8621 | 0.0696 | >0.10 | 8.21e-271 | `Stationary I(0)` |
| **XLK** | Daily Log Returns r_t | -18.4308 | 2.17e-30 | 15 | -33.1535 | -2.8621 | 0.3614 | 0.0938 | 3.45e-239 | `Stationary I(0)` |
| **SPY** | Daily Simple Returns R_t | -18.4870 | 2.13e-30 | 17 | -33.3770 | -2.8621 | — | — | 2.94e-295 | `Stationary I(0)` |
| **EFA** | Daily Simple Returns R_t | -16.3223 | 3.12e-29 | 21 | -32.6200 | -2.8621 | — | — | 8.77e-283 | `Stationary I(0)` |
| **EEM** | Daily Simple Returns R_t | -16.5925 | 1.79e-29 | 19 | -33.8051 | -2.8621 | — | — | 0.00e+00 | `Stationary I(0)` |
| **AGG** | Daily Simple Returns R_t | -15.6327 | 1.68e-28 | 21 | -31.6639 | -2.8621 | — | — | 1.03e-163 | `Stationary I(0)` |
| **GLD** | Daily Simple Returns R_t | -75.1313 | 0.0000 | 0 | -31.1989 | -2.8621 | — | — | 3.86e-76 | `Stationary I(0)` |
| **XLE** | Daily Simple Returns R_t | -54.7752 | 0.0000 | 1 | -31.0182 | -2.8621 | — | — | 6.57e-272 | `Stationary I(0)` |
| **XLK** | Daily Simple Returns R_t | -18.6625 | 2.05e-30 | 15 | -33.4847 | -2.8621 | — | — | 1.06e-223 | `Stationary I(0)` |
| **EW-PLACEHOLDER** | Portfolio Daily Log Returns (equal-weight placeholder) | -16.6159 | 1.71e-29 | 21 | -32.7774 | -2.8621 | 0.0852 | >0.10 | 0.00e+00 | `Stationary I(0)` |

### Conclusions and Limits
- **Price levels are non-stationary, I(1):** the ADF p-value on log prices is at least 0.29 for all 7 ETFs, so the unit-root null is not rejected. Modelling price levels directly risks spurious relationships.
- **Return series reject a unit root:** ADF statistics on daily log returns range from -75.0 to -14.4 with AIC lags (largest p-value 8.1e-27) and from -33.3 to -30.7 with a fixed 5 lags, against a 5% critical value of about -2.86. KPSS does not reject stationarity at 5% for 7 of 7 ETFs.
- **Why GLD looks different:** AIC selected 0 lags for GLD returns, which pushes the ADF statistic towards -sqrt(N) (about -75). It is a lag-selection artefact, not stronger evidence; at a fixed lag GLD is comparable to the others.
- **Stationary in mean is not constant variance:** the ARCH-LM test rejects 'no ARCH effects' for every ETF (largest p-value 1.4e-74). Volatility clusters, which is why the risk models use conditional (GARCH-filtered) volatility. These tests do not validate normality or any tail model.
- **Scope:** unit-root and KPSS tests concern weak stationarity of the mean; they do not show strict stationarity. The brief asks for the check on the return series used for modelling, i.e. the portfolio. The equal-weight row is a PLACEHOLDER; rerun `test_portfolio_return_series` on the final recommended weights. Placeholder portfolio: ADF -16.62 (p 1.71e-29), ARCH-LM p 0.0e+00.

## Outlier & Anomaly Audit Summary
- **Total Flagged Anomalies:** 242
- **Flags on a date with a compiled event label:** 116 (labels are date-level and analyst-compiled; not verified per ticker)
- **Flags corroborated by at least one other asset (|z| >= 2, same direction, same date):** 219
See `data/clean/anomaly_log.csv` for the row-level log.

## Other Data-Quality Checks

| Check | Rule | Findings |
|---|---|---|
| STALE_PRICE_STREAK | >= 3 consecutive trading days with zero log return | 0 |
| SHARP_TWO_DAY_REVERSAL | |r| >= 6% on two consecutive days with opposite signs | 29 |
| VOLATILITY_REGIME_SHIFT | ICSS variance-break test per ticker (informational) | 7 |

Findings are in `data/clean/data_quality_log.csv`.

## Largest Flagged Moves

**Largest flagged losses**

| Date | Ticker | Log return | Simple return | Z-score | Date-level event label (not verified per ticker) |
|---|---|---|---|---|---|
| 2020-03-09 | XLE | -0.2249 | -20.14% | -11.98 | COVID-19 and oil price war: Saudi-Russia crude price war; NYSE circuit breaker triggered |
| 2008-10-15 | EEM | -0.1763 | -16.17% | -10.17 | GFC: recession fears reignite; deep global equity liquidation |
| 2008-10-15 | XLE | -0.1560 | -14.44% | -8.32 | GFC: recession fears reignite; deep global equity liquidation |
| 2008-10-09 | XLE | -0.1554 | -14.40% | -8.29 | GFC panic week: sharp sell-off in energy and commodity-linked equities |
| 2020-03-18 | XLE | -0.1550 | -14.36% | -8.26 | COVID-19: global dash for dollar cash; liquidation across asset classes including gold |
| 2020-03-16 | XLK | -0.1487 | -13.81% | -10.48 | COVID-19: emergency Fed cut to zero over the weekend; circuit breaker triggered |
| 2020-03-16 | XLE | -0.1463 | -13.61% | -7.80 | COVID-19: emergency Fed cut to zero over the weekend; circuit breaker triggered |
| 2008-11-05 | EEM | -0.1361 | -12.73% | -7.86 | GFC: post-US-election sell-off and emerging-market outflows |
| 2020-03-16 | EEM | -0.1333 | -12.48% | -7.69 | COVID-19: emergency Fed cut to zero over the weekend; circuit breaker triggered |
| 2020-03-12 | XLE | -0.1332 | -12.47% | -7.11 | COVID-19: WHO pandemic declaration and US-Europe travel restrictions; circuit breaker triggered |

**Largest flagged gains**

| Date | Ticker | Log return | Simple return | Z-score | Date-level event label (not verified per ticker) |
|---|---|---|---|---|---|
| 2008-10-13 | EEM | +0.2051 | +22.77% | +11.80 | GFC policy response: G7 and US Treasury announce bank recapitalisation; global relief rally |
| 2008-10-28 | EEM | +0.1901 | +20.93% | +10.93 | GFC: sharp short-covering rally from depressed levels |
| 2008-10-13 | XLE | +0.1525 | +16.48% | +8.09 | GFC policy response: G7 and US Treasury announce bank recapitalisation; global relief rally |
| 2020-03-24 | XLE | +0.1487 | +16.04% | +7.89 | COVID-19: Fed announces open-ended quantitative easing; relief rally |
| 2008-10-13 | EFA | +0.1475 | +15.89% | +11.14 | GFC policy response: G7 and US Treasury announce bank recapitalisation; global relief rally |

## Calendar & Holiday Audit
- Total trading sessions: 5,470
- Gap from 2006-12-29 to 2007-01-03 (5 days): National Day of Mourning for President Gerald R. Ford
- Gap from 2012-10-26 to 2012-10-31 (5 days): Hurricane Sandy: Emergency weather closure of NYSE and Nasdaq; Hurricane Sandy: Day 2 weather closure (first consecutive 2-day storm closure since 1888)
- Missing weekdays by class: {'STANDARD_HOLIDAY': 198, 'NON_STANDARD_CLOSURE': 5}
- Non-standard closure 2007-01-02: National Day of Mourning for President Gerald R. Ford
- Non-standard closure 2012-10-29: Hurricane Sandy: Emergency weather closure of NYSE and Nasdaq
- Non-standard closure 2012-10-30: Hurricane Sandy: Day 2 weather closure (first consecutive 2-day storm closure since 1888)
- Non-standard closure 2018-12-05: National Day of Mourning for President George H.W. Bush
- Non-standard closure 2025-01-09: National Day of Mourning for President Jimmy Carter
- Unexplained missing weekdays: none
- Full classification in `data/clean/calendar_audit.csv`.

## Macro Alignment
- Daily series forward-filled on 78 series-days (log: `data/clean/macro_ffill_log.csv`).
- CPIAUCSL becomes usable 1 month + 20 days after its reference month; FEDFUNDS 1 month after. No back-fill; series are carried from their full FRED history.
