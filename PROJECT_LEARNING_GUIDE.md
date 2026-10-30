# QuantEdgeFinal: owner learning guide

Created at the owner's request on 29 October 2026. This guide lets Claude Code,
Codex or another assistant teach the existing project across separate sessions.
It is a learning aid, not a replacement for AGENTS.md, PLAN.md or source evidence.

## How to resume with Claude Code or Codex

Paste this into a new session opened in this repository:

> Read PROJECT_LEARNING_GUIDE.md, then follow its teaching instructions. Read
> AGENTS.md and the relevant sections of PLAN.md. Inspect the current repository
> and teach me the next unfinished topic using the actual code and saved results.
> Explain one topic at a time, starting with plain language and a small numerical
> example. Show the relevant files and explain how the implementation works.
> Do not change the investment policy, regenerate results or edit analytical code
> unless I ask. Ask me a few understanding questions, explain any mistakes, and
> update the learning progress in this guide with my agreement. Do not mark a
> topic understood merely because you explained it.

## Instructions for the teaching assistant

- The owner is the sole entrant responsible for understanding and defending the
  submission. Explain patiently without assuming knowledge of financial formulas
  or Python. Define each new term before using it.
- Read current files before describing implementation details. Start with Git
  status and preserve unrelated changes. Use the competition brief for rules,
  PLAN.md/configuration for policy, code for implementation, and saved artifacts
  for results. Identify discrepancies instead of hiding them.
- Existing records mention Claude, Codex and Antigravity assistance. Attribute a
  specific contribution only when records support it. Never invent which model
  wrote a module. Automated checks are not independent human review.
- Teach one topic per lesson unless the owner asks otherwise. Use this order:
  concept, why the competition needs it, worked example, actual implementation,
  actual saved result, assumptions/limitations, likely judge questions.
- Explain formulas symbol by symbol and units explicitly. Trace one input through
  the relevant function into an output. Quote small code excerpts with file and
  line references rather than dumping whole modules.
- Ask two or three short comprehension questions. If an answer is wrong, explain
  and try a simpler example. Invite the owner to explain the result in their own
  words. Understanding a topic does not certify the whole submission.
- Do not claim to run commands, inspect figures, verify calculations or obtain
  human approval unless that actually happened. Teaching does not require a new
  expensive pipeline run. Use existing evidence unless asked to verify or rebuild.
- Keep continuation notes in the progress section below. Do not create separate
  learning prompts or work logs. Leave policy changes and engineering decisions
  in their established records.

## Project orientation to verify at the start of a new session

- Client: Serendib University Endowment Fund; initial portfolio USD 10,000,000.
- Eligible ETFs: SPY, EFA, EEM, AGG, GLD, XLE, XLK. Zero weights are allowed.
- Current frozen price snapshot: 3 January 2005 to 30 September 2026. Returns
  begin 4 January 2005. The training return sample ends 30 December 2016 and has
  3,020 aligned observations; the configured cutoff is 31 December 2016.
- W_train uses the training sample. W_rec and the recommended adjustment use the
  full frozen sample through September 2026. Do not imply recommended weights
  were known in 2017. All historical allocation replays are retrospective.
- Current result folder: results/final-20261027, also named by results/latest.txt.
- Frozen rule outcome: Adjust; proposed alternative A1_min_cvar is SPY 15%,
  AGG 70%, GLD 15%. The original selected allocation and proposed adjustment are
  distinct entries; read decision.reported_portfolio before reporting numbers.
- FHS is primary, GARCH-EVT is the named challenger. For the proposed adjustment,
  FHS fails the gate and the challenger passes with a yellow final monitoring
  zone. Explain the exact saved tests rather than calling every model reliable.
- Recorded concerns include substantial illustrative real-capital shortfall risk
  after spending. Passing risk limits does not establish spending sustainability.
- Policy acceptance is recorded; independent human validation, solo eligibility
  and deadline confirmation remain pending in the current configuration.
- The ETF charts page uses the frozen snapshot. Earlier attempts to obtain
  1995-to-today history failed due to network/DNS access. A 1995 axis does not mean
  1995 prices exist. Never claim the app currently has complete history to today.
