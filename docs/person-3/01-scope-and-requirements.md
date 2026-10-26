# Scope and requirements

## Sources reviewed and precedence

The source documents are in the workspace parent of the repository:

| Source | Use |
|---|---|
| `Quant edge 1.0 Final Challenge 1.pdf`, 10 pages | Authoritative final mandate, universe, deliverables, methods and rubric |
| `Advanced_Risk_Management_English_final.pdf` and matching PPTX, 28 pages/slides | VaR/ES definitions, POT/GPD, dependence and interpretation; examples are synthetic |
| `EDGEFORGE_Polished_Finance_First_Masterclass_2026.pdf` and matching PPTX, 99 pages/slides including notes | Return accounting, model interpretation, validation and research discipline |
| User-pasted competition summary | Supplemental explanation; final brief prevails on conflicts |
| Existing code, tests, saved results and previous Person 3 plan | Evidence of implementation and development choices, not additional competition rules |

Masterclass slide 4 uses a draft three-year mandate and broader universe. Its slide 79 notes also quote draft rubric weights. Use the final brief instead: seven eligible ETFs; team-justified horizon; 30% investment decision, 25% technical rigor, and 15% each software, innovation and communication. Futures, options, FX overlays, copulas, wavelets and ML examples do not enlarge the eligible universe or create mandatory tasks.

## Requirements mapped to ownership

| Final brief | Requirement | Person 3 responsibility and evidence |
|---|---|---|
| pp. 3-5, mandate | Explain what can go wrong, severity and confidence in estimates | Interpretable risk estimates, uncertainty, limitations and risk-budget implications |
| p. 7, 8.2 | Historical, parametric and Monte Carlo VaR at 95% and 99% | Same input portfolio, dates and horizon; reproducible functions and comparison narrative |
| p. 7, 8.3 | ES with rationale | Validated tail-average estimator and clear benefit beyond VaR |
| p. 7, 8.4 | EVT and justified threshold | POT fit, diagnostics, selection rule, tail estimates, threshold sensitivity |
| pp. 5-6, section 6 | Sidebar 90/95/99%; matching VaR/ES/EVT displays | Queryable estimates and labels for Person 5 at all sidebar levels |
| p. 7, 8.5 | Out-of-sample validation | Prior-data forecasts and metadata for Person 4's Kupiec/Christoffersen/traffic light |
| p. 8, 8.6 | Marginal risk, position sizing, crisis and hypothetical stress | Model/scenario support and interpretation; Person 4 owns attribution and stress execution |
| p. 9, section 9 | Approved sources, adjusted prices, alignment, log statistics, flags, ADF | Validate consumed data, disclose transformations, coordinate with Person 1 |
| p. 6, section 7 | Reproducible repository/app, 7-15 page report, one-page tear sheet, finalist 10-12 minute pitch | Risk code, documentation, report content and presentation evidence |
| pp. 8-9, 8.7 | AI disclosure and human responsibility | Record tools, purposes, material components and actual validation |

## Mandatory versus chosen work

Mandatory methods are historical VaR, a justified parametric VaR, Monte Carlo VaR, ES and EVT with a defended threshold. Out-of-sample validation is mandatory for the selected VaR model, shared with Person 4.

Existing optional extensions are `student_t`, `mc_t`, `fhs` and `garch_evt`. They are useful candidates, not competition requirements. Bootstrap intervals, numerical convergence and sensitivity checks are project validation choices supporting reliability. Do not sacrifice correctness of the required methods to add more models.

## Implementation snapshot (26 October 2026, commit 13c0619)

`quanedge/risk/` contains eight models, portfolio aggregation, input validation, diagnostics, bootstrap intervals, rolling forecasts, plots and a command-line runner. Seven test files exercise these components. A full run writes 24 risk rows (eight methods times three levels), 38 threshold candidates, 4,719 forecast dates, ten CSV tables, seven PNG figures and a `manifest.json`. Treat these counts as a dated record; the latest run's manifest is authoritative.

The cached price file contains 5,470 rows from 3 January 2005 to 30 September 2026. Differencing gives 5,469 return observations starting 4 January 2005. These describe the cached development snapshot, not independently verified source provenance. Equal weights are temporary. The prior plan marked implementation phases complete but left write-up and final input replacement open; this pack identified correctness and robustness work, whose status is tracked in the [implementation plan](05-implementation-plan.md).

## Deliverable boundary

Person 3 delivers the risk engine and its evidence. Person 1 supplies the approved dataset, Person 2 supplies justified exposures, Person 4 supplies formal validation and stress decisions, and Person 5 integrates the app and submissions. Completion requires agreement on one consistent result set across those deliverables.
