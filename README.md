# QuantEdgeFinal

Solo Ghosted entry for the SAIFA Quant Edge 1.0 final challenge. Python research and a Streamlit committee application for a USD 10 million university endowment. This is a review package: independent human validation, solo eligibility and deadline confirmation remain pending.

## Setup and local use

Use Python 3.12 from the repository root. An isolated environment avoids conflicts with unrelated applications.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m quanedge.data.run --check-only
python -m pytest -q
python -m streamlit run dashboard.py
```

`dashboard.py` is the committee dashboard for the final portfolio, monthly dynamic EWMA risk parity on SPY, AGG, GLD and XLE. It reads the frozen price snapshot and the pre-registered strategy evidence in `results/dynamic-parity-r1/` (rebuilt by `python -m quanedge.dynamic_parity_eval`). It refuses that evidence if the price file or the forecasts' strategy hash has changed. It makes no data downloads. Pages: Decision, Portfolio, Risk (VaR, ES, EVT), EVT tail, Backtesting, Stress tests, Risk contributions, Assumptions & Limitations, Data & provenance. Real returns are deflated by US CPI (FRED CPIAUCSL index ratios).

The earlier multi-portfolio viewer, `python -m streamlit run app.py`, still reads the run named by `results/latest.txt`.

## Reproduce the analysis

```powershell
python -m quanedge.data.run
python -m quanedge.data.enrich
python -m quanedge.pipeline --stage training --config config/final.yaml
python -m quanedge.pipeline --config config/final.yaml
```

The data pipeline rebuilds offline from frozen raw/cache snapshots. `--refresh` deliberately changes inputs; never use it just to edit documents. The final pipeline requires the policy config to match the tag named in it (`prereg_tag`, currently `prereg-v2`) and refuses prices after or short of 2026-09-30. The training command uses only 2005-2016 returns. A new final run is staged before publication to a new local folder; failed runs do not replace completed evidence. Final analysis may take several minutes because every distinct allocation receives its own forecasts.

`requirements.txt` lists direct dependencies; `requirements.lock.txt` pins the tested clean-environment dependency set. Editable pitch contents and speaker notes are included with each delivered deck. Regenerating the PPTX uses `scripts/build_pitch.mjs` and the Codex bundled Artifact Tool runtime, configured with `QUANTEDGE_RUNTIME` and `QUANTEDGE_PRESENTATION_SKILL`; this is separate from the portable Python analytics/app workflow.

## Structure and evidence

- `quanedge/data/`: approved-source ingestion, cleaning, calendar/quality audits, stationarity and manifests.
- `quanedge/risk/`: VaR/ES, Monte Carlo, EVT, conditional models, rolling forecasts and uncertainty.
- Other `quanedge` modules: portfolio construction, formal backtests, stress, result identity, orchestration and reports.
- `config/final.yaml`: accepted policy and frozen estimator/model settings.
- `tests/`: synthetic numerical tests and offline snapshot integration checks.
- `data/`: frozen source snapshots, clean inputs and dictionary.
- `results/<run_id>/`: weights, risk, forecasts, stress, validation, manifest and generated documents.

Risk values distinguish log loss, simple percentage points and USD. Dollar ES averages dollar tail losses. Risk replay is daily rebalanced without costs; investment performance uses quarterly/drift rebalancing and five-basis-point one-way costs. All historical allocation evaluations are retrospective. Each portfolio's sequential forecasts carry its own weight hash; altered Explore weights cannot inherit a traffic light or verdict.

## Decision and governance

### Current mandate (v3)

Mandate v3 (tag `prereg-v3`, PLAN.md section 13c) keeps every v2 rule below and limits holdings to SPY, AGG, GLD and XLE, because EFA, EEM and XLK move almost in step with SPY (daily correlation 0.82-0.91). SPY and XLE are still 0.70 correlated; AGG and GLD are the diversifiers.

Run `final-v3-20261030` returns **evaluation incomplete**, with the same allocation and evidence as v2: **SPY 5.8%, AGG 88.0%, GLD 6.0%, XLE 0.2%** (the v2 pick already used only these four ETFs). C1-C3 and C5 pass; the risk-model check fails (FHS 41 breaches vs 24.5 expected, Kupiec p 0.002; GARCH-EVT 36, p 0.026). No A1-A2 alternative passes all checks: the four-ETF risk-parity mix (SPY 14 / AGG 61 / GLD 16 / XLE 9) now passes the stress limit (GFC 18.1%) but fails conditional coverage (FHS p 0.009). The fixed benchmarks SPY 35 / AGG 50 / GLD 15 and SPY 25 / AGG 50 / GLD 25 pass all five checks but are outside the selection rule. The return and reserve qualifications under v2 below apply unchanged.

Review the [v3 investment memorandum](results/final-v3-20261030/documents/investment_memorandum.pdf), [executive tear sheet](results/final-v3-20261030/documents/executive_tear_sheet.pdf), [committee memo](results/final-v3-20261030/documents/committee_memo.pdf) and [speaker/Q&A notes](results/final-v3-20261030/documents/speaker_qa_notes.md); verify with `python -m quanedge.verify results/final-v3-20261030`.

### Mandate v2

Mandate v2 (owner change, 30 October 2026, tag `prereg-v2`, PLAN.md section 13b) removes all ETF percentage limits, assumes zero trading cost, withdraws a cash reserve for the university every 1 January (USD 400,000 in year 1, then growing 3.64% a year: USD 414,560 in year 2), and targets a 1-3% real return after the owner's 3.64% inflation assumption. The optimiser picks the lowest-CVaR99 allocation whose expected return reaches 3% real, within the 2.5% ES99 budget and 20% stress limit; C3 requires at least 1% real.

Run `final-v2-20261030` returns **evaluation incomplete**. The selected allocation is **SPY 5.8%, AGG 88.0%, GLD 6.0%, XLE 0.2%** (the 3% target does not bind, so this is the minimum-CVaR portfolio). It passes feasibility, the ES budget (USD 124,433 against USD 240,000), the return check (3.54% real expected) and the stress check (GFC drawdown 13.1%). It fails the risk-model check: on its own 2017-2026 forecasts FHS had 41 breaches of 99% VaR against 24.5 expected (Kupiec p 0.002) and the GARCH-EVT challenger 36 (p 0.026). Under the frozen rule a risk-model failure blocks a verdict rather than producing Adjust or Reject. None of the A1-A2 alternatives passes all five checks either.

Material qualifications, shown in the app and documents:
- The return check depends on the 50% mean shrinkage, which lifts AGG's expected return. On raw historical means the allocation expects 3.90% nominal (0.25% real) on full history and 1.41% nominal over five years, below the 1% real floor. Over 2017-2026 it realised about -0.26% a year real.
- The reserve (4% of the initial fund in real terms) exceeds the return objective. In the 25-year resampled-history simulation, 67.4% of paths pay every reserve in full, the median failing path runs out in year 24, and no path keeps USD 10 million in real terms.
- Among the fixed benchmarks, SPY 35 / AGG 50 / GLD 15 and SPY 25 / AGG 50 / GLD 25 pass all five checks on their own forecasts. They are comparisons outside the frozen selection rule and adjustment set, so adopting one would be a further logged owner decision.

Review the [v2 investment memorandum](results/final-v2-20261030/documents/investment_memorandum.pdf), [executive tear sheet](results/final-v2-20261030/documents/executive_tear_sheet.pdf), [committee memo](results/final-v2-20261030/documents/committee_memo.pdf) and [speaker/Q&A notes](results/final-v2-20261030/documents/speaker_qa_notes.md). The editable PPTX deck has not been rebuilt for v2.

```powershell
python -m quanedge.verify results/final-v2-20261030
```

### Mandate v1 (superseded, kept as recorded)

The accepted policy assumed 4% annual spending, 2.5% inflation, a 6.77% geometric-return hurdle, USD 250,000 historical one-day ES99 budget and 20% stress/drawdown limit. FHS is primary; GARCH-EVT is the pre-named challenger. Earlier development results were seen and are disclosed in PLAN.md. The frozen C1-C5 and A1-A5 rules determine Accept, Adjust, Reject or evaluation incomplete. The owner's final investment judgement is separate.

The local run `final-20261027` returned **Adjust** to the minimum-CVaR allocation: **15% SPY, 70% AGG, 15% GLD**. The original allocation fails the GFC drawdown gate. For the adjusted allocation, FHS fails coverage and the pre-named GARCH-EVT challenger passes the gate with a yellow final zone. The illustrative spending simulation shows substantial real-capital shortfall risk; this qualifies the owner's decision and must not be hidden by the mechanical verdict.

Review the [investment memorandum](results/final-20261027/documents/investment_memorandum.pdf), [executive tear sheet](results/final-20261027/documents/executive_tear_sheet.pdf), [committee memo](results/final-20261027/documents/committee_memo.pdf), [editable pitch](results/final-20261027/documents/committee_pitch_v2.pptx) and [speaker/Q&A notes](results/final-20261027/documents/speaker_qa_notes.md).

```powershell
python -m quanedge.verify results/final-20261027
```

After the v2 code change this check also reports source-hash differences for the v1 run, because the code that produced it has since changed; its data, artifact and forecast checks are unaffected. Use tag `final-run-final-20261027-v2` to reproduce it exactly.

This read-only check verifies artifact/input/source hashes, forecast timing, allocation identities, recomputed backtests, ES reconciliation and document page counts. Source hashes normalize line endings; data hashes preserve exact bytes. Post-snapshot descriptive monitoring, when present under `monitoring/`, is separate from the frozen selection and never changes its verdict.

### Standalone history and documentation revision r1

Added after preregistration; neither changes the frozen data, weights, forecasts, gates or verdict.

```powershell
python -m quanedge.context --download   # each ETF's full Yahoo history to 2026-09-30, then tables
python -m quanedge.context              # rebuild tables from the saved, hash-checked snapshot
python -m quanedge.docrev               # memorandum addenda, tear-sheet box and Q&A from the run
python -m quanedge.docrev --verify      # read-only: parent identity, own hashes, page limits
```

The snapshot and tables live in `context/` (outside `data/`, which the final pipeline hashes). The app's ETF charts page reads them when present and falls back to the frozen panel otherwise. Revision r1 is in `results/docrev/final-20261027-r1/`: [memorandum with addenda](results/docrev/final-20261027-r1/investment_memorandum.pdf), [tear sheet](results/docrev/final-20261027-r1/executive_tear_sheet.pdf), [Q&A notes](results/docrev/final-20261027-r1/speaker_qa_notes.md). It discloses that C3 passes only under the frozen mean shrinkage, compares spending shortfall for both allocations, and reports what pre-2005 ETF history shows. The parent run's documents, manifest and the PPTX deck are unchanged.

Use release tag `final-run-final-20261027-v2` for the verified checkout, including attributes that preserve exact artifact bytes. The earlier `prereg-v1` policy freeze remains unchanged.

Traditional Basel zones are used only for 250 observations at 99%, following [BIS guidance](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/99/inforce/2019-12-15/published/2019-12-15). They are a monitoring comparison, not an endowment regulatory requirement.

## AI disclosure and review

Codex assisted code restoration, portfolio/validation/stress modules, tests, integration, UI and document generation. Earlier project records identify Claude Code and Antigravity assistance. Automated numerical checks do not constitute independent human validation. Reviewer and review date remain pending. The sole owner must understand and defend the methods and recommendation. No publication, deployment or organiser communication is performed by the local pipeline.
