# Person 4: Application and integration

**Mission:** connect data, portfolio and risk into one reproducible run, and present it in a Streamlit app the committee can use without help. Owns `main` and the one-command workflow.

## Code and files owned

| Path | Purpose |
|---|---|
| `app.py` | Streamlit committee application |
| `quanedge/pipeline.py` (orchestration: `load_inputs`, `evaluate`, `run`, `main`) | One-command training and final runs |
| `quanedge/results.py` | Result keys and result states (matched / computed in app / rerun required) |
| `quanedge/evidence.py` | Staging and sealing a completed run folder |
| `quanedge/config.py`, `config/final.yaml` (loading and validation) | Config access |
| `results/latest.txt`, `results/<run_id>/index.json`, `manifest.json`, `submission.json` | Run identity |
| `requirements.txt`, `requirements.lock.txt`, `pytest.ini`, `.gitignore`, `.gitattributes` | Environment and repository hygiene |

## Tasks

### 1. Build the Streamlit dashboard
The app must contain the six mandatory elements plus recommendation and provenance. Current pages in `app.py`:
- **Sidebar:** portfolio dropdown, Precomputed/Explore mode, confidence (90/95/99%), VaR method (historical, normal, Student-t, MC normal, MC t, EVT, FHS, GARCH-EVT), backtest dates.
- **Recommendation:** fixed "Frozen recommendation" panel that always shows W_rec, its weight hash, run ID, verdict and traffic light, whatever the sidebar says.
- **Portfolio:** weights, KPIs, candidate table, performance chart.
- **Risk:** VaR/ES table by method and confidence, distribution and EVT figures, intervals.
- **Backtesting:** breaches, Kupiec/Christoffersen results, traffic light.
- **Stress & contributions:** historical and hypothetical stresses, reverse stress, component ES.
- **Assumptions & Limitations:** written with Person 5.
- **Provenance:** run ID, git SHA, input hashes, package versions.

### 2. Connect data, portfolio and risk outputs
- `python -m quanedge.pipeline --stage training --config config/final.yaml` uses only 2005-2016 returns.
- `python -m quanedge.pipeline --config config/final.yaml` writes the full `results/<run_id>/`: weights, performance, risk, forecasts, stress, validation, manifest and documents.
- The final run refuses a config that does not match the `prereg-v1` tag and refuses prices after or short of 2026-09-30.
- A new run is staged first and published only when complete. A failed run must never replace completed evidence (`evidence.py`).
- Every distinct allocation gets its own forecasts; agree output file names with Persons 2 and 3 before they write code (`tests/test_contracts.py`).

### 3. Add charts, controls and error messages
- Plotly charts for weights, cumulative performance, drawdown, loss distribution, rolling VaR with breaches, stress bars and risk contributions. Reuse Person 3's figures from `quanedge/risk/plots.py`.
- Clear messages for every failure state:
  - No completed run: explain how to produce one.
  - Explore weights that do not sum to 100% within 0.01 pp: error.
  - Allocation outside policy: warning.
  - Run inputs changed since the run: error naming the changed source.
  - Survival results: warning that they do not gate the verdict.
- Traffic light shows colour only for a matched result; otherwise grey with a label.

### 4. Ensure results update correctly and are reproducible
- **Result states** keyed by weight hash and all material inputs (`results.py`):
  - *Matched:* loaded from the frozen run.
  - *Computed in app:* cheap results (weights, replay, KPIs, historical/normal/t VaR and ES, small fixed-seed MC, stress replays, historical component ES), labelled "computed in app, not part of frozen run".
  - *Unavailable, rerun required:* expensive results (rolling forecasts, backtests, bootstrap intervals, EVT threshold uncertainty, survival, walk-forward, verdict), with the command to run.
- Editing any weight in Explore mode must turn backtest, intervals and verdict to "rerun required". Returning to W_rec must restore the matched results.
- The app reads only `results/latest.txt` and the run folder; it makes no downloads.
- Fresh clone test: clone, create `.venv`, install `requirements.lock.txt`, run pytest, run the app. Fix anything that depends on local state.
- Deploy to Streamlit Community Cloud if practical; a local one-command run is the minimum.
- Merge each person's branch to `main` after their tests pass, and tag the final run `final-run-<run_id>`.

## Handoffs

| From / To | What |
|---|---|
| From Person 1 | Loaders, manifest, data rebuild command |
| From Person 2 | Weight files, KPIs, candidate table, dropdown list |
| From Person 3 | Risk tables, forecasts, backtests, stress, figures |
| To Person 5 | Completed run ID, screenshots of every page, the reproduce commands for README |

## Tests to keep green
- `tests/test_app.py`: `streamlit.testing.AppTest` smoke test, Explore-mode state changes.
- `tests/test_run.py`: pipeline end-to-end on snapshot data.
- `tests/test_contracts.py`: output file contracts between modules.

## Done when
- [ ] `python -m streamlit run app.py` works from a fresh clone.
- [ ] All six mandatory elements, recommendation and provenance pages render on the final run.
- [ ] Explore edits move the expensive panels to "rerun required"; W_rec restores them (AppTest).
- [ ] One command reproduces the run folder and `results/latest.txt` points to it.
- [ ] `python -m pytest -q` passes on `main`.

## Questions you must answer in Q&A
- How does a judge run the app from scratch? Show it live.
- What happens if I change a weight? Why does the traffic light go grey?
- How do you know the numbers in the app are the ones in the report (run ID, hashes)?
- What stops a failed run from overwriting good results?
- Why does the app never download data at runtime?
