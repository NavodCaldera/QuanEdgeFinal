# Institutional Data Dictionary — Serendib University Endowment Fund

**Mandate Size:** USD 10,000,000  
**Investment Objective:** Capital preservation, income generation, and sustainable real growth  
**Workstream:** Person 1 — Data Engineering & Reproducibility Lead  
**Last Updated:** October 2026 (Reproducible snapshot from 2005-01-03 to 2026-09-30)

---

## 1. Permitted Investable Universe

The endowment is restricted strictly to the 7 permitted exchange-traded funds (ETFs) defined in the SAIFA Quant Edge 1.0 competition brief. No other assets, leveraged ETFs, or undisclosed proxies are permitted.

| Ticker | Asset Name | Asset Class / Segment | Primary Exchange | Currency | Inception Date | Underlying Benchmark / Index | Endowment Strategic Role |
|---|---|---|---|---|---|---|---|
| **SPY** | SPDR S&P 500 ETF Trust | US Large-Cap Equities | NYSE Arca | USD | 1993-01-22 | S&P 500 Index | Core domestic growth and dividend income |
| **EFA** | iShares MSCI EAFE ETF | Developed International Equities | NYSE Arca | USD | 2001-08-14 | MSCI EAFE Index | Geographic diversification across Europe, Australasia, and Far East |
| **EEM** | iShares MSCI Emerging Markets ETF | Emerging Market Equities | NYSE Arca | USD | 2003-04-07 | MSCI Emerging Markets Index | High-growth potential, demographic tailwinds; higher tail risk |
| **AGG** | iShares Core U.S. Aggregate Bond ETF | US Investment-Grade Fixed Income | NYSE Arca | USD | 2003-09-22 | Bloomberg US Aggregate Bond Index | Capital preservation anchor, volatility dampener, reliable coupon income |
| **GLD** | SPDR Gold Shares | Real Assets / Precious Metals | NYSE Arca | USD | 2004-11-18 | LBMA Gold Price PM | Inflation hedge, fiat debasement buffer, crisis liquidity diversifier |
| **XLE** | Energy Select Sector SPDR Fund | Commodity / Energy Equities Proxy | NYSE Arca | USD | 1998-12-16 | Energy Select Sector Index | Real-asset inflation protection; high cyclical and tail risk |
| **XLK** | Technology Select Sector SPDR Fund | Technology Sector Equities | NYSE Arca | USD | 1998-12-16 | Technology Select Sector Index | Capital appreciation engine, productivity exposure; high valuation beta |

> **Timeline Justification:** All 7 ETFs have continuous, daily exchange-traded pricing starting November 18, 2004 (GLD listing date). The standard common clean sample begins **January 3, 2005** (the first trading session of 2005), yielding a contiguous, balanced panel of **5,470 trading days** (21.75 years) covering the 2008 GFC, 2010 Flash Crash, 2011 US Debt Downgrade, 2015 China/Oil Turmoil, March 2020 COVID Crash, and the 2022 Fed Rate-Hiking Cycle.

---

## 2. Core Datasets & File Inventory

All datasets are stored in `data/clean/` in human-readable and machine-parseable CSV format with full UTF-8 encoding. Cryptographic hashes and file schemas are recorded in `data/clean/data_manifest.json`.

