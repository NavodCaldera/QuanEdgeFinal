# Person 3 — VaR, Expected Shortfall and EVT

Workstream plan, interface contract and defence notes for the risk-measurement layer
(brief §8.2–8.4). Owner: Navod Caldera. Code: [`quanedge/risk/`](../quanedge/risk/).

## 1. What the brief asks of this workstream

| Brief | Requirement | Where it is answered |
|---|---|---|
| §8.2 Layer 2 | Historical, parametric and Monte Carlo VaR on the same portfolio at 95% and 99%; explain where they disagree and why; assess each model's assumptions | `var_es.py`, `diagnostics.py` |
| §8.3 Layer 3 | Report Expected Shortfall and justify it alongside VaR | every model reports `.es(alpha)` |
| §8.4 Layer 4 | EVT for extreme losses; limitations of conventional measures; behaviour under stress; threshold **justified, not arbitrary** | `evt.py`, `conditional.py` |
| §6 | Dashboard shows VaR, ES and the EVT estimate side by side at the sidebar's level (90/95/99%) and chosen method | `risk_table()`, `plots.py` |
| §5 | "How confident are you in your risk estimates" | `uncertainty.py` (bootstrap intervals) |
| §10 | Technical rigour 25%; innovation 15% (e.g. regime-conditioned risk, alternative EVT threshold rules) | conditional models, threshold-rule scan |

## 2. Conventions (agreed once, used everywhere)

| Item | Choice | Reason |
|---|---|---|
| Horizon | 1 trading day | Matches daily data and the daily breach counts in Kupiec/Christoffersen |
| Confidence | 90, 95, 99% (95 and 99 are the headline) | Brief §6 and §8.2 |
| Returns | Log returns for all statistics; **simple returns only to aggregate across assets** | Log returns add over time but not across assets: $R_p=\sum_i w_i(e^{r_i}-1)$, then $r_p=\ln(1+R_p)$ |
| Weights | Current weights held fixed (daily rebalanced) and replayed over history | Risk of the portfolio as it is held today |
| Sign | Loss $L=-r_p$; VaR and ES are positive losses | One convention for every model |
| Money | USD loss $=10{,}000{,}000\times(1-e^{-L})$ | Exact for VaR (monotone map); for ES a very slightly conservative bound (Jensen), negligible at one day |
| Headline sample | 2005-01-03 to 2026-09-30, all seven ETFs (GLD listed Nov 2004) | Contains GFC, COVID and 2022; ~5,400 days gives EVT enough exceedances |
| Rolling window | 750 days (~3 years) | Forecasts start in early 2008, so the GFC crash is genuinely out-of-sample |
| Reproducibility | Fixed end date, cached prices, seed 20261026 | Judges must get identical numbers |

## 3. Interface contract

**Inputs**

- *Person 1:* daily **log returns**, a `DataFrame` indexed by date with the seven tickers as columns and no NaNs.
  Until then: `quanedge.risk.dev_data.load_log_returns()` (temporary, same cleaning discipline, cached CSV).
- *Person 2:* weights as `{ticker: weight}` summing to 1.
  Until then: equal weights. **These are a placeholder, not a recommendation, so every number changes once Person 2 delivers.**

**Outputs**

```python
from quanedge.risk import portfolio_log_returns, fit_models, risk_table, rolling_forecasts

r_p    = portfolio_log_returns(asset_log_returns, weights)
models = fit_models(asset_log_returns, weights)      # {name: model}, each has .var(alpha), .es(alpha)
table  = risk_table(models, alphas=(0.90, 0.95, 0.99))  # VaR/ES as log-loss, % of value and USD
fc     = rolling_forecasts(r_p)                      # one-day-ahead VaR/ES + realised return, no look-ahead
```

- *Person 4* takes `rolling_forecasts` into Kupiec, Christoffersen and the traffic light. For marginal/component
  VaR and ES they can refit `fit_models` with bumped weights, or reuse the Monte Carlo scenarios.
- *Person 5* puts `risk_table` in the dashboard; the functions in `quanedge.risk.plots` return matplotlib figures (`st.pyplot`).

## 4. Methods

