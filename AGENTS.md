# QuantEdgeFinal: complete competition build prompt

## 1. Your assignment

You are the quantitative research and software-development assistant for the solo Ghosted entry in the SAIFA Quant Edge 1.0 final challenge. One person owns the whole submission: data, portfolio, risk, validation, stress testing, the app and every document. There is no division of work between people. Build and validate the complete competition submission from the current repository. This file is the single implementation prompt for GPT, Claude, Gemini or another coding assistant. Read it fully, inspect the current project, identify the remaining work, make an ordered plan, and implement that plan in tested stages.

Solo ownership is the owner's confirmed choice. Do not introduce a five-person workload, teammate handoffs or dependencies on other members. AI agents may assist with parallel implementation or review, but they do not replace the sole owner's responsibility for validation and defence. The brief's stated entry format remains a source fact; organiser acceptance of a solo entry must be recorded honestly, not assumed. Pending confirmation does not prevent preparation; resolve eligibility before submission.

When this file is supplied in another model's chat, follow the same specification using that model's available tools. If repository files or execution tools are unavailable, state the limitation and provide concrete implementation artifacts where possible. Do not pretend to inspect files, run commands or produce results without doing so.

Preserve working components and extend the existing Python package. `PLAN.md` holds the competition facts and the ordered work plan; do not create further AGENTS.md files, implementation prompts, planning packs or work-log documents. Keep build instructions and a concise progress/decision record here. README is for users; technical reports, data dictionaries, generated evidence and final submissions remain separate artifacts.

## 2. Client, objective and authoritative requirements

The client is the Serendib University Endowment Fund, a conservative institutional investor with a USD 10,000,000 portfolio supporting scholarships, research, faculty development and capital projects. Preserve and grow capital over the long term, balance income and sustainable real growth, and prioritize avoiding large losses and maintaining resilience over maximizing expected return.

Define and justify the investment horizon, nominal/real return objective, asset allocation, acceptable loss, concentration limits, risk constraints, rebalancing and monitoring rules. Treat numerical targets as proposed assumptions until the owner accepts them. Once accepted they are frozen in the decision log and tagged `prereg-v1` before any post-2016 or recommended-weight evaluation result is computed (PLAN.md sections 13 and 13a); later changes are logged mandate changes. Mandate v2 (30 October 2026, PLAN.md section 13b, tag `prereg-v2`) supersedes the v1 policy: no ETF limits, zero trading cost, a 1 January cash reserve of USD 400,000 growing 3.64% a year, and a 1-3% real return objective; the v1 run and its verdict stay as recorded. The assistant may develop a defensible candidate portfolio and recommendation, but final human investment judgement and review must be identified honestly.

Only these investments are eligible:

| Ticker | Exposure |
|---|---|
| SPY | US large-cap equity |
| EFA | International developed-market equity |
| EEM | Emerging-market equity |
| AGG | US investment-grade bonds |
| GLD | Gold |
| XLE | Energy-sector equity, not a direct oil futures position |
| XLK | Technology-sector equity |

One fund or any combination is permitted. Do not add futures, options, unlisted cash instruments or FX overlays to the investable universe based on teaching examples. Make long-only, full-investment and other implementation constraints explicit chosen policy assumptions rather than falsely attributing them to the brief.

Authoritative source: `Quant edge 1.0 Final Challenge 1.pdf` (repository root), 10 pages. Supporting sources: `Advanced_Risk_Management_English_final.pdf` (repository root) and matching PPTX in `../` (28 pages/slides); `EDGEFORGE_Polished_Finance_First_Masterclass_2026.pdf` (repository root) and matching PPTX in `../` (99 pages/slides, with additional speaker notes). The pasted competition summary is supplemental. This prompt includes the core requirements so it remains usable when those local references are unavailable.

The final brief prevails over draft teaching material. In particular, a three-year investment horizon, broader instruments and reversed rubric weights in the masterclass are not final rules. Numerical illustrations in the teaching decks are synthetic, not verified historical estimates.

Judging weights: investment decision-making 30%, technical rigor/correctness 25%, software/interface quality 15%, innovation/ambition 15%, communication/defence 15%. Prioritize a correct and defensible decision before optional complexity.

## 3. Required submission

Deliver:
1. A public or judge-accessible GitHub repository with documented, reproducible code and clear setup/run instructions.
2. A working Python/Streamlit application, deployed or runnable locally from the repository with one documented launch command after setup.
3. A 7-15 page technical report/investment memorandum covering data, cleaning, portfolio construction, methods, results, backtesting, stress tests, assumptions, limitations and the final recommendation.
4. A one-page executive tear sheet presenting allocation, risk metrics, validation/stress findings and an actionable recommendation.
5. A 10-12 minute live-pitch deck if selected for the final five; prepare an editable deck and speaker/Q&A notes as appropriate.
6. An accurate AI-use disclosure identifying tools, purposes, material AI-assisted components and actual independent validation.

Before creating or revising the technical report/investment memorandum or one-page executive tear sheet, read `Ideas.md` for the owner's proposed framing and assumptions. Reconcile proposals with the frozen policy and actual evidence; do not silently adopt a mandate change or present uncomputed results as completed analysis.

Use free-tier/open tools and approved open data. A notebook alone is not the application. Local completion does not imply permission to publish, deploy, send messages or change repository visibility; prepare reviewable artifacts before any separately authorized external action.

## 4. Inspect the project before planning

Inspect Git status, code, tests, configuration, source documents, data manifests and saved outputs. Preserve unrelated changes. Use current code and manifests to resolve stale historical claims. Do not overwrite a completed module just because its implementation differs from a proposed layout.

Observed state, 26 October 2026: the working tree was stripped to `.gitattributes`, `.gitignore` and this file (commit f3609a8); `PLAN.md` was added afterwards. The implementation described below is in Git at commit e94c0ae. Wherever this file says "existing", it means that implementation: restore a module from e94c0ae and re-run its tests before relying on it (PLAN.md decision D-01).

At e94c0ae:
- `quanedge/data/` implements source ingestion, calendar alignment, anomaly/quality auditing, stationarity diagnostics, manifests and loaders. Clean datasets exist in `data/clean/`, source snapshots in `data/raw/` and `data/cache/`.
- `quanedge/risk/` implements historical, normal, Student-t, normal/t Monte Carlo, EVT, FHS and GARCH-EVT models, input validation, exact monetary ES, uncertainty, rolling forecasts, plots and a runner.
- Existing tests cover data and risk. Test counts are historical evidence, not a fixed acceptance requirement.
- The data adapter prefers the clean price file and falls back to the development cache. The default portfolio remains equal-weight placeholders until a justified portfolio replaces it.
- `results/risk/manifest.json` records the inputs actually used for that saved run. It may describe an older development-cache run even though clean data now exists. Do not relabel saved results based on the current adapter.
- No portfolio-construction package, formal backtest/stress package or Streamlit entry point was present in the inspected file inventory. Verify again before implementing.

Structure at e94c0ae:
```text
quanedge/
    config.py
    data/       # sources, cleaning, anomalies, stationarity, manifest, run, loaders
    risk/       # portfolio, var_es, evt, conditional, models, validation,
                # diagnostics, uncertainty, rolling, plots, settings, run
tests/
data/
    cache/
    raw/
    clean/
    data_dictionary.md
results/
    data/
    risk/
docs/
    person-1/01-data-pipeline.md  # data technical report; move to docs/ if restored
requirements.txt
pytest.ini
README.md
AGENTS.md
```

Keep the existing package. Add portfolio and validation/stress modules and an app entry point only as needed. The exact new filenames are implementation choices. Preserve numerical computation outside the UI.

## 5. Plan the stages

One owner builds every stage in the order given in `PLAN.md`. Each stage produces outputs the next stage consumes:

| Stage | Scope | Output |
|---|---|---|
| Data | Approved sources, adjustment, cleaning, quality, calendars, stationarity, provenance and reproducibility | Versioned prices/returns, risk-free/macro series, data dictionary, audit logs and manifest |
| Portfolio | Investment policy, expected returns/covariance, Markowitz/CAPM, candidate selection and performance | Weights, effective date, constraints, rebalancing, benchmark and validated portfolio series/KPIs |
| Risk | Three VaR families, ES, EVT, diagnostics, uncertainty, risk API and forecast engine | Matching-level risk table, model status/parameters, threshold evidence, prior-data forecasts and plots |
| Validation/stress | Kupiec, Christoffersen, traffic light, historical/hypothetical stress and marginal/component risk | Formal test results, scenario attribution, risk budgets and model-acceptability assessment |
| Product/communication | Streamlit, integration, run workflow, report, tear sheet and pitch | Usable application and consistent submission artifacts |

The owner validates and writes up every stage and must be able to explain any material code, assumption or conclusion.

Use stable task IDs such as DATA-001, PORT-001, RISK-001, VAL-001, APP-001 or DOC-001. For each milestone define an output, dependencies, validation and completion criterion. Review interfaces before dependent implementation. Where inputs are pending, continue with labelled development data/weights and synthetic tests. Do not treat placeholders as a final recommendation.

Maintain the compact record in section 17 rather than generating another planning system. Record meaningful changes, evidence and blockers, not keystrokes. Use Git commits/PRs for exact code history; do not fabricate a commit reference.

## 6. Data and shared numerical contracts

Approved sources: Yahoo Finance through yfinance for the core ETF universe; FRED for risk-free rates and macro series; World Bank/IMF for appropriate macro context. Proprietary or undisclosed data is not permitted.

Requirements:
- Use adjusted close prices so dividends/splits do not distort returns. Explain provider adjustment and reinvestment assumptions; do not add dividends twice.
- Align calendars before portfolio calculation. Log missing days, incomplete rows, holiday handling, forward fills and other transformations.
- Flag stale prices, implausible jumps, structural changes and large losses. Genuine crisis observations must remain. Correct verified errors only through documented reproducible code; the brief forbids silent deletion, not justified transparent correction.
- Use log returns for statistical analysis and state where simple returns are necessary.
- Check return-series stationarity, at least ADF, including the portfolio actually used for risk modelling. Supplementary KPSS/ARCH tests do not prove constant parameters or validate the tail model.
- Record retrieval timestamps, source identifiers, date ranges, adjustment rules, schema, hashes, parameters and environment. Hash equality proves file identity, not economic correctness.

Existing input loaders in `quanedge.data`: `load_clean_prices`, `load_log_returns`, `load_simple_returns`, `load_macro_data`, `load_risk_free_rate`, `load_worldbank_data`, `get_data_manifest`, `get_anomaly_log`, `get_stationarity_report`.

Validate production data: numeric finite values, positive prices, unique columns and unique increasing dates, permitted tickers, explicit column order and sufficient sample size. Internal bootstrap resamples may repeat observations and must not be represented as chronological history. Synthetic tests may use fictitious tickers.

Weights are a ticker-to-decimal-weight mapping. Reject unknown keys, NaN/infinity, inconsistent sums and policy violations. Omitted tickers may have zero weight if documented. Distinguish full allocation from leverage/short exposure and ensure positive simulated wealth for log transforms.

Shared return/loss definitions:
```text
R_i,t = exp(r_i,t) - 1
R_p,t = sum_i(w_i,t-1 * R_i,t)
r_p,t = log(1 + R_p,t)
L_t = -r_p,t                      # positive denotes loss, negative denotes gain
g(L) = 1 - exp(-L)                # simple fractional loss
USD_loss = portfolio_value * g(L)
```

Log returns add through time, not by portfolio weights across assets. Constant weights at every daily observation describe a daily-rebalanced replay without costs, not buy-and-hold. Distinguish replay of today's allocation from a historically investable strategy with weights known before each period.

Baseline risk horizon is one trading day; sidebar confidence levels are 0.90, 0.95 and 0.99; value is USD 10 million. Label log units, simple fractions, percentage points and dollars separately. Investment horizon is different from risk horizon. Multi-day risk requires justified aggregation/simulation, not automatic square-root scaling.

Risk-free data requires matching frequency and units. Existing DTB3 is a discount-basis quote converted to bond-equivalent yield before daily conversion. Verify the chosen convention and any approximations. Macro alignment must respect release availability. Publication-lag approximations and revised modern data are not automatically a point-in-time vintage dataset; disclose limitations and avoid future-data leakage.

Changing data, weights, policy, date range, horizon or model settings invalidates affected estimates, forecasts, app caches and submission numbers.

## 7. Portfolio construction and performance

Implement and explain:
- Client policy: horizon, return objective, inflation/spending assumptions where used, tolerable drawdown/loss, concentration, liquidity/rebalancing and risk budgets. Use the PLAN.md section 15 conventions: inflation from CPI index ratios (never the index level as a rate), spending once a year after returns and costs, hurdle h = (1+pi*)/(1-s)-1 after costs and before spending, compared with expected geometric return, and a real-capital target 10m x CPI_T/CPI_0 that never adds spending again.
- Expected returns, volatility, correlation, covariance and diversification. Use consistent frequency and annualization; justify estimators and stability measures.
- Markowitz mean-variance construction and CAPM concepts, including benchmark, beta, risk-free alignment and expected/realized-return distinctions.
- Transparent candidate comparison: suitable baselines (for example equal-weight and constrained minimum-variance) plus proposed allocation. Explain feasibility, sensitivity to estimates, diversification and downside trade-offs.
- Optimization constraints, objective (PLAN.md section 13 selection rule), solver status, budget checks, sensitivity and controlled constraint-relaxation comparisons (one limit changed, data, scenarios, estimators, costs, objective and solver fixed). Verify that weights are feasible; show infeasibility rather than silently relaxing client limits.
- Benchmark-aligned Sharpe, Sortino, Treynor, Jensen's alpha, Information ratio, maximum drawdown, Calmar ratio, cumulative return and relevant annualized return/volatility.