- The full source verifier may flag subsequent UI changes. app.py explicitly
  permits a changed viewer while preserving data/numerical-code checks and
  displaying an updated-interface caption. Do not rewrite frozen hashes to hide
  differences or claim the entire current tree is the original verified release.

These are orientation notes, not substitutes for inspecting the latest files.

## The 22 lessons

### 1. Understand the competition problem

Learn the client mandate, judging criteria, seven-fund universe and required
deliverables. Connect each requirement to the actual submission. Separate final
brief requirements from teaching-deck illustrations and our policy choices.

Read: Quant edge 1.0 Final Challenge 1.pdf; PLAN.md sections 1–11; README.md.
Be able to answer: What problem are we solving, and what would a successful
submission demonstrate?

### 2. Understand the investment objective

Learn capital preservation, income, sustainable real growth and the role of an
endowment. Distinguish a perpetual mandate, strategic review horizon, simulation
horizon and one-day risk horizon.

Read: PLAN.md sections 3, 13 and 15; config/final.yaml.
Be able to answer: Why is avoiding large losses important for this client?

### 3. Understand our chosen investment policy

Explain spending, inflation, return hurdle, concentration constraints, ES budget,
drawdown/stress limits, rebalancing and the prereg-v1 freeze. Show that the hurdle
is (1 + inflation)/(1 - spending) - 1, approximately 6.77% under the current
assumptions, and identify which return measure it is compared against.

Read: config/final.yaml; PLAN.md sections 13, 13a and 15; AGENTS.md decision record.
Be able to answer: Which numbers are rules from the brief, and which did we choose?

### 4. Understand the project structure and AI contributions

Trace data ingestion, portfolio construction, risk, validation, reports and UI.
Explain restoration from earlier Git history and the difference between code
generation, automated checking and independent owner judgement. Use records for
AI attribution and say when exact authorship is unknown.

Read: README.md; AGENTS.md progress record; quanedge/pipeline.py; app.py.
Be able to answer: How does one input reach the app, and who validated each claim?

### 5. Understand the seven ETFs

Explain each fund's underlying exposure, equity/bond/gold roles and overlapping
positions. Discuss SPY with XLK, emerging-market risk, rate risk in AGG and why
XLE is energy-sector equity rather than a direct oil futures investment.

Read: PLAN.md section 4; quanedge/config.py; data/data_dictionary.md.
Be able to answer: Why can seven funds still contain concentrated risk?

### 6. Understand where the data came from

Explain Yahoo/yfinance prices, FRED rates/macroeconomic series and approved macro
context. Read retrieval metadata and hashes. Explain the requested 2005 start,
the common-history limit imposed by ETF availability, and revised macro data.

Read: quanedge/data/sources.py; data/clean/price_provenance.json;
data/raw/source_inventory.json; data/clean/data_manifest.json.
Be able to answer: Can another person identify and reproduce our inputs?

### 7. Understand adjusted prices and data cleaning

Explain dividends, splits, common calendars, missing observations, anomalies and
stationarity checks. Show a real audit entry. Explain why flagged crisis losses
remain and why adjusted returns must not receive dividends a second time.

Read: quanedge/data/cleaning.py, anomalies.py and stationarity.py;
data/clean/calendar_audit.csv, anomaly_log.csv and stationarity_tests.csv.
Be able to answer: What did we change, retain or flag, and why?

### 8. Understand returns and portfolio accounting

Work one day by hand: price to simple/log return, weighted simple portfolio
return, log portfolio return, loss and dollar P&L. Log asset returns cannot simply
be weight-averaged to obtain an exact portfolio log return. Explain daily replay
versus buy-and-hold and implemented rebalancing.

Read: quanedge/risk/portfolio.py; quanedge/portfolio.py; AGENTS.md numerical contracts.
Be able to answer: How do ETF returns become portfolio losses in dollars?

### 9. Understand training and evaluation periods

Explain W_train, W_rec, the 2016 cutoff, 2017 onward retrospective evaluation,
daily prior-data forecasts and the separate descriptive monitoring period.
Distinguish allocation-selection information from risk-forecast information.