| Family | Model (`name`) | Key assumption | What it adds |
|---|---|---|---|
| Historical | `historical` | The past sample repeats; days are interchangeable | No distributional assumption; cannot exceed the worst day seen |
| Parametric | `normal` | Gaussian returns | Textbook variance–covariance VaR; benchmark that understates fat tails |
| Parametric | `student_t` | Location-scale Student-t (MLE) | Fat tails with one extra parameter, the tail index ν |
| Monte Carlo | `mc_normal` | Multivariate normal on the seven assets | Scenario-by-scenario aggregation through the weights; validates `normal` |
| Monte Carlo | `mc_t` | Multivariate t, same covariance, ν by profile likelihood | Joint fat tails: assets crash together more often than under the normal |
| EVT | `evt` | Losses above a threshold *u* are GPD (Pickands–Balkema–de Haan) | Extrapolates beyond the sample; tail index ξ quantifies tail heaviness |
| Conditional | `fhs` | GJR-GARCH(1,1) filter; i.i.d. residuals | Today's volatility regime (Barone-Adesi et al. 1999) |
| Conditional | `garch_evt` | GARCH filter + EVT on residual tail | McNeil & Frey (2000): conditional *and* fat-tailed |

**Why ES as well as VaR:** VaR says where the tail starts, not how deep it goes. ES is the average loss on the days
VaR is breached. It is coherent: it is sub-additive, so diversification never appears to add risk, which VaR can violate.
Basel's FRTB replaced 99% VaR with 97.5% ES for this reason. For a client that says "avoiding large losses is more
important than maximising gains", the size of the bad day matters, not just how often it happens.

## 5. EVT threshold: the procedure

1. Candidate thresholds are the 80.0th, 80.5th, … 98.5th percentiles of daily losses.
2. For each candidate, fit the GPD by maximum likelihood (hand-rolled, cross-checked against `scipy` in the tests) and record:
   the mean excess (should be linear in *u* once the GPD holds), ξ̂ with its standard error, the modified scale
   σ* = σ − ξu (should be flat), and the Kolmogorov–Smirnov distance between the excesses and the fitted GPD.
3. **Stability flag:** ξ̂(u) must lie inside the 95% interval of ξ̂ at every higher threshold.
4. **Rule:** among stable candidates with at least 50 exceedances, take the lowest KS distance (the rule of
   Clauset, Shalizi & Newman 2009). This makes the bias–variance trade-off explicit and reproducible.
5. Report how sensitive 99% VaR/ES are across all stable thresholds, plus the 90th/95th-percentile rules of thumb.

Below *u* the model uses the empirical losses, above *u* the GPD. That way EVT VaR/ES exist at every sidebar level, and
whenever VaR lies above *u* they equal the classic POT formulas.

## 6. Confidence in the estimates

- **Block bootstrap:** 500 resamples of 20-day blocks of the asset-return matrix. Blocks keep volatility clusters and
  cross-asset dependence. Each resample refits every unconditional model (Monte Carlo with 20,000 scenarios per
  resample, EVT threshold held at the selected percentile), giving 95% percentile intervals for every VaR and ES.
- **GPD standard errors:** asymptotic, from Smith (1987).
- **Threshold sensitivity band:** see §5.

## 7. Assumption tests

| Assumption | Used by | Test |
|---|---|---|
| Normal returns | `normal`, `mc_normal` | Jarque–Bera; skewness, excess kurtosis |
| No autocorrelation | all unconditional models | Ljung–Box Q(10) on returns |
| Constant volatility | all unconditional models | Ljung–Box Q(10) on squared returns; ARCH-LM |
| Stationarity | all | Augmented Dickey–Fuller |
| GARCH removed the clustering | `fhs`, `garch_evt` | Ljung–Box Q(10) on squared residuals |

## 8. Build plan

