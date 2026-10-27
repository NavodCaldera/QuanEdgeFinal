# Person 3: Risk management

**Mission:** measure how much the portfolio can lose (Layers 2-4), prove the risk model works against reality (Layer 5), and translate risk into contributions and stress losses the committee can act on.

## Code and files owned

| Path | Purpose |
|---|---|
| `quanedge/risk/var_es.py` | Historical, normal, Student-t, Monte Carlo (normal and multivariate t) VaR/ES, MC convergence |
| `quanedge/risk/evt.py` | Peaks-over-threshold GPD fit, threshold scan and selection |
| `quanedge/risk/conditional.py` | GARCH filter, FHS (primary) and GARCH-EVT (challenger) |
| `quanedge/risk/rolling.py` | Rolling one-day forecasts with weight hash per row |
| `quanedge/risk/models.py`, `diagnostics.py`, `uncertainty.py`, `validation.py`, `portfolio.py`, `settings.py` | Risk table, assumption checks, block-bootstrap intervals, input checks, loss units |
| `quanedge/risk/plots.py`, `run.py` | Risk figures and standalone risk run |
| `quanedge/backtest.py` | Kupiec, Christoffersen, conditional coverage, traffic light, model pass checks |
| `quanedge/stress.py`: `attribution`, `stress_tests`, `hypothetical`, `reverse_stress` | Risk contributions and stress losses |
| `quanedge/robustness.py` | Threshold, block, rate, co-exceedance and stress-eve sensitivity |
| `quanedge/monitoring.py` | Post-snapshot descriptive monitoring |
| `results/<run_id>/*/risk.csv`, `forecasts.csv`, `uncertainty.csv`, `selected/robustness/`, `selected/evt_thresholds.csv` | Risk outputs |

## Tasks

### 1. Calculate VaR and Expected Shortfall
- Compute VaR and ES at 90%, 95% and 99% for every portfolio Person 2 produces.
- Report each value in three units and label them: log loss, simple percentage points, and USD on the USD 10m portfolio. **Dollar ES is the average of dollar tail losses**, not ES% times NAV.
- Explain why ES is reported in addition to VaR: VaR says nothing about the size of losses beyond it, and ES is subadditive.
- Check the ES99 against the USD 250,000 budget in `config/final.yaml`.

### 2. Implement historical, parametric, Monte Carlo and EVT models
- **Historical simulation:** empirical quantile and tail mean of portfolio losses.
- **Parametric:** normal, with Student-t as a fat-tail variant (`fit_t`).
- **Monte Carlo:** multivariate t as primary, normal as a check, `n_sim: 100000`, fixed seed. Show convergence (`mc_convergence.csv`) and the matching one-asset case against the analytical result.
- **EVT:** peaks over threshold with GPD. Choose the threshold from mean excess, parameter stability and goodness of fit (KS distance). Compare at least two threshold rules (`threshold_sensitivity.csv`). The threshold must be justified, not arbitrary.
- **Conditional models:** GARCH-filtered historical simulation (FHS, primary) and GARCH-EVT (challenger), as frozen in the config.
- **Disagreement analysis:** explain where and why the methods differ (fat tails, sample extremes, distribution assumptions, volatility clustering).
- **Uncertainty:** block-bootstrap confidence intervals (500 reps, block 20) and an EVT shape interval.
- **Stress-eve view:** models fitted on data up to 1 Sep 2008 and 19 Feb 2020 versus the losses that followed (`stress_eve.csv`).

### 3. Perform backtesting
- Rolling one-day forecasts: 750-day window, refit every 21 days, EVT threshold re-chosen inside each window, no future data.
- **One forecast file per allocation.** Every row carries the portfolio's weight hash. Backtest functions must refuse a file whose hash differs from the portfolio being evaluated.
- Label results as **sequential risk-forecast evaluation**, with the allocation's data cut-off.
- Add a future-data perturbation test: changing returns after day t must not change the day-t forecast.

