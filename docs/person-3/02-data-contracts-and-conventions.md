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

The current `risk_table` and `with_intervals` transform log ES using g. In general, g(E[L in tail]) is not E[g(L) in tail]. Treat those current dollar/percentage ES fields as approximations pending correction. Calculate exact monetary ES by transformed tail scenarios or validated quadrature/closed form. Apply the same definition within every bootstrap replicate before constructing monetary confidence intervals.

Because g is concave, transforming a finite log-tail mean gives an upper bound under the consistent tail distribution. Measure the difference rather than asserting it is negligible. An infinite log ES must remain flagged; converting infinity through g to 100% does not produce a valid exact monetary ES. For positive-wealth long-only portfolios, monetary losses are bounded above by NAV even when the chosen log-loss model has infinite mean. Keep these facts and units distinct.

## Existing public outputs and required extensions

Keep `.var(alpha)`, `.es(alpha)`, `.params` and current model identifiers stable while coordinating any new exact monetary APIs. Existing risk-table fields:

| Fields | Current meaning |
|---|---|
| `method`, `label`, `family`, `alpha` | Identity and confidence |
| `var`, `es` | Decimal log-loss statistics |
| `var_pct`, `var_usd` | Transformed VaR in percentage points and USD |
| `es_pct`, `es_usd` | Currently transformed log ES; requires corrected computation or explicit approximation label |
| `es_over_var` | Ratio in log-loss units; undefined/unstable near zero VaR |
| `var_lo`, `var_hi`, `es_lo`, `es_hi` | Bootstrap bounds in log-loss units |
| corresponding `_pct`, `_usd` bounds | Current transformed bounds; revisit ES bounds as above |

Add metadata, either in a stable result object or companion manifest: schema version, as-of date, training dates, sample size, horizon, value, weights, portfolio/data hashes, conditional/unconditional flag, configuration, seed, data mode, fit status, warnings and unit definitions. Preserve missing/unavailable values explicitly, never as zero.

Forecast outputs use realised `return` in log units and columns such as `var_evt_99` and `es_evt_99`. Include training-end date and last refit date so Person 4 can audit timing. Use full numeric precision internally and enough CSV precision to preserve breach decisions; current `%.6g` export needs round-trip testing. Compare strict loss > VaR for breach counts, with tie policy documented separately from ES tail-mass treatment.