| File Name | Description | Rows | Columns | Key Date Range |
|---|---|---|---|---|
| `prices_clean.csv` | Dividend- and split-adjusted daily closing prices | 5,470 | SPY, EFA, EEM, AGG, GLD, XLE, XLK | 2005-01-03 to 2026-09-30 |
| `log_returns.csv` | Continuously compounded daily log returns $r_{i,t} = \ln(P_{i,t}/P_{i,t-1})$ | 5,469 | SPY, EFA, EEM, AGG, GLD, XLE, XLK | 2005-01-04 to 2026-09-30 |
| `simple_returns.csv` | Discrete daily percentage returns $R_{i,t} = P_{i,t}/P_{i,t-1} - 1$ | 5,469 | SPY, EFA, EEM, AGG, GLD, XLE, XLK | 2005-01-04 to 2026-09-30 |
| `macro_clean.csv` | Aligned FRED risk-free rates, Treasury yields, CPI, Fed Funds, and VIX | 5,470 | DTB3, DGS10, CPIAUCSL, FEDFUNDS, VIXCLS, rf metrics | 2005-01-03 to 2026-09-30 |
| `worldbank_macro.csv` | Annual macroeconomic context (US GDP growth and CPI inflation); the latest year may be blank for one indicator until the World Bank publishes it | 66 | NY.GDP.MKTP.KD.ZG, FP.CPI.TOTL.ZG | 1960 to 2025 |
| `anomaly_log.csv` | Row-level log of all 242 flagged $\ge 4\sigma$ or $\ge 8\%$ moves | 242 | date, ticker, log_return, simple_return_pct, z_score, category, corroborating_assets, historical_context, label_source, disposition | 2006-05-15 to 2026-06-05 |
| `data_quality_log.csv` | Findings of the stale-price, sharp-reversal and variance-regime-shift checks | 36 | check, ticker, start_date, end_date, metric, value, detail, disposition | Full sample |
| `data_quality_checks.csv` | One row per data-quality check with its rule and number of findings (zero findings stay visible) | 3 | check, rule, findings | Full sample |
| `calendar_audit.csv` | Every weekday missing from the price file, classified as standard holiday, documented non-standard closure, or unexplained | 203 | date, weekday, classification, reason | 2005-01-03 to 2026-09-30 |
| `price_provenance.json` | Where the prices came from: source, snapshot SHA-256, dates before/after the common-calendar filter, installed library versions, and an explicit warning that the retrieval time of the committed snapshot is unknown | — | JSON | — |
| `macro_ffill_log.csv` | Every forward-fill of a daily FRED series on a trading day without a published value | 78 | date, series, day_of_week, filled_from_date, action | 2005-10-10 to 2026-09-30 |
| `stationarity_tests.csv` | ADF (AIC lag and fixed 5 lags), KPSS and ARCH-LM results for log prices, log returns, simple returns and an equal-weight placeholder portfolio | 22 | asset, series_type, adf_stat, adf_p_value, adf_lags, adf_stat_lag5, kpss_stat, kpss_p_value, kpss_p_capped, arch_lm_p_value, verdict | Full sample (5,470 days) |
| `data_manifest.json` | Cryptographic SHA-256 provenance manifest and environment metadata | — | Hierarchical JSON dictionary | Full repository snapshot |

---

## 3. Variable Definitions & Mathematical Specifications

### 3.1 Price Series (`prices_clean.csv`)
- **Unit:** US Dollars (USD) per share.
- **Adjustment Convention:** Auto-adjusted close prices via `yfinance`.
- **Mathematical Specification:**
  $$P_{\text{adj}, t} = P_{\text{raw}, t} \times \prod_{\tau > t} \left(1 - \frac{D_\tau}{P_{\text{raw}, \tau - 1}}\right) \times \prod_{\tau > t} S_\tau$$
  where $D_\tau$ is the per-share cash dividend distribution and $S_\tau$ is the split factor. This guarantees that return calculations reflect **Total Shareholder Return (TSR)** without artificial price drops on ex-dividend dates or stock splits.
- **Integrity Rule:** All prices strictly satisfy $P_{i,t} > 0.0$ and are finite numbers.

---

### 3.2 Return Series (`simple_returns.csv` & `log_returns.csv`)

#### Simple Returns ($R_{i,t}$):
- **Formula:**
  $$R_{i,t} = \frac{P_{i,t} - P_{i,t-1}}{P_{i,t-1}} = \frac{P_{i,t}}{P_{i,t-1}} - 1$$
- **Unit:** Decimal fraction (e.g., $0.0125 = +1.25\%$).
- **Institutional Role:** Simple returns are **linear across assets**. Portfolio-level return is the exact dot product of asset weights and simple returns:
  $$R_{p,t} = \sum_{i=1}^N w_{i,t} R_{i,t}$$
  Person 2 must use simple returns for cross-sectional portfolio aggregation and cash accounting.

#### Log Returns ($r_{i,t}$):
- **Formula:**
  $$r_{i,t} = \ln\left(\frac{P_{i,t}}{P_{i,t-1}}\right)$$
- **Unit:** Decimal fraction continuously compounded (e.g., $0.0125 = +1.25\%$ log return).
- **Institutional Role:** Log returns are **additive through time**:
  $$r_{i, t_1 \to t_T} = \sum_{t=t_1}^{t_T} r_{i,t}$$
  Person 3 and Person 4 must use log returns for time-series modeling (ADF stationarity, GARCH volatility clustering, VaR, Expected Shortfall, and Extreme Value Theory).

