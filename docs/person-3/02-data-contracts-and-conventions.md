# Data contracts and conventions

## Input contract

`fit_models(asset_log_returns, weights, ...)` consumes a pandas DataFrame of daily asset log returns and a ticker-to-weight mapping. Require numeric finite values, unique asset columns, and an explicit matching asset order. For dated history, require a unique increasing DatetimeIndex, an agreed timezone/date convention, and documented trading-day gaps. Bootstrap samples deliberately repeat observations and must use a separate internal path rather than falsely claiming to be chronological market data.

Validate eligible tickers at the production boundary. Synthetic tests may use A/B/C without being treated as real investments. Allow omitted weights to mean zero only when the convention is explicit. Reject unknown keys, NaN/infinite weights and invalid sums. Adopt the team's portfolio constraints; long-only and fully invested are sensible proposed baseline constraints, not rules to invent on behalf of Person 2. Validate any supported short/leverage case separately, including positive portfolio wealth.

From Person 1 obtain source identifiers, download timestamp, price adjustment convention, calendar/cleaning rules, missing-value and anomaly logs, dataset checksum/version and stationarity evidence. Never add dividends again to an already adjusted return series. Audit dropped dates in `dev_data.py`; its current `dropna()` is not a complete cleaning log. A hard-coded 5,000-row download check is a development assumption and must not reject legitimate shorter approved samples without explanation.

From Person 2 obtain weights, effective date, policy constraints, portfolio value, rebalancing schedule and whether historical weights are fixed or time-varying. Distinguish a replay of today's portfolio from a historically investable strategy whose weights were selected without future data.

## Return and loss definitions

For asset log returns r_i and beginning-of-period weights w_i:

```text
R_i = exp(r_i) - 1
R_p = sum_i(w_i * R_i)
r_p = log(1 + R_p)
L   = -r_p                         # positive means a loss
g(L) = 1 - exp(-L)                 # fraction of NAV lost
monetary loss = V * g(L)
```

Current `portfolio_log_returns` uses this aggregation and assumes the same weights each day, effectively daily rebalancing without costs. Do not describe it as buy-and-hold. Log loss 0.01 and simple loss 1% are different quantities. Percentage output is 100 times a fractional loss; confidence input 0.99 is not 99.

Baseline horizon is one trading day, portfolio value is USD 10,000,000, and confidence levels are 0.90, 0.95 and 0.99. Do not apply square-root-of-time scaling to non-normal or conditional risk without a justified horizon model. Investment horizon is a different concept from the one-day risk horizon.

## Critical ES valuation distinction

For a continuous model and monotone g, monetary VaR is V*g(VaR of L). Monetary ES instead requires averaging transformed losses over the worst tail:

```text
ES_USD(alpha) = V/(1-alpha) * integral_alpha^1 g(Q_L(p)) dp
```

In general, g(E[L in tail]) is not E[g(L) in tail]. Since commit 70153ba every model provides `es_fraction(alpha)`, the exact monetary ES as a fraction of NAV: transformed tail scenarios for samples (historical, Monte Carlo, FHS), the closed form for the normal, and quadrature over the quantile otherwise (Student-t, EVT tail). `risk_table` and `with_intervals` use it, and every bootstrap replicate recomputes it before the monetary intervals are formed.

Because g is concave, transforming a finite log-tail mean gives an upper bound under the consistent tail distribution. Measure the difference rather than asserting it is negligible: the run summary reports the largest overstatement the shortcut would cause. An infinite log ES must remain flagged; converting infinity through g to 100% does not produce a valid exact monetary ES. For positive-wealth long-only portfolios, monetary losses are bounded above by NAV even when the chosen log-loss model has infinite mean. Keep these facts and units distinct.

## Existing public outputs and required extensions

Keep `.var(alpha)`, `.es(alpha)`, `.es_fraction(alpha)`, `.params`, `.status` and the model identifiers stable; coordinate any change with Persons 4 and 5. Risk-table fields:

| Fields | Meaning |
|---|---|
| `method`, `label`, `family`, `alpha` | Identity and confidence |
| `var`, `es` | Decimal log-loss statistics (`es` is infinite when an EVT tail has xi >= 1) |
| `var_pct`, `var_usd` | VaR converted to percentage points and USD (exact: g is monotone) |
| `es_pct`, `es_usd` | Exact monetary ES from `es_fraction` |
| `es_over_var` | Ratio in log-loss units; blank when VaR is not positive |
| `basis` | For EVT rows: whether the GPD tail or the empirical body below the threshold answers |
| `status` | `ok`, `warning: ...` or `failed: ...`; failed models carry NaN, never zero |
| `var_lo`, `var_hi`, `es_lo`, `es_hi` | Bootstrap bounds in log-loss units |
| `es_frac_lo`, `es_frac_hi`, `reps_ok`, `reps_failed` | Bootstrap bounds of monetary ES as a fraction of NAV; successful and failed resamples |
| corresponding `_pct`, `_usd` bounds | VaR bounds converted from log loss; ES bounds from the per-resample monetary ES |

Each run folder's `manifest.json` carries the metadata: schema version, as-of dates, sample size, horizon, value, weights, input and weight hashes, configuration, seeds, data mode, model statuses, threshold rule, bootstrap failures and unit definitions. Missing or unavailable values stay explicit, never zero.

Forecast outputs use realised `return` in log units and columns such as `var_evt_99` and `es_evt_99`, plus `train_start`, `train_end` and `refit_train_end` so Person 4 can audit timing. Save and reload them with `rolling.save_forecasts` / `rolling.load_forecasts` (17 significant digits, round-trip parsing): pandas' default CSV round trip can move a value by one unit in the last place. Breach counts use strict loss > VaR, and days without a forecast are excluded from the denominator.