Read: config/final.yaml; quanedge/pipeline.py; results/final-20261027/W_train/weights.json;
results/final-20261027/selected/weights.json; monitoring/final-20261027/summary.json.
Be able to answer: What was known before each forecast, and which data had already
influenced our research choices?

### 10. Understand expected returns, volatility and diversification

Explain sample means, annualisation, mean shrinkage, covariance, correlation and
Ledoit–Wolf estimation. Distinguish arithmetic expectations from geometric growth
and estimated returns from realised returns. Discuss instability and bond-return
assumptions honestly.

Read: quanedge/portfolio.py; config/final.yaml;
results/final-20261027/estimator_sensitivity.csv.
Be able to answer: Why can small estimation changes alter the allocation?

### 11. Understand portfolio construction

Explain Markowitz concepts, minimum variance, maximum Sharpe, historical CVaR and
our actual selection objective. Trace constraints, solver outcomes, tie-breaking,
budget checks, canonical weights and controlled constraint comparisons.

Read: quanedge/portfolio.py; quanedge/pipeline.py; results/training/candidates.json;
results/training/constraint_effects.json; results/final-20261027/candidate_table.csv.
Be able to answer: Why did this procedure produce these weights, and were they feasible?

### 12. Understand portfolio performance

Explain wealth compounding, quarterly/drift rebalancing, costs and benchmarks.
Teach CAGR, volatility, Sharpe, Sortino, beta, Treynor, Jensen's alpha,
Information ratio, drawdown and Calmar, including unreliable denominators.

Read: quanedge/portfolio.py; results/final-20261027/A1_min_cvar/performance.csv;
results/final-20261027/A1_min_cvar/summary.json.
Be able to answer: What does each KPI measure, and when can it mislead?

### 13. Understand VaR and Expected Shortfall

Calculate a small empirical example with ties and fractional tail mass. Explain
confidence, horizon, log loss, simple percentage loss and USD. Dollar ES averages
transformed tail losses; it generally differs from transforming average log ES.

Read: quanedge/risk/var_es.py; results/final-20261027/A1_min_cvar/risk.csv.
Be able to answer: Why is VaR not maximum loss, and what extra information does ES add?

### 14. Understand the different risk models

Explain historical, normal, Student-t and joint-asset Monte Carlo assumptions.
Cover dependence, fitted parameters, covariance handling, seeds, scenario counts
and convergence. Explain why joint-asset Monte Carlo can differ from fitting a
normal distribution directly to portfolio log returns.

Read: quanedge/risk/models.py and var_es.py;
results/final-20261027/A1_min_cvar/robustness/mc_convergence.csv.
Be able to answer: Why do methods disagree, and how do we investigate the gap?

### 15. Understand Extreme Value Theory

Explain peaks over threshold, exceedances, GPD shape/scale, threshold diagnostics,
empirical body versus extrapolated tail, support and uncertainty. Distinguish
infinite log ES from bounded long-only dollar losses and unavailable fits.

Read: quanedge/risk/evt.py and uncertainty.py;
results/final-20261027/A1_min_cvar/robustness/threshold_sensitivity.csv;
results/final-20261027/A1_min_cvar/uncertainty.csv.
Be able to answer: Why this threshold, and how sensitive is the extreme-loss estimate?

### 16. Understand changing volatility

Explain clustering, GJR-GARCH, filtered historical simulation and GARCH-EVT.
Separate volatility forecasts from return-direction predictions. Explain rolling
windows, parameter-refit intervals and daily volatility updates. Disclose earlier
development evidence seen before primary/challenger selection.

Read: quanedge/risk/conditional.py and rolling.py; config/final.yaml;
PLAN.md model-choice disclosure; saved residual diagnostics.
Be able to answer: Why use these conditional models, and what can make them fail?

### 17. Understand backtesting

Trace a forecast row and strict breach rule. Explain coverage, unavailable days,
Kupiec, Christoffersen independence/conditional coverage and calibrated Basel
zones. Use the proposed adjustment's own weight-hashed forecasts and saved tests.