### 4. Run Kupiec, Christoffersen and traffic-light tests
- Kupiec proportion-of-failures: breach count versus expected, LR statistic, p-value.
- Christoffersen independence and conditional coverage.
- Basel traffic light on the last 250 forecasts at 99% (green 0-4, yellow 5-9, red 10+) and on rolling 250-day windows. State that it is a monitoring comparison, not a regulatory requirement for an endowment.
- Binomial p-values at 90% and 95%; Holm adjustment where several models are tested.
- `model_pass` and `verdict` in `backtest.py` feed the frozen C1-C5 checks. In `final-20261027`, FHS fails coverage on the adjusted allocation and GARCH-EVT passes with a yellow zone. Be ready to explain this.

### 5. Calculate risk contributions and stress losses
- **Component ES** from joint historical scenarios (primary), multivariate-t MC as a check. Contributions must sum to portfolio dollar ES with identical tail weights, including ties and fractional boundary mass. Negative contributions stay visible.
- Marginal VaR and parametric Euler VaR as a cross-check (`marginal_var.csv`). Risk budget versus capital weight.
- FHS is portfolio-level, so it reports attribution as **unavailable**; the budget uses unconditional ES.
- **Historical stresses**, buy-and-hold: GFC 9 Oct 2007 - 9 Mar 2009; COVID 19 Feb - 23 Mar 2020; rate shock 3 Jan - 12 Oct 2022.
- **Hypothetical scenario:** stocks and bonds fall together (for example SPY -25%, AGG -10%, GLD 0%), other assets filled by conditional mean under a stressed covariance.
- **Reverse stress test:** the smallest shock that breaches the 20% drawdown limit.
- For each scenario: return, USD loss, per-asset contribution, largest contributors, policy-limit breaches.
- Macro: rolling 252-day SPY-AGG correlation (the 2022 flip) and sensitivity to DGS10 changes (`rate_sensitivity.csv`).
- Diversification in stress: co-exceedance on SPY's worst 1% days and the ES diversification benefit in USD.

## Handoffs

| From / To | What |
|---|---|
| From Person 1 | Clean log returns, VIX, DGS10 |
| From Person 2 | Canonical weights and hashes, ES budget, drawdown limit |
| To Person 2 | ES99 and worst stress per candidate for the candidate table |
| To Person 4 | `risk.csv`, `forecasts.csv`, backtest results, stress and contribution tables, figures |
| To Person 5 | Disagreement explanation, threshold justification, backtest interpretation, stress narrative |

## Tests to keep green
- `tests/test_var_es.py`: every model against known distributions.
- `tests/test_evt.py`: GPD fit and threshold selection.
- `tests/test_conditional_and_uncertainty.py`: GARCH, FHS, GARCH-EVT, bootstrap.
- `tests/test_rolling.py`, `tests/test_temporal_and_simulation.py`: no look-ahead, hash refusal, MC convergence.
- `tests/test_plots.py`: risk figures render.

## Done when
- [ ] Every model matches an independent calculation on a known distribution.
- [ ] The risk table states units, basis and status for every number.
- [ ] Each reported portfolio has its own forecast file and backtest; a mismatched hash is refused.
- [ ] Kupiec, Christoffersen and traffic light results exist for the recommended weights.
- [ ] Component ES sums to portfolio ES; all four stress scenarios plus reverse stress report USD losses and attribution.

## Questions you must answer in Q&A
- Why do historical, parametric and Monte Carlo VaR disagree here? Which do you trust and why?
- How did you choose the EVT threshold? What changes with a different rule?
- What does a Kupiec failure mean for the committee? Why was FHS primary and GARCH-EVT the challenger?
- What is the worst stress loss in USD, and which asset drives it?
- Which position uses more risk budget than capital weight?
- How confident are you in the 99% ES number (show the interval)?