- [x] **Phase 0 — Foundation:** package layout, shared config, temporary data loader with cached prices, portfolio aggregation, this plan
- [x] **Phase 1 — VaR and ES:** historical, normal, Student-t, MC-normal, MC-t at 90/95/99%; unit tests against closed forms
- [x] **Phase 2 — EVT:** GPD MLE, threshold scan and selection rule, hybrid EVT VaR/ES; tests on data with known tails
- [x] **Phase 3 — Evidence:** assumption tests, worst-day table, block-bootstrap intervals
- [x] **Phase 4 — Regime-conditioned risk:** GJR-GARCH filter, FHS, GARCH-EVT
- [ ] **Phase 5 — Hand-offs:** rolling one-day-ahead forecasts (Person 4), figures (Person 5), one-command run writing tables, figures and `summary.md`
- [ ] **Phase 6 — Write-up:** disagreement narrative, ES rationale, threshold justification, limitations for the report and the app page
- [ ] Swap in Person 1's data and Person 2's weights; re-run; freeze the numbers with the team

## 9. Questions to be ready for

1. Why does normal VaR understate the 99% loss? Use the measured excess kurtosis and the gap to EVT.
2. Why can Student-t VaR be *below* normal VaR at 90–95%? The t puts more mass in the centre; the fat tail only bites far out.
3. Why is `mc_normal` almost identical to `normal`, and what does Monte Carlo add? It shares the assumption, so it agrees up to
   simulation error. Its value is per-scenario aggregation through the weights and swapping the distribution (`mc_t`).
4. Why ES? Coherence, tail depth, Basel FRTB, and the client's stated loss aversion.
5. How was the threshold chosen, and what changes at the 90th versus the 95th percentile? See §5 and the sensitivity table.
6. What does ξ mean? ξ > 0 is a power-law tail; ξ < 0.5 means finite variance; ξ < 1 means ES exists.
7. Why do unconditional VaR breaches cluster? Volatility clustering (Ljung–Box on r²) is what the conditional models fix.
8. How sure are you? Bootstrap intervals, and the CI width at 99% compared with 95%.
9. Why one day, and how would you scale to ten? √10 assumes i.i.d. normal; with ξ > 0 and clustering it is an approximation.
10. Where are simple returns used? Only to aggregate across assets (§2).

## 10. Limitations (for the Assumptions & Limitations page)

- One-day horizon: losses that compound over weeks in a crisis are covered by Person 4's stress tests, not by VaR.
- Every model learns from 2005–2026; a crisis unlike any in that sample can be worse than every estimate.
- Unconditional models ignore today's volatility; the conditional models depend on the GARCH specification.
- EVT extrapolates beyond the data, and the further out it goes, the wider the confidence interval.
- Fixed weights; no transaction costs, liquidity or price-impact effects; trading at the closing price is assumed.
- Correlations jump in crises; `mc_normal` understates joint crashes, and `mc_t` only partly captures them.
- Bootstrap intervals measure estimation noise, not model risk (choosing the wrong model altogether).

## 11. AI-use log (feeds the team disclosure)

| Tool | Purpose | Human validation |
|---|---|---|
| Claude Code | Code scaffolding for `quanedge/risk/`, test design, this plan | Every formula has a unit test against a closed form or simulation; Person 3 re-derives each formula and reviews every number before it reaches the report |

## References

- Balkema, A. & de Haan, L. (1974). Residual life time at great age. *Annals of Probability*.
- Barone-Adesi, G., Giannopoulos, K. & Vosper, L. (1999). VaR without correlations for portfolios of derivative securities. *Journal of Futures Markets*.
- Clauset, A., Shalizi, C. R. & Newman, M. E. J. (2009). Power-law distributions in empirical data. *SIAM Review*.
- Coles, S. (2001). *An Introduction to Statistical Modeling of Extreme Values*. Springer.
- Glosten, L., Jagannathan, R. & Runkle, D. (1993). On the relation between the expected value and the volatility of the nominal excess return on stocks. *Journal of Finance*.
- Hosking, J. R. M. & Wallis, J. R. (1987). Parameter and quantile estimation for the generalized Pareto distribution. *Technometrics*.
- McNeil, A. J. & Frey, R. (2000). Estimation of tail-related risk measures for heteroscedastic financial time series: an extreme value approach. *Journal of Empirical Finance*.
- McNeil, A. J., Frey, R. & Embrechts, P. (2015). *Quantitative Risk Management*, 2nd ed. Princeton University Press.
- Pickands, J. (1975). Statistical inference using extreme order statistics. *Annals of Statistics*.
- Smith, R. L. (1987). Estimating tails of probability distributions. *Annals of Statistics*.