Define each KPI precisely: excess/active return, downside target, sample/annualization choices, benchmark and risk-free proxy, drawdown path and CAGR. Handle zero or negative denominators appropriately; beta near zero makes Treynor unreliable. Information ratio needs tracking error; Calmar uses a consistent annualized return/drawdown period.

Use simple returns to compound wealth and calculate portfolio P&L. Decide how costs and rebalancing enter reported performance; do not imply cost-free replay is a realistic traded strategy. Freeze the selection procedure before computing post-training results. Produce training-period weights (W_train) and recommended weights (W_rec) from the same procedure, as canonical weight files with a SHA-256 weight hash. All historical replays are retrospective portfolio evaluations: the owner has seen the full sample and the policy was written knowing past crises. Do not describe any period up to the snapshot end as untouched or "genuinely out of sample". Adjusted closes are already net of ETF expense ratios; do not deduct them again from historical returns.

Produce a machine-readable weight file compatible with the risk runner, policy/configuration, effective date, portfolio/benchmark series, KPI table, allocation/return/drawdown charts and a reasoned selection narrative.

## 8. VaR and Expected Shortfall

Required: historical simulation, parametric and Monte Carlo VaR on the same portfolio at 95% and 99%, with 90% also supported for the app. Explain model disagreement and assumptions. ES must accompany VaR and explain tail severity.

Keep existing method identifiers: `historical`, `normal`, `student_t`, `mc_normal`, `mc_t`, `evt`, `fhs`, `garch_evt`. Student-t and conditional extensions are optional; preserve useful existing work but validate it separately.

For loss L and confidence a, VaR is its a-quantile; ES is the integral of loss quantiles over [a,1], divided by 1-a. Conditional tail means coincide under suitable continuous distributions; discrete samples/ties need explicit probability-mass weighting.

Historical:
- Preserve the implemented documented VaR quantile convention (currently NumPy linear/type 7) unless a reviewed migration changes it.
- For empirical ES, average the worst n*(1-a) observations with fractional boundary mass. Test ties and noninteger tail counts. Document the distinction between step-quantile ES and interpolated VaR rather than assuming every statistical property follows from mixing conventions.
- Report effective tail count and sensitivity to window. Historical estimates cannot extrapolate beyond sample extrema.

Normal log-return baseline, with fitted mean mu, sample standard deviation sigma and z=Phi^-1(a):
```text
VaR_log = -mu + sigma*z
ES_log  = -mu + sigma*phi(z)/(1-a)
ES_fraction = 1 - exp(mu + sigma^2/2) * Phi(-z-sigma)/(1-a)
```
Use stable evaluation and independent checks. Explain inclusion/exclusion of the mean. Check normality, volatility clustering and serial dependence without treating non-rejection as proof.

Monetary VaR is V*g(VaR_log), but monetary ES must average transformed tail losses:
```text
ES_USD = V/(1-a) * integral_a^1 g(Q_L(p)) dp
```
Generally g(ES_log) differs from ES_fraction. Preserve existing exact `es_fraction` implementations and per-bootstrap monetary ES. An infinite log ES is a distinct status; transforming infinity to a 100% loss is not an exact monetary ES calculation. Monetary loss is bounded above by NAV under the positive-wealth long-only accounting even if a fitted log-tail mean is infinite.

Monte Carlo:
- Simulate documented joint asset distributions, preserve dependence and asset order, aggregate scenarios using the portfolio accounting above.
- Record fitted parameters, seed, scenario count and covariance treatment. Do not silently regularize covariance, clip disasters or ignore overflow.
- Preserve per-asset scenarios and labels for risk attribution.
- Assess convergence across sizes/seeds and distinguish simulation error from estimation/model uncertainty.
- Normal Monte Carlo converges to the corresponding analytical calculation only when both use the same distribution, parameters and portfolio accounting. Joint normal asset log returns aggregated through simple returns need not produce normally distributed portfolio log returns, so a gap from a normal fit to portfolio log returns is a model difference, not an error. Use the one-asset matching-model case for exact-model convergence checks.

For optional Student-t, distinguish scale from standard deviation, check MLE convergence and boundaries, and require the moments needed by each calculation. Current univariate nu bounds exceed 1; multivariate covariance matching requires nu>2. Shared scenario scale shocks preserve multivariate-t dependence. Do not assume t or EVT always has larger VaR at every confidence.

## 9. EVT, uncertainty and conditional models

Use peaks over threshold on loss exceedances Y=L-u for L>u. Fit a GPD with shape xi, scale sigma>0 and support 1+xi*Y/sigma>0. Record sample n, count k and exceedance rate zeta=k/n.

For a>=1-zeta:
```text
xi != 0: VaR_log = u + sigma/xi * ((zeta/(1-a))^xi - 1)
xi == 0: VaR_log = u + sigma*log(zeta/(1-a))
xi < 1:  ES_log  = (VaR_log + sigma - xi*u)/(1-xi)
xi >= 1: finite log ES does not exist
```

Validate fitted support, optimizer success, likelihood, counts, distinct excesses, near-zero-shape limits and negative-shape endpoints. Failed fits must stay visible and unavailable.

Threshold justification:
- Inspect mean excess versus actual threshold u, xi/uncertainty, modified scale sigma-xi*u, counts, tail QQ/PP and survival diagnostics.
- Current scan uses percentiles 0.800-0.985 by 0.005, minimum 50 exceedances, approximate 1.96-standard-error stability comparisons and at least three higher candidates. These are project choices, not competition rules.
- Current selection minimizes KS distance among stable eligible fits, with explicit fallback and tie handling. Treat it as a heuristic, not a universally optimal or automatically calibrated significance procedure.
- Compare selected results with feasible 90th/95th-percentile thresholds and other reasonable windows. Report decision sensitivity.
- Handle empty scans, failed candidates and no stable region explicitly. Approximate parameter standard errors have validity conditions, including xi>-0.5 for the implemented formula.
- Select thresholds inside each training window, never from future test observations.

Existing EVT combines an empirical body and GPD tail. Validate probability normalization, ties, body/tail integration and exact monetary ES. Below the tail cutoff, label estimates as empirical-body/hybrid rather than extrapolated tail quantiles. Keep all three app confidence levels understandable when tail fitting cannot support a pure-tail estimate.

Current uncertainty defaults: 500 circular moving-block resamples, 20-day blocks, 20,000 MC scenarios within resamples, 95% percentile intervals. Resample whole asset rows to preserve cross-asset dependence and disclose circular wraparound. Record failures. Monetary ES must be recalculated per resample before interval construction.

The bootstrap currently fixes the selected threshold percentile, recomputes its numeric value and omits full threshold-selection uncertainty. State this scope and test sensitivity to block length, repetitions and threshold selection. No bootstrap establishes immunity to misspecified models.

Existing GJR-GARCH/FHS/GARCH-EVT models are optional extensions. Check convergence, valid variance recursion, residual dependence and parameter boundaries. The fixed 90th-percentile residual EVT threshold needs its own justification. GARCH forecasts volatility, not return direction; filtering does not automatically eliminate clustering.

## 10. Sequential risk-forecast validation

Generate each day-t forecast using data available through t-1. Preserve training start/end, last parameter-refit date, forecast date, selected settings, data/weight hashes and failures.

Evaluation labels are retrospective portfolio evaluation, sequential risk-forecast evaluation and untouched evaluation, as defined in PLAN.md section 15; every exported result carries exactly one. Each weight vector requires its own forecast file with its weight hash in every row, and backtest statistics must refuse a mismatched hash. A portfolio never inherits another portfolio's traffic light: the app, memo and verdict use W_rec's own forecasts, and any revised or adjusted allocation shows "not evaluated" until its own forecasts exist. No untouched historical data exists (all data through 2026-09-30 was used in the e94c0ae development runs); post-snapshot returns are descriptive monitoring only. Also run the walk-forward procedure check (PLAN.md phase 4).

Existing default rolling implementation: 750 observations, daily historical/normal refits, slow-model refits every 21 observations and daily conditional-volatility updates. Justify final choices. Forecasts include historical, normal, Student-t, EVT, FHS and GARCH-EVT; MC is absent. If MC becomes the selected validation model, implement its actual forecast path rather than substituting normal forecasts.

Use `save_forecasts`/`load_forecasts` to preserve precision and breach decisions. Forecast column example: `var_evt_99`, in log-loss units. A breach is strictly `-return > var_forecast`. Show unavailable forecast days and coverage; exclude failures from numerical denominators without hiding them or treating them as safe days.

Implement:
- Kupiec proportion-of-failures test: counts, expected rate, LR statistic, p-value and interpretation, including zero/all-exception boundaries.
- Christoffersen independence test: transition counts, LR statistic, p-value and explicit handling of insufficient transitions or degenerate sequences.
- Basel traffic-light classification with a clearly specified confidence and observation count. The traditional benchmark is 99% one-day VaR over 250 observations; do not reuse its thresholds unaltered for arbitrary sidebar levels or sample lengths. Verify and cite the chosen authoritative calibration or explicitly label an alternative binomial assessment.

Show whether breaches are too frequent, clustered or inconclusive and whether the model is acceptable, questionable or unreliable. Name the primary and challenger models and their settings at the `prereg-v1` tag, before computing their backtests on the evaluated weights, and disclose evidence seen earlier (the e94c0ae equal-weight forecasts). Only the primary at 99% gates the verdict (PLAN.md check C4); a risk-model failure leads to the challenger and then to "evaluation incomplete", never to Adjust or Reject. Other models and levels are descriptive. In-sample breach counts are descriptive fit checks, not a backtest. A passing coverage test alone does not establish independence or model suitability.

## 11. Stress testing and risk contributions

Replay historical return paths for 2008 GFC, March 2020 COVID and the 2022 rate-hiking drawdown. Choose and document exact scenario dates, positions and rebalancing/cost assumptions; give valid data coverage and comparable cumulative wealth loss.

Design at least one clearly labelled hypothetical scenario with justified joint shocks, such as simultaneous equity/bond losses, technology collapse or emerging-market crisis. A deterministic scenario does not have an implied calibrated probability unless separately estimated.

For every scenario report portfolio return, USD loss, per-asset impact, largest damage contributors and whether policy limits are breached. Explain why bonds/gold may or may not diversify the scenario rather than promising protection.

Implement and interpret marginal/component VaR, marginal ES, position sizing and risk budgeting where appropriate to the model. Specify derivatives with respect to dollar exposures or funded reallocations: bump-and-renormalize weights measures a different quantity from an independent exposure derivative. Use common random scenarios and test finite-difference sensitivity. For derivative-based (Euler/marginal) VaR/ES, reconcile component sums only where homogeneity and differentiability support it and report the residual; the scenario-based dollar ES decomposition below reconciles exactly by construction. FHS, fitted to portfolio returns, cannot supply attribution: risk budgeting uses joint historical scenarios (multivariate-t Monte Carlo as a check), labelled "historical attribution".

Calculate ES contributions in dollars from joint historical asset-return rows or joint simulated asset scenarios. For portfolio value V, asset weights w_i and scenario simple returns R_i,s:
```text
asset_loss_usd[i,s] = -V * w_i * R_i,s
portfolio_loss_usd[s] = sum_i asset_loss_usd[i,s]
component_es_usd[i] = sum_s tail_weight[s] * asset_loss_usd[i,s]
portfolio_es_usd = sum_s tail_weight[s] * portfolio_loss_usd[s]
sum_i component_es_usd[i] = portfolio_es_usd
```
Select the worst portfolio-dollar-loss scenarios with probability mass exactly 1-alpha, then normalize their selected masses to tail weights summing to one. For n equally probable scenarios, this is the worst n*(1-alpha) observations with fractional boundary mass. When portfolio losses tie at the boundary, distribute the remaining selected mass proportionally to the tied scenarios' original probabilities (equally for equally probable scenarios). Apply exactly the same tail weights to every asset and the portfolio; never select a separate tail for each asset's contribution.

Negative asset ES contributions are valid when an asset gains in the portfolio's bad scenarios; do not clip them. Reconcile contributions to dollar ES from these same joint scenarios, confidence and valuation, within numerical tolerance, not to log-unit ES or a separately fitted model's ES. A model fitted only to portfolio returns cannot supply asset attribution by itself: report attribution as unavailable unless joint asset scenarios consistent with that model are supplied. A separately labelled historical attribution may be shown, but must not be presented as that model's decomposition.

Distinguish largest negative asset return from largest weighted P&L contribution. Suggest allocation/risk-limit changes based on measured evidence and rerun affected analysis.

## 12. Stable integration interfaces

Preserve existing public APIs or migrate them together with consumers and tests:
```python
from quanedge.data import load_log_returns, load_simple_returns, get_data_manifest
from quanedge.risk import (
    portfolio_log_returns, fit_models, risk_table,
    rolling_forecasts, breach_summary, save_forecasts, load_forecasts,
)
```

Risk models expose `.var(alpha)`, `.es(alpha)` in log-loss units, `.es_fraction(alpha)` for exact simple-loss ES, `.params` and `.status`. Failed models return explicit unavailable values and a reason, never zero.

Risk-table contract:
- Identity: method, label, family, alpha.
- Log loss: var, es; log-unit es_over_var only where denominator is valid.
- Simple loss: var_pct/es_pct in percentage points, var_usd/es_usd.
- Interpretation: status and EVT basis (GPD tail versus empirical body).
- Uncertainty: log bounds, per-resample monetary ES fraction bounds, percentage/USD bounds and successful/failed replicate counts.

Run metadata records schema/version, code revision, data/weight hashes, source mode, dates, value, confidence, horizon, rebalancing, parameters, seeds, fit/forecast failures and environment. Never infer human approval from the runner's development flag or provided-file mode.

