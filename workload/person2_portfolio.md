# Person 2: Portfolio construction

**Mission:** turn the investment policy into feasible portfolios, measure them with the Layer 1 KPIs, and show the committee the trade-off between return and risk. Owns the candidate table and the recommended weights.

## Code and files owned

| Path | Purpose |
|---|---|
| `quanedge/portfolio.py` | Estimates, constraints, construction, replay, KPIs, money-weighted return |
| `quanedge/pipeline.py`: `make_candidates`, `adjustments`, `constraint_effects`, `walk_forward` | Candidate set, A1-A5 adjustment set, constraint effects, walk-forward check (shared with Person 4) |
| `quanedge/stress.py`: `survival` | Real-capital survival (spending sustainability) simulation |
| `config/final.yaml` (policy block) | Constraints, hurdle inputs, estimators |
| `results/training/` | Training-only candidates, constraint effects, freeze values |
| `results/<run_id>/*/weights.json`, `performance.csv`, `spending.csv` | Per-portfolio outputs |
| `results/<run_id>/candidate_table.csv`, `estimator_sensitivity.csv`, `rebalancing_comparison.csv`, `walk_forward.csv`, `survival.json` | Comparison outputs |

## Tasks

### 1. Select portfolio weights
- Define the return objective: the geometric-return hurdle that covers 4% spending plus 2.5% inflation plus costs (`hurdle` in `portfolio.py`; currently 6.77%).
- Write the selection rule: objective, estimators, constraints, solver and tie-break. It is frozen at the `prereg-v1` tag before any post-2016 result is computed.
- Produce **W_train** (fitted on 2005-2016 only) and **W_rec** (the recommendation, fitted on all data to the snapshot end).
- Store each portfolio as a canonical weight file: 6-decimal weights summing exactly to 1, rounding residual on the largest weight, SHA-256 weight hash, effective date (`canonical_weights`, `weight_hash`). Person 3 and Person 4 depend on this hash.

### 2. Build Markowitz/CAPM portfolios
- Expected returns: historical means with shrinkage (`mean_shrinkage: 0.50`) or a CAPM equilibrium view. State which one is used and why.
- Covariance: sample and Ledoit-Wolf shrinkage (`covariance: LedoitWolf`); report the correlation matrix.
- Efficient frontier under the policy constraints.
- CAPM: beta to SPY, Treynor ratio, Jensen's alpha.
- Candidates (A1 list): minimum CVaR (also the governance de-risk portfolio), minimum variance, near-parity (constrained equal risk contribution, with its risk-contribution dispersion), constrained maximum Sharpe, plus unconstrained parity.
- Benchmarks: 60/40, 40/60, equal weight, permanent portfolio.

### 3. Apply investment constraints
From `config/final.yaml`:
- Long only, fully invested.
- Gold cap 15%, equity cap 55%, AGG between 25% and 70%, single-asset cap 40%, sector ETFs (XLE, XLK) capped at 10%.
- One-day ES99 budget of 2.5% of NAV (USD 250,000) and a 20% stress/drawdown limit (checked with Person 3).
- Transaction cost 5 bp one way, quarterly/drift rebalancing at a 5% drift band.
- `bounds` and `feasible` must reject any allocation outside these limits. The app warns when an Explore allocation breaks them.
- Constraint effects: re-solve with each constraint relaxed one at a time and report what it costs or adds (`constraint_effects.json`).

### 4. Calculate returns, volatility, Sharpe, Sortino and drawdown
- `kpis` must report: annual return (arithmetic and geometric), volatility, Sharpe, Sortino, Treynor, Jensen's alpha, Information ratio, maximum drawdown, Calmar, distribution yield, diversification ratio.
- Time under water: peak to trough, trough to recovery, or "not recovered by [date]".
- Money-weighted return under the spending rule and time-weighted CAGR, both against the realised-inflation hurdle (`money_weighted`).
- Rebalanced versus buy-and-hold after costs over 2017 to snapshot end (`rebalancing_comparison.csv`), labelled as a policy cost/benefit, not alpha.
- Every replay of weights over history is labelled **retrospective portfolio evaluation**.
- Check at least one KPI per portfolio by hand (spreadsheet) and keep the working for Person 5.

### 5. Compare candidate portfolios
- `candidate_table.csv`: expected arithmetic and geometric return versus hurdle, volatility, ES99 USD, maximum drawdown, worst stress USD, distribution yield, diversification ratio, and "each +1% of expected return costs USD X of ES99".
- Estimator sensitivity: how weights change under a different mean/covariance estimator (`estimator_sensitivity.csv`).
- Walk-forward procedure check: re-run the frozen rule each January from 2017 on data to the prior 31 December, hold for the year (`walk_forward.csv`). This is the only historically investable record.
- Real-capital survival: 10,000 block-bootstrap paths, spending applied each year, probability of ending below the real-capital target at 5 and 10 years, with Monte Carlo standard errors (`survival.json`). Labelled illustrative.

## Handoffs

| From / To | What |
|---|---|
| From Person 1 | Clean returns, risk-free rate, dividends |
| To Person 3 | Canonical weight files and hashes for every portfolio; ES budget and drawdown limit |
| To Person 4 | `weights.json`, `performance.csv`, `candidate_table.csv` in the run folder; the list of dropdown portfolios |
| To Person 5 | Candidate table, KPI definitions, hand-check working, the selection rule in plain English |

## Tests to keep green
- `tests/test_portfolio_and_decision.py`: feasibility, canonical weights, KPI values on known inputs, adjustment logic.
- `tests/test_contracts.py`: weight-file format and hash contract (shared with Person 4).

## Done when
- [ ] Every candidate and benchmark is feasible (or flagged as outside policy) and has a weight hash.
- [ ] KPIs match hand calculations for at least one portfolio.
- [ ] The candidate table quantifies the return/risk trade-off.
- [ ] The selection rule and policy values match the `prereg-v1` tag.
- [ ] Walk-forward and survival results exist and carry their labels.

## Questions you must answer in Q&A
- Why these constraints for a conservative endowment? Where do 15% gold and 55% equity come from?
- Why shrink expected returns? What happens to weights without shrinkage?
- Why minimum CVaR rather than maximum Sharpe for the adjusted allocation?
- Does the recommended portfolio meet the 6.77% hurdle? If not, what does the committee give up?
- How much does each constraint cost in expected return or ES?
- What does the survival simulation say about spending 4% a year, and how reliable is it?
