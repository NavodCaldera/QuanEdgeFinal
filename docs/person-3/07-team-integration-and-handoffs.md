# Integration and handoffs

## Person 1: data owner

Receive adjusted-price/return snapshot, metadata and quality log. Confirm dates, ticker ordering, adjustment and missing-value policy before fitting. Supply any suspected anomalies for investigation; retain real extreme observations. Keep `dev_data.py` and its cache as explicitly temporary until the approved dataset has a tested adapter. Do not make a second untracked cleaning pipeline.

## Person 2: portfolio owner

Receive weight mapping, constraints, effective/as-of date, rebalancing rule and value. Return matched VaR/ES/EVT estimates for their candidate portfolios and evidence on sensitivity to weights. Person 2 decides allocation and investment policy with the team. Avoid reporting development equal weights as a recommendation.

If weights are changed, invalidate affected risk estimates, forecasts and saved tables by portfolio/configuration identifiers. Separately document static historical exposure replay and time-varying strategy evaluation.

## Person 4: validation, stress and risk-budget owner

Callable interface:

```python
from quanedge.risk import portfolio_log_returns, rolling_forecasts, breach_summary, load_forecasts

r = portfolio_log_returns(asset_log_returns, weights)
fc = rolling_forecasts(r)  # needs window + 1 days; rejects unsupported methods and bad settings
counts = breach_summary(fc, start="2020-01-01", end="2020-12-31")
fc = load_forecasts("results/risk/tables/rolling_forecasts.csv")  # the saved full run, bit for bit
```

Forecasts use `return`, `var_{method}_{level}` and `es_{method}_{level}`, all in log-return/loss units, plus `train_start`, `train_end` and `refit_train_end`. A breach is `-return > forecast_var` (strict). What Person 4 needs is in place: full precision through `save_forecasts`/`load_forecasts`, training and refit dates, rolling settings and data/weight hashes in `manifest.json`, and failed refits listed there with their forecasts left NaN. `breach_summary` excludes NaN days from the denominator, because failed forecasts cannot count as non-breaches.

The default rolling methods are historical, normal, Student-t, EVT, FHS and GARCH-EVT. MC methods are absent. Agree the selected method before formal validation; implement its actual forecasting path if it is not supported. Filter a precomputed forecast series by evaluation dates; do not trim away required training history before producing the series.

Person 4 performs Kupiec, Christoffersen and traffic-light interpretation, historical crises (2008, March 2020, 2022), one hypothetical scenario and attribution. Person 3 supplies model assumptions, callable risk functions and common simulations and helps explain failures. A model passing coverage alone may still fail independence.

For marginal/component risk, agree exposures and derivative definition. Bumping one portfolio weight while renormalizing all weights measures a funded reallocation, not the same derivative as changing one dollar exposure holding others fixed. Use consistent units and common random scenarios when comparing nearby exposures. Person 4 owns the attribution mathematics and reconciliation; Person 3 should expose per-asset scenarios instead of only aggregated MC losses when needed. Do not claim simple risk contributions sum to log ES without checking the homogeneity assumptions.

## Person 5: app and submission owner

Current interface:

```python
from quanedge.risk import fit_models, risk_table
from quanedge.risk import plots

models = fit_models(asset_log_returns, weights)
table = risk_table(models, alphas=(0.90, 0.95, 0.99))
figure = plots.fig_comparison(table)
```

Fit once and query confidence where possible. Cache by dataset, weights, as-of date, model settings, simulation seed and valuation convention; invalidate on any material input change. Benchmark real execution time instead of promising earlier claimed runtimes.

Provide matching-confidence, matching-horizon VaR/ES/EVT views, log versus dollar-unit metadata, empirical-body versus extrapolated-tail labels, conditional versus unconditional labels, warnings and model availability. Keep expensive bootstrap/rolling work outside each sidebar rerun where practical, with visible run provenance. Map the selected backtest date range to valid forecasts. Do not display absent formal tests as a green traffic light.

Plot functions are `fig_distribution`, `fig_threshold`, `fig_evt_fit`, `fig_comparison`, `fig_tail_curve`, `fig_uncertainty`, and `fig_rolling`. They return matplotlib Figure objects for `st.pyplot`. Prerequisites: `fig_threshold(scan, chosen)` takes a scan and the row from `select_threshold`; `fig_evt_fit` needs fitted EVT and normal models; `fig_rolling` needs forecast columns for its methods. Unavailable models are skipped or labelled "(unavailable)". `risk_table` carries `status` and, for EVT rows, `basis` (GPD tail or empirical body) for the labels this section asks for. Reconcile every figure with the associated table and run identifier.

## Handoff checklist

- [ ] Inputs and weights/version accepted by the relevant owners.
- [ ] Callable API, schema, example use and status/error definitions delivered.
- [ ] Source/calculation provenance and validated output files supplied.
- [ ] Person 4 confirms forecast timing, units and usable observations.
- [ ] Person 5 confirms confidence controls, cache invalidation and unavailable-result display.
- [ ] Risk write-up and limitations incorporated consistently in all submissions.
- [ ] Team records reviewer, accepted settings and final decision; later changes trigger affected recalculation and review.
