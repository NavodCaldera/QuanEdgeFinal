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
| `validation.py` | Shared input checks and `ModelFitError` |
| `run.py` | Orchestration, input adapters, CSV/PNG output, manifest and generated summary |
| `__init__.py` | Public risk API exports |

Paths in the table after the first two are relative to `quanedge/risk/`. Keep this package layout. No extra implementation files are required merely to match the documentation structure; add small helpers only where they simplify shared validation or metadata.

Status notes cite the commit that did the work. A ticked box records automated tests passing, not human review: the person-3 acceptance gates in [06](06-testing-and-acceptance.md) still need a named reviewer.

## Priority 0: establish reliable contracts

- [ ] Confirm Person 1 dataset and Person 2 weights availability; retain explicit development mode until accepted. *Open (needs Persons 1 and 2). Development mode is now explicit in every output: the summary banner, `manifest.json` `inputs.development`, and `--returns`/`--weights` adapters for the approved inputs (70153ba).*
- [ ] Agree quantile and empirical ES conventions, exact monetary ES, one-day horizon and rebalancing interpretation. *Open (team agreement). Implemented proposal: VaR uses numpy linear interpolation (type 7); ES is the exact worst-mass average with a fractional boundary observation; dollar ES averages dollar losses; one-day horizon; daily-rebalanced replay of current weights (70153ba).*
- [x] Add input and parameter validation, including empty/short samples, dates, non-finite values and model-specific support. *`validation.py`; dated-history checks at the run boundary, not in `fit_models`, because the bootstrap refits on undated rows (70153ba).*
- [x] Replace or clearly label transformed-log ES monetary fields and their bootstrap intervals. Update consumers and numerical tests together. *`es_fraction` on every model; `es_pct`/`es_usd` and ES bounds are exact; the summary reports the measured overstatement of the shortcut (70153ba).*
- [x] Preserve usable information about invalid/non-finite fits rather than displaying them as finite dollar risk. *`Unavailable` entries with NaN and a reason; `status` column; infinite log ES flagged (70153ba).*

## Priority 1: harden mandatory calculations

- [x] Validate historical, normal and Monte Carlo outputs with independent examples and tests. *`tests/test_contracts.py` (70153ba).*
- [x] Handle Student-t zero MAD, optimizer failure and covariance singularity where optional methods are retained. *Zero-MAD fallback, collapse and convergence checks; singular covariance raises without jitter; overflow raises without clipping (70153ba).*
- [x] Harden GPD fitting, threshold scan and selection; validate hybrid ES across the body/tail boundary. *Fit status checks; failed candidates kept and never selected; stability needs 3 higher thresholds; flagged fallback; brute-force mixture test (70153ba). EVT rows now say whether the GPD tail or the empirical body answers (13c0619).*
- [x] Add mean excess versus u and modified-scale plots; test insufficient-tail and non-finite-ES cases. *`fig_threshold` is a 2x2 panel against u (70153ba).*
- [x] Verify convergence and record simulation error without assuming every normal comparison is mathematically identical. *`mc_convergence` table (5 sizes x 3 seeds) and batch errors with a minimum tail count; the summary explains why MC and parametric normal differ (70153ba).*

## Priority 2: validate forecasts and optional models

- [ ] Audit current 750-day rolling window and 21-day slow-model refit schedule against the chosen final settings. Historical/normal refit daily; conditional volatility updates daily between parameter refits. *Open (needs the team's final settings); defaults unchanged.*
- [x] Validate method names, requested confidence, window/refit sizes and short samples. *Unsupported names, bad levels, windows under 250 days, non-positive refits, short or unordered series all raise (70153ba).*
- [x] Check training cutoff and refit metadata. Test future-data perturbations across daily, refit and conditional recursion boundaries. *`train_start`, `train_end`, `refit_train_end` columns; perturbation test on a refit day and between refits (70153ba).*
- [x] Retain full precision for saved forecasts; confirm reloaded breach counts match in-memory counts. *`save_forecasts`/`load_forecasts` (17 significant digits, round-trip parsing); bit-identical reload test (70153ba).*
- [x] Avoid fitting an unrequested GARCH-EVT model when only FHS is requested. *(70153ba)*
- [x] Check GARCH fit status and parameter domain. Suppressed optimizer warnings are not evidence of successful estimation. *Convergence flag and variance domain checked; boundary solutions within 1e-6 of a constraint are accepted and clipped; failed refits leave NaN that breach counts exclude (70153ba).*
- [ ] If a Monte Carlo method is selected for formal backtesting, provide its actual forecast implementation. Current rolling output excludes MC; normal forecasts are not a universal substitute. *Open: not selected.*

## Priority 3: reliable evidence and runs

- [x] Add a run manifest with input hashes, weights, actual dates, parameters, version/commit, units, model statuses, random seeds and run mode. *`manifest.json` in every run folder (70153ba).*
- [x] Separate quick and full outputs or prevent stale files from appearing current. *Quick runs write `results/risk_quick/` (git-ignored); `--out` for anything else (70153ba).*
- [x] Make output publication consistent, preferably through a completed run directory and manifest. A failed run must not mix old and new evidence. *Runs build in a hidden sibling folder and swap in only when complete (70153ba).*
- [x] Add approved data/weights configuration to the runner. *`--returns` (CSV of daily asset log returns) and `--weights` (JSON) (70153ba).*
- [x] Make sample/horizon and selected as-of dates drive narrative text. A conditional forecast after the dataset's last date is not necessarily today's forecast. *(70153ba)*
- [x] Audit generated narrative assertions: normal risk need not always understate alternatives; ES/VaR depends on mean and confidence; bootstrap intervals do not measure every uncertainty; failure to reject a test does not prove an assumption. *Sign-aware comparisons; ES/VaR wording; interval scope stated; test conclusions say "not proof" (70153ba).*
- [x] Label plots using log loss as log-loss percent. *(70153ba)*
- [x] Distinguish the worst-performing asset from the largest portfolio loss contributor. *`worst_days` has `lowest_return_asset` and `top_loss_contributor` (70153ba).*

## Priority 4: final integration and write-up

- [ ] Supply forecast files and schema to Person 4; incorporate their model-validation findings.
- [ ] Supply tested table/plot interfaces and warnings to Person 5.
- [ ] Write the risk-methodology and results sections, assumptions/limitations text and presentation evidence.
- [ ] Recompute with approved data and portfolio, compare with development results, reconcile app/report/tear sheet and obtain independent review.

## Execution and cleanup policy

The README documents `python -m pytest`, `python -m quanedge.risk.run --quick`, and `python -m quanedge.risk.run`. Read `run.py` before using them: a full run replaces `results/risk/` (only once it has finished), a quick run replaces `results/risk_quick/`, and `--refresh-data` replaces the development cache. When validating changed numerical methods, write to a separate folder with `--out` and compare it with the published run before replacing it.

Preserve `data/cache/prices_dev.csv` until an approved replacement is integrated; it enables offline reproduction. Preserve existing CSVs/PNGs as development evidence until a replacement run is verified. PDFs and PPTXs are reference artifacts with different uses; the masterclass PPTX includes notes absent from its PDF.

The only redundant project file removed during this documentation consolidation is `docs/person3_risk_plan.md`. Its owner, API, defaults, model inventory, work plan, limitations and bibliography have been carried into this pack, with overly broad claims marked for review. Its content remains recoverable from Git history. Update all live references to the new entry point.