Keep expensive bootstrap and rolling computations out of ordinary sidebar reruns where practical. Cache using all material inputs, including valuation convention and as-of date. Do not mix outputs from different runs. Existing runner stages output before replacing a completed run; preserve that behaviour and retain comparison runs separately.

Existing matplotlib factories: `fig_distribution`, `fig_threshold(scan, chosen)`, `fig_evt_fit`, `fig_comparison`, `fig_tail_curve`, `fig_uncertainty`, `fig_rolling`. Verify prerequisites and units; handle unavailable models and empty date ranges.

## 13. Streamlit product

Build an understandable investment-committee application with:
- Sidebar: 90/95/99% confidence, VaR methodology, backtest dates and portfolio choice (a dropdown of precomputed portfolios by default; free weights in a labelled "Explore" mode).
- Portfolio panel: recommended/current weights, policy/benchmark context, cumulative return, drawdown and performance KPIs.
- Risk dashboard: VaR, ES and EVT estimate side by side at matching confidence, horizon, value and portfolio, with status/basis labels and relevant uncertainty.
- Backtesting: forecasts and exceptions, Kupiec and Christoffersen statistics/p-values, observation coverage and correctly calibrated traffic light or explicit unavailability, for the displayed weight hash only.
- Stress panel: all required historical scenarios plus the hypothetical scenario, dollar/percentage loss and asset attribution.
- Risk-contribution view showing its scenario source, and "attribution unavailable" for portfolio-only models.
- Actionable accept/adjust/reject recommendation (or "evaluation incomplete") computed by the PLAN.md 13a rule, linked to limits and evidence.
- A fixed "Frozen recommendation" panel showing W_rec, its weight hash, run ID, verdict and traffic light whatever the sidebar says.
- A clearly labelled **Assumptions & Limitations** page in plain language.
- Data/source provenance, as-of dates, development/final status and downloadable evidence as useful.

Result keys and states:
- `weight_hash` = SHA-256 of canonical JSON of all seven tickers in fixed order with 6-decimal weight strings (omitted tickers are 0.000000). `artifact_key` = SHA-256 of {weight_hash, method, data_snapshot_hash, config_hash, code_rev} keys expensive artifacts; `view_key` = {artifact_key, confidence, eval_start, eval_end} keys cheap derivations. Lookups are scoped to the loaded run's `results/<run_id>/index.json`; the run ID is displayed as provenance and is not hashed.
- A pure, Streamlit-free function `result_state(view_key, index)` returns MATCHED (precomputed, identical key; badge "run <id>, weights <hash8>"), LIVE (cheap result computed in the app for exactly these inputs; "computed in app, not part of frozen run"), RERUN_REQUIRED ("unavailable for these weights - rerun required" plus the command), FAILED (model status and reason) or INPUT_ERROR (weights not summing to 100% within 0.01 point, or negative; outside-policy weights are allowed but flagged).
- Cheap, LIVE allowed: weights, replay return and drawdown, KPIs, historical/normal/Student-t VaR and ES, Monte Carlo with 20k scenarios and a fixed seed, stress replays and the hypothetical scenario, historical component ES, and date re-filtering of a MATCHED forecast file. Expensive, MATCHED or RERUN_REQUIRED only: rolling forecasts, Kupiec/Christoffersen/traffic light, bootstrap intervals, EVT threshold uncertainty, the real-capital bootstrap, the walk-forward check and the verdict.
- The traffic light shows colour only when MATCHED; otherwise grey with its label. The verdict renders only when C1-C5 are all MATCHED for the same weight hash.

Changing weights must invalidate relevant results. A backtest date filter selects evaluation dates while preserving earlier training history. A method unavailable for forecasting must be explained rather than silently substituted. Distinguish exploratory user weights from the recommended portfolio.

Provide clear loading, input-error, insufficient-history and failed-fit states. Never display missing validation as a green indicator. Use readable charts/labels and avoid fabricated results. Add Streamlit and any necessary packages to the documented dependency setup only when implemented.

## 14. Verification and reproducibility

Keep unit tests offline using synthetic distributions or versioned snapshots. Use independent calculations, integration, known-parameter simulation and cross-implementation likelihood checks. Match stochastic tolerances to sampling uncertainty; do not cherry-pick seeds.

Required coverage:
- Data: returns identity, calendar classification, missing/anomaly handling, as-of macro alignment, risk-free units, manifest hashes and report/data consistency.
- Portfolio: budget/constraint feasibility, solver failures, benchmark alignment, independent KPI/wealth/drawdown examples and temporal leakage.
- Portfolio policy: CPI index-ratio inflation (a CPI level passed as a rate raises an error); h(2.5%, 4%) = 0.067708; a path earning exactly h ends on the real-capital target (no double count); annual (1-s) versus monthly (1-s)^(1/12) spending give the same year-end NAV; money-weighted return equals R for a constant return with draws and equals CAGR without draws; expense ratios not deducted from adjusted-close returns; constraint effect is exactly 0 for a non-binding cap and matches the dual for a small relaxation, with identical scenario-matrix hashes in both solves.
- Verdict: one test per branch (incomplete, Accept, each Adjust A1-A5 in order, Reject); a property test that random check vectors give exactly one outcome; missing C4 gives incomplete, never Accept or Reject; frozen config values equal the decision-log values at the `prereg-v1` tag.
- Risk: tail ties/fractional mass, exact monetary ES, normal/t closed forms, simulation convergence and singular covariance/overflow. Normal Monte Carlo: one-asset convergence to the closed form within 4 sampling standard errors at N = 1e4, 1e5, 1e6, with error falling roughly as 1/sqrt(N); weights (1, 0, ..., 0) in the seven-asset simulation equal the one-asset result under common random numbers; two identical assets at rho = 1 need an eigen- or LDL-based sampler because Cholesky fails.
- EVT: positive/zero/negative shape, support, infinite log ES, threshold failure/fallback, body/tail normalization and sensitivity.
- Conditional/rolling: recursion, timing/refit boundaries, future-data perturbation, missing forecasts and exact CSV round trips.
- Validation: known exception sequences, zero/all breaches, transition degeneracy and traffic-light calibration; refusal of a forecast file with a mismatched weight hash; walk-forward weights for year Y unchanged by perturbing data dated on or after 1 January Y; the final pipeline refuses post-snapshot data.
- Stress/attribution: scenario arithmetic, path/rebalancing assumptions and units; dollar ES contribution reconciliation using shared tail weights, noninteger tail counts, boundary ties, negative contributions and explicit unavailable attribution for portfolio-only models.
- App/integration: controls, cache invalidation, missing data, unavailable models and consistent run identifiers; weight_hash invariant to key order and omitted zeros and changed by a 1e-6 weight change; every result_state branch; AppTest that an edited weight gives a grey light, "rerun required" and no verdict, reverting restores MATCHED, and the frozen-recommendation panel never changes.
- Artifacts: report length, one-page tear sheet, readable exported figures/deck, consistent final numbers and no broken local links.

Within one consistently defined distribution, quantiles are non-decreasing with confidence; validate ES/quantile relationships under the documented finite-sample conventions. Do not impose a universal ordering between different models. NAV scaling changes dollar risk linearly, not percentage/log risk.

Use current commands from the repository root:
```text
python -m pip install -r requirements.txt
python -m quanedge.data.run --check-only
python -m pytest -q
python -m quanedge.data.run
python -m quanedge.risk.run --quick
python -m quanedge.risk.run
python -m quanedge.risk.run --returns data/clean/log_returns.csv --weights <portfolio-weights.json> --out results/risk_final
```
The last command is a template; replace the weight path with an actual produced file. Data-run rebuilds outputs from cached snapshots; `--refresh` explicitly redownloads data. The risk runner's `--refresh-data` can replace its development snapshot. Preserve frozen snapshots and never refresh or regenerate final evidence merely to edit documentation.

Quick risk output goes to `results/risk_quick/`; full default output to `results/risk/`; use `--out` for comparison runs. Do not claim a run is final solely from its folder name. Once an app exists, document its actual one-command launch, such as `python -m streamlit run app.py` if that entry point is chosen.

## 15. Reports, decision and AI disclosure

Every table/chart must state portfolio, data period/as-of date, confidence, horizon, unit and model as applicable. Keep one consistent final run across the app, memo, tear sheet and deck. Derive narrative numbers from outputs; labels and generated reports must not drift.

The memo must explain:
- Client policy and allocation selection, data provenance/cleaning and assumptions.
- Markowitz/CAPM, performance, three VaR methods, ES rationale and EVT threshold evidence.
- Method disagreements, uncertainty and sensitivity.
- Formal validation with its evaluation label, stress losses, attribution and practical risk-budget actions.
- An actionable accept/adjust/reject recommendation computed by the PLAN.md 13a rule, what can go wrong, how bad losses may become and reliability limits.

Explicit limitations: historical sample/regime dependence, sparse extremes, threshold/model uncertainty, mean/covariance estimation, conditional-filter specification, static exposure replay versus strategy, costs/liquidity/price impact, revised macro data, and unsupported effects. High p-values do not prove assumptions; ADF rejection is not proof of stable distribution parameters. VaR is not maximum loss; ES is not a loss cap; tail index alone is not crash probability.

Prepare defence material explaining aggregation and units, exact dollar ES, empirical estimator choices, horizon/window choice, MC assumptions, EVT threshold/shape/failures, uncertainty scope, leakage prevention, validation and resulting portfolio actions.

Retain AI provenance from existing artifacts: earlier risk work records Claude Code; data work records Antigravity and Claude Code; consolidation of this prompt used Codex. Verify these records rather than inferring ownership of every line. Disclose tool, purpose, affected components, automated checks and actual human reviewer/date. Do not invent human sign-off or submit an unexamined AI recommendation as the owner's independent judgement.

Theory leads retained from prior plans: Artzner et al. (1999), Acerbi and Tasche (2002), Balkema and de Haan (1974), Pickands (1975), Hosking and Wallis (1987), Smith (1987), Coles (2001), Glosten/Jagannathan/Runkle (1993), Barone-Adesi et al. (1999), McNeil and Frey (2000), McNeil/Frey/Embrechts (2015), Clauset et al. (2009). Verify exact equations/assumptions and primary references before citation; the threshold heuristic is not automatically the Clauset procedure.

## 16. Execution stages and acceptance gates

1. **Inventory and plan:** inspect actual state, record dependencies and an ordered task list here. Separate implemented, tested, reviewed and final-input status.
2. **Contracts/data:** verify source provenance, schemas, units and data-quality evidence. Record unresolved macro vintage/event-label/manual-review limitations.
3. **Portfolio baseline:** implement policy/candidates/KPIs, validate feasibility and establish time-consistent weights and benchmark.
4. **Integrated analytical baseline:** connect existing risk engine, actual forecast model, formal validation, required stresses and basic app. Prefer an early connected pipeline over isolated polished components.
5. **Robustness:** resolve failing checks, sensitivity, EVT justification, input failures and optional-model evidence. Record supported and unsupported cases.
6. **Decision and communication:** turn evidence into a proposed investment action, report, tear sheet and pitch; identify decisions requiring the owner's actual review.
7. **Final reproducibility:** lock selected inputs/settings, run from documented setup, reconcile artifacts, verify UI and record code/data/run identifiers and remaining limitations.

Completion requires all mandatory analytical layers and app panels, reproducible run instructions, independent numerical evidence, honest model failures, formal sequential risk-forecast tests of the recommended weights' own forecasts, required scenarios and attribution, deliverable artifacts and accurate AI disclosure. A passing test suite alone is not final human review or investment approval.

At the end of each stage, provide a runnable example, schema/units, input/output identifiers, validation evidence, warnings and outstanding dependencies. If the next stage cannot use the output without rewriting calculations, the interface is not accepted.

Continue useful independent work when an input is pending. Ask only for genuinely missing material choices or authority. Do not mark the competition complete with placeholder weights, missing formal tests or draft artifacts represented as final.

## 17. Compact progress and decision record

This section is the only manually maintained progress/decision log; the work plan itself lives in `PLAN.md`. Keep it concise; use generated manifests and Git references for detailed run/code evidence. Do not copy thousands of results into this prompt.

Initial consolidation record, 26 October 2026:
- Task DOC-001: combine the project and risk-engine instructions into one whole-competition prompt and simplify README.
- Scope: documentation consolidation and obsolete-reference cleanup; no change to analytical methods or regenerated data/results.
- Preserved: data/risk source and tests, snapshots, manifests, generated evidence, institutional data dictionary and the data-pipeline technical report.
- Removed after consolidation: nine instruction files under `docs/person-3/`; historical content is recoverable from Git.
- Open: re-inventory portfolio/validation/app work at implementation time; review final policy/weights and model selection.
- Technical choices still requiring evidence/review: final sample/windows/refit settings, empirical estimator convention, EVT threshold/minimum counts and residual-tail threshold, uncertainty sensitivity and actual human validation.
- Verification for DOC-001: targeted documentation checks passed (4 tests, 27 deselected) using the existing stationarity/report, README and data-documentation tests. All retained local Markdown links resolve and `git diff --check` passed. The full numerical suite and analysis pipeline were not rerun for this documentation-only change.

DOC-002, 26 October 2026:
- Single owner: removed the five-person workstream split; stages, task IDs and the record template no longer name people. Repository renamed QuantEdgeFinal.
- Added `PLAN.md`: competition facts from the brief and both teaching decks, investment policy proposals, verdict rule, phased plan with milestones and cut list, conventions and Q&A bank. Draft reviewed by two AI critic agents (judge view and engineering view) who cross-critiqued; settled points are in PLAN.md section 17.
- Section 4 now states that the tree was stripped and the implementation lives at e94c0ae; restore per PLAN.md D-01.
- No code, data or results changed. Policy numbers in PLAN.md section 13 are proposals awaiting the owner's review.

