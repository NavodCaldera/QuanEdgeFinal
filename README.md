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
python -m streamlit run app.py
```

The app reads the completed run named by `results/latest.txt`; it makes no data downloads. Its initial state explains when no completed run is present.

## Reproduce the analysis

```powershell
python -m quanedge.data.run
python -m quanedge.data.enrich
python -m quanedge.pipeline --stage training --config config/final.yaml
python -m quanedge.pipeline --config config/final.yaml
```

The data pipeline rebuilds offline from frozen raw/cache snapshots. `--refresh` deliberately changes inputs; never use it just to edit documents. The final pipeline requires the policy config to match the local `prereg-v1` tag and refuses prices after or short of 2026-09-30. The training command uses only 2005-2016 returns. A new final run is staged before publication to a new local folder; failed runs do not replace completed evidence. Final analysis may take several minutes because every distinct allocation receives its own forecasts.

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

The accepted policy assumes 4% annual spending, 2.5% inflation, a 6.77% geometric-return hurdle, USD 250,000 historical one-day ES99 budget and 20% stress/drawdown limit. FHS is primary; GARCH-EVT is the pre-named challenger. Earlier development results were seen and are disclosed in PLAN.md. The frozen C1-C5 and A1-A5 rules determine Accept, Adjust, Reject or evaluation incomplete. The owner's final investment judgement is separate.

The completed local run `final-20261027` returns **Adjust** to the minimum-CVaR allocation: **15% SPY, 70% AGG, 15% GLD**. The original allocation fails the GFC drawdown gate. For the adjusted allocation, FHS fails coverage and the pre-named GARCH-EVT challenger passes the gate with a yellow final zone. The illustrative spending simulation shows substantial real-capital shortfall risk; this qualifies the owner's decision and must not be hidden by the mechanical verdict.

Review the [investment memorandum](results/final-20261027/documents/investment_memorandum.pdf), [executive tear sheet](results/final-20261027/documents/executive_tear_sheet.pdf), [committee memo](results/final-20261027/documents/committee_memo.pdf), [editable pitch](results/final-20261027/documents/committee_pitch_v2.pptx) and [speaker/Q&A notes](results/final-20261027/documents/speaker_qa_notes.md).

```powershell
python -m quanedge.verify results/final-20261027
```

This read-only check verifies artifact/input/source hashes, forecast timing, allocation identities, recomputed backtests, ES reconciliation and document page counts. Source hashes normalize line endings; data hashes preserve exact bytes. Post-snapshot descriptive monitoring, when present under `monitoring/`, is separate from the frozen selection and never changes its verdict.

Traditional Basel zones are used only for 250 observations at 99%, following [BIS guidance](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/99/inforce/2019-12-15/published/2019-12-15). They are a monitoring comparison, not an endowment regulatory requirement.

## AI disclosure and review

Codex assisted code restoration, portfolio/validation/stress modules, tests, integration, UI and document generation. Earlier project records identify Claude Code and Antigravity assistance. Automated numerical checks do not constitute independent human validation. Reviewer and review date remain pending. The sole owner must understand and defend the methods and recommendation. No publication, deployment or organiser communication is performed by the local pipeline.
