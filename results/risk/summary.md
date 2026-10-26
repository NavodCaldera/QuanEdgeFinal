# Risk measurement summary (Person 3)

Run `20261026T072825Z` (full mode). Every number is read from this run's `tables/`; `manifest.json` records the inputs, settings and code version.

> **Development inputs.** Data: temporary development cache from yfinance, standing in for Person 1's dataset. Weights: placeholder equal weights, not a recommendation. Every number here will change when Person 1's approved data and Person 2's weights are used.

## Data

- 5,469 trading days, 04 Jan 2005 to 30 Sep 2026; the as-of date of every estimate is 30 Sep 2026. Data: temporary development cache from yfinance, standing in for Person 1's dataset.
- Weights (placeholder equal weights, not a recommendation): SPY 14.3%, EFA 14.3%, EEM 14.3%, AGG 14.3%, GLD 14.3%, XLE 14.3%, XLK 14.3%.
- Daily volatility 1.00% (15.9% annualised); skewness -0.20; excess kurtosis 15.0 (normal: 0).
- Worst day 12 Mar 2020: 8.68% of portfolio value ($868,470).

## One-day VaR and ES on USD 10m

ES is the exact average dollar loss over the worst days, not the dollar value of log ES. Brackets: 95% moving-block bootstrap interval (500 resamples), covering estimation and simulation noise but not EVT threshold re-selection or model risk. No bracket means not estimated (conditional models), not zero uncertainty. The 90% level is in `risk_table.csv`.

| Model | 95% VaR | 95% ES | 99% VaR | 99% ES |
|---|---|---|---|---|
| Historical simulation | $143k [$132k–$156k] | $236k [$202k–$279k] | $287k [$239k–$349k] | $425k [$323k–$533k] |
| Parametric (normal) | $160k [$139k–$185k] | $201k [$174k–$233k] | $226k [$197k–$262k] | $260k [$226k–$300k] |
| Parametric (Student-t) | $132k [$121k–$144k] | $223k [$193k–$261k] | $264k [$228k–$307k] | $410k [$331k–$515k] |
| Monte Carlo (normal) | $159k [$138k–$187k] | $200k [$174k–$233k] | $225k [$197k–$261k] | $258k [$225k–$298k] |
| Monte Carlo (Student-t) | $147k [$130k–$166k] | $218k [$188k–$254k] | $257k [$220k–$298k] | $346k [$292k–$421k] |
| EVT (POT-GPD) | $145k [$133k–$159k] | $238k [$204k–$282k] | $286k [$245k–$338k] | $414k [$320k–$530k] |
| Filtered HS (GARCH) | $128k | $177k | $200k | $265k |
| GARCH-EVT | $125k | $177k | $208k | $264k |

## Model status

- All 8 models fitted without warnings.

## Where the models disagree (99%, one day)

- Unconditional 99% VaR runs from $225k for Monte Carlo (normal) to $287k for Historical simulation, a ratio of 1.27.
- Normal 99% VaR is 21% below historical simulation; normal 99% ES is 39% below.
- ES/VaR at 99% (log units): normal 1.15, historical 1.49, EVT 1.46. For a normal model the ratio depends only on the confidence level and the mean-to-volatility ratio (1.146 at 99% with zero mean); a larger ratio means a deeper tail beyond VaR.
- Student-t VaR (ν = 2.9) is below normal VaR at 90%, 95% and above it at 99%: the fitted t has more mass near zero and in the far tail, and less in between.
- Monte Carlo (normal) is within $1k of parametric normal VaR at every level; across 3 seeds at 200,000 scenarios its 99% VaR moves by $1k. Exact agreement is not expected: Monte Carlo simulates the seven assets and aggregates simple returns, while parametric normal fits the portfolio return directly.
- Monte Carlo (Student-t) adds joint fat tails (ν = 4.1): 99% ES $346k against $258k under the multivariate normal.
- The GARCH volatility forecast for 01 Oct 2026, the weekday after the data end, is 0.76% against a sample average of 1.00%, so conditional 99% VaR for that day is $208k (GARCH-EVT) and $200k (FHS), against $287k for whole-sample historical simulation.
- Converting log ES into dollars, instead of averaging dollar losses, would overstate ES by up to $3,132 (Parametric (Student-t) at 99%).

## EVT