DOC-003, 26 October 2026:
- Integrated the owner's ideas (Google Doc "Quant Edge - thoughts": diversification techniques and NIBM capital-budgeting slides) into `PLAN.md` section 19, after review by a second pair of AI critic agents who cross-critiqued.
- Policy fixes found in that review: the return objective is now a hurdle h = CPI + 4% spending + costs set from the spending need (the earlier frontier-derived target made Reject impossible); AGG is 25-70% and exempt from the 40% single-ETF cap (the earlier text capped AGG at 40%, forcing at least 45% equity).
- Added: permanent-portfolio-inspired benchmark, constrained volatility risk parity, co-exceedance and ES diversification benefit, shortfall-against-hurdle bootstrap, money-weighted return and time under water, alternatives-considered memo text. NPV/PI dropped as redundant.
- No code, data or results changed; policy numbers remain proposals awaiting the owner's review.

DOC-004, 26 October 2026:
- Owner confirmed that the project remains solo. Both prompts now explicitly prohibit a return to five-person work allocation or teammate dependencies; AI review agents remain permitted assistance.
- Retained the brief's stated entry format as a source fact. Solo eligibility remains unconfirmed in these records; preparation may continue, with confirmation required before submission.
- Scope: solo ownership and eligibility wording only. Other audit findings remain outstanding; no code, data or results changed.
- Verification: reviewed both documents for conflicting ownership and eligibility wording; `git diff --check` passed.

DOC-005, 26 October 2026:
- Adopted the owner's dollar-ES attribution convention in AGENTS.md and PLAN.md. Contributions use joint asset simple-return scenarios and shared normalized tail weights, including fractional boundary mass and proportional allocation across boundary ties.
- Negative contributions remain valid. Reconciliation is to the same scenario-based dollar ES; portfolio-only fitted models cannot supply asset contributions without consistent joint scenarios.
- Removed PLAN.md's ambiguous weighted-log-loss conditional-expectation formula and clarified the phase-5 acceptance check. Other audit findings remain outstanding.
- Verification: targeted formula/wording review and `git diff --check`; documentation only, no numerical implementation or tests run.

DOC-006, 26 October 2026: external audit items 2-7, reviewed by a third pair of AI critic agents who cross-critiqued (PLAN.md section 20). Closes the "other audit findings remain outstanding" notes in DOC-004 and DOC-005.
- Evaluation labels (retrospective / sequential risk-forecast / untouched); "genuinely out of sample" removed; one forecast file per weight hash, so W_rec has its own backtest and no portfolio inherits another's traffic light; walk-forward procedure check made core. No untouched historical data exists (seen at e94c0ae); post-snapshot data is descriptive only.
- Spending once a year after returns and costs; inflation from CPI index ratios; h = (1+pi*)/(1-s)-1 = 6.77% after costs, before spending, against expected geometric return; real-capital target 10m x CPI_T/CPI_0; expense ratios not double-counted. Supersedes DOC-003's additive hurdle.
- Verdict 13a rewritten: frozen checks C1-C5, ordered finite adjustment set A1-A5, "evaluation incomplete" first, exactly one outcome; named selection rule; ES budget measured on the weights' estimation sample; freeze tag `prereg-v1` before any post-2016 result (phase 2 split into 2a/2b).
- Normal Monte Carlo wording corrected with one-asset convergence tests; app result states keyed by weight/data/config/code hashes, precomputed-portfolio dropdown and frozen-recommendation panel; constraint effects by controlled re-solves (benchmark gaps no longer cited as the gold-cap cost).
- Disclosed: e94c0ae equal-weight forecasts were seen before naming FHS primary (99%: FHS 65 breaches vs 47.2 expected, Kupiec p about 0.014; GARCH-EVT 52, p about 0.49). Owner to confirm or swap the primary model before the tag.
- Documentation only; tests specified, not run. Organiser PDFs now committed at the repository root.

For subsequent meaningful updates append a compact entry using:
```text
Date/time and task ID:
Stage/milestone and state: planned / in progress / ready for review / accepted / blocked
Completed and why:
Changed components and Git/run references:
Validation command, actual outcome and evidence location:
Decision/assumptions and downstream impact:
Dependencies/blockers and next action:
AI assistance and actual human review:
```

2026-10-27, DATA-001 / PORT-001 / VAL-001, implementation and preregistration:
- Owner accepted PLAN.md section 13 policy and FHS primary / GARCH-EVT challenger in this conversation before current recommended-weight evaluation. Independent human code/investment review remains pending. Solo eligibility and deadline remain pending; cash excluded.
- Restored required data/risk modules and tests from e94c0ae; removed development adapter and automatic placeholder allocation. Fresh Yahoo snapshot: 5,470 dates, 2005-01-03 through 2026-09-30; 242 flagged moves retained. Macro HTTP retrieval timestamps were not separately captured; source inventory labels filesystem write timestamps honestly.
- Frozen estimator: annual sample simple-return means shrunk 50% toward their cross-asset mean; Ledoit-Wolf covariance; expected annual turnover 1.0 times NAV at 5 bp one-way (fixed 5 bp expected cost reserve). Geometric approximation is (1+net arithmetic mean)*exp(-annual variance/2)-1. Maximum-Sharpe comparison uses fixed 2% risk-free assumption; realised KPIs use aligned DTB3. No double deduction of expenses.
- Selection: HiGHS return-maximising historical CVaR99 LP followed by CVaR minimisation within 1e-8 of optimal return. Training-only scenario hash and candidates in results/training; computed A4 budget = 3.0% NAV. Original policy/config, C1-C5 and ordered A1-A5 are frozen at prereg-v1 before current post-2016 allocation evaluation.
- Development evidence seen before model choice remains disclosed: earlier equal-weight FHS coverage failure and GARCH-EVT results in PLAN.md phase 4. No claim of untouched historical evaluation.
- Validation so far: 130 checks passed in the first full restored-suite run; six obsolete documentation-path checks failed and were migrated to generated evidence. New portfolio/accounting/tail/hash/verdict tests passed (8). Normal Monte Carlo now supports PSD covariance using an explicit eigen factor; singular multivariate-t density MLE remains unavailable. Final full-suite, application and artifact verification follow.
- AI: Codex implemented restoration, integration and tests; automated checks are not human sign-off. Code and generated documents remain ready for owner review, not accepted investment judgement.

2026-10-27, PORT-002 / RISK-001 / VAL-002 / APP-001 / DOC-002, local package ready for review:
- Policy frozen at prereg-v1 (a12617b). Final implementation source at d73da5f; subsequent run metadata includes the precise Git revision and normalized source-tree hashes. Current data/weight/policy identities and the initial calculation revision remain in the run manifest. No policy values were changed after preregistration.
- Run results/final-20261027 evaluates 20 named allocations with their own weight-hashed forecasts. The original allocation fails C5 (GFC path drawdown 23.38%). Frozen rule selects Adjust, A1_min_cvar: SPY 15%, AGG 70%, GLD 15%; GFC path drawdown 14.74%, historical ES99 about USD 141,417.
- For that adjusted allocation, FHS fails the gate (Kupiec p about 0.0067, conditional coverage about 0.0092); pre-named GARCH-EVT challenger passes (about 0.1007 and 0.0565), with a yellow final zone requiring review. This is not proof of model suitability. Forecast failures and coverage remain visible.
- Material non-gating concern: illustrative after-spending real-capital shortfall probabilities are 60.92% at five years and 67.41% at ten years. Prominent in report, tear sheet, app and pitch. Common-mean shrinkage can overstate bond expected returns; fixed-weight estimator/window sensitivity is exported without re-selection.
- Delivered code: portfolio candidates and constrained CVaR, performance/spending/KPIs, formal coverage/independence tests, crisis/hypothetical/reverse stress, shared-tail dollar attribution and marginal risk, macro/co-exceedance, real-capital simulation, own-allocation forecasts, walk-forward check, uncertainty, run identity, Streamlit and document generation. Canonical pipeline weights are accepted and hash-verified by the standalone risk runner.
- Evidence: clean virtual-environment suite passed 143 tests. quanedge.verify passed for 20 allocations and 162 artifacts, including forecast round trips/backtest recomputation and dollar-ES reconciliation. Data manifest passed. Generated memorandum is 11 pages; tear sheet and committee memo are one page each; editable pitch is 12 slides with native tables and speaker notes. PDF/deck rendering and layout review performed; no claim of opening PowerPoint.
- Completion state: local computational/artifact package ready for owner review. Independent human validation/investment judgement, organiser solo eligibility, deadline and any external publication/submission remain pending. No messages, push, deployment or visibility changes authorised or performed. Codex assisted implementation and communications; the sole owner retains responsibility.

2026-10-27, VAL-003 / APP-002, reproducibility closure:
- Clean Python 3.12 virtual environment: 143 tests passed. Local clean checkout: all 143 tests passed, offline data manifest verified, training-stage pipeline reproduced its committed outputs without a diff, and all seven application pages passed AppTest. Full final forecasts were computed in the main checkout; the clean checkout independently re-read and verified their numerical/identity contracts rather than recomputing every expensive final forecast.
- Final clean-checkout verifier passed: 20 allocations, 162 artifact hashes, data/source hashes, forecast timing and recomputed backtests, ES contribution reconciliation and document page counts. Fixed Git attributes and re-normalized previously tracked Markdown so data/artifact bytes survive checkouts; source hashes deliberately normalize LF.
- Browser: localhost:8501 returned HTTP 200; desktop and 390-pixel mobile layouts inspected, risk page had zero Streamlit exceptions. All 12 pitch slides and PDF pages were rendered/reviewed; native-table PPTX integrity, typography/layout and first-party import checks passed. Current reviewed deck is committee_pitch_v2.pptx.
- Frozen run was tagged before a separate monitoring download. monitoring/final-20261027 covers 18 sessions, 2026-10-01 through 2026-10-26: zero 99% breaches for FHS and GARCH-EVT, exact count probability about 0.8345. Descriptive only, no traffic light, no selection/verdict change. Initial final-run tag retained; final-run-final-20261027-v2 includes checkout-byte preservation and this closure record.
- Remaining dependencies are human/organiser decisions already identified above; no additional numerical or application blocker is known. No independent human sign-off is claimed.

2026-10-29, APP-003, ETF comparison and viewer integrity fix:
- Added ETF charts page with Plotly overlays, indexed/adjusted-price views, ticker selection, hover, zoom and range controls using the frozen price snapshot.
- UI-only app.py revisions may display frozen results with an explicit interface-update caption. Data and numerical-source mismatches still stop the app; original manifests and analysis revision are preserved. The standalone verifier continues to report full source differences honestly.
- Validation: tests/test_app.py passed (2 tests), including changed-viewer acceptance, chart modes, empty selection and changed-price rejection. AppTest against final-20261027 opened the new chart page with one chart and no errors or exceptions. Initial pytest attempt encountered restricted default temp/cache paths; rerun used a workspace temp directory and disabled pytest cache.
- Codex implemented and automatically checked the changes; independent owner review remains pending.

2026-10-29, CTX-001 / DOC-007 / APP-004, standalone history, estimator disclosure and documentation revision r1 (ready for review):
- Why: owner request to use maximum ETF history for context and to disclose prominently that C3 depends on the return estimator. Scope excluded any change to selection, models, gates, verdict, frozen data, config, forecasts or manifests; no EWMA, regime models, re-selection or multi-window backtests.
- quanedge/context.py: new Yahoo snapshot (auto-adjusted, retrieved 2026-10-29, capped at 2026-09-30) in context/raw with manifest and hashes, kept outside data/ because the final pipeline hashes everything under data/. Each ETF keeps its own dates; nothing filled. First prices: SPY 1993-01-29, XLE/XLK 1998-12-22, EFA 2001-08-27, EEM 2003-04-14, AGG 2003-09-29, GLD 2004-11-18; issuer launch dates not verified. Overlapping daily returns differ from the frozen panel by at most 2.7e-6.
- Findings: only XLK has a deeper pre-2005 drawdown (-82.05%, 2000-03-27 to 2002-10-09, 16.9 years under water; -53.04% since 2005). Dot-com crash cannot be replayed (AGG, GLD absent); observed SPY+XLK sleeves of W_rec lost USD 2.49m (24.94% NAV) buy-and-hold, A1's SPY sleeve USD 0.71m; partial sleeve losses only. Recomputation reproduces the frozen estimator_sensitivity.csv exactly: A1_min_cvar expected geometric 4.34/4.88/5.41% on raw means (5y/10y/all) versus the 6.77% hurdle, so C3 passes only under the frozen 50% shrinkage; W_rec clears it on raw means (8.37-9.89%). Spending shortfall 60.92/67.41% (A1) versus 29.27/25.09% (W_rec). Descriptive fixed-weight historical ES99 by window: A1 USD 128-150k, W_rec USD 213-257k. Recorded C3 and Adjust verdict unchanged.
- App: Recommendation page shows the hash-checked sensitivity chart/table beside C3 and labels shortfall as not exhaustion; ETF charts page adds the context source, common-period and own-start indexing, drawdown view and coverage/drawdown tables, falling back to the frozen panel when context is absent or altered.
- quanedge/docrev.py builds results/docrev/final-20261027-r1: parent memorandum plus two addendum pages (13 pages), parent tear sheet with an overlaid revision box (1 page), parent Q&A notes plus four questions, revision.json with parent manifest hash and own hashes. Parent documents, committee memo and PPTX untouched. Pages rendered and visually inspected.
- Validation: tests/test_context.py (10), tests/test_docrev.py (2), tests/test_app.py (4) pass; full suite 156 passed with pytest's temp directory outside the repository. Earlier runs with a temp directory inside the repository hit an intermittent Windows rename lock in test_run (passes alone and outside the repository) and exposed an over-broad isolation assertion and a 3-second AppTest default timeout, both corrected. python -m quanedge.docrev --verify PASS. python -m quanedge.verify results/final-20261027 reports one difference, source hash app.py, the viewer-only change already present since APP-003; all data, artifact, forecast and document checks otherwise pass. Data manifest verified.
- Claude Code implemented and automatically checked this work; independent owner review remains pending. No publication, push or organiser contact.

