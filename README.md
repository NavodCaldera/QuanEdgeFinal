# QuanEdgeFinal

Team Ghosted — SAIFA Quant Edge 1.0 final challenge.

## Competition objective

Build a transparent Python and Streamlit investment-risk application for a conservative university endowment managing a USD 10 million portfolio. The recommendation must prioritize capital preservation, explain downside risk, survive historical and hypothetical stress scenarios, and be supported by reproducible analysis.

Permitted assets: SPY, EFA, EEM, AGG, GLD, XLE, and XLK.

## Five-person workload split

Each person owns the deliverables below, but every member must understand and be able to defend the submitted code, assumptions, calculations, and recommendation. Use pull requests or clearly separated branches, and have at least one other member review every material result.

### Person 1 — Data engineering and reproducibility lead (Completed; independent review pending)

- Built the automated download and caching pipeline using `yfinance` for the 7 permitted ETFs (`SPY`, `EFA`, `EEM`, `AGG`, `GLD`, `XLE`, `XLK`); automated ingestion for risk-free proxy (`DTB3`) and macro data from St. Louis Fed FRED and World Bank Open Data.
- Ingested auto-adjusted close prices, verified calendar alignment across 5,470 common trading days (2005–2026), classified all 203 missing weekdays against the NYSE holiday calendar (198 scheduled holidays, 5 documented non-standard closures including the 2007, 2018 and 2025 days of mourning and Hurricane Sandy, 0 unexplained), and aligned FRED series as-of each trading day: bond-market holidays are forward-filled and logged, and monthly CPI and Fed Funds are used only after a publication lag, with no back-fill.
- Derived both simple returns (cross-sectional linear aggregation for Person 2) and continuously compounded log returns (time-series modeling for Persons 3–4); machine-verified mathematical identity $\max |r - \ln(1+R)| < 10^{-12}$.
- Implemented comprehensive stationarity diagnostics (Augmented Dickey-Fuller and KPSS tests); demonstrated price non-stationarity $I(1)$ and return-series stationarity $I(0)$ ($p < 10^{-26}$).
- Executed audit suite across 38,283 observations: flagged 242 events ($\ge 4\sigma$ or $\ge 8\%$), tested each for cross-asset corroboration, attached date-level event labels (analyst-compiled, not verified per ticker), saved the stale-price, sharp-reversal and variance-shift checks, and enforced a **strict 0-deletion rule** to preserve genuine tail risk.
- Published common clean datasets (`data/clean/`), institutional data dictionary (`data/data_dictionary.md`), cryptographic SHA-256 manifest (`data/clean/data_manifest.json`), and comprehensive technical documentation (`docs/person-1/01-data-pipeline.md`).

Primary outputs: `quanedge/data/`, `data/clean/`, `data/data_dictionary.md`, `tests/test_data_pipeline.py`, `docs/person-1/01-data-pipeline.md`, `results/data/data_summary.md`.

```bash
python -m quanedge.data.run              # Run full cleaning, stationarity, anomaly audit, manifest (11s)
python -m quanedge.data.run --refresh    # DELIBERATE ONLY: re-downloads everything; adjusted prices shift after dividends, so all figures change
python -m quanedge.data.run --check-only # Verify file hashes against cryptographic SHA-256 manifest
pytest tests/test_data_pipeline.py tests/test_data_quality.py tests/test_data_robustness.py   # Person 1 tests (63)
```

### Person 2 — Portfolio construction and performance lead

- Define the investment policy: horizon, target return, acceptable loss, risk limits, constraints, and suitability for a conservative endowment.
- Implement expected returns, volatility, correlations, covariance matrix, diversification analysis, Markowitz mean-variance optimisation, and CAPM comparisons.
- Compare candidate portfolios and justify the selected allocation and position sizes.
- Calculate and interpret cumulative return, Sharpe, Sortino, Treynor, Jensen's alpha, Information ratio, maximum drawdown, and Calmar ratio.
- Provide portfolio weights and performance series to the risk and Streamlit workstreams.

Primary outputs: portfolio-construction module, optimisation results, KPI tables/charts, investment-policy assumptions.

### Person 3 — VaR, Expected Shortfall, and EVT lead

- Implement historical, parametric, and Monte Carlo VaR at 90%, 95%, and 99% where applicable, with mandatory comparison at 95% and 99%.
- Implement Expected Shortfall and explain why it adds information beyond VaR for a conservative investor.
- Identify extreme negative returns, justify the EVT threshold, fit a Generalized Pareto or other appropriate tail model, and estimate extreme losses.
- Compare VaR, ES, and EVT results, including model assumptions and reasons for disagreement.
- Expose reusable functions and clearly documented inputs for the Streamlit dashboard.