- Threshold rule: lowest KS distance among stable thresholds; every candidate needs at least 50 exceedances, and stability needs at least 3 higher thresholds to compare with. Chosen: the 85th percentile of daily losses, u = 0.72% log loss, 821 exceedances.
- Tail index ξ = 0.212 (s.e. 0.042). ξ > 0: a power-law tail. ξ < 0.5: finite variance. ξ < 1: log ES exists.
- ξ is stable from the 84th to the 97th percentile. Across those thresholds 99% VaR stays within 2.80%–2.88% and 99% ES within 4.11%–4.33% of portfolio value: a sensitivity band, not a confidence interval.
- Rules of thumb for comparison: the 90th percentile gives 99% VaR 2.86%; the 95th percentile gives 99% VaR 2.81%.
- At 99.9% (about one day in four years, an extrapolation with wider uncertainty): EVT VaR 5.86%, historical 6.57%, normal 3.01%.
- After the GARCH filter, the residual tail index (fixed 90th-percentile threshold, as in McNeil & Frey) is ξ = 0.053 (s.e. 0.045), against 0.212 for raw losses; that fixed threshold has not been scanned like the raw one.

## Assumption checks

A rejected null is evidence against it; a null that is not rejected is not proof of the assumption.

| assumption | test | null_hypothesis | statistic | p_value | conclusion |
|---|---|---|---|---|---|
| Returns are normal | Jarque-Bera | returns are normal | 51,241.12 | <0.0001 | null rejected at 5%: evidence against the assumption |
| No autocorrelation in returns | Ljung-Box Q(10) on r | no autocorrelation up to lag 10 | 88.88 | <0.0001 | null rejected at 5%: evidence against the assumption |
| Constant volatility (no clustering) | Ljung-Box Q(10) on r^2 | no autocorrelation in squared returns up to lag 10 | 4,810.91 | <0.0001 | null rejected at 5%: evidence against the assumption |
| Constant volatility (no clustering) | ARCH-LM(10) | no ARCH effects | 1,538.60 | <0.0001 | null rejected at 5%: evidence against the assumption |
| Returns are stationary | ADF | unit root (non-stationary) | -16.62 | <0.0001 | null rejected at 5%: supports the assumption |
| GARCH filter removed the clustering | Ljung-Box Q(10) on z^2 | no autocorrelation in squared residuals up to lag 10 | 12.04 | 0.2827 | null not rejected at 5%: no evidence against it (not proof) |
| GARCH residuals are normal | Jarque-Bera on z | residuals are normal | 1,332.96 | <0.0001 | null rejected at 5%: evidence against the assumption |

## In-sample breach rate of the full-sample 99% VaR (a fit check, not a backtest)

| model | breaches | breach rate | expected |
|---|---|---|---|
| Historical simulation | 55 | 1.01% | 1.00% |
| Parametric (normal) | 97 | 1.77% | 1.00% |
| Parametric (Student-t) | 67 | 1.23% | 1.00% |
| Monte Carlo (normal) | 97 | 1.77% | 1.00% |
| Monte Carlo (Student-t) | 69 | 1.26% | 1.00% |
| EVT (POT-GPD) | 55 | 1.01% | 1.00% |

## Rolling out-of-sample breaches (raw counts; formal tests are Person 4's)

4,719 forecast days, 27 Dec 2007 to 30 Sep 2026; window 750 days, slow models refitted every 21 days. Days without a forecast are excluded, not counted as passes. Failed refits: 0 (listed in manifest.json).

| model | 90% breaches (expected) | 95% breaches (expected) | 99% breaches (expected) | days without forecast |
|---|---|---|---|---|
| EVT (POT-GPD) | 475 (471.9) | 235 (236.0) | 62 (47.2) | 0 |
| Filtered HS (GARCH) | 477 (471.9) | 251 (236.0) | 65 (47.2) | 0 |
| GARCH-EVT | 477 (471.9) | 249 (236.0) | 52 (47.2) | 0 |
| Historical simulation | 477 (471.9) | 233 (236.0) | 70 (47.2) | 0 |
| Parametric (normal) | 359 (471.9) | 221 (236.0) | 95 (47.2) | 0 |
| Parametric (Student-t) | 536 (471.9) | 282 (236.0) | 68 (47.2) | 0 |

## Files

`tables/`: risk_table, evt_threshold_scan, assumption_checks, worst_days, in_sample_breaches, model_parameters, mc_simulation_error, mc_convergence, rolling_forecasts, rolling_breaches. `figures/`: one PNG per figure. `manifest.json`: inputs, hashes, settings, seeds, statuses.
