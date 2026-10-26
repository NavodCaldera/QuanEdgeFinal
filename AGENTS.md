# QuantEdgeFinal: complete competition build prompt

## 1. Your assignment

You are the quantitative research and software-development assistant for Team Ghosted in the SAIFA Quant Edge 1.0 final challenge. One person owns the whole submission: data, portfolio, risk, validation, stress testing, the app and every document. There is no division of work between people. Build and validate the complete competition submission from the current repository. This file is the single implementation prompt for GPT, Claude, Gemini or another coding assistant. Read it fully, inspect the current project, identify the remaining work, make an ordered plan, and implement that plan in tested stages.

When this file is supplied in another model's chat, follow the same specification using that model's available tools. If repository files or execution tools are unavailable, state the limitation and provide concrete implementation artifacts where possible. Do not pretend to inspect files, run commands or produce results without doing so.

Preserve working components and extend the existing Python package. `PLAN.md` holds the competition facts and the ordered work plan; do not create further AGENTS.md files, implementation prompts, planning packs or work-log documents. Keep build instructions and a concise progress/decision record here. README is for users; technical reports, data dictionaries, generated evidence and final submissions remain separate artifacts.

## 2. Client, objective and authoritative requirements

The client is the Serendib University Endowment Fund, a conservative institutional investor with a USD 10,000,000 portfolio supporting scholarships, research, faculty development and capital projects. Preserve and grow capital over the long term, balance income and sustainable real growth, and prioritize avoiding large losses and maintaining resilience over maximizing expected return.

Define and justify the investment horizon, nominal/real return objective, asset allocation, acceptable loss, concentration limits, risk constraints, rebalancing and monitoring rules. Treat numerical targets as proposed assumptions until the owner accepts them. The assistant may develop a defensible candidate portfolio and recommendation, but final human investment judgement and review must be identified honestly.

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

Authoritative source: `../Quant edge 1.0 Final Challenge 1.pdf`, 10 pages. Supporting sources: `../Advanced_Risk_Management_English_final.pdf` and matching PPTX (28 pages/slides); `../EDGEFORGE_Polished_Finance_First_Masterclass_2026.pdf` and matching PPTX (99 pages/slides, with additional speaker notes). The pasted competition summary is supplemental. This prompt includes the core requirements so it remains usable when those local references are unavailable.

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
- Client policy: horizon, return objective, inflation/spending assumptions where used, tolerable drawdown/loss, concentration, liquidity/rebalancing and risk budgets.
- Expected returns, volatility, correlation, covariance and diversification. Use consistent frequency and annualization; justify estimators and stability measures.
- Markowitz mean-variance construction and CAPM concepts, including benchmark, beta, risk-free alignment and expected/realized-return distinctions.
- Transparent candidate comparison: suitable baselines (for example equal-weight and constrained minimum-variance) plus proposed allocation. Explain feasibility, sensitivity to estimates, diversification and downside trade-offs.
- Optimization constraints, objective, solver status, budget checks and sensitivity. Verify that weights are feasible; show infeasibility rather than silently relaxing client limits.
- Benchmark-aligned Sharpe, Sortino, Treynor, Jensen's alpha, Information ratio, maximum drawdown, Calmar ratio, cumulative return and relevant annualized return/volatility.

Define each KPI precisely: excess/active return, downside target, sample/annualization choices, benchmark and risk-free proxy, drawdown path and CAGR. Handle zero or negative denominators appropriately; beta near zero makes Treynor unreliable. Information ratio needs tracking error; Calmar uses a consistent annualized return/drawdown period.

Use simple returns to compound wealth and calculate portfolio P&L. Decide how costs and rebalancing enter reported performance; do not imply cost-free replay is a realistic traded strategy. Avoid optimizing on the same full dataset used to claim out-of-sample performance. Final candidate weights should be selected using training/validation evidence, with a locked final evaluation where practical.

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
- Normal asset-log simulation followed by nonlinear portfolio aggregation need not match a normal fit to portfolio log returns exactly; use the one-asset matching-model case for exact-model convergence checks.

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

## 10. Out-of-sample validation

Generate each day-t forecast using data available through t-1. Preserve training start/end, last parameter-refit date, forecast date, selected settings, data/weight hashes and failures.

Existing default rolling implementation: 750 observations, daily historical/normal refits, slow-model refits every 21 observations and daily conditional-volatility updates. Justify final choices. Forecasts include historical, normal, Student-t, EVT, FHS and GARCH-EVT; MC is absent. If MC becomes the selected validation model, implement its actual forecast path rather than substituting normal forecasts.

Use `save_forecasts`/`load_forecasts` to preserve precision and breach decisions. Forecast column example: `var_evt_99`, in log-loss units. A breach is strictly `-return > var_forecast`. Show unavailable forecast days and coverage; exclude failures from numerical denominators without hiding them or treating them as safe days.