Primary outputs: risk-measurement module, tail-risk tables, threshold diagnostics, VaR/ES/EVT charts and interpretation.

### Person 4 — Backtesting, stress testing, and risk-budgeting lead

- Create an out-of-sample backtest for the selected VaR model.
- Implement Kupiec proportion-of-failures, Christoffersen independence, and Basel traffic-light classification.
- Test the 2008 Global Financial Crisis, March 2020 COVID crash, and 2022 interest-rate hiking period.
- Design and justify one hypothetical scenario, then report portfolio return, dollar loss, asset-level effects, damage sources, and endowment acceptability.
- Calculate marginal VaR, component VaR, marginal Expected Shortfall, and risk contributions; recommend position-size or risk-budget changes where needed.

Primary outputs: validation module, crisis-scenario definitions, stress-test results, risk-contribution analysis, model-acceptability conclusions.

### Person 5 — Streamlit, communication, and integration lead

- Build the Streamlit application for a non-technical investment committee.
- Include sidebar controls for confidence level (90%, 95%, 99%), VaR method, backtest date range, and portfolio weights.
- Add the portfolio panel, cumulative-return and drawdown charts, side-by-side VaR/ES/EVT results, backtesting panel, traffic-light indicator, and stress-test panel.
- Add a clearly labelled **Assumptions & Limitations** page in plain language.
- Integrate all modules, manage the final user experience, and run end-to-end checks.
- Coordinate the 7–15-page technical report, one-page executive tear sheet, 10–12-minute presentation, final investment recommendation, and AI-use disclosure.

Primary outputs: Streamlit app, report, tear sheet, presentation, final recommendation, release checklist.

## Shared delivery sequence

1. **Foundation checkpoint:** Person 1 publishes the clean, reproducible dataset and Person 2 agrees the investment policy and portfolio interface.
2. **Model checkpoint:** Persons 2–4 independently produce tested modules using the shared data and standardised portfolio inputs.
3. **Integration checkpoint:** Person 5 connects the modules to Streamlit; all members verify numerical outputs against hand calculations or independent checks.
4. **Decision checkpoint:** The team agrees on one recommendation, one risk limit, and one consistent set of numbers across the app, report, tear sheet, and presentation.
5. **Defence checkpoint:** Every member rehearses the full pipeline and can explain data cleaning, assumptions, formulas, limitations, and AI-assisted components.

## Required submission checklist

- Public or judge-accessible GitHub repository with clean, documented, reproducible code.
- Working Streamlit application runnable locally with one command or deployed for judges.
- 7–15-page technical report/investment memorandum.
- One-page executive tear sheet.
- 10–12-minute live presentation if selected for the final five.
- AI disclosure covering tools used, purpose, human validation, and AI-assisted components.

## Technical requirements to keep visible

- Use only the permitted investment universe and approved data sources.
- Do not silently remove or manually edit observations; document all cleaning and outlier decisions.
- Use log returns for statistical analysis and explain any use of simple returns.
- Compare all three VaR methods, report ES, justify EVT threshold selection, and backtest the selected VaR model out of sample.
- Translate every metric into an actionable decision for a conservative endowment, including what could go wrong and how severe losses could be.

## Common clean dataset & data governance (Person 1)

Person 1's data pipeline is fully operational in [`quanedge/data/`](quanedge/data/). The common clean dataset covers **5,470 trading days** (2005-01-03 to 2026-09-30) across all 7 permitted ETFs, macroeconomic series, and risk-free benchmarks.

```bash
# 1. Reproduce or refresh clean datasets, stationarity tests, and anomaly logs:
python -m quanedge.data.run              # Run pipeline using cached snapshots (~11s)
python -m quanedge.data.run --refresh    # DELIBERATE ONLY (see data/clean/price_provenance.json): prices and every figure will change
python -m quanedge.data.run --check-only # Verify file hashes against SHA-256 cryptographic manifest

# 2. Run unit and integration tests:
python -m pytest -v
```

### Approved data sources & citations

Following Section 9.1 of the competition brief, all data originates from approved institutional open-access sources:
1. **Yahoo Finance (`yfinance` package):** Primary source for daily ETF open, high, low, close, volume, and auto-adjusted close prices for `SPY`, `EFA`, `EEM`, `AGG`, `GLD`, `XLE`, `XLK`. Auto-adjusted prices incorporate cash dividends and splits for true Total Shareholder Return (TSR).
2. **Federal Reserve Economic Data (FRED, Federal Reserve Bank of St. Louis):**
   - `DTB3`: 3-Month Treasury Bill Secondary Market Rate (Discount Basis, % annualized). Primary risk-free proxy; converted to a bond-equivalent yield (`DTB3_bey`) before use.
   - `DGS10`: 10-Year Treasury Constant Maturity Rate (% annualized). Long-term benchmark discount rate.
   - `CPIAUCSL`: Consumer Price Index for All Urban Consumers (Index 1982-1984=100). Inflation benchmark.
   - `FEDFUNDS`: Effective Federal Funds Rate (% annualized). Federal Reserve monetary policy rate.
   - `VIXCLS`: CBOE Volatility Index (Closing level). Equity market stress indicator.
