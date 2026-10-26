# Implementation plan and current gaps

## Existing files to extend

| File | Responsibility |
|---|---|
| `quanedge/config.py` | Shared universe, portfolio value, confidence and paths |
| `quanedge/risk/settings.py` | Development dates/weights, random seed, simulation, EVT, bootstrap and rolling settings |
| `portfolio.py` | Weight validation, portfolio return construction and loss transformations |
| `var_es.py` | Empirical, normal, Student-t and multivariate Monte Carlo models |
| `evt.py` | GPD fitting, threshold diagnostics, hybrid body/tail distribution |
| `conditional.py` | GJR-GARCH filter, FHS and GARCH-EVT |
| `models.py` | Model dispatch, identifiers and comparison tables |
| `uncertainty.py` | Circular block bootstrap and interval attachment |
| `diagnostics.py` | Distribution statistics, assumption tests, worst days, in-sample breaches |
| `rolling.py` | Prior-data forecasts and breach summaries |
| `plots.py` | Seven matplotlib figure factories |
| `dev_data.py` | Temporary yfinance adjusted-price loader/cache |
| `run.py` | Orchestration, CSV/PNG output and generated summary |
| `__init__.py` | Public risk API exports |

Paths in the table after the first two are relative to `quanedge/risk/`. Keep this package layout. No extra implementation files are required merely to match the documentation structure; add small helpers only where they simplify shared validation or metadata.

## Priority 0: establish reliable contracts

- [ ] Confirm Person 1 dataset and Person 2 weights availability; retain explicit development mode until accepted.
- [ ] Agree quantile and empirical ES conventions, exact monetary ES, one-day horizon and rebalancing interpretation.
- [ ] Add input and parameter validation, including empty/short samples, dates, non-finite values and model-specific support.
- [ ] Replace or clearly label transformed-log ES monetary fields and their bootstrap intervals. Update consumers and numerical tests together.
- [ ] Preserve usable information about invalid/non-finite fits rather than displaying them as finite dollar risk.

## Priority 1: harden mandatory calculations

- [ ] Validate historical, normal and Monte Carlo outputs with independent examples and tests.
- [ ] Handle Student-t zero MAD, optimizer failure and covariance singularity where optional methods are retained.
- [ ] Harden GPD fitting, threshold scan and selection; validate hybrid ES across the body/tail boundary.
- [ ] Add mean excess versus u and modified-scale plots; test insufficient-tail and non-finite-ES cases.
- [ ] Verify convergence and record simulation error without assuming every normal comparison is mathematically identical.

## Priority 2: validate forecasts and optional models

- [ ] Audit current 750-day rolling window and 21-day slow-model refit schedule against the chosen final settings. Historical/normal refit daily; conditional volatility updates daily between parameter refits.
- [ ] Validate method names, requested confidence, window/refit sizes and short samples. Current `rolling_forecasts` can silently allocate NaN columns for unsupported names.
- [ ] Check training cutoff and refit metadata. Test future-data perturbations across daily, refit and conditional recursion boundaries.
- [ ] Retain full precision for saved forecasts; confirm reloaded breach counts match in-memory counts.
- [ ] Avoid fitting an unrequested GARCH-EVT model when only FHS is requested; current rolling code builds both residual models.
- [ ] Check GARCH fit status and parameter domain. Suppressed optimizer warnings are not evidence of successful estimation.
- [ ] If a Monte Carlo method is selected for formal backtesting, provide its actual forecast implementation. Current rolling output excludes MC; normal forecasts are not a universal substitute.

## Priority 3: reliable evidence and runs

- [ ] Add a run manifest with input hashes, weights, actual dates, parameters, version/commit, units, model statuses, random seeds and run mode.
- [ ] Separate quick and full outputs or prevent stale files from appearing current. Today quick mode overwrites common tables/summary while leaving older rolling CSVs/figure behind.
- [ ] Make output publication consistent, preferably through a completed run directory and manifest. A failed run must not mix old and new evidence.
- [ ] Add approved data/weights configuration to the runner; it currently hard-codes the temporary loader and equal weights.
- [ ] Make sample/horizon and selected as-of dates drive narrative text. A conditional forecast after the dataset's last date is not necessarily today's forecast.
- [ ] Audit generated narrative assertions: normal risk need not always understate alternatives; ES/VaR depends on mean and confidence; bootstrap intervals do not measure every uncertainty; failure to reject a test does not prove an assumption.
- [ ] Label plots using log loss as log-loss percent. Several current plots say daily loss/return while others show simple loss fractions.
- [ ] Distinguish the worst-performing asset from the largest portfolio loss contributor; `worst_days` currently identifies lowest asset return without weighting.

## Priority 4: final integration and write-up

- [ ] Supply forecast files and schema to Person 4; incorporate their model-validation findings.
- [ ] Supply tested table/plot interfaces and warnings to Person 5.
- [ ] Write the risk-methodology and results sections, assumptions/limitations text and presentation evidence.
- [ ] Recompute with approved data and portfolio, compare with development results, reconcile app/report/tear sheet and obtain independent review.

## Execution and cleanup policy

The README documents `python -m pytest`, `python -m quanedge.risk.run --quick`, and `python -m quanedge.risk.run`. Read `run.py` before using them: both analysis modes write results, and `--refresh-data` replaces the development cache. Use a copied or versioned result destination when validating changed numerical methods.

Preserve `data/cache/prices_dev.csv` until an approved replacement is integrated; it enables offline reproduction. Preserve existing CSVs/PNGs as development evidence until a replacement run is verified. PDFs and PPTXs are reference artifacts with different uses; the masterclass PPTX includes notes absent from its PDF.

The only redundant project file removed during this documentation consolidation is `docs/person3_risk_plan.md`. Its owner, API, defaults, model inventory, work plan, limitations and bibliography have been carried into this pack, with overly broad claims marked for review. Its content remains recoverable from Git history. Update all live references to the new entry point.
