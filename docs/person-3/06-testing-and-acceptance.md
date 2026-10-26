# Testing and acceptance

## Existing baseline

Run from the repository root with the documented Python environment:

```text
python -m pytest -q
```

Existing tests cover portfolio aggregation and weights, loss conversions, normal/t formulas, simulation convergence, GPD likelihood and formulas, threshold selection on synthetic data, conditional filtering, block resampling, plot rendering and forecast timing. Since 70153ba the suite also covers exact empirical and monetary ES, input validation, visible failure states, EVT edge cases, forecast metadata and precision, and the runner's manifest and all-or-nothing publication (`tests/test_contracts.py`, `tests/test_run.py` and additions to the others). Passing tests establishes only the covered behaviours: not final data provenance, not human review, and not investment suitability.

Documentation-review baseline on 26 October 2026: `python -m pytest -q -p no:cacheprovider` completed with **31 passed in 62.81 seconds** in the existing workspace Python environment. This was an automated baseline run, not human sign-off or execution of the additional tests specified below. The analysis pipeline and saved results were not regenerated during this documentation task.

Implementation-plan baseline on 26 October 2026 (code commit 13c0619): **65 passed** with `python -m pytest -q -p no:cacheprovider`, followed by a full `python -m quanedge.risk.run` whose `manifest.json` records the code commit and settings. Automated evidence again, not human sign-off.

## Required numerical tests

| Area | Independent evidence to add or retain |
|---|---|
| Portfolio accounting | Hand-calculated multi-asset simple returns and reconstructed log returns; reordered columns and zero-weight assets |
| Validation | Empty samples, NaN/infinity, duplicate dates/columns, invalid weights/confidence/value, unsupported method and invalid horizon |
| Empirical ES | Small arrays with ties and noninteger tail counts; worst-probability-mass calculation independent of implementation |
| Monetary ES | Mean of transformed tail scenarios versus transform of mean; a deliberately dispersed tail showing the difference |
| Normal | Closed-form quantile and conditional log-tail mean; exact monetary-tail expectation checked by numerical integration |
| Student-t | Parameter recovery, independent likelihood and ES integration; zero MAD and optimization failure |
| MC | One-asset exact-model convergence, multiple seeds, batch error, sample-size sensitivity, singular covariance policy and overflow |
| GPD | Known positive, zero and negative shape; independent fit; CDF/PPF inverse and support checks |
| EVT limits | xi near 0, xi near/above 1, finite endpoint, inadequate/constant excesses, invalid fits and empty scans |
| Hybrid EVT | Normalized probability mass, boundary continuity where appropriate, atom/tie handling and ES across body plus tail |
| Thresholds | Stability over neighbours, sensitivity to candidate grid/count, transparent fallback and no test-data tuning |
| Conditional models | Filter recursion, fit status, residual diagnostics, refit-day alignment and requested-method isolation |
| Bootstrap | Whole-row blocks, circular wraparound disclosure, reproducibility, failed replicate accounting, monetary ES recomputation |
| Rolling | Day t excludes t return; future changes do not affect earlier forecasts; short/empty windows and invalid refit settings |
| Serialization | Full-precision forecast round trip preserves breaches; unavailable/infinite values remain identifiable |
| Presentation | Plot/table units, confidence/horizon labels, missing models, empty date ranges and warning displays |

Distribution properties: within one fitted loss distribution VaR should be non-decreasing with confidence; ES should be at least VaR and non-decreasing when the definitions are consistent. Do not impose a universal ordering across different models. Scaling NAV should scale monetary risk linearly without changing percentage/log risk.

Choose stochastic tolerances using simulation uncertainty and sample size. A single random sample need not recover a population parameter exactly. Do not change seeds solely to make a failed test disappear. Use synthetic data for unit tests without network downloads; integration tests should consume a known snapshot.

## Leakage and validation boundary

For each forecast store training start/end, forecast date, parameter refit date and settings. Recompute earlier forecasts after perturbing only future observations; include threshold selection and conditional updates in this check. Confirm any optimized weights used for a strategy evaluation were also obtained without future information. A fixed current-portfolio replay answers a different question and must be labelled.

Person 4 owns formal tests. Person 3 must verify alignment and provide both realised losses and model forecasts. Counts from `in_sample_breaches` are fit diagnostics, not an out-of-sample pass. The historical traffic-light benchmark has a particular confidence/sample design; arbitrary app date ranges need explicit interpretation rather than automatic application of the same cutoffs.

## Acceptance gates

1. **Contract gate:** approved schemas and units, explicit development/final inputs, agreed ES estimator and valuation.
2. **Numerical gate:** mandatory models pass independent numerical and edge-case checks; model failures are visible.
3. **EVT gate:** defended threshold, valid fit/support, diagnostics, sensitivity and uncertainty statements.
4. **Forecast gate:** no-look-ahead evidence, valid date alignment, precision-preserving handoff and Person 4 review.
5. **Integration gate:** Person 5 can render required risk outputs at 90/95/99% without recalculating formulas or silently using stale results.
6. **Release gate:** approved portfolio/data, one reproducible run, reconciled submissions, human review and accurate AI disclosure.

Record command, environment, date, outcome, failures and reviewer for each material check. Do not mark gates complete because functions exist or an old plan contains checked boxes. Avoid rerunning the full computational pipeline merely for a documentation edit; numerical changes require proportionate model and integration testing.