3. **The World Bank Open Data:** US Real GDP Growth (`NY.GDP.MKTP.KD.ZG`) and CPI Inflation (`FP.CPI.TOTL.ZG`) for macroeconomic context.

### Permitted ETF universe & data dictionary summary

Full data specifications are documented in [`data/data_dictionary.md`](data/data_dictionary.md).

| Ticker | Asset Name | Asset Class / Segment | Currency | Exchange | Inception | Endowment Role |
|---|---|---|---|---|---|---|
| **SPY** | SPDR S&P 500 ETF Trust | US Large-Cap Equities | USD | NYSE Arca | 1993-01-22 | Core equity growth and dividend income |
| **EFA** | iShares MSCI EAFE ETF | Developed International Equities | USD | NYSE Arca | 2001-08-14 | Geographic diversification (Europe, Australasia, Far East) |
| **EEM** | iShares MSCI Emerging Markets ETF | Emerging Market Equities | USD | NYSE Arca | 2003-04-07 | High economic growth exposure; tail risk awareness |
| **AGG** | iShares Core U.S. Aggregate Bond ETF | US Investment-Grade Bonds | USD | NYSE Arca | 2003-09-22 | Capital preservation anchor, reliable coupon cash flow |
| **GLD** | SPDR Gold Shares | Real Assets / Precious Metals | USD | NYSE Arca | 2004-11-18 | Inflation hedge, purchasing power buffer, crisis liquidity |
| **XLE** | Energy Select Sector SPDR Fund | Energy / Commodity Equities | USD | NYSE Arca | 1998-12-16 | Natural resource inflation protection; high cyclical risk |
| **XLK** | Technology Select Sector SPDR Fund | Technology Sector Equities | USD | NYSE Arca | 1998-12-16 | Innovation engine, high valuation beta, long-duration growth |

### Stationarity tests (ADF, KPSS, ARCH-LM)

Full diagnostics are in [`data/clean/stationarity_tests.csv`](data/clean/stationarity_tests.csv) and [`results/data/data_summary.md`](results/data/data_summary.md). The table below is generated from that file and checked by a test.

<!-- BEGIN stationarity -->
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
| **AGG** | Daily Log Returns r_t | -15.6546 | 1.58e-28 | 21 | -31.6661 | -2.8621 | 0.3102 | >0.10 | 2.91e-145 | `Stationary I(0)` |
| **GLD** | Daily Log Returns r_t | -75.0381 | 0.0000 | 0 | -31.2263 | -2.8621 | 0.1604 | >0.10 | 1.42e-74 | `Stationary I(0)` |
| **XLE** | Daily Log Returns r_t | -14.4164 | 8.05e-27 | 28 | -30.7094 | -2.8621 | 0.0696 | >0.10 | 8.20e-271 | `Stationary I(0)` |
| **XLK** | Daily Log Returns r_t | -18.4308 | 2.17e-30 | 15 | -33.1535 | -2.8621 | 0.3614 | 0.0938 | 3.44e-239 | `Stationary I(0)` |
| **SPY** | Daily Simple Returns R_t | -18.4870 | 2.13e-30 | 17 | -33.3770 | -2.8621 | — | — | 2.92e-295 | `Stationary I(0)` |
| **EFA** | Daily Simple Returns R_t | -16.3223 | 3.12e-29 | 21 | -32.6200 | -2.8621 | — | — | 8.76e-283 | `Stationary I(0)` |
| **EEM** | Daily Simple Returns R_t | -16.5925 | 1.79e-29 | 19 | -33.8051 | -2.8621 | — | — | 0.00e+00 | `Stationary I(0)` |
| **AGG** | Daily Simple Returns R_t | -15.6327 | 1.68e-28 | 21 | -31.6640 | -2.8621 | — | — | 1.00e-163 | `Stationary I(0)` |
| **GLD** | Daily Simple Returns R_t | -75.1313 | 0.0000 | 0 | -31.1989 | -2.8621 | — | — | 3.86e-76 | `Stationary I(0)` |
| **XLE** | Daily Simple Returns R_t | -54.7752 | 0.0000 | 1 | -31.0182 | -2.8621 | — | — | 6.56e-272 | `Stationary I(0)` |
| **XLK** | Daily Simple Returns R_t | -18.6625 | 2.05e-30 | 15 | -33.4847 | -2.8621 | — | — | 1.06e-223 | `Stationary I(0)` |
| **EW-PLACEHOLDER** | Portfolio Daily Log Returns (equal-weight placeholder) | -16.6159 | 1.71e-29 | 21 | -32.7774 | -2.8621 | 0.0852 | >0.10 | 0.00e+00 | `Stationary I(0)` |