Read: quanedge/backtest.py; quanedge/risk/rolling.py;
results/final-20261027/A1_min_cvar/forecasts.csv and summary.json.
Be able to answer: Why did FHS fail, why did the challenger pass, and why is passing
not proof that future losses are controlled?

### 18. Understand stress testing and risk contributions

Explain exact crisis dates, cumulative loss versus path drawdown, costs and
rebalancing assumptions. Cover hypothetical and reverse stress. Work an example
using the same portfolio-tail scenario weights for every asset's dollar ES
contribution; retain negative contributions and reconcile to portfolio dollar ES.

Read: quanedge/stress.py and robustness.py;
results/final-20261027/A1_min_cvar/summary.json and robustness/.
Be able to answer: Which assets cause damage, and when do bonds/gold fail to protect us?

### 19. Understand the final recommendation

Trace C1–C5, the finite A1–A5 adjustment sequence and the difference between a
risk-model failure and an allocation failure. Explain the original allocation's
GFC drawdown failure, the Adjust outcome and proposed 15/70/15 allocation.

Read: PLAN.md section 13a; quanedge/portfolio.py and pipeline.py;
results/final-20261027/submission.json, decision and reported portfolio entries.
Be able to answer: Why Adjust, and what is still awaiting owner judgement?

### 20. Understand spending sustainability and remaining weaknesses

Explain annual spending after returns/costs, CPI index ratios, real-capital target,
resampled paths, shortfall probability and simulation uncertainty. Discuss why
the proposal may satisfy loss limits yet struggle to maintain real capital.

Read: quanedge/evidence.py; results/final-20261027/survival.json;
results/final-20261027/A1_min_cvar/spending.csv; memorandum limitations.
Be able to answer: What assumptions drive the sustainability concern, and which
spending/policy decisions require human review?

### 21. Understand the application and submission artifacts

Trace saved results into Streamlit, the report, tear sheet, committee memo and
pitch. Explain hashes, provenance, Explore invalidation and the ETF comparison
page. Explain indexed charts versus adjusted USD prices and their actual dates.

Read: app.py; quanedge/results.py, reporting.py and verify.py; README.md;
results/final-20261027/documents/; scripts/chart_etf_prices.py.
Be able to answer: How do we keep every displayed recommendation tied to its inputs?

### 22. Prepare to defend the work

Practise a short explanation of the mandate, method, recommendation, main weakness
and monitoring action. Answer questions about weights, tail models, historical
knowledge, spending, reproducibility and AI use. Never claim personal independent
validation or organiser acceptance that has not occurred.

Read: results/final-20261027/documents/speaker_qa_notes.md,
committee_pitch_v2.pptx, investment_memorandum.pdf and executive_tear_sheet.pdf.
Be able to answer: What can go wrong, how bad could it become, how confident are we,
and what would make us change the recommendation?

## Learning progress and continuation

Status meanings: Not started; In progress; Explained, review needed; Owner can
explain. The last status requires the owner's demonstrated explanation and agreement.

| Topic | Status | Questions or notes |
|---|---|---|
| 1. Competition problem | Not started | |
| 2. Investment objective | Not started | |
| 3. Investment policy | Not started | |
| 4. Structure and AI contributions | Not started | |
| 5. Seven ETFs | Not started | |
| 6. Data sources | Not started | |
| 7. Adjustments and cleaning | Not started | |
| 8. Returns and accounting | Not started | |
| 9. Training and evaluation | Not started | |
| 10. Estimators and diversification | Not started | |
| 11. Portfolio construction | Not started | |
| 12. Performance | Not started | |
| 13. VaR and ES | Not started | |
| 14. Risk models | Not started | |
| 15. EVT | Not started | |
| 16. Conditional volatility | Not started | |
| 17. Backtesting | Not started | |
| 18. Stress and contributions | Not started | |
| 19. Recommendation | Not started | |
| 20. Spending sustainability | Not started | |
| 21. App and artifacts | Not started | |
| 22. Defence preparation | Not started | |

Next lesson: Topic 1. Brief earlier chat answers are not evidence that a full
lesson or an independent owner review has been completed.

At the end of a teaching session update here: date, topic, examples covered,
owner's questions, points needing clarification, and exact next step. Keep notes
short; do not record an entire transcript.
