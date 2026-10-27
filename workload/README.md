# Workload split

The project is divided across five roles. Each file lists the role's code, outputs, tasks, handoffs, tests and the questions that person must be able to answer in Q&A.

| # | Role | File | Owns |
|---|---|---|---|
| 1 | Data | [person1_data.md](person1_data.md) | `quanedge/data/`, `data/` |
| 2 | Portfolio construction | [person2_portfolio.md](person2_portfolio.md) | `quanedge/portfolio.py`, candidates and spending survival |
| 3 | Risk management | [person3_risk.md](person3_risk.md) | `quanedge/risk/`, `backtest.py`, `stress.py`, `robustness.py` |
| 4 | Application and integration | [person4_app_integration.md](person4_app_integration.md) | `app.py`, `pipeline.py`, `results.py`, `evidence.py` |
| 5 | Reports, presentation and QC | [person5_reports_qc.md](person5_reports_qc.md) | `reporting.py`, `verify.py`, `scripts/build_pitch.mjs`, README |

## Order of work

```
Person 1  data snapshot + clean returns
   │
   ├──► Person 2  weights, candidates, KPIs ──┐
   │                                           ├──► Person 4  pipeline run + app ──► Person 5  documents, deck, checks
   └──► Person 3  VaR/ES/EVT, backtests, stress┘
```

- Person 1 freezes the data first. Nobody refreshes snapshots after that without telling the whole team.
- Persons 2 and 3 work in parallel on the same clean returns. Person 3 needs Person 2's canonical weight files (with weight hashes) before running rolling forecasts.
- Person 4 connects everything through `python -m quanedge.pipeline --config config/final.yaml` and the app.
- Person 5 starts the document outlines from day one, but fills every number only from a completed `results/<run_id>/`.

## Shared rules

- `config/final.yaml` is the single source of policy values. Change it only by team decision, and record the change in the decision log in `AGENTS.md`.
- Every number in the app, report, tear sheet, memo and deck comes from the same run folder. `python -m quanedge.verify results/<run_id>` must pass before submission.
- Each person runs `python -m pytest -q` before pushing, and pushes only to their own branch (`p1-data`, `p2-portfolio`, `p3-risk`, `p4-app`, `p5-reports`). Person 4 merges to `main`.
- Each person adds their own AI-tool use to the AI-use log kept by Person 5.
- Every person must be able to explain the final verdict (currently **Adjust** to 15% SPY / 70% AGG / 15% GLD in `final-20261027`) and the three committee questions: what can go wrong, how bad, how confident.