### Conclusions and Limits
- **Price levels are non-stationary, I(1):** the ADF p-value on log prices is at least 0.29 for all 7 ETFs, so the unit-root null is not rejected. Modelling price levels directly risks spurious relationships.
- **Return series reject a unit root:** ADF statistics on daily log returns range from -75.0 to -14.4 with AIC lags (largest p-value 8.1e-27) and from -33.3 to -30.7 with a fixed 5 lags, against a 5% critical value of about -2.86. KPSS does not reject stationarity at 5% for 7 of 7 ETFs.
- **Why GLD looks different:** AIC selected 0 lags for GLD returns, which pushes the ADF statistic towards -sqrt(N) (about -75). It is a lag-selection artefact, not stronger evidence; at a fixed lag GLD is comparable to the others.
- **Stationary in mean is not constant variance:** the ARCH-LM test rejects 'no ARCH effects' for every ETF (largest p-value 1.4e-74). Volatility clusters, which is why the risk models use conditional (GARCH-filtered) volatility. These tests do not validate normality or any tail model.
- **Scope:** unit-root and KPSS tests concern weak stationarity of the mean; they do not show strict stationarity. The brief asks for the check on the return series used for modelling, i.e. the portfolio. The equal-weight row is a PLACEHOLDER; rerun `test_portfolio_return_series` on the final recommended weights. Placeholder portfolio: ADF -16.62 (p 1.71e-29), ARCH-LM p 0.0e+00.
<!-- END stationarity -->

### Anomaly auditing & zero-deletion rule

- **Total Observations Scanned:** 38,283 asset-days.
- **Flagged Outliers ($\ge 4\sigma$ or $\ge 8\%$):** 242 events (219 corroborated by at least one other asset moving the same way on the same date).
- **Event labels:** 116 flags fall on a date with an analyst-compiled event label (e.g. Lehman, US downgrade, COVID circuit breakers, Brexit, 2025 tariffs). Labels are date-level and have not been verified per ticker against primary sources; 126 flags are unlabelled.
- **Other quality checks:** 0 stale-price runs, 29 sharp two-day reversals, and an informational variance-break test per ticker. See [`data/clean/data_quality_log.csv`](data/clean/data_quality_log.csv).
- **Deleted Observations:** **0**. All genuine market crashes are preserved to avoid artificially truncating tail risk. See [`data/clean/anomaly_log.csv`](data/clean/anomaly_log.csv).

## Risk measurement module (Person 3)

VaR, Expected Shortfall, and EVT live in [`quanedge/risk/`](quanedge/risk/). Prices now come from Person 1's clean dataset (via the `dev_data` adapter), but the **weights are still equal-weight placeholders** until Person 2 delivers, so the numbers are not yet a recommendation.

```bash
pip install -r requirements.txt
python -m quanedge.data.run           # rebuild/verify the common clean dataset (Person 1)
python -m quanedge.risk.run           # tables, figures, summary and manifest in results/risk/ (a few minutes)
python -m quanedge.risk.run --quick   # fast look in results/risk_quick/: 50 resamples, no rolling forecasts
python -m quanedge.risk.run --returns returns.csv --weights weights.json --out results/risk_final
python -m pytest                      # unit tests against closed forms, simulations and known tails
```

`--returns` takes daily asset log returns (dates in the first column, one column per permitted ticker) and `--weights` a JSON object such as `{"SPY": 0.3, "AGG": 0.7}`: that is how Person 1's dataset and Person 2's weights plug in. A run replaces its output folder only once it has finished, and `manifest.json` records its inputs, hashes, settings and model statuses.

- Detailed Person 1 technical report: [docs/person-1/01-data-pipeline.md](docs/person-1/01-data-pipeline.md)
- Institutional Data Dictionary: [data/data_dictionary.md](data/data_dictionary.md)
- Detailed Person 3 instructions, remaining work, conventions, testing and team handoffs: [docs/person-3/AGENTS.md](docs/person-3/AGENTS.md)
- Project-wide agent instructions: [AGENTS.md](AGENTS.md)
- Latest numbers, every sentence computed from the tables: [results/risk/summary.md](results/risk/summary.md)
