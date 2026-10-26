# QuanEdgeFinal agent instructions

## Project and source of truth

Team Ghosted is preparing the SAIFA Quant Edge 1.0 final challenge for the Serendib University Endowment Fund: USD 10 million, conservative capital preservation, income and sustainable growth. Python is the analysis language and Streamlit is the required interface.

The final competition brief, `../Quant edge 1.0 Final Challenge 1.pdf`, takes precedence over teaching decks, the pasted summary, and earlier project plans. Eligible investments are SPY, EFA, EEM, AGG, GLD, XLE and XLK. The investment horizon and constraints must be justified by the team; they are not fixed by examples in the masterclass. Approved data sources are Yahoo Finance via yfinance, FRED, and World Bank/IMF where relevant.

## Person 3 routing

Before any Person 3 implementation, review, or reporting work, explicitly read [the Person 3 instructions](docs/person-3/AGENTS.md) and the relevant linked specifications. That directory's AGENTS.md is not automatically applied to Python files elsewhere; this root instruction explicitly requires consulting it for risk work.

Person 3's existing owner is Navod Caldera, as recorded in the previous project plan. Primary code is `quanedge/risk/`, with related tests in `tests/`. Extend this implementation rather than creating a parallel `src/risk/` package.

## Shared ownership and working rules

- Person 1 owns approved data, cleaning, provenance and reproducibility. Person 2 owns investment policy, portfolio weights, construction and performance KPIs.
- Person 3 owns VaR, ES, EVT, model diagnostics, uncertainty, and forecast generation interfaces. Person 4 owns formal backtests, stress scenarios and risk attribution. Person 5 owns Streamlit and final document integration.
- Each member writes and validates their own report section. Final investment judgments remain the team's responsibility.
- Inspect current files and Git status before editing. Preserve unrelated work, source documents, data snapshots, and results. Do not delete useful code because an optional model is not compulsory.
- Development prices and equal weights are placeholders. Label their results accordingly. Do not describe existing tests or saved numbers as proof of final investment suitability.
- Document units, loss signs, dates, confidence, horizon, exposure assumptions and data versions. A forecast for day t may use only information available before t.
- Keep model calculations independent of the UI. Preserve public interfaces or coordinate migrations with their consumers and tests.
- Run relevant tests for numerical changes. Never refresh downloaded prices or regenerate published results silently; record the source and configuration of each run.
- Document AI assistance accurately, distinguishing automated tests from human review that has actually occurred.

## Existing commands

From this repository directory:

```text
python -m pytest -q
python -m quanedge.risk.run --quick
python -m quanedge.risk.run
```

The risk runner writes into `results/risk/`; quick mode can leave old rolling files beside new tables. Consult the Person 3 implementation plan before using those outputs as a release. This repository currently contains the risk workstream, not a completed Streamlit application.
