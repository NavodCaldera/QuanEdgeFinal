# Reporting and defence

## Person 3's report contribution

Write a coherent section sized to the team's overall 7-15 page memo, with supporting diagnostics in the repository. Cover data period and portfolio source, loss conventions, three VaR families, ES definition, EVT threshold/fit, assumptions, uncertainty, model comparison, validation findings from Person 4 and implications for the endowment. Person 5 edits the combined document; Person 3 remains responsible for this content.

Every reported risk number must identify confidence, horizon, portfolio, value, date, unit and method. Distinguish log loss from simple percentage loss and exact monetary ES from any labelled approximation. Identify development versus final results and conditional forecasts versus long-run historical estimates.

## Tables and figures to deliver

| Artifact | Required interpretation |
|---|---|
| VaR/ES comparison at 95% and 99%, plus app 90% | Comparable losses across required methods; gaps and their causes |
| Threshold scan and selected fit | Rule, count, shape/scale, stability, fit quality and limitations |
| Sensitivity table | Threshold, lookback and relevant bootstrap/simulation setting changes |
| Assumption checks | Null hypotheses, statistics, p-values and appropriate interpretation |
| Model/run metadata | Reproducible inputs, parameters, seed, dates, units and warnings |
| MC convergence/error | Simulation noise distinguished from other uncertainty |
| Distribution and normal QQ plot | Observed fit departures without claiming a diagnostic predicts crises |
| Mean excess versus u, xi and modified-scale stability | Evidence supporting threshold choice |
| EVT tail survival and excess QQ/PP plot | Where the fitted tail agrees/disagrees with observed extremes |
| VaR/ES comparison and uncertainty plots | Tail severity and estimation precision |
| Rolling forecasts and exceptions | Prior-data forecasts, timing and clustered exceptions; formal evaluation from Person 4 |

Retain `worst_days.csv` as descriptive evidence. It separates `lowest_return_asset` (the asset that fell most) from `top_loss_contributor` (the largest weight x return loss); they differ when weights differ. A threshold sensitivity band is not automatically a confidence interval. Blank intervals for conditional methods mean not estimated, not zero uncertainty.

## Interpretation and decision contribution

Explain a 99% one-day VaR as a model loss quantile expected to be exceeded on about 1% of days under its assumptions, not a maximum possible loss or a guaranteed once-per-100-days schedule. Explain ES as average worst-tail loss and EVT as extrapolation of extremes with uncertainty. Risk measures cannot identify the date of the next crash.

Explain method disagreement using the actual estimates and assumptions. Do not assert normal always understates, EVT always dominates, or a more complicated model is safer. Discuss whether changing exposures or risk limits is warranted, supplying evidence to Persons 2 and 4. Do not select whichever model produces the lowest risk merely to make the mandate appear acceptable.

Daily risk, crisis cumulative loss and maximum drawdown answer different questions. Relate them through the investment policy without substituting one metric for another. The final accept/adjust/reject recommendation must be evaluated and owned by the team.

## Assumptions and limitations text

Explicitly cover: sample dependence and regime change; limited tail observations; EVT threshold uncertainty; extrapolation; estimated means/covariances; conditional-filter specification; model fitting constraints; current-portfolio replay and rebalancing; trading costs, liquidity and price impact; no automatic protection against unseen events; simulation error; parameter versus model uncertainty; and any unresolved data or valuation approximation.

Report statistical tests as evidence against a null or failure to reject it. A high p-value does not prove normality, independence or successful filtering. ADF rejection of a unit root does not establish that every distribution parameter is stable. Coherence of ES applies to the properly defined loss measure; do not transfer every aggregation claim automatically to nonlinear log losses.

## Presentation and judge preparation

Prepare concise slides on VaR/ES interpretation, matched model comparison, EVT justification, and validation/decision implications. Agree speaking time within the team's 10-12 minute finalist pitch. Bring backup diagnostics and be able to answer:

1. How were log returns aggregated and converted into USD loss?
2. Why is dollar ES not simply a transformation of log ES?
3. Which empirical quantile/ES definition handles ties and finite samples?
4. Why were these lookback and risk horizons chosen?
5. What distinguishes parametric normal from this implementation's multivariate MC?
6. What evidence supports the chosen EVT threshold and minimum count?
7. What changes when xi approaches one, or the fitted model fails?
8. What is shown at 90% if the EVT tail begins above that percentile?
9. Which uncertainty does the bootstrap include or omit?
10. How were future information, parameter refit timing and portfolio-selection leakage handled?
11. Does the selected model pass Person 4's tests, and what do failures imply?
12. What portfolio action follows, and which assumption could overturn it?

## AI-use record

The superseded plan recorded Claude Code for scaffolding risk code, tests and documentation. Preserve that provenance, but do not assert that a human re-derived every formula without a completed review record. This instruction pack was AI-assisted using Codex for repository/source review and documentation consolidation. No model corrections described by this pack were implemented merely by writing the instructions.

For each material contribution record tool, purpose, affected files/components, automated checks, actual human reviewer/date, changes after review and remaining limitations. Human approval and final investment judgement cannot be inferred from passing tests.

## Theory bibliography and verification work

Retained from the previous plan: Balkema and de Haan (1974), residual lifetime tails; Pickands (1975), extreme order statistics; Hosking and Wallis (1987), GPD estimation; Smith (1987), tail estimation; Coles (2001), statistical modelling of extremes; McNeil, Frey and Embrechts (2015), Quantitative Risk Management; Glosten, Jagannathan and Runkle (1993), asymmetric volatility; Barone-Adesi, Giannopoulos and Vosper (1999), filtered historical simulation; McNeil and Frey (2000), conditional EVT; Clauset, Shalizi and Newman (2009), power-law fitting.

Verify the exact equation, assumptions and bibliographic details before citing these works in the final submission. In particular, the current threshold heuristic should not be presented as a verbatim procedure from Clauset et al. without evidence. The supplied teaching material also points to Artzner et al. (1999) for coherent risk measures. [Acerbi and Tasche](https://arxiv.org/abs/cond-mat/0104295) addresses why ES definitions require care for discontinuous distributions.