2026-10-30, APP-004, maximum-history chart default:
- ETF charts now defaults to the verified standalone full-history snapshot and indexing from each ETF's first observed date. Common-period comparison and frozen panel remain selectable; contextual snapshot ends 2026-09-30.
- Actual-run Streamlit AppTest opened with zero errors/exceptions and confirmed all seven trace start dates: SPY 1993-01-29, EFA 2001-08-27, EEM 2003-04-14, AGG 2003-09-29, GLD 2004-11-18, XLE/XLK 1998-12-22. No analytical results or policy changed; owner review remains pending.

2026-10-30, PORT-003, drawdown-contingent risk budgets (exploratory mandate-change comparison, ready for review):
- Why: owner asked whether the fixed USD 250k ES99 budget and 20% decline limit should tighten as the portfolio falls. Proposed rule only; frozen prereg-v1 policy, run, verdict and manifests unchanged. Rule designed after the data were seen, so every result is a retrospective portfolio evaluation.
- quanedge/dynamic.py: decline measured from the high-water mark of the pre-spending wealth index after costs. Bands 0-5/5-10/10-15/15-20% give ES99 budgets 2.5/2.0/1.5% of current NAV and then minimum-CVaR weights; bands tighten at quarter-end (immediately at 15%+), loosen only 2.5 points inside the band edge. CPPI variant: budget min(2.5%, (20% - decline)/8). Targets blend base and minimum-CVaR weights (same bounds, expanding window, data through the decision close). Flat 2.5% quarterly re-check isolates the band effect.
- Output: results/dynamic-risk-r1/ (comparison.csv, daily paths, metadata.json with weight hashes and returns hash). For A1_min_cvar the bands change almost nothing (max decline 16.8% vs 16.8%; CAGR 5.45% vs 5.49%). For the original selection, steps/CPPI cut max decline from 27.0% to 22.7%/21.2% and days beyond 20% from 57 to 4/1, at CAGR 7.56%/7.20% vs 8.64% and higher turnover. No variant kept the riskier portfolios inside 20%: in October 2008 the minimum-risk portfolio itself fell (AGG -6.8% on 10 Oct).
- Validation: tests/test_dynamic.py (5) pass, including exact match to portfolio.replay for the static rule and unchanged paths before a future-data perturbation; full suite 161 passed.
- Claude Code implemented and automatically checked this work; owner review and any decision to adopt it as a logged mandate change remain pending.

2026-10-30, PORT-004, long-only risk mitigation (exploratory mandate-change comparison, ready for review):
- Why: owner asked for hedging without short selling. Variants fixed in quanedge/hedging.py before the first run: XLE 5/10% funded from SPY; frozen return-maximising CVaR LP plus a buy-and-hold loss cap of 15%/12% in each named stress scenario; EWMA (lambda 0.94) volatility overlay scaling the equity sleeve to the expanding-window volatility, weekly review, 5-point minimum change, freed weight to AGG then GLD within caps. Frozen prereg-v1 policy, run and verdict unchanged; retrospective portfolio evaluation.
- Output: results/hedging-r1/. Overlay does nothing for A1_min_cvar (AGG and GLD at caps). Original selection: max decline 27.0% to 19.4%, days beyond 20% 57 to 0, CAGR 8.64% to 8.39%, turnover 0.16 to 0.67x/yr. XLE 10% on A1: 2022 path -15.3% to -8.8%, worst year -11.9% to -4.8%, COVID -6.5% to -8.8%, ES99 1.43% to 1.53%. Scenario cap 12%: max decline 18.8%, CAGR 6.86%, but fitted to crises already observed. The hypothetical scenario's XLE shock is -34% (training stressed covariance), so it does not represent an energy-led inflation shock.
- Validation: tests/test_hedging.py (5) pass, including no future-data dependence of the overlay and equality to the static path at the capped corner.
- Claude Code implemented and automatically checked this work; owner review and any adoption as a logged mandate change remain pending.

2026-10-30, PORT-005, full evaluation of original selection plus volatility overlay (mandate-change candidate, ready for review):
- quanedge/overlay_eval.py evaluates the frozen selected weights with the PORT-004 EWMA overlay under the frozen C1-C5 criteria, with a strategy hash (base weight hash plus overlay settings) on every forecast row. Departures from the fixed-weight evaluation are listed in results/overlay-eval-r1/metadata.json (path-based forecasts after costs, path-based stress windows, approximate C3 via realised drag).
- Result: C1-C5 all pass, so the frozen rule would give Accept for this candidate; this is not the frozen verdict, which remains Adjust to A1_min_cvar. FHS 99% on the overlay path, 2017-01-01 to 2026-09-30: 34 breaches vs 24.5 expected, Kupiec p 0.068, conditional coverage p 0.150, green zone; GARCH-EVT 32, 0.145, 0.256. GFC path drawdown 19.37% (limit 20%; static 23.38%). Overlay expected geometric about 9.09% vs 6.77% hurdle; path ES99 1.96%. Real-capital shortfall 27.7%/23.6% at 5/10 years (static selected 28.8%/24.4%, method-matched).
- Thin margins and caveats: GFC drawdown 0.63 points inside the limit and Kupiec p just above 0.05. Walk-forward 2017-2026 (yearly re-selection on prior data): overlay CAGR 9.01% vs 10.46% static, max decline 19.0% vs 19.6%, so most of the drawdown benefit is in 2008, which the overlay design had already seen. Turnover 0.67x vs 0.16x per year.
- Validation: tests/test_overlay_eval.py (3) pass, including mismatched-hash refusal and walk-forward independence from later data.
- Claude Code implemented and automatically checked this work; owner review, any logged mandate change and any replacement of the frozen recommendation remain pending.