#### Mathematical Equivalence & Tolerance:
The exact mathematical identity holds:
$$r_{i,t} = \ln(1 + R_{i,t}) \iff R_{i,t} = \exp(r_{i,t}) - 1$$
The pipeline verifies that across all 38,283 return observations in the dataset:
$$\max_{i,t} \left| r_{i,t} - \ln(1 + R_{i,t}) \right| < 10^{-12}$$

#### Sign & Loss Conventions:
- **Returns ($R, r$):** Positive values represent investment profits/gains; negative values represent portfolio losses.
- **Loss Variable ($L$):** Following standard risk literature:
  $$L = -r_p$$
  A positive loss ($L > 0$) corresponds to a negative return.
- **Monetary NAV Loss ($USD$):** For mandate value $V = \$10,000,000$:
  $$\Delta V = V \times (1 - \exp(-L)) = V \times (-R_p)$$

---

### 3.3 Macroeconomic & Interest Rate Series (`macro_clean.csv`)

Approved data sources: Federal Reserve Economic Data (FRED), Federal Reserve Bank of St. Louis.

| Column Name | FRED Series ID | Description & Units | Frequency | Cleaning & Alignment Policy |
|---|---|---|---|---|
| `DTB3` | `DTB3` | 3-Month Treasury Bill Secondary Market Rate (Discount Basis, % annualized). Mandatory risk-free benchmark. | Daily | Last published value carried forward on bond market holidays (Columbus Day, Veterans Day) where stock exchanges traded; each fill is in `macro_ffill_log.csv`. |
| `DGS10` | `DGS10` | 10-Year Treasury Constant Maturity Yield (% annualized). Long-term benchmark discount rate. | Daily | Same as `DTB3`. |
| `CPIAUCSL` | `CPIAUCSL` | Consumer Price Index for All Urban Consumers: All Items (Index 1982-1984=100). | Monthly | Usable only from observation date + 1 month + 20 days (publication lag); the previous month's value is used until then. No back-fill. |
| `FEDFUNDS` | `FEDFUNDS` | Effective Federal Funds Rate (% annualized), monthly average. Federal Reserve monetary policy rate. | Monthly | Usable only from observation date + 1 month; the previous month's value is used until then. No back-fill. |
| `VIXCLS` | `VIXCLS` | CBOE Volatility Index (VIX Closing Level, % implied volatility). Equity stress indicator. | Daily | Carried forward on any trading day without a published value (none occurred in this sample). |
| `DTB3_bey` | Derived | DTB3 converted from discount basis to bond-equivalent yield (% , 365-day year): $100 \cdot 365\,d / (360 - 91\,d)$ with $d=\text{DTB3}/100$. Typically 0.1-0.2 pp above DTB3 at 4-5% rates. | Daily | The risk-free yield used everywhere (`load_risk_free_rate("annualized")`). |
| `rf_daily_effective` | Derived | Effective 252-day compounding daily risk-free rate: $(1 + \text{DTB3\_bey}/100)^{1/252} - 1$ | Daily | Unbiased daily reinvestment return for Sharpe/Sortino ratios. |
| `rf_daily_simple` | Derived | Nominal daily risk-free rate: $(\text{DTB3\_bey}/100) / 252$ | Daily | Linear daily interest accrual rate. |
| `rf_daily_log` | Derived | Daily log risk-free rate: $\ln(1 + \text{rf\_daily\_effective})$ | Daily | Used for excess log return calculations in risk models. |
| `term_spread_10y_3m` | Derived | Yield curve slope: $\text{DGS10} - \text{DTB3\_bey}$ (percentage points; both are yields) | Daily | Recession forecasting and macroeconomic stress indicator. |

---

### 3.4 World Bank Macro Context (`worldbank_macro.csv`)

Approved data sources: The World Bank Open Data API (Country: USA).