Implement:
- Kupiec proportion-of-failures test: counts, expected rate, LR statistic, p-value and interpretation, including zero/all-exception boundaries.
- Christoffersen independence test: transition counts, LR statistic, p-value and explicit handling of insufficient transitions or degenerate sequences.
- Basel traffic-light classification with a clearly specified confidence and observation count. The traditional benchmark is 99% one-day VaR over 250 observations; do not reuse its thresholds unaltered for arbitrary sidebar levels or sample lengths. Verify and cite the chosen authoritative calibration or explicitly label an alternative binomial assessment.

Show whether breaches are too frequent, clustered or inconclusive and whether the model is acceptable, questionable or unreliable. Test model selection outside the final evaluation set. In-sample breach counts are descriptive fit checks, not a backtest. A passing coverage test alone does not establish independence or model suitability.

## 11. Stress testing and risk contributions

Replay historical return paths for 2008 GFC, March 2020 COVID and the 2022 rate-hiking drawdown. Choose and document exact scenario dates, positions and rebalancing/cost assumptions; give valid data coverage and comparable cumulative wealth loss.

Design at least one clearly labelled hypothetical scenario with justified joint shocks, such as simultaneous equity/bond losses, technology collapse or emerging-market crisis. A deterministic scenario does not have an implied calibrated probability unless separately estimated.

For every scenario report portfolio return, USD loss, per-asset impact, largest damage contributors and whether policy limits are breached. Explain why bonds/gold may or may not diversify the scenario rather than promising protection.

Implement and interpret marginal/component VaR, marginal ES, position sizing and risk budgeting where appropriate to the model. Specify derivatives with respect to dollar exposures or funded reallocations: bump-and-renormalize weights measures a different quantity from an independent exposure derivative. Use common random scenarios and test finite-difference sensitivity. Reconcile component sums only where the homogeneity/differentiability assumptions support it.

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
- Sidebar: 90/95/99% confidence, VaR methodology, backtest dates and portfolio weights.
- Portfolio panel: recommended/current weights, policy/benchmark context, cumulative return, drawdown and performance KPIs.
- Risk dashboard: VaR, ES and EVT estimate side by side at matching confidence, horizon, value and portfolio, with status/basis labels and relevant uncertainty.
- Backtesting: forecasts and exceptions, Kupiec and Christoffersen statistics/p-values, observation coverage and correctly calibrated traffic light or explicit unavailability.
- Stress panel: all required historical scenarios plus the hypothetical scenario, dollar/percentage loss and asset attribution.
- Risk-contribution view and actionable accept/adjust/reject recommendation linked to limits and evidence.
- A clearly labelled **Assumptions & Limitations** page in plain language.
- Data/source provenance, as-of dates, development/final status and downloadable evidence as useful.

Changing weights must invalidate relevant results. A backtest date filter selects evaluation dates while preserving earlier training history. A method unavailable for forecasting must be explained rather than silently substituted. Distinguish exploratory user weights from the recommended portfolio.

Provide clear loading, input-error, insufficient-history and failed-fit states. Never display missing validation as a green indicator. Use readable charts/labels and avoid fabricated results. Add Streamlit and any necessary packages to the documented dependency setup only when implemented.

## 14. Verification and reproducibility

Keep unit tests offline using synthetic distributions or versioned snapshots. Use independent calculations, integration, known-parameter simulation and cross-implementation likelihood checks. Match stochastic tolerances to sampling uncertainty; do not cherry-pick seeds.

Required coverage:
- Data: returns identity, calendar classification, missing/anomaly handling, as-of macro alignment, risk-free units, manifest hashes and report/data consistency.
- Portfolio: budget/constraint feasibility, solver failures, benchmark alignment, independent KPI/wealth/drawdown examples and temporal leakage.
- Risk: tail ties/fractional mass, exact monetary ES, normal/t closed forms, simulation convergence and singular covariance/overflow.
- EVT: positive/zero/negative shape, support, infinite log ES, threshold failure/fallback, body/tail normalization and sensitivity.
- Conditional/rolling: recursion, timing/refit boundaries, future-data perturbation, missing forecasts and exact CSV round trips.
- Validation: known exception sequences, zero/all breaches, transition degeneracy and traffic-light calibration.
- Stress/attribution: scenario arithmetic, path/rebalancing assumptions, contribution reconciliation and units.
- App/integration: controls, cache invalidation, missing data, unavailable models and consistent run identifiers.
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
- Formal validation, stress losses, attribution and practical risk-budget actions.
- An actionable accept/adjust/reject recommendation, what can go wrong, how bad losses may become and reliability limits.

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

Completion requires all mandatory analytical layers and app panels, reproducible run instructions, independent numerical evidence, honest model failures, formal out-of-sample tests, required scenarios and attribution, deliverable artifacts and accurate AI disclosure. A passing test suite alone is not final human review or investment approval.

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