2026-10-30, MANDATE-002 / PORT-006, mandate v2 (owner rule change, frozen before its final run):
- Owner instructions in this conversation: remove all ETF percentage limits; trading cost 0%; withdraw a cash reserve for the university every 1 January (USD 400,000 in year 1, USD 414,560 in year 2, growing 3.64% a year, the owner's average world inflation figure); real return target 1-3% a year. Owner choices when asked: minimise CVaR99 subject to 3% real expected return; keep the 2.5% ES99 budget and 20% drawdown limit; reserve paid out and earns 0%; keep the 50% mean shrinkage after seeing that it decides the outcome. Policy, checks and A1-A2 order in PLAN.md section 13b.
- Code: target selection (bisection over the arithmetic floor of the CVaR LP), reserve replay and 25-year reserve survival, v2 C3 (expected real return >= 1%), v2 adjustment set, mandate-aware report and app text. Mandate v1 comparison modules (dynamic, hedging, overlay_eval) now read the policy frozen at prereg-v1 via config.frozen_policy. v1 runs remain viewable in the app.
- Disclosed before the tag: full-sample v2 selections were seen (frozen estimator about SPY 6 / AGG 88 / GLD 6; raw means about AGG 65 / GLD 17 / XLK 18) and the exploratory no-limit run (AGG 50 / GLD 22 / XLK 28) failed C4. No v2 backtest was computed before the tag.
- Validation before the run: full suite passed after migrating v1-dependent tests (new tests: v2 policy values, binding and non-binding target selection, exact 25th-payment depletion, reserve survival and C3 thresholds). The 3.64% inflation source is unverified.
- Claude Code implemented and automatically checked this work; owner review pending. Results follow in the run entry below.

2026-10-30, PORT-007 (exploratory), correlation study and "winner to loser" rebalancing rule:
- State: ready for review. Owner asked whether the seven ETFs are correlated, and whether to sell an ETF after a 10% rise and buy the one that fell. Findings are in PLAN.md section 19a; reproduce with `python scripts/correlation_rebalancing_study.py`.
- Equities form one block (first factor 58% of variance; SPY-XLK 0.91). AGG/GLD are the diversifiers, but SPY-AGG correlation changes sign by regime. The rule showed no reversal signal. Its best-looking variant broke the gold cap (52%) and the AGG minimum (20%). Decision: reject as a trading rule; keep quarterly-plus-drift rebalancing.
- Retrospective and descriptive only. No change to policy, weights, the frozen run or the verdict at `prereg-v1`. No new results artifacts.
- Validation: the script runs offline on data/clean. Its cost convention matches `portfolio.replay`. PLAN.md numbers were copied from its output. No unit tests were added for this exploratory script.
- AI: Claude Code wrote the analysis and text. Owner review is pending.

2026-10-30, PORT-008 (exploratory), four-ETF portfolio (SPY/AGG/GLD/XLE) and risk-mitigation overlays:
- State: ready for review. `python scripts/four_etf_study.py` reuses `quanedge.portfolio.construct` with EFA/EEM/XLK fixed at zero and frozen policy limits, plus a 4-asset risk-parity solve. Weights for the 2017-2026 test come from 2005-2016 estimation only.
- The frozen selection rule fails C5 again: the max-return candidate has a 23.4% GFC drawdown. Its A1 fallback, min CVaR, is SPY 15 / AGG 70 / GLD 15, identical to the current adjusted recommendation.
- Four-asset risk parity (SPY 14 / AGG 64 / GLD 15 / XLE 8 on training estimates) passes C1-C3 and C5. Over 2017-2026 it had a higher CAGR and a smaller maximum drawdown than the current allocation. Its 2022 advantage came from the energy rally, after the correlation evidence had been seen, so this is hindsight-exposed. C4 has not been evaluated (it needs its own weight-hashed forecasts).
- Trend and volatility overlays cannot act on SPY15/AGG70/GLD15, because AGG and GLD are already at their caps. On the max-return mix they cut drawdown and lowered CAGR, with higher turnover.
- No change to policy, W_rec, the frozen run or the verdict. AI: Claude Code. Owner review pending.

2026-10-30, PORT-006 / VAL-004 / DOC-008, mandate v2 final run final-v2-20261030 (ready for review):
- Run under tag prereg-v2 (config identical to the tag). Outcome: evaluation incomplete. W_rec = min CVaR (3% real target not binding): SPY 5.8 / AGG 88.0 / GLD 6.0 / XLE 0.2. C1-C3 and C5 pass (ES99 USD 124,433 vs USD 240,000; expected 7.31% nominal = 3.54% real; GFC drawdown 13.1%). C4 fails: FHS 41 breaches vs 24.5 expected, Kupiec p 0.002, yellow; GARCH-EVT challenger 36, p 0.026, yellow. No A1-A2 alternative passes all checks (near parity fails C5 at 21.4%; min variance and max Sharpe fail C4). Benchmarks SPY35/AGG50/GLD15 and SPY25/AGG50/GLD25 pass C1-C5; they are outside the selection rule and adjustment set, so adopting one would need a new logged owner decision.
- Qualifications: on raw means W_rec expects 3.90% nominal (0.25% real) on full history and 1.41% over five years; realised 2017-2026 real CAGR about -0.26%. Reserve survival over 25 years: 67.4% of paths pay every reserve, median failing path depletes in year 24, real capital preserved in 0% of paths.
- Operational: the pipeline's final rename of the staging folder hit a Windows access-denied lock; all stages, documents and the sealed manifest had completed, so the folder was renamed and results/latest.txt set by hand. python -m quanedge.verify results/final-v2-20261030: PASS (18 allocations, 139 files). AppTest on the real run: all eight pages, zero errors or exceptions. Memorandum 11 pages; tear sheet and committee memo one page each. The editable PPTX was not rebuilt for v2 (its builder needs the Codex runtime).
- Claude Code ran and checked this work; owner review pending. No organiser contact.

2026-10-30, MANDATE-003, mandate v3 four-ETF universe (owner rule change, frozen before its run):
- Owner instruction: invest only in SPY, XLE, AGG and GLD because of their lower correlation with each other. Implemented as cfg universe (other ETFs bounded at zero in every construction, benchmarks' equal weight and risk parity over the four). PLAN.md section 13c.
- Evidence recorded with the rule: EFA/EEM/XLK correlate 0.82-0.91 with SPY daily; XLE 0.70 (0.76 on SPY's worst 5% of days), so the low-correlation reason holds for AGG and GLD, not for SPY-XLE. Pre-tag check: v3 selects the same weights as v2.
- Validation before the run: 175 tests passed, including a new test that no construction method holds an excluded ETF and that holding one is outside policy. Claude Code implemented; owner review pending.

2026-10-30, PORT-009 / VAL-005, mandate v3 final run final-v3-20261030 (ready for review):
- Outcome: evaluation incomplete. W_rec identical to v2 (weight hash bd13d897): SPY 5.8 / AGG 88.0 / GLD 6.0 / XLE 0.2; C1-C3, C5 pass; C4 fails (FHS 41 vs 24.5, p 0.002; GARCH-EVT 36, p 0.026). A1: min variance and max Sharpe fail C4, four-ETF near parity (SPY 14.0 / AGG 60.9 / GLD 16.3 / XLE 8.8) passes C5 (GFC 18.1%) but fails C4 (FHS conditional coverage p 0.009). Benchmarks SPY35/AGG50/GLD15 and SPY25/AGG50/GLD25 pass C1-C5; outside the selection rule.
- Operational: same Windows rename lock as v2; the complete, sealed staging folder was renamed and results/latest.txt set by hand. quanedge.verify PASS (18 allocations, 139 files); AppTest all eight pages without errors; memorandum 11 pages, tear sheet and committee memo one page. PPTX not rebuilt.
- Claude Code ran and checked this work; owner review pending.


2026-10-30, PORT-010 (exploratory), six weighting methods through every crisis found so far:
- State: ready for review. Owner asked to replay inverse variance, inverse volatility, risk parity, minimum variance, minimum CVaR (W_rec) and maximum Sharpe through all crises identified so far, and to show which ETFs gained and lost in each. `python scripts/crisis_methods_study.py` writes results/crisis-methods-r1/ (report.md, CSVs, metadata.json with weight hashes and price-file hash).
- Scope: 11 historical windows (3 frozen scenarios plus the deepest-drawdown episodes in results/charts/etf_top3_drawdowns.csv) and the frozen hypothetical shock; buy-and-hold, no costs or reserve. Dot-com not replayable (AGG, GLD absent). Weights are the rounded full-sample comparison weights, so the crises were in the estimation data: retrospective only.
- Finding: the bond-heavy methods (minimum CVaR, minimum variance, inverse variance) lose least in equity crises (GFC +2.5 to +4.6%, COVID -3.5 to -5.4%) but most in the 2020-22 bond bear (-11 to -16%). Inverse volatility and risk parity lose more in equity crises (GFC -5.3/-3.7%, COVID -12.4/-11.2%, GFC drawdown -19.0/-18.2%) but are the only ones near flat through 2020-22 (+3.8/+1.4%), because XLE gained 154%. No method avoided the October 2008 and March 2020 liquidity weeks (-10 to -15%), when AGG also fell. Average loss across the 12 scenarios is -5.2% to -5.7% for every method.
- No change to policy, W_rec, the frozen run or the verdict. No unit tests added for this exploratory script. AI: Claude Code. Owner review pending.

2026-10-30, PORT-011, candidate v4c: risk parity plus volatility overlay (pre-registered, evaluated):
- State: ready for review. Owner asked to test the combination proposed after PORT-010. Pre-registered in PLAN.md section 13d (commit 085b621, local tag prereg-v4c, not pushed) before any overlay path on these weights was computed: v3 A1_near_parity weights (hash ece535c3), PORT-004 overlay settings unchanged, v3 policy frozen at prereg-v3, checks C1-C5 as in PORT-005 with the v3 real-return floor, no retuning on failure.
- `python -m quanedge.parity_overlay` writes results/parity-overlay-r1/ (summary, metadata with strategy hash 'v4c' + base hash + overlay, forecasts with the strategy hash on every row, overlay and walk-forward paths, crisis_paths.csv).
- Outcome: evaluation incomplete. C1, C2 (path ES99 1.56%, base 1.76%), C3 (about 4.6% real), C5 (GFC drawdown 16.7% vs 19.1% static; COVID -8.6%, 2022 -9.7%) pass. C4 fails: FHS 37 vs 24.5 expected, Kupiec p 0.018, conditional coverage p 0.0005; GARCH-EVT 30, Kupiec 0.28, independence 0.0004. Clustering worse than static parity (conditional coverage p 0.009 / 0.011). Breaches cluster in 2018, 2020, 2024 and 2025, at the onset of sudden shocks.
- Descriptive: 2017-2026 CAGR 6.34% vs 6.92% static parity and 3.09% W_rec; max decline 13.1% vs 14.4% / 17.0%; walk-forward CAGR 6.14% vs 6.74%. Overlay acted on 17% of days; turnover 0.25x vs 0.15x a year. 25-year reserve survival 98.3% (static parity 97.4%, W_rec 67.4%). Overlay inactive in the slow crises (gold bear, oil, 2018) and does not help in the 2020-22 bond bear.
- No change to v3 policy, W_rec, run or verdict. Validation: tests/test_parity_overlay.py (4) pass. AI: Claude Code. Owner review pending.

2026-10-30, PORT-012 (exploratory), rebalancing rules and the risk carried:
- State: ready for review. Owner asked for the rebalancing math with the aim of knowing the risk taken, not maximising return. `python scripts/rebalancing_risk_study.py` writes results/rebalancing-risk-r1/ (report.md, rebalancing_risk.csv, metadata.json with weight hashes and price hash). Three allocations (W_rec, v3 near parity, inverse variance) x eight rules (daily, monthly, quarterly, current quarterly + 5-pt band, annual, 5/10-pt band only, never), USD 9.6m, 0% cost, no reserve, 2005-2026.
- Cross-check: W_rec daily-rebalanced ES99 USD 124,433 equals the frozen v3 run value.
- Findings: any rule that trades at least annually or on a 5-10 pt band keeps risk close to target (W_rec ES99 USD 124-126k; risk parity 161-169k). Never rebalancing raises ES99 to USD 139k (W_rec) and 209k (risk parity); risk parity's equity weight drifts from 23% to 43% and its GFC fall reaches 21.4%, beyond the 20% limit. Daily rebalancing does not lower risk. In the GFC, quarterly rebalancing of risk parity lost -6.7% against -3.6% buy-and-hold, because it buys equity as it falls; that is the price of holding risk constant.
- No change to policy, W_rec, the frozen run or the verdict. No unit tests for this exploratory script. AI: Claude Code. Owner review pending.

2026-10-30, PORT-013 (exploratory), portfolio history chart and regime/dynamic comparisons:
- State: ready for review. Owner asked how each candidate would have performed from 2005. `python scripts/portfolio_history_chart.py` writes results/charts/portfolio_history_2005.png: USD 10m from 3 January 2005 to 30 September 2026 in the final-v3-20261030 weights (W_rec, max Sharpe, static risk parity, permanent 25/50/25, balanced 35/50/15, 60/40) plus monthly EWMA (lambda 0.97) dynamic risk parity from January 2007.
- Ending values: W_rec USD 23.0m (CAGR 3.9%, max drawdown 17.1%); static risk parity 39.0m (6.5%, 19.1%); dynamic risk parity 6.2% from 2007 (18.5%); permanent 45.7m (7.3%, 19.1%); balanced 46.3m (7.3%, 22.0% on the rebalanced path although its C5 buy-and-hold GFC check passes); 60/40 53.3m (8.0%, 35.1%).
- Also shown to the owner in conversation, not saved as artifacts: per-ETF crisis versus normal risk (crisis ES99 multipliers SPY 2.6, XLE 2.9, AGG 4.3, GLD 1.3); FZ0 VaR/ES scoring of the run's own 2017-2026 forecasts, where GARCH-EVT ranks first on all seven portfolios scored and FHS second.
- Retrospective and descriptive only: weights estimated on the full sample, 0% cost, no reserve withdrawals. No change to policy, W_rec, the frozen run or the v3 verdict (evaluation incomplete). Any switch of primary model or selection rule needs a logged owner decision and a new tag.
- Validation: script re-run from the repository reproduced the conversation figures. No unit tests added for this exploratory script.
- AI: Claude Code. Owner review pending.

2026-10-30, APP-005, portfolio comparison page:
- State: ready for review. Owner asked for the PORT-013 comparison in the app. New sidebar page "Portfolio comparison": choose precomputed portfolios of the loaded run, optionally add monthly EWMA dynamic risk parity (exploratory), choose full-history or common start, and show or hide the comparison table (weights, end value, CAGR, real CAGR, volatility, maximum drawdown, GFC/COVID/2022 returns) with a CSV download. Plotly value and drawdown charts with stress windows and the drawdown limit.
- Calculations are in quanedge/comparison.py (Streamlit-free); fixed allocations use portfolio.replay. Labelled "computed in app, not part of frozen run"; dynamic risk parity has no weight hash, forecasts or verdict. With the dynamic line off the table matches the PORT-013 chart exactly; dynamic starts 2006-12-28 (500 days of history) instead of the script's 2007-01-02, so its end value is USD 39.1m rather than 39.2m.
- Validation: tests/test_comparison.py (4) and the extended tests/test_app.py pass; AppTest and a headless browser on final-v3-20261030 showed no exceptions. Full suite: 178 passed, 1 failed (tests/test_rolling.py, a GJR-GARCH fit outside the variance domain in this Linux container; it fails identically without these changes). Tag-dependent tests needed `git fetch --tags` in a fresh clone. quanedge.verify reports source hash app.py, the expected viewer-only difference; no data, policy or results changed.

2026-10-30, VAL-006 (renumbered from VAL-004 at merge), mandate v2 check run (Linux container, not the official v2 run):
- State: ready for review. `results/v2check-linux-20261030` was produced by `python -m quanedge.pipeline --stage final` against the config frozen at `prereg-v2`, in a Python 3.12 virtual environment built from `requirements.lock.txt`. `results/latest.txt` still points to the v1 run. In this environment `test_saved_forecasts_reload_to_identical_breach_counts` fails (a GJR-GARCH fit-boundary difference from the owner's Windows build); 173 other tests pass.
- Outcome: evaluation incomplete. The selected portfolio is SPY 6 / AGG 88 / GLD 6; it passes C1, C2 (ES99 1.30%), C3 (3.54% expected real) and C5 (GFC drawdown 13.1%), and fails C4. At 99%, FHS had 41 breaches against 24.5 expected (Kupiec p 0.002, conditional coverage p 0.0002, yellow). The GARCH-EVT challenger had 36 breaches (p 0.026 and 0.0006, yellow, 99.1% coverage after one GPD fit failure). Of the A1 alternatives, only risk parity passed C4 (FHS 30, GARCH-EVT 25 breaches), but it fails C5 (GFC drawdown 21.4%).
- Decision under the frozen rule: risk-model failure gives "evaluation incomplete", not Adjust or Reject. Next action, for the owner: rerun on the owner's machine for the official v2 record, then decide on a logged response (another C4 model, a changed limit, or disclosed incomplete status with an interim action).
- AI: Claude Code ran and summarised. No human validation is claimed.

2026-10-30, PORT-014 (renumbered from PORT-009 at merge; exploratory), mandate v2 allocation methods for SPY/XLE/AGG/GLD:
- State: ready for review. The owner intends to hold only SPY, XLE, AGG and GLD, and asked whether to allocate by historical variance. `python scripts/four_etf_v2_study.py` builds seven candidates (inverse variance, inverse volatility, equal risk contribution, minimum variance, minimum CVaR99, the v2 rule and maximum Sharpe). It uses the frozen v2 estimator on 2005-2026 data and runs each through `pipeline.evaluate`, including C4 on the candidate's own sequential forecasts. A compact table is in `results/four-etf-v2-r1/` (Linux, pinned Python 3.12).
- Only inverse variance (SPY 7 / XLE 3 / AGG 83 / GLD 7) passed C1-C5. Its C4 pass came from the GARCH-EVT challenger (31 breaches vs 24.5 expected, Kupiec p 0.19, conditional coverage p 0.075); FHS failed. Inverse volatility (SPY 16 / XLE 10 / AGG 57 / GLD 17) and risk parity (SPY 14 / XLE 9 / AGG 61 / GLD 16) have higher expected real returns (4.8% and 4.6%) and realised CAGRs (6.9% and 6.5% over 2005-2026, against 4.4%). They fail C4 only on breach clustering (conditional coverage p 0.011), with GFC drawdowns of 19.2% and 18.1%.
- Caveats: the method was chosen after seeing the v2 C4 failures, and seven candidates were tried, so the inverse-variance pass is thin and exposed to multiple testing. Adopting any of these is a logged mandate change (v2 selects minimum CVaR). Platform-sensitive GARCH-EVT fits apply.
- AI: Claude Code. Owner review pending.

2026-10-30, PORT-015, candidates v4d/v4e: dynamic EWMA risk parity, monthly and weekly (pre-registered, evaluated):
- State: ready for review. Owner asked for C1-C5 on the monthly dynamic risk parity and a weekly variant. Definitions committed in PLAN.md section 13e (commit 37345ca, local tag prereg-v4de; the tag push was refused by the remote) before any forecast. `python -m quanedge.dynamic_parity_eval` writes results/dynamic-parity-r1/ (paths with daily holdings and targets, forecasts with a strategy hash on every row, summary, metadata).
- Both start 2006-12-28 at SPY 21.9 / AGG 62.4 / GLD 9.4 / XLE 6.3. v4d monthly: C1, C3, C4 (GARCH-EVT challenger: 26 breaches vs 24.5, Kupiec p 0.76, conditional coverage p 0.091; FHS fails at 0.011) and C5 pass; C2 fails because the 30 September 2026 target (SPY 20.8 / AGG 51.7 / GLD 8.4 / XLE 19.1) has estimation-sample ES99 2.60% (USD 250k vs USD 240k); path ES99 1.69%. v4e weekly fails C2 (2.56%), C4 (conditional coverage p 0.011 / 0.045) and C5 (GFC drawdown 20.7%), with 1,031 rebalances and 1.73x turnover a year against 237 and 0.94x.
- Correction before recording: the first run skipped the final-day month-end decision and used the 31 August target (ES99 2.24%, which passed C2). quanedge/comparison.py now lets the last row decide when it closes its period on the business-day calendar; returns and forecasts are unchanged. The app comparison table shows each dynamic strategy's first target with "(changes monthly)" or "(changes weekly)" and adds a weekly row.
- No change to v3 policy, W_rec, run or verdict. Validation: tests/test_dynamic_parity_eval.py (4), tests/test_comparison.py and tests/test_app.py pass. AI: Claude Code. Owner review pending.

2026-10-30, MANDATE-004 / PORT-016, mandate v4: realised real CAGR floor of 4% (owner rule change, ready for review):
- Owner instruction: C3 becomes "realised real CAGR at least 4%", measured on each allocation's 2005-2026 replay (quarterly or 5-point drift rebalancing, 0% cost, no reserve withdrawals, deflated at 3.64%). Owner choices when asked: apply it to the C3 minimum only, not the selection target (still 3% expected real), and use realised rather than estimated return. PLAN.md section 13f; committed at 92bd0f0 and tagged prereg-v4 (local) before the recheck. Realised figures had already been shown to the owner, as disclosed there.
- Code: portfolio.realised_real_cagr and a v4 branch in return_check; pipeline passes each allocation's realised real CAGR; report wording follows the policy. tests/test_mandate_v4.py (3) added; the v3 C3 test now strips the v4 key. 188 other tests pass; tests/test_rolling.py still fails in this Linux container as before.
- Result (`python scripts/mandate_v4_c3_recheck.py`, results/v4-c3-recheck/): only C3 changed and weights are identical, so C1, C2, C4 and C5 carry over from final-v3-20261030. Outcome unchanged: evaluation incomplete (C4). W_rec realised real CAGR 0.27% also fails C3, as do every A1 alternative and A2. No allocation passes C1-C5: permanent (3.47%) and balanced (3.53%) now fail C3; max return (5.34%), 60/40 (4.21%) and equal weight (5.70%) pass C3 but fail C5. Outside the run, v4c 2.7%, v4d 2.4%, v4e 2.0% and inverse variance 0.8% also fall short. If C4 were fixed, the rule would give Reject. A full pipeline rerun under prereg-v4 was not performed; it would reproduce v3's C1, C2, C4 and C5.
- AI: Claude Code. Owner review pending.

2026-10-30, DOC-009, session record for deliverables (conversation of this date, Claude Code session on branch claude/wizardly-dirac-loe61w):
- State: ready for review. Owner asked that everything worked out in this conversation be logged for the memo, tear sheet and pitch. Conversation-only numbers are now reproducible: `python scripts/session_findings.py` writes results/session-findings-r1/ (regime_risk.csv, regime_correlation.csv, dynamic_strategies.csv, model_scores.csv, four_etf_returns.csv). All are retrospective portfolio evaluations on the frozen snapshot (2005-01-03 to 2026-09-30), 0% cost, no reserve withdrawals; none changes policy, W_rec or any verdict. Entries PORT-013, APP-005, PORT-015 and MANDATE-004/PORT-016 above record the committed work of the same conversation.
- Challenge rules versus our rules (for the memo's policy section): the brief fixes the client, the seven-ETF universe, the five technical layers (Markowitz/CAPM and KPIs; historical, parametric and Monte Carlo VaR at 95/99%; ES; EVT with a justified threshold; Kupiec, Christoffersen and traffic-light backtests), GFC/COVID/2022 plus one hypothetical stress, risk budgeting, an accept/adjust/reject memo, the six app components, data rules and AI disclosure. It sets no numerical horizon, return target, risk limit, weight limit or construction method ("full discretion", brief pp. 3-4); every number in PLAN.md sections 13-13f is our choice.
- Per-ETF risk, normal days versus the pooled stress windows (576 crisis days; regime_risk.csv): historical ES99 a day SPY 3.53% -> 9.20%, XLE 5.13% -> 15.00%, AGG 0.84% -> 3.62%, GLD 4.19% -> 5.62%; crisis/normal ES99 multipliers 2.6, 2.9, 4.3, 1.3. Normal VaR99 understates crisis historical VaR99 for every ETF (XLE 8.0% vs 12.4%). Correlation with SPY in crises: XLE 0.66 -> 0.78, AGG -0.04 -> 0.06, GLD 0.09 -> 0.01. Buy-and-hold GFC: SPY -54.8%, XLE -46.9%, AGG +7.2%, GLD +24.9%; 2022: XLE +49.0%, AGG -15.0%. W_rec daily ES99 normal 0.85% (about USD 84k on 10m), crisis 3.45% (about USD 345k), above the USD 240k budget, which C2 measures on the full estimation sample, not crisis days only.
- Why W_rec differs from risk parity: the v2/v3 rule minimises CVaR99 subject to 3% expected real return; minimum CVaR (SPY 5.8 / AGG 88 / GLD 6 / XLE 0.2) already expects 7.31% nominal = 3.54% real (Fisher: 1.07313/1.0364 - 1), so the target never binds and the rule concentrates in AGG. Risk parity (14 / 60.9 / 16.3 / 8.8, 25% volatility contribution each) is only the A1 near-parity comparison candidate. On raw means W_rec expects about 0.25% real.
- Dynamic study (dynamic_strategies.csv; monthly decisions from data through each month-end close, 2007-2026): EWMA (lambda 0.97) risk parity CAGR 6.18%, max drawdown 18.5%, GFC -4.9%, COVID -9.3%, 2022 -10.3%, turnover 0.95x; static risk parity 5.99%, 19.1%; 1-year-covariance risk parity 6.06%, 18.1%; dynamic min-variance 3.83% and min-CVaR 4.27% stay 55-100% AGG. 2017-2026: EWMA risk parity 7.26% (max drawdown 13.5%) vs W_rec 3.09% (17.0%). No method avoided the 2022 loss (-10 to -15%). EWMA explanation for the memo: day weights proportional to 0.97^k (half-life about 23 trading days), covariance from those weights, then equal 25% risk contributions; at 30 September 2026 the target is SPY 20.8 / AGG 51.7 / GLD 8.4 / XLE 19.1 (gold EWMA volatility 25.3% vs 18.3% long-run).
- Risk-model scoring (model_scores.csv; FZ0 joint VaR/ES99 loss of each model's own sequential forecasts, 2017-2026): GARCH-EVT scores best on all seven portfolios scored (W_rec, near parity, max Sharpe, min variance, permanent, balanced, 40/60), FHS second; historical, unconditional EVT and normal clearly worse because their breaches cluster. Evidence for a possible logged switch of primary model to GARCH-EVT; not adopted. Under the C4 pass rule only balanced 35/50/15 and permanent 25/50/25 pass with GARCH-EVT among fixed portfolios in final-v3-20261030.
- Portfolios holding all four ETFs, with actual US CPI and 3-month T-bills (four_etf_returns.csv): CPI averaged 2.59% a year and T-bills 1.80% (real -0.77%). Real CAGR on CPI (3.64% basis in brackets): W_rec 1.29% (0.27%), min variance 1.10% (0.07%), inverse variance 1.77% (0.74%), dynamic weekly 3.06% (2.01%), dynamic monthly 3.49% (2.43%), static risk parity 3.77% (2.72%), v4c 3.75% (2.70%), equal weight 6.78% (5.70%). Sharpe over T-bills: v4c 0.73 highest, dynamic monthly 0.71, risk parity 0.68, W_rec 0.43. Under v4's C3 (4% real on the 3.64% basis) only equal weight passes, and it fails C2, C4 and C5; the CPI basis would be another logged rule change and gives the same C3 results.
- Candidate inventory for the deliverables: fixed-weight portfolios rebalance quarterly or on a 5-point drift; strategies that change targets over time are walk-forward yearly re-selection (validation only), PORT-003 drawdown bands/CPPI, PORT-004/005 EWMA volatility overlay, PORT-007 winner-to-loser (rejected), PORT-008 trend and volatility-target filters, v4c (PORT-011), v4d/v4e (PORT-015) and the governance ladder (policy text, never simulated). Benchmarks: 40/60 SPY/AGG (Information ratio and tracking), SPY (beta, Treynor, Jensen), DTB3 (Sharpe, Sortino), plus 60/40, equal weight, permanent 25/50/25, balanced 35/50/15 and unconstrained risk parity as comparisons. No allocation passes C1-C5 under v4.
- Repository housekeeping in this conversation: branches claude/gracious-mendel-uemnkf and claude/funny-mendel-xbog3a were merged into main (b0937cd) so main is behind no branch; duplicate task IDs from parallel sessions were renumbered (this session's chart PORT-010 -> PORT-013; that branch's VAL-004 -> VAL-006 and PORT-009 -> PORT-014). Local tags prereg-v4c, prereg-v4de and prereg-v4 could not be pushed (remote refused); their commits are on GitHub.
- Limits for the memo: everything above is hindsight on data used to build the portfolios; realised-return gates are path-dependent; the CPI series is revised data with an approximate publication lag; the 3.64% inflation source is still unverified. Conversation content from other chats is only recorded where those sessions committed AGENTS.md entries (PORT-010 to PORT-012, VAL-006, PORT-014 above).
- Validation: scripts/session_findings.py reproduces the conversation figures (checked against the values shown). No unit tests for this evidence script. AI: Claude Code. Owner review pending.

2026-10-30, PORT-023 (renumbered from PORT-013 at merge; exploratory), real return on FRED CPI and reward over the FRED 3-month T-bill:
- State: ready for review. Owner asked to use only approved sources (brief section 9.1) for inflation and the risk-free rate. `python scripts/real_return_riskfree_study.py` writes results/real-return-rf-r1/ (report.md, summary.csv, yearly.csv, metadata.json with source hashes and weight hashes). CPIAUCSL index ratios as published; DTB3 bond-equivalent daily rate; quarterly + 5-pt rebalancing, 0% cost, no reserve.
- 2005-2026: US CPI 2.59% a year, T-bill 1.80% (-0.77% real). Real CAGR / excess over T-bill / Sharpe: W_rec 1.29% / 2.12% / 0.43; risk parity 3.77% / 4.66% / 0.68; SPY25/AGG50/GLD25 4.53% / 5.44% / 0.72; 60/40 5.27% / 6.20% / 0.57 (max fall 35%). 2017-2026: W_rec -0.26% real, 0.58% over T-bills, Sharpe 0.13, beat T-bills in 5 of 10 years; risk parity 3.44% real, Sharpe 0.64.
- Decision point for the owner: the mandate's 3.64% "world" inflation has no approved-source record (World Bank WLD could not be fetched: data.worldbank.org and api.worldbank.org are blocked by this session's network policy). FRED CPI is approved and gives 2.59% over the sample. Any change of the policy inflation figure is a logged mandate change.
- No change to policy, W_rec, runs or verdict. No unit tests for this exploratory script. AI: Claude Code. Owner review pending.

2026-10-30, PORT-017 (exploratory), risk parity with a correlation-threshold tilt into gold:
- State: ready for review. Owner proposed starting from risk parity and, when the stock-bond correlation leaves +/-0.3, selling SPY for GLD (example: 2022 Q1). Rule fixed in the docstring of `scripts/correlation_tilt_study.py` before the first run: quarterly ERC on the trailing 750-day covariance; 63-day corr(SPY, AGG) at the decision close; rho > 0.3 moves 10 points SPY -> GLD (two-sided variant: rho < -0.3 moves 10 points GLD -> SPY); targets apply from the next day; 0% cost, no reserve. Output in results/correlation-tilt-r1/.
- Finding: the signal did not fire before 2022. corr(SPY, AGG) was -0.26 at 2021-12-31 and +0.02 at 2022-03-31; it first exceeded 0.3 at 2022-09-30, after the losses, when SPY recovered. 2022 return -10.52% with tilt vs -10.62% without. GLD was not at a low in 2022 Q1: it peaked on 2022-03-08 (+12%) and bottomed on 2022-09-26 (-12%). Even a perfect-hindsight 10-point SPY -> GLD switch on 2021-12-31 would have saved about 1.7% of NAV in 2022 (SPY -18.2%, GLD -0.8%).
- Full path 2006-12-29 to 2026-09-30: CAGR 6.37% no tilt, 6.24% one-sided, 6.41% two-sided; max fall 18.2%, 18.2%, 19.2%; GFC -6.0%, -6.0%, -9.8% (two-sided added equity before 2008). Tilt helped in 17 of 30 quarters, +0.9 points in total. Across thresholds 0.2-0.4, windows 63/126 and sizes 5-20 points, CAGR changes stay within -0.31 to +0.03 points and maximum fall is unchanged. Base risk parity already responds to correlation through the covariance.
- Decision proposed: do not adopt. Retrospective, prompted by 2022; no change to policy, W_rec, the frozen run or the verdict. No unit tests for this exploratory script.
- AI: Claude Code. Owner review pending.

2026-10-30, PORT-018 (exploratory), negative-correlation trigger (< -0.25):
- State: ready for review. Owner follow-up to PORT-017: act when the correlation is below -0.25. Implemented as the PORT-017 base plus a 10-point SPY -> GLD move when the 63-day corr(SPY, AGG) or corr(SPY, GLD) is below -0.25 at a quarter-end close. `python scripts/correlation_tilt_study.py --negative` writes results/correlation-tilt-r2/; the PORT-017 output is unchanged.
- Hindsight: -0.25 was proposed after the 2021-12-31 corr(SPY, AGG) of -0.26 and 2022-03-31 corr(SPY, GLD) of -0.38 had been shown.
- 2006-12-29 to 2026-09-30, no tilt / SPY-AGG signal / SPY-GLD signal: CAGR 6.37 / 6.32 / 6.53%; max fall 18.2 / 17.2 / 16.0%; ES99 1.72 / 1.72 / 1.64%; GFC -6.0 / -1.9 / -3.6%; COVID -9.9 / -6.8 / -6.8%; 2022 -10.6 / -9.7 / -9.7%. The SPY-GLD signal fired in 11 of 80 quarters (5 helped, +2.9 points in total); the SPY-AGG signal fired in 29 (12 helped, -0.7 points). The crisis improvements hold for thresholds -0.2 to -0.3 and windows of 63 or 126 days; the 2022 gain disappears in some settings.
- Reading: the SPY-GLD version acts as a flight-to-safety signal that cuts equity in stress. The gains are small, rest on few events and were fitted after seeing them. Adoption would need pre-registration and its own C1-C5 evaluation with weight-hashed forecasts, as for v4d. No change to policy, W_rec, the frozen run or any verdict. No unit tests for this exploratory script.
- AI: Claude Code. Owner review pending.

2026-10-30, PORT-019 (exploratory), rebalancing risk parity on a negative-correlation trigger:
- State: ready for review. Owner proposed selling the ETF that rose and buying the one that fell whenever a pair's correlation is below -0.5, rebalancing the risk-parity weights. Rules fixed in the docstring of `scripts/negcorr_rebalance_study.py` before the first run; output in results/negcorr-rebalance-r1/. Target v3 near parity (hash ece535c3); trigger at a month-end when any pair's within-month daily correlation is below -0.5 (66 of 261 months); 0% cost, no reserve.
- 2005-2026, CAGR / max fall / ES99 / turnover a year: normal quarterly + 5-point band 6.46% / 19.1% / 1.72% / 0.15x; trigger only 6.44% / 18.9% / 1.69% / 0.12x; normal plus trigger 6.45% / 19.2% / 1.73% / 0.18x; 5-point contrarian tilt 6.47% / 19.2% / 1.73% / 1.00x; buy-and-hold 7.12% / 21.4% / 2.18%. 2020-2026: normal 7.29% CAGR, trigger only 6.93%, tilt 7.23%. Differences between the rebalancing variants are within about 0.4 points of CAGR and 0.4 points of maximum fall; no reversal benefit, consistent with PORT-007.
- Decision proposed: do not adopt; keep quarterly plus 5-point drift. Retrospective (full-sample weights; trigger proposed after the 2020-2026 correlations were shown). No change to policy, W_rec, the frozen run or any verdict. No unit tests for this exploratory script.
- AI: Claude Code. Owner review pending.

2026-10-30, PORT-019 addendum, quarterly trigger:
- Owner asked to test the same trigger on calendar quarters (within-quarter correlation below -0.5, at quarter-end). It fired in 9 of 87 quarters, the last before 2026 in 2016-06. 2005-2026: trigger-only quarterly 6.79% CAGR, 18.6% max fall, ES99 1.86%, 0.05x turnover; quarterly contrarian tilt 6.45%, 19.0%, 1.72%, 0.25x; normal 6.46%, 19.1%, 1.72%, 0.15x. Trigger-only quarterly is close to buy-and-hold (one rebalance since 2016); its higher return comes from equity and gold drift, not timing. Quarterly tilt matches normal. Conclusion unchanged.

2026-10-30, PORT-020 (exploratory), relative-band rebalancing and a capped dip-buying ladder:
- State: ready for review. Owner asked to test both "buy low, sell high" options proposed in conversation. Rules fixed in the docstring of `scripts/band_ladder_study.py` before the first run; output in results/band-ladder-r1/ (summaries, ladder_events.csv, metadata with weight hash ece535c3 and price hash). Option 1: quarter-end plus +/-20% relative band. Option 2: option 1 plus +2.5/+5 points for SPY, GLD or XLE at 30%/45% below the 756-day high, funded from the ETF furthest above target, removed at half recovery. 0% cost, 5 bp sensitivity, no reserve.
- 2005-2026, CAGR / max fall / ES99 / GFC / COVID / turnover: normal 6.46% / 19.1% / 1.72% / -6.5% / -11.2% / 0.15x; relative band 6.45% / 18.8% / 1.76% / -5.7% / -12.2% / 0.17x; band only 6.40% / 19.2% / 1.76%; band + ladder 6.65% / 19.3% / 2.00% / -9.0% / -14.4% / 0.26x; buy-and-hold 7.12% / 21.4% / 2.18%. 2020-2026: normal 7.29%, relative band 7.03%, band + ladder 7.47% (max fall 16.9% vs 14.4%). 5 bp costs change CAGR by at most 0.02 points.
- Reading: relative bands are equivalent to the current rule. The ladder adds about 0.2 points of CAGR with higher risk (ES99 +0.28 points, deeper crisis losses) because it buys during crashes (XLE and SPY in Oct 2008 and Mar 2020); its gain comes mainly from the 2009 and 2020 rebounds and the 2021-22 energy rally. The ladder re-triggered XLE several times while it stayed 30% below its 3-year high. Decision proposed: keep the current rule; do not adopt the ladder for a conservative endowment. No change to policy, W_rec, the frozen run or any verdict. No unit tests for this exploratory script.
- AI: Claude Code. Owner review pending.

2026-10-30, PORT-020 addendum, dynamic EWMA risk parity added to the table:
- Owner asked to add monthly dynamic EWMA risk parity (lambda 0.97, 750-day window) from 2005. A 63-day warm-up starts it on 2005-04-06; the pre-registered v4d version (500 days) starts 2006-12-28. 2005-2026: 6.43% CAGR (6.38% at 5 bp), max fall 18.5%, ES99 1.64%, GFC -4.9%, COVID -9.3%, 2022 -10.3%, 12 trades and 0.96x turnover a year (v4d: 6.16% CAGR, same falls). 2020-2026 (same targets in both): 7.62% CAGR, max fall 13.5%, ES99 1.96%. Lowest volatility, ES99 and crisis losses of the rebalanced rules, with similar return; unlike the static rules it uses only data available at each decision. v4d's C2 failure (PORT-015) still applies. No change to policy, W_rec, the frozen run or any verdict.
- Common start (owner request): the full-period table now starts every method on 2005-04-06 (first return after dynamic RP's 63-day warm-up); fixed rules start at target on the 2005-04-05 close and the v4d row is dropped. 2005-04 to 2026-09: normal 6.47% / 19.1% / ES99 1.73%; relative band 6.47% / 18.8% / 1.76%; band only 6.41% / 18.8%; band + ladder 6.67% / 19.3% / 2.01%; buy-and-hold 7.13% / 20.4% / 2.14%; dynamic RP 6.43% / 18.5% / 1.64%. 2020-2026 already shared a 2020-01-02 start.
- Weekly and quarterly dynamic RP added (same lambda 0.97, 750-day window, 63-day warm-up, start 2005-04-06). 2005-04 to 2026-09, CAGR / max fall / ES99 / GFC / COVID / 2022 / turnover: monthly 6.43% / 18.5% / 1.64% / -4.9% / -9.3% / -10.3% / 0.96x; weekly 5.99% / 20.7% / 1.74% / -8.1% / -10.5% / -9.9% / 1.74x; quarterly 6.22% / 18.1% / 1.69% / -4.4% / -12.9% / -11.7% / 0.55x. 2020-2026: monthly 7.62%, weekly 7.31%, quarterly 7.17%. Monthly is the best balance; weekly breaches the 20% decline limit in the GFC (as v4e did in PORT-015), quarterly reacts too slowly to COVID.

2026-10-30, PORT-021 (exploratory), correlation tables, buy-low evidence and rebalancing-frequency reasoning:
- State: ready for review. Saves figures shown to the owner in conversation so the deliverables can cite them. `python scripts/session_evidence_study.py` writes results/session-evidence-r1/ (CSVs plus metadata with the price hash). Summary in PLAN.md section 19b.
- Correlations (daily log returns, 2020 to 2026-09): only XLE-AGG 2026 (-0.38) is below -0.3 for a full year. Below -0.3: 10 pair-quarters and 52 pair-months; below -0.5: 12 months (XLE-AGG in 8, SPY-GLD in Jan 2020, Mar 2022 and May 2025, SPY-AGG in 3, SPY-XLE in Apr-May 2026). Monthly ETF returns are saved beside each row. Owner's observation, confirmed: correlation measures co-movement, not the size of the return gap (XLE-AGG -0.68 in Mar 2023 with a 2.6-point gap; -0.51 in Nov 2020 with a 26.8-point gap). Gap measures: spread, spread volatility sqrt(s_a^2 + s_b^2 - 2 rho s_a s_b), spread z-score.
- Buy low / sell high: after the first 30% fall since 2005, SPY (2008-10-06) fell to -55% and returned +3.4% a year later; XLE (2008-09-29) -7.2% a year later and later -71% (2014-2020); GLD (2013-06-20) to -46% and +2.3%. After a +20% trailing year, next-12-month returns were SPY 10.5% vs 12.3% on all dates, XLE 8.9% vs 10.7%, GLD 17.8% vs 12.9% (AGG has one such day). Proposed method: target weights with relative bands; optional capped dip ladder (tested in PORT-020). Criticisms recorded in PLAN.md 19b.
- Rebalancing frequency for dynamic EWMA risk parity: GJR-GARCH volatility half-lives (full-sample fit) SPY 34, AGG 49, XLE 68, GLD 219 trading days; share of an SPY shock left after 1 week / month / quarter 90% / 65% / 28%. EWMA lambda 0.97: half-life 22.8 days, effective sample 66 days, new information 14% / 47% / 85% after 5 / 21 / 63 days. With monthly CPI and payrolls and eight FOMC meetings a year, these support monthly re-estimation; the backtest agrees but is not the reason. Business cycles and stock-bond correlation regimes move over years, so the allocation should change gradually; no calendar catches day-scale crashes.
- No change to policy, W_rec, the frozen run or any verdict. No unit tests for this exploratory script. AI: Claude Code. Owner review pending.

2026-10-30, PORT-022, owner's choice of dynamic EWMA risk parity (monthly) as the final portfolio: rule check, not adopted yet:
- State: blocked on owner decisions. Owner asked to make monthly dynamic EWMA risk parity (lambda 0.97, 750-day window) the final portfolio and to check it against the rules. Checked against mandate v4 using the pre-registered v4d evaluation (results/dynamic-parity-r1, PORT-015); the 63-day warm-up version starting 2005-04-06 has the same targets and the same 2017-2026 path, so the results carry over (its own strategy hash and forecast file would be needed in a formal run).
- C1 pass (targets long-only, four ETFs; ranges SPY 6-26%, AGG 34-84%, GLD 3-32%, XLE 4-19%). C2 fail: 30 Sep 2026 target (SPY 20.8 / AGG 51.7 / GLD 8.4 / XLE 19.1) has estimation-sample ES99 2.60% (USD 250k vs USD 240k); path ES99 1.69%. C3 (v4) fail: realised real CAGR 2.4% (v4d from 2006-12) or 2.7% (from 2005-04) vs 4%; under v3's expected-real measure it passes at 4.9%. C4 pass via GARCH-EVT challenger (26 breaches vs 24.5, Kupiec p 0.76, conditional coverage p 0.091, green); FHS primary fails on clustering (p 0.011). C5 pass (GFC -5.0%, drawdown 18.5%; COVID -9.5%; 2022 -10.0%). It is not what the v4 selection rule (minimum CVaR99) picks and is not in A1-A2, so adopting it is a mandate change. 25-year reserve survival has not been computed for it.
- No allocation in the v3/v4 runs passes both the 4% realised floor and C5.
- Proposed (awaiting owner): (1) C2: monthly ES cap, shifting weight to AGG until the target's ES99 is at most 2.5%; (2) C3: return to v3's expected real >= 1%, or lower the realised floor, disclosed as a change after results were seen; (3) mandate v5 in PLAN.md with tag prereg-v5 before a full run (strategy-hashed forecasts, reserve survival, app frozen panel, memo, tear sheet). Disclose: chosen after many comparisons in this session; C4 passes only through the challenger; GFC margin 1.5 points; C2 missed by 4%.
- W_rec, the v3/v4 verdict (evaluation incomplete) and all frozen runs unchanged. AI: Claude Code. Owner review pending.

2026-10-30, session index (one conversation, all on branch claude/laughing-curie-b5ewos), for building deliverables:
- PORT-017 correlation-threshold SPY->GLD tilt (> +0.3): signal came after the 2022 losses; not adopted. results/correlation-tilt-r1.
- PORT-018 negative-correlation trigger (< -0.25): SPY-GLD signal slightly lower risk, few events, hindsight-chosen. results/correlation-tilt-r2.
- PORT-019 correlation-triggered rebalancing (< -0.5, monthly and quarterly): no gain over normal rebalancing. results/negcorr-rebalance-r1.
- PORT-020 relative bands, capped dip ladder and dynamic EWMA risk parity (monthly, weekly, quarterly; common start 2005-04-06): monthly dynamic has the lowest risk with similar return. results/band-ladder-r1.
- PORT-021 correlation tables, buy-low evidence, frequency reasoning. results/session-evidence-r1; PLAN.md 19b.
- PORT-022 rule check of dynamic risk parity as final portfolio: fails C2 and C3 (v4); owner decisions pending.

2026-10-30, PORT-024 / PORT-025 / PORT-026 / DOC-010 (exploratory; numbered after the parallel sessions' PORT-013 to PORT-023 and DOC-009), correlations by year, risk-parity windows, 4% real target, findings index:
- State: ready for review. Owner asked to put everything from this conversation on GitHub for the final deliverables. Scratch analyses converted to reproducible scripts: `scripts/yearly_correlation_study.py` (results/yearly-correlation-r1), `scripts/risk_parity_window_study.py` (results/risk-parity-window-r1), `scripts/real_target_study.py` (results/real-target-r1). PLAN.md section 19c indexes PORT-010 to PORT-012 and PORT-023 to PORT-026 with commands, findings, a code issue and the open owner decisions.
- Findings: SPY-AGG correlation negative 2007-2019, positive from 2020. Shorter risk-parity windows take more risk; use all history with a 3-year check. 4% real (break-even 4.17%) was met historically only by SPY 28 / AGG 42 / GLD 30 at a 19.9% GFC fall.
- Code issue: near_parity squared-gap solver can return a corner on short windows (2007 data: AGG 0%); committed runs unaffected (match convex ERC). Not fixed, to keep frozen source hashes; fix with a test before any new risk-parity run.
- Tag prereg-v4c could not be pushed (remote refused, HTTP 403); its commit 085b621 is on GitHub. No change to policy, W_rec, runs or verdict. No unit tests for the exploratory scripts. AI: Claude Code. Owner review pending.