| Column Name | World Bank Indicator Code | Description | Frequency | Analytical Value |
|---|---|---|---|---|
| `NY.GDP.MKTP.KD.ZG` | `NY.GDP.MKTP.KD.ZG` | US Annual Real GDP Growth (%) | Annual | Macroeconomic growth baseline for endowment spending sustainability. |
| `FP.CPI.TOTL.ZG` | `FP.CPI.TOTL.ZG` | US Annual Consumer Price Inflation (%) | Annual | Benchmark for real purchasing power preservation ($r_{\text{real}} = r_{\text{nominal}} - \pi$). |

---

## 4. Market Calendar & Alignment Rules

### 4.1 Exchange Trading Calendar
All 7 permitted ETFs trade on US equity exchanges (NYSE Arca, Nasdaq) governed by the standard US National Market System (NMS) holiday calendar:
- New Year's Day
- Martin Luther King Jr. Day (3rd Monday of January)
- Washington's Birthday / Presidents' Day (3rd Monday of February)
- Good Friday (Friday before Easter)
- Memorial Day (Last Monday of May)
- Juneteenth National Independence Day (June 19, observed since 2022)
- Independence Day (July 4)
- Labor Day (1st Monday of September)
- Thanksgiving Day (4th Thursday of November)
- Christmas Day (December 25)

### 4.2 Non-Standard Unscheduled Closures
Five weekdays in the sample are absent from the price file without being scheduled holidays. All are documented in `NON_STANDARD_MARKET_CLOSURES` (`cleaning.py`):
1. **2007-01-02:** National Day of Mourning for President Gerald R. Ford.
2. **2012-10-29** and 3. **2012-10-30:** Hurricane Sandy emergency closures.
4. **2018-12-05:** National Day of Mourning for President George H.W. Bush.
5. **2025-01-09:** National Day of Mourning for President Jimmy Carter.

`calendar_audit.csv` classifies all 203 missing weekdays (198 scheduled holidays + these 5; 0 unexplained). Any future unexplained gap is flagged by the pipeline and fails a test.

### 4.3 Equity vs Bond Market Alignment Policy
On federal holidays where US equity exchanges are OPEN but US bond markets and the Federal Reserve are CLOSED (Columbus Day / Indigenous Peoples Day and Veterans Day):
- Equity ETF prices trade normally.
- FRED secondary market Treasury yields (`DTB3`, `DGS10`) are not published.
- **Rule:** the last published value is carried forward ($DTB3_t = DTB3_{t-1}$). All 78 occurrences are saved in `data/clean/macro_ffill_log.csv`.
- **Monthly series** (`CPIAUCSL`, `FEDFUNDS`) are aligned as-of with a publication lag (see 3.3), never back-filled.

---

## 5. Anomaly Detection & Zero-Deletion Governance

Competition Brief Section 9.2 mandates:
> *"Flag, don't silently delete, suspected data errors (stale/flat-lined prices, structural breaks, implausible jumps, large negatives) — outlier handling must be documented, not hidden."*

### 5.1 Checks
1. **Sigma Outliers:** $|r_{i,t} - \mu_i| \ge 4.0 \sigma_i$ (log returns, full-sample $\mu_i, \sigma_i$; for auditing only).
2. **Extreme Single-Day Return:** $|r_{i,t}| \ge 8.0\%$.
3. **Stale / Flatline Runs:** $\ge 3$ consecutive sessions with zero price change. *0 findings.*
4. **Reversals:** opposite-sign moves of $\ge 6.0\%$ on 2 consecutive days. *29 findings.*
5. **Variance regime shift:** ICSS test, one per ticker (informational; assumes i.i.d. returns).

Checks 1-2 are in `anomaly_log.csv`; checks 3-5 in `data_quality_log.csv`. No mean-level structural-break test is run.

### 5.2 Disposition & Retention
**242 events** met the outlier thresholds across 38,283 asset-day observations. **0 observations were deleted.** For each event the log states what was checked:
- `corroborating_assets`: other tickers with $|z| \ge 2$ in the same direction on the same date (219 of 242 events have at least one).
- `historical_context` / `label_source`: a date-level event label from an analyst-compiled list; **not verified per ticker against primary sources**. 116 events fall on a labelled date, 126 are unlabelled.

Largest moves (generated from the log; see also `results/data/top_tail_events.md`):

<!-- BEGIN top-tail-events -->
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
<!-- END top-tail-events -->

Silently deleting or winsorizing these points would suppress measured tail risk for the endowment. Asset-specific events without cross-asset corroboration remain open for manual review.
