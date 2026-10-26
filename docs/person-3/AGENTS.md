# Person 3: risk measurement instructions

Owner recorded in the existing project: **Navod Caldera**. Role: VaR, Expected Shortfall and Extreme Value Theory lead. This instruction pack supersedes `docs/person3_risk_plan.md` and describes work to finish and validate an existing implementation.

## Read in order

1. [Scope, source hierarchy and requirements](01-scope-and-requirements.md)
2. [Data contracts and conventions](02-data-contracts-and-conventions.md)
3. [VaR and Expected Shortfall](03-var-and-expected-shortfall.md)
4. [Extreme Value Theory](04-extreme-value-theory.md)
5. [Implementation plan and current gaps](05-implementation-plan.md)
6. [Testing and acceptance](06-testing-and-acceptance.md)
7. [Team integration and handoffs](07-team-integration-and-handoffs.md)
8. [Reporting and defence](08-reporting-and-defence.md)

Read all eight before first implementation. For subsequent focused work, reread the relevant specification and inspect the current code. These documents are specifications, not evidence that their checklists are already completed.

## Working sequence

1. Inventory current code, tests, data and saved outputs; establish a baseline test result.
2. Agree the data/weights contract, loss definition, ES estimator and valuation conventions with the relevant owners.
3. Resolve release-critical correctness gaps, especially ES monetary conversion, invalid inputs, tail fitting and transparent failure states.
4. Validate mandatory historical, parametric, Monte Carlo and EVT outputs at matching confidence and horizon.
5. Validate existing optional Student-t and conditional models separately; retain them only with defensible evidence and clear labels.
6. Produce forecasts without look-ahead for Person 4 and stable numerical/plot interfaces for Person 5.
7. Replace development inputs, rerun approved analysis, reconcile outputs and write the risk narrative.
8. Obtain independent review and record remaining limitations before freezing submission results.

## Required completion evidence

- Reproducible functions for the three VaR families, ES and justified EVT estimates.
- Explicit units and well-defined failure behaviour, including non-finite log ES and insufficient tail data.
- Comparison tables, diagnostics, uncertainty/sensitivity evidence and explanations of disagreements.
- Validated forecast timestamps and a documented handoff to Person 4; formal backtest conclusions are supplied by that owner.
- Dashboard integration with 90/95/99% support and honest labels for hybrid EVT/body estimates.
- Risk report section, figures, assumptions/limitations text and a reviewed AI-use record.
- Final data and portfolio provenance; placeholder outputs cannot close the final acceptance gate.

## Scope controls

Do not independently choose the final portfolio, risk tolerance or investment recommendation. Supply evidence and propose changes for the team to evaluate. Do not replace Person 4's backtests with in-sample breach counts. Keep data source changes with Person 1 and portfolio policy changes with Person 2.

When an integration input is missing, continue with labelled development inputs and list the missing dependency. Never invent final weights, fabricate validation approval, or silently treat an unsuccessful model fit as a usable result.
