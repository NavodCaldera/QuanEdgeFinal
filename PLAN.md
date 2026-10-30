# QuantEdgeFinal: competition plan

Solo-entry plan for the SAIFA Quant Edge 1.0 final challenge (Ghosted). The owner has confirmed the solo approach: one person builds, validates and defends everything. Do not divide work among five people or wait for teammates. AI assistants and review agents may help under the disclosure rules in section 9. `AGENTS.md` holds the build specification and the progress record; this file holds the competition facts, the policy choices and the ordered plan.

Status: final draft, 26 October 2026. Draft 1 was reviewed by two critics (a judge/committee view and a one-person-delivery engineering view) who critiqued each other's findings; section 17 records how their disagreements were settled. The owner's own ideas ("Quant Edge - thoughts") were then integrated and reviewed the same way by a second pair of critics; section 19 records them. An external audit on accounting, validation and decision rules was then applied after review by a third pair of critics (section 20).

## 1. Sources and precedence

| Rank | Source | Pages | Status |
|---|---|---|---|
| 1 | `Quant edge 1.0 Final Challenge 1.pdf` (Competition Brief, Oct 2026) | 10 | Authoritative. Wins every conflict. |
| 2 | `EDGEFORGE_Polished_Finance_First_Masterclass_2026.pdf` (+ PPTX with speaker notes) | 99 | Teaching material built from an earlier draft of the brief. Use for judging expectations, not rules. |
| 3 | `Advanced_Risk_Management_English_final.pdf` (+ PPTX) | 28 | Teaching deck (VaR, ES, EVT, copulas, wavelets). All numbers are synthetic. |

The three PDFs are committed at the repository root (the PPTX files stay outside the repository, in `Final competition/`). The brief's section numbering skips section 4 (3 is followed by 5); no text is missing.

## 2. The competition in brief

- **Event:** Quant Edge 1.0, a national STEM quantitative investment research competition for undergraduates in Sri Lanka, informed by the CFA Program curriculum.
- **Theme:** "From Portfolio Theory to Value at Risk, Expected Shortfall and Extreme Value Theory".
- **Core idea:** successful investing means sustainable returns while protecting capital and managing downside risk, not maximising return.
- **Format:** the brief says "teams of five"; this is a source requirement, not this project's staffing plan. The owner has chosen a solo entry. Request written organiser confirmation in phase 0 and resolve eligibility before submission. Preparation may continue while confirmation is pending; do not assume approval or convert the project into a five-person workflow.
- **Role:** we are the quantitative research division of an asset manager competing for a mandate.
- **Deadline:** not stated in the brief. Confirm with the organisers and record it in phase 0.

## 3. Client and mandate

**Client:** The Serendib University Endowment Fund, a conservative institutional investor; a long-term pool funding scholarships, research, faculty development and strategic capital projects. **Amount:** USD 10,000,000.

**Investment objective:** preserve and grow capital over the long term with a conservative risk profile; balance **capital preservation, income generation and sustainable real growth**, with particular emphasis on resilience in market stress.

**Investment Committee beliefs (quoted in the brief):**
- "Avoiding large losses is more important than maximizing gains."
- "A good investment decision is not the one with the highest expected return - it is the one whose downside you have actually measured, tested, and can defend."

**The application must:**
1. construct and recommend a portfolio from the prescribed universe using quantitative portfolio construction;
2. measure and compare risk with VaR, ES and EVT-based tail estimates;
3. validate the selected risk models through out-of-sample backtesting;
4. evaluate portfolio behaviour under historical and hypothetical stress scenarios;
5. deliver a clear recommendation supported by evidence, communicated through an investment committee memorandum.

Teams have full discretion over analytical approach, risk metrics, lookback period and construction method; the quality, transparency and justification of each decision is assessed. "The quality of the reasoning behind the recommendation is as important as the recommendation itself."

**Manager's responsibilities (each must be answered in the memo):**
1. Determine the investment horizon and asset allocation, and defend them. A single fund or any combination is allowed.
2. Set a return objective consistent with the mandate and risk tolerance.
3. Define and justify the risk constraints used in construction.
4. Show why the portfolio suits a conservative institutional investor.
5. Quantify the trade-off between return-seeking and risk reduction.
6. State the assumptions behind the recommendation.
7. Downside protection and tail-risk management.
8. Robustness under stress scenarios.
9. Optional: other macroeconomic, industry or market-specific risks and their impact.

**The committee requires demonstration of:** diversification benefits, robust risk measurement, tail-risk awareness, practical stress testing, resilience in crises.

**The committee will ask:** (1) what can go wrong, (2) how bad losses could become, (3) how confident we are in the risk estimates. A "three questions" page answers these in the memo, app and pitch (section 6).

## 4. Investable universe

| # | Ticker | Fund | Role |
|---|---|---|---|
| 1 | SPY | SPDR S&P 500 ETF | US large-cap equities |
| 2 | EFA | iShares MSCI EAFE | International developed equities |
| 3 | EEM | iShares MSCI Emerging Markets | Emerging-market equities |
| 4 | AGG | iShares US Aggregate Bond | US investment-grade bonds |
| 5 | GLD | SPDR Gold Shares | Gold / real asset |
| 6 | XLE | Energy Select Sector SPDR | Energy / commodities proxy (an equity sector, not oil futures) |
| 7 | XLK | Technology Select Sector SPDR | Technology sector |

Only these seven. No futures, options or FX overlays from the teaching decks. Treating the universe as excluding a cash sleeve is our reading of "eligible funds"; ask the organisers and state it as an interpretation. Long-only and full investment are our policy choices, not brief rules. GLD's first price is 18 Nov 2004; the frozen common sample starts on 3 Jan 2005, the first full year with all seven ETFs, so it covers the 2008 crisis but not 2000-02 (see the standalone context, CTX-001).

**Base currency:** USD (the mandate is USD and all funds are US-listed). Inflation is US CPI. Sri Lankan rupee exposure is out of scope and listed under Limitations.

## 5. Technology and the Streamlit app

Python is required for all analysis. Streamlit is the required interface: the point is something a non-technical committee can use, "not to produce a notebook".

**Mandatory app content (brief section 6):**
1. Sidebar: confidence level (90 / 95 / 99%), VaR methodology, backtest date range.
2. Portfolio panel: weights, cumulative return, drawdown chart.
3. Risk dashboard: VaR, ES and the EVT tail estimate side by side at the same confidence level, so the gap is visually obvious.
4. Backtesting panel: Kupiec and Christoffersen results and a traffic-light indicator.
5. Stress-test panel: portfolio impact under each crisis scenario.
6. A clearly labelled "Assumptions & Limitations" page in plain language. Non-negotiable and explicitly graded.

Plus our additions: recommendation / "three questions" page, candidate comparison, risk contributions, data provenance, and a fixed "Frozen recommendation" panel. Portfolio choice defaults to a dropdown of fully precomputed portfolios; free weights sit in a labelled "Explore" mode where expensive results show "unavailable - rerun required" (phase 6).

**Suggested free-tier toolkit:** pandas, NumPy, SciPy; statsmodels or arch; pyextremes or a hand-written GPD maximum-likelihood fit; matplotlib or Plotly; Streamlit Community Cloud or a university server. Free tools are a fairness requirement.

## 6. Deliverables

| # | Deliverable | Requirement | Brief |
|---|---|---|---|
| D1 | GitHub repository | Public, or private with judge access. Clean, documented, reproducible code; README explains how to run the app. | 7.1 |
| D2 | Streamlit application | Deployed, or runnable locally from the repository with one command. | 7.2 |
| D3 | Technical report / investment memo | 7-15 pages: methodology, data sources and cleaning, results, and explicitly assumptions and limitations. | 7.3 |
| D4a | Executive tear sheet | One page: recommended portfolio, risk metrics, recommendation; readable by a committee in under five minutes. | 7.4 |
| D4b | One-page committee memo | Plain English: accept the mandate as proposed / adjust the risk limit / reject, with the three questions, actions and triggers. | 8.6 |
| D5 | Live pitch (final five only) | 10-12 minutes with a deck, then Q&A where the judges act as the client's investment committee. | 7.5 |
| - | AI-use disclosure | Tools, purposes, human validation, material AI-generated components. Goes in the README and the memo. | 8.7 |

## 7. Technical framework: five required layers

Every layer is mandatory. How it is implemented (which VaR method, threshold rule, optimiser) is where innovation is judged.

**Layer 1, portfolio theory and KPIs.** Markowitz mean-variance construction and CAPM. Compute and interpret Sharpe, Sortino, Treynor, Jensen's alpha, Information ratio, maximum drawdown, Calmar ratio and similar.

**Layer 2, Value-at-Risk.** Historical simulation, parametric and Monte Carlo on the same portfolio at both 95% and 99%; explicitly discuss where the three disagree and why; evaluate model assumptions critically rather than applying techniques mechanically.

**Layer 3, Expected Shortfall.** Report ES with a rationale for using it in addition to VaR.

**Layer 4, EVT.** Advanced methods for extreme downside; how approaches perform under stressed market conditions; limits of conventional measures; what alternatives add for rare, severe losses. Threshold selection must be justified, not arbitrary.

**Layer 5, model validation.** Backtest the chosen VaR model out of sample with Kupiec proportion-of-failures, Christoffersen independence and the Basel traffic light. "A risk model that has not been tested against reality is an opinion, not a measurement."

**From metrics to decisions (8.6), graded on translation into actions:**
- Risk budgeting and position sizing from each position's marginal VaR/ES contribution.
- Stress tests: historical crisis paths (2008 GFC, March 2020 COVID crash, 2022 rate-hiking drawdown) plus one hypothetical scenario we design, with the portfolio impact.
- The one-page committee memo with an accept / adjust / reject verdict.

## 8. Data rules

**Approved sources only:** Yahoo Finance via yfinance (prices, dividend history); FRED (risk-free proxy such as the 3-month T-bill DTB3, CPI CPIAUCSL, 10-year yield DGS10, 10-year breakeven inflation T10YIE as a reasonableness check); World Bank / IMF open data (macro context for the memo). An undisclosed or proprietary source is a rubric violation; judges must be able to reproduce the data.

**Mandatory cleaning discipline:**
- Adjusted close prices, so dividends and splits do not distort returns.
- Align trading calendars before portfolio returns; document holidays and non-overlapping days.
- Log returns for statistical work; state where and why simple returns are used. Portfolio returns are aggregated across assets in simple returns, then converted to log.
- Flag, never silently delete, suspected errors: stale or flat prices, structural breaks, implausible jumps, large negatives. Document outlier handling.
- Run a stationarity check (at least ADF) on the return series used for modelling and report it.
- Every cleaning step reproducible from code. No manual edits to downloaded files.

**Our additions:** DTB3 is a discount-basis quote; convert to bond-equivalent yield before turning it into a daily rate. Adjusted prices hide income, so download dividend history separately for the yield KPI. Freeze raw downloads as dated snapshots with retrieval time and SHA-256 hash; the app never calls yfinance at runtime.

## 9. AI-use rules

AI may support implementation, debugging, research and software. Everything submitted must reflect our own judgement. Required disclosure (brief 8.7):

| Item | Example from the brief |
|---|---|
| AI tools used | Claude, ChatGPT, GitHub Copilot |
| Purpose | Debugging, Streamlit layout, code scaffolding, documentation |
| Human validation | How output was tested, checked and revised |
| Material AI-generated components | "Initial Streamlit dashboard structure was AI-assisted; risk calculations were independently reviewed and tested by the team." |

Obligations: disclose every tool and purpose; independently review, test and validate AI output; be able to explain the logic, assumptions and limits of everything; take full responsibility for accuracy and reproducibility; construction, risk interpretation, stress conclusions and the recommendation must be developed and defended by us. An AI-generated recommendation may not be presented as our own without independent evaluation. Judges may ask about any code or claim; failing to explain material work can reduce marks or disqualify.

Practical rules for one person: keep an AI-use log (date, tool, purpose, files, how checked) from day one. Code restored from commit e94c0ae was AI-assisted; disclose it as "prior AI-assisted code, reviewed, re-tested and rewritten where not understood".

## 10. Judging rubric and what it means for us

| Criterion | Weight | Assessed | Plan response |
|---|---|---|---|
| Investment decision-making | 30% | Sound, actionable, client-appropriate recommendation; depth across all relevant variables, including optional items | Policy and verdict rule fixed before testing; candidate table; macro add-on; three questions answered |
| Technical rigour & correctness | 25% | Correct KPIs, VaR, ES, EVT, optional macro variables, statistically sound backtesting | Conventions in section 15; independent checks; honest failures; no look-ahead; three evaluation labels (section 15) |
| Software & interface quality | 15% | Streamlit usability, front-end design, code structure, documentation, reproducibility | One-command pipeline; app reads frozen results; tests; README |
| Innovation & ambition | 15% | Well-justified extensions, e.g. regime-conditioned risk, risk overlays, alternative EVT threshold rules | Regime-conditioned (FHS) primary model; EVT threshold-rule comparison; reverse stress test |
| Communication & defence | 15% | Clarity of memo and pitch; answers under questioning | Three questions page; Q&A bank; every number checked by script |

The brief says the weighting is deliberate: technical correctness plus decision usefulness outweigh a polished but statistically wrong analysis.

## 11. Where the teaching material differs from the brief

| Topic | Masterclass / deck | Brief (wins) |
|---|---|---|
| Horizon | Three-year investment horizon | Not given; we must choose and defend it |
| Universe | Global equity, bond, commodity; optional FX and local exposure; futures examples | Seven listed ETFs only |
| Rubric | Draft: technical 30%, decision 25% (speaker notes) | Decision 30%, technical 25% |
| Name | Draft called it "Alpha Challenge" | Quant Edge 1.0 |
| Oil, futures, margin, wavelets, copulas | Worked examples | Not required; the notes call wavelets optional extensions |

**Lessons from the decks that judges are likely to test:**
- VaR is a threshold, not the maximum loss; ES is the average beyond it and is coherent (subadditive), VaR is not.
- Use the quantile-integral ES definition; simple conditional expectation needs care with ties.
- Fat tails, skew and clustering make normal models understate extremes; EVT models the far tail, but very high quantiles rest on few points with wide intervals. Positive xi means a heavy tail, not a crash probability.
- Choose EVT thresholds by diagnostics (mean excess, stability), not convenience.
- Correlation is an average; it can rise in crises. Copulas describe joint crashes; Gaussian copulas have no tail dependence.
- When models disagree, do not average: check units, horizon, calibration, assumptions and tail sample size.
- Kupiec tests frequency, Christoffersen tests clustering. The Basel traffic light is calibrated for 99% one-day VaR over 250 observations.
- Avoid leakage, test-set tuning, unrealistic implementation and missing walk-forward validation.
- Stress losses are conditional "what if" outcomes; a scenario limit can bind before VaR.
- Every parameter needs units, horizon, uncertainty and an action. "A credible recommendation can be 'reduce and reassess', not always 'buy'."
- Masterclass slide 79, what the committee should receive: allocation, performance, loss limit (VaR/ES in dollars), tail robustness, model trust (out-of-sample), governance (limits, rebalancing, caveats).

## 12. Current repository state and reuse (decision D-01)

On 26 October 2026 the working tree was stripped to `.gitattributes`, `.gitignore` and `AGENTS.md` (commit f3609a8, merged as b31b8d4). Commit e94c0ae holds about 4,000 lines of earlier AI-assisted Python and tests:
- `quanedge/data`: yfinance/FRED/World Bank ingestion, NYSE calendar audit, as-of macro alignment, DTB3 bond-equivalent conversion, anomaly logs, ADF/KPSS, SHA-256 manifest.
- `quanedge/risk`: historical, normal, Student-t, normal/t Monte Carlo, EVT with threshold scan, FHS, GARCH-EVT, exact dollar ES, block-bootstrap intervals, 750-day rolling forecasts.
- Missing: Kupiec/Christoffersen/traffic light, optimiser, stress module, app; `streamlit` is not in requirements. Hazards: placeholder equal weights (`settings.DEV_WEIGHTS`), a dev-cache price fallback (`dev_data.py`), a price snapshot with unknown retrieval time, "Person N" wording in `risk/run.py`.

**Decision:** restore only the modules that feed final outputs, each with its tests: `quanedge/data/*`, `risk/var_es`, `risk/evt`, `risk/portfolio`, `risk/validation`, `risk/rolling`, `risk/conditional` (FHS is the primary model), `risk/uncertainty` (confidence intervals), `pytest.ini`. Restore `diagnostics` and `plots` only when used. Rewrite `risk/run.py` and `config.py`. Do not restore `dev_data.py`, `DEV_WEIGHTS`, `docs/person-*` or `results/`. Weights become a required input file (a test fails the run without it). Re-download prices once through the pipeline and freeze the snapshot with its metadata and hash.

For every restored module: the owner writes a short summary of what it does, adds one hand-checked test, and can explain it without notes. Budget about one day of review per 1,000 lines.

## 13. Investment policy (owner-approved values, frozen in the decision log and tagged `prereg-v1` before any post-2016 result is computed)

**Mandate v1, superseded by section 13b on 30 October 2026; kept as the record of the `prereg-v1` run.** The values below are proposals until the owner approves them. Once tagged they are fixed; later changes are logged mandate changes and do not alter the verdict on the original mandate.

| Item | Policy | Notes |
|---|---|---|
| Investment horizon | Long-term (the endowment is perpetual); strategic review every 5 years | Defend with spending needs and intergenerational equity |
| Risk horizon | 1 trading day for VaR, ES and backtesting | Our choice, matched to the daily backtest. Multi-day views use overlapping historical returns, not square-root-of-time scaling |
| Return objective (hurdle h) | h = (1 + π*) / (1 - s) - 1, after costs and before spending; π* = 2.5% a year assumed US CPI inflation; s = 4% of NAV spent once a year; so h = 6.77% | Set from the spending need, not from the frontier, so it can genuinely fail. Compared with the expected geometric return. s and π* are stated assumptions (sensitivity π* 2% and 3.5%; T10YIE and trailing 10-year CPI growth reported as a check); conventions in section 15 |
| Binding risk budget | 1-day 99% ES of at most B = 2.5% of NAV (USD 250k), fixed | Measured as historical ES99 in dollars on the estimation sample of the weights being judged (the same sample as the optimiser's CVaR constraint). FHS conditional ES is a monitoring figure, not the budget test |
| Selection rule | Maximise expected arithmetic return subject to CVaR99 ≤ B and all constraints (Rockafellar-Uryasev linear programme, scipy `linprog` with HiGHS); tie-break by a second-stage minimisation of CVaR within 1e-8 of the optimum | Unique and reproducible. The optimiser ranks on arithmetic return; check C3 tests the geometric return (gap about σ²/2, roughly 0.3 points) |
| Constraints | Long-only, fully invested, zero weights allowed; AGG 25-70% (a diversified bond index, so exempt from the single-ETF cap); equity (SPY+EFA+EEM+XLE+XLK) at most 55%; any other single ETF at most 40%; GLD at most 15%; XLE and XLK at most 10% each | Constraint effects are measured by controlled re-solves (section 15), never by benchmark gaps. The AGG cap reflects rate-risk concentration (AGG lost about 13% in 2022) |
| Drawdown limit | 20%, checked after the fact on the GFC replay (verdict check C5) and reported on bootstrapped 1-year paths (not a gate) | Not an optimiser constraint (path-dependent, overfits one crisis) |
| Rebalancing | Quarterly, or when a weight drifts more than 5 points; cost 5 bp one-way per unit of turnover; ETF expense ratios are already in adjusted prices | Risk models and backtests assume daily rebalancing to constant weights; the label on every backtest states the mismatch |
| Governance | Drawdown 10% or a yellow backtest zone: review. Drawdown 15% or red zone: de-risk toward the minimum-CVaR de-risk portfolio | Escalation ladder for the memo. The de-risk portfolio is precomputed and validated with its own forecasts like any candidate |
| Benchmarks | 40/60 and 60/40 SPY/AGG; equal weight; permanent-portfolio-inspired SPY 25 / AGG 50 / GLD 25 (Browne 1987; AGG stands in for the long-Treasury and cash legs); unconstrained volatility risk parity | Outside policy, for comparison only, rebalanced quarterly, fixed in the decision log before results are seen. In-policy variant 35% equity / 50% AGG / 15% GLD. A cash-leg variant (DTB3) only if organisers confirm cash is eligible |

### 13a. Verdict rule (frozen with section 13 and tagged `prereg-v1` before any post-2016 result is computed)

**Original mandate (fixed):** the section 13 constraints, B = 2.5% of NAV, s = 4%, π* = 2.5%, drawdown limit 20%.

**Acceptance checks, all required, each computed for one weight vector with its own matching results:**
- **C1 feasibility:** the solver succeeded and every constraint holds within 1e-6.
- **C2 risk budget:** historical 1-day ES99 in dollars on the weights' estimation sample ≤ B (point estimate; bootstrap interval shown, not gating).
- **C3 return:** expected geometric annual return after costs ≥ h, from the frozen estimator.
- **C4 risk model:** the pre-named primary model at 99%, run on this weight hash's own sequential forecasts. The Basel zone on the last 250 forecasts is not red (yellow is disclosed and triggers the governance "review"). Kupiec and conditional-coverage p > 0.05 on forecasts from 2017 to the snapshot end. Forecasts exist for at least 95% of days. If the primary fails, the pre-named challenger is evaluated once; if both fail, the outcome is "evaluation incomplete: no validated risk model". A model failure never produces Adjust or Reject, because no change of weights or limits can fix it. Results for 2008-2016 and the share of red rolling 250-day windows are reported, not gating.
- **C5 stress:** worst historical-scenario loss and GFC replay drawdown both within 20%.

Shortfall probability, bootstrapped 1-year drawdowns, other models and other confidence levels are reported but do not gate (so no multiple-testing correction applies to the gate).

**Permitted adjustment set (fixed, finite, tried in this order; the first alternative that passes C1-C5 with its own forecasts wins):**
- **A1** the other pre-listed in-policy phase-2a candidates, in ascending training ES99 (minimum CVaR, minimum variance, near-parity risk budget, constrained maximum Sharpe): "adjust weights within the mandate".
- **A2** GLD cap raised to 20%, frozen procedure re-run.
- **A3** spending s lowered to 3.5% (the spending floor; h becomes 6.22%, and the fund spends USD 50k a year less).
- **A4** B raised to the lower of 3.0% of NAV and the 60/40 benchmark's training ES99, never below B (that number is computed and written into the log at freeze).
- **A5** A2, A3 and A4 together.

Risk is raised last, in line with "avoiding large losses is more important than maximizing gains". Long-only, full investment, the universe, the AGG range, the equity cap, the XLE/XLK and single-ETF caps and the 20% drawdown limit are not relaxable. Any change outside this set needs the owner's explicit, logged agreement.

**Decision, evaluated in order (exactly one outcome):**
1. **Evaluation incomplete** if any C1-C5 result for the portfolio being judged is missing, failed to compute or has insufficient forecasts. This blocks submission: fix it, or (for the risk-model case above) state it in the memo with an interim action. It is never shown to the committee as a bare status.
2. **Accept the mandate as proposed** if the recommended weights W_rec pass C1-C5.
3. **Adjust** if Accept fails and some A1-A5 alternative passes: name the first one, its weights and limits, and the check it fixes. A1 is "adjust the weights"; A2-A5 are "adjust the risk limit / spending".
4. **Reject** if every A1-A5 alternative was fully evaluated and none passes.

With h at 6.77% and equity capped at 55%, Adjust or Reject is a realistic outcome; prepare the dollar trade-off (each 0.5% of spending is USD 50k a year of scholarships).

### 13b. Mandate v2 (owner change, 30 October 2026, tagged `prereg-v2`; supersedes sections 13 and 13a)

The owner changed the mandate after reviewing the v1 run (`final-20261027`, verdict Adjust to SPY 15 / AGG 70 / GLD 15) and an exploratory run without ETF limits. Sections 13 and 13a stay as the record of mandate v1; its run, tag and verdict are unchanged. Mandate v2 is evaluated in its own run.

| Item | Mandate v2 policy | Notes |
|---|---|---|
| ETF limits | None. Long-only and fully invested in the seven ETFs; any single fund or combination | Owner decision. The AGG range, equity cap, gold cap, XLE/XLK caps and 40% single-ETF cap are removed |
| Trading cost | 0% | Owner assumption. Spreads and market impact are not modelled; the expected-cost reserve is zero |
| Cash reserve | Each 1 January, cash for the university's spending that year is withdrawn from the portfolio: USD 400,000 in year 1, then growing 3.64% a year (year 2 USD 414,560; year t USD 400,000 × 1.0364^(t-1)) | The reserve earns 0% and is paid out; it is not an investment and not part of the universe. Year 1 invests USD 9,600,000. Fixed real schedule (Ideas.md section 1), not a percentage of NAV |
| Inflation | 3.64% a year | Owner's figure, described as an average world inflation rate; its source, period and calculation are not yet verified. The client is USD-based, so US CPI remains the reference series in data |
| Return objective | 1-3% real a year: nominal target (1.0364)(1.03)-1 = 6.75%; acceptance floor (1.0364)(1.01)-1 = 4.68% | Compared with the expected geometric return from the frozen estimator. A 4%-of-initial real reserve exceeds this objective, so real capital is expected to decline |
| Selection rule | Minimise historical CVaR99 subject to expected geometric return ≥ the 6.75% target and CVaR99 ≤ B (Rockafellar-Uryasev LP, HiGHS); the smallest arithmetic floor meeting the geometric target is found by bisection. If minimum CVaR already meets the target, the target does not bind | Owner choice ("minimum tail risk, aim 3% real"). The v1 rule (maximise return within B) is kept as the `max_return` comparison candidate |
| Return estimator | Unchanged: sample means shrunk 50% toward the cross-asset mean; Ledoit-Wolf covariance | Owner kept it after being shown that it decides the outcome (see disclosure below) |
| Risk budget | Historical 1-day ES99 ≤ 2.5% of invested NAV (USD 240,000 at inception), on the weights' estimation sample | Kept by the owner |
| Drawdown/stress limit | 20%, GFC replay and worst historical scenario (C5) | Kept by the owner. Dollar limits use the USD 9.6m invested at inception |
| Risk model | FHS primary, GARCH-EVT challenger, unchanged | |
| Rebalancing, horizon, benchmarks | Unchanged from section 13 (benchmarks no longer have an "in policy" variant; the 35/50/15 mix is named `balanced_35_50_15`) | |

**Checks (v2):** C1 feasibility; C2 ES99 ≤ B; C3 expected real geometric return ≥ 1% (nominal ≥ 4.68%); C4 risk model, unchanged; C5 stress, unchanged.

**Adjustment set (v2, in order):** A1 the other candidates (minimum CVaR, minimum variance, risk parity, maximum Sharpe) in ascending training ES99; A2 B raised to the frozen training value (lower of 3.0% of NAV and the 60/40 training ES99, never below B). The reserve schedule and the 1% real floor are client needs and are not relaxed. The decision order (incomplete, Accept, Adjust, Reject) is unchanged.

**Spending evidence (not gating):** 25-year joint 12-month block bootstrap reporting the share of paths that pay every reserve in full, depletion year, real balances and the share preserving the initial USD 10m in real terms.

**Disclosure before the tag:** full-sample results were seen before `prereg-v2`. An exploratory run without ETF limits (AGG 50 / GLD 22 / XLK 28 at a 2.0% ES budget, which failed C4 with 40 FHS breaches against 24.5 expected) was shown to the owner. While choosing the estimator, the owner was also shown that under v2 the frozen estimator selects about SPY 6 / AGG 88 / GLD 6 (about 3.5% real expected, but about 0.25% real on raw historical means). Raw means would select about AGG 65 / GLD 17 / XLK 18. The owner kept the frozen estimator. No v2 backtest (C4) was computed before the tag.

### 13c. Mandate v3 (owner change, 30 October 2026, tagged `prereg-v3`; amends section 13b)

**Universe:** the portfolio may hold only SPY, AGG, GLD and XLE; EFA, EEM and XLK are held at zero. Every other v2 rule is unchanged (no percentage limits, zero cost, 1 January cash reserve, 1-3% real objective, minimum-CVaR selection with a 3% real target, ES and stress limits, checks C1-C5, adjustments A1-A2, FHS and GARCH-EVT).

**Owner's reason and the evidence:** lower correlation between the holdings. Daily return correlations, 2005-2026: SPY with EFA 0.88, EEM 0.82, XLK 0.91, so those three add little beyond SPY. XLE is the least SPY-correlated equity ETF but is not low-correlation with SPY: 0.70 daily, 0.60 monthly, 0.76 on SPY's worst 5% of days. AGG and GLD are the diversifiers: 0.00 and 0.07 with SPY daily, 0.21 with each other. Correlation is measured on the full sample and is not stable across regimes (the SPY-AGG sign changes, PLAN.md section 20 and PORT-007).

**Disclosure before the tag:** the v2 run (final-v2-20261030) was already seen. The v2 selection already held only these four ETFs, and a pre-tag check confirmed that v3 selects the same weights (SPY 5.8 / AGG 88.0 / GLD 6.0 / XLE 0.2), so the same risk-model result is expected. The comparison candidates change (for example, maximum Sharpe becomes about SPY 13 / AGG 79 / GLD 8.5).

### 13d. Candidate v4c: risk parity plus volatility overlay (pre-registered 30 October 2026, before its run)

A candidate for a possible mandate v4, not a mandate change. The v3 policy, run (final-v3-20261030) and verdict (evaluation incomplete) stay as recorded. Everything below was fixed and committed before any overlay path on these weights was computed.

| Item | Fixed choice |
|---|---|
| Base weights | The v3 run's `A1_near_parity` weights, full-sample estimate: SPY 14.03 / AGG 60.87 / GLD 16.25 / XLE 8.85, weight hash ece535c3 |
| Overlay | `quanedge.hedging.vol_target` with PORT-004 settings unchanged: EWMA lambda 0.94, weekly review, 5-point minimum change, 252-day minimum history, scale = min(1, expanding vol / EWMA vol) on the equity sleeve (SPY, XLE). Under v3 there are no caps, so freed weight goes to AGG |
| Policy | v3 config as tagged `prereg-v3`: USD 9.6m invested, 0% cost, quarterly plus 5-point drift rebalancing, FHS primary and GARCH-EVT challenger (window 750, refit 21) |
| Evaluation | 2017-01-01 to 2026-09-30; forecasts carry a strategy hash (base weight hash plus overlay settings) |
| C1 | Every overlay target is long-only, fully invested and inside the four-ETF universe |
| C2 | Base weights' estimation-sample ES99 and the overlay path's realised ES99 both at or below 2.5% |
| C3 | Base expected geometric return minus the overlay's realised log-return drag against static parity; real return at 3.64% inflation at least 1% |
| C4 | `model_pass` for FHS or GARCH-EVT at 99% on the overlay path's own forecasts |
| C5 | Overlay path from each scenario start (GFC, COVID, Rates 2022): loss at most 20% of value and GFC drawdown at most 20% |
| Descriptive only | Walk-forward (yearly near-parity weights on earlier data, then the overlay), 25-year reserve survival, daily-path replay of the 11 crisis windows in PORT-010, turnover, comparison with static parity and W_rec |

**Outcome rule:** if C1-C5 all pass, the result reads "would be Accept under v3 criteria for this candidate". It does not replace the v3 verdict; adopting it needs a new owner-logged mandate v4. If any check fails, the failure is the result. The base weights, overlay settings and windows are not retuned in response.

**Seen before this registration:** the v3 static near-parity results (FHS 33 breaches vs 24.5 expected, conditional coverage p 0.009, GFC drawdown 18.1%), the PORT-010 crisis replay, and PORT-005 (the same overlay on the v1 selection passed C1-C5). The overlay was designed after 2008 had been seen. Several weighting methods have been compared, so a pass is after multiple tries.

**Result (run results/parity-overlay-r1, PORT-011):** C1, C2, C3 and C5 pass; C4 fails, so the outcome is "evaluation incomplete", the same as v3. FHS 37 breaches vs 24.5 expected (Kupiec p 0.018, conditional coverage p 0.0005); GARCH-EVT 30 (Kupiec p 0.28, independence p 0.0004). The overlay made clustering worse, not better (static parity: FHS conditional coverage p 0.009, GARCH-EVT 0.011). Breaches bunch in 2018, 2020, 2024 and 2025 on the first days of sudden shocks, before a weekly reaction can act. Per the outcome rule, nothing is retuned.

## 14. Work plan

Fix phase timeboxes as shares of the time left once the deadline is known. Two milestones are hard: the **thin slice** at about 15% of the time and the **minimum viable submission** at about 60%.

### Phase 0: setup and decisions (day 1)
- Request written organiser confirmation of solo eligibility and the deadline; record confirmed or pending status in AGENTS.md section 17. Continue solo preparation while eligibility is pending, but require confirmation before submission.
- Ask whether a cash sleeve counts as eligible.
- Python environment, pinned `requirements.txt` (with streamlit and plotly), package skeleton, `pytest`.
- Execute D-01 (section 12). Start the AI-use log and the decision log.
- **Done when:** `python -m pytest` passes on the restored modules, the deadline is recorded and solo eligibility status is explicitly recorded. Pending eligibility remains an open submission dependency, not a teammate dependency.

### Phase 1: data
- Fresh snapshot: adjusted prices and dividends for the seven ETFs; DTB3, CPIAUCSL, DGS10 from FRED.
- Pipeline rebuilds clean data from snapshots with one command; quality logs; ADF per asset and for the portfolio.
- **Done when:** clean data rebuilds offline from snapshots and tests cover the return identity and calendar handling.

### Phase 1.5: thin end-to-end slice (milestone, about 15% of the time)
Snapshot data → provisional policy weights → historical VaR/ES → Kupiec → one stress replay → `results/<run_id>/` → a stub app with all six mandatory pages, including Assumptions & Limitations.
- **Done when:** one command produces a run folder and the app opens on it.

### Phase 2a: portfolio construction on training data (Layer 1), then freeze
- Expected returns with shrinkage or a CAPM equilibrium view (state which; the cost rule in section 15 depends on it); sample and shrinkage covariance; correlations.
- Efficient frontier under policy; the recommended portfolio comes from the section 13 selection rule. Other candidates (the A1 list): minimum CVaR (also the governance de-risk portfolio), minimum variance, constrained risk-budget portfolio (volatility equal risk contribution solved in scipy, reported as "near-parity" with its risk-contribution dispersion), constrained maximum Sharpe; plus the benchmarks (section 13).
- KPIs, defined in section 15, including distribution yield.
- Training-only candidate table: expected arithmetic and geometric return versus h, volatility, ES99 USD, maximum drawdown, worst stress USD, distribution yield, diversification ratio and its ES analogue, constraint effects (controlled re-solves, section 15), and "each +1% expected return costs USD X of ES99".
- Freeze: write the selection procedure (objective, estimators, constraints, solver, tie-break), the section 13 values, the 13a checks and adjustment set, and the primary and challenger risk models into the decision log; commit and tag `prereg-v1`.
- **Done when:** weights are feasible, KPIs match hand calculations, the trade-off is quantified, and the tag exists with values matching the config.

### Phase 2b: weights and retrospective columns (after the tag)
- From the same frozen procedure: **W_train** on 2005-2016 and **W_rec**, the recommendation, on all data to the snapshot end; also every A1-A5 alternative and the de-risk portfolio. Each is stored as a canonical weight file (6-decimal weights summing to exactly 1, any rounding residual on the largest weight) with a SHA-256 weight hash and an effective date.
- Retrospective evaluation, 2017 to snapshot end (labelled retrospective, section 15): money-weighted return under the spending rule and time-weighted CAGR, both against the realised-inflation hurdle; time under water (peak to trough, trough to recovery, "not recovered by [date]" where the sample ends first).
- **Done when:** all weight files and hashes exist and the retrospective columns carry their label.

### Phase 3: risk measurement (Layers 2-4)
- VaR at 90/95/99%: historical, parametric normal (Student-t as a variant), Monte Carlo with multivariate t as the primary simulation. Normal Monte Carlo converges to the corresponding analytical calculation only when both use the same distribution, parameters and portfolio accounting; joint normal asset log returns aggregated through simple returns need not give normal portfolio log returns, so a gap from the portfolio-level normal fit is a model difference, not an error. Basic convergence check: a matching one-asset case.
- ES for each, with dollar ES averaged from dollar losses.
- EVT: peaks over threshold with GPD; threshold from mean excess, parameter stability and goodness of fit; compare at least two threshold rules (innovation).
- Disagreement analysis: why methods differ (fat tails, sample extremes, distribution assumptions).
- Stress-eve views: models fitted on data up to 1 Sep 2008 and 19 Feb 2020 versus realised losses (Layer 4 "performance under stressed conditions").
- Uncertainty: block-bootstrap intervals; EVT shape interval.
- **Done when:** every model matches independent calculations on known distributions and the risk table states units, basis and status.

### Phase 4: validation (Layer 5)
- Primary and challenger models are named at the `prereg-v1` tag. Proposal: FHS at 99% primary, GARCH-EVT challenger; the owner confirms or swaps them before the tag. Disclose that the e94c0ae equal-weight development forecasts were seen before this choice: at 99% over 4,719 days, FHS had 65 breaches against 47.2 expected (Kupiec p ≈ 0.014, a fail) and GARCH-EVT 52 (p ≈ 0.49).
- Rolling one-day forecasts: 750-day window, refit every 21 days, EVT threshold re-chosen inside each window, no future data.
- **One forecast set per allocation.** Every weight vector that is reported, benchmarked or recommended gets its own rolling forecast file with its weight hash in every row; backtest functions refuse a file whose hash differs from the portfolio evaluated. The app, memo and verdict show W_rec's own results, labelled "sequential risk forecast; allocation chosen with data through [snapshot end]". W_train's results sit beside them as evidence that the procedure was not tuned to 2017 onward; they never stand in for W_rec. A revised allocation (including any Adjust alternative) shows "not evaluated" until its own forecasts exist.
- **Walk-forward procedure check (core).** Re-run the frozen procedure each January from 2017 on data to the previous 31 December and hold the weights for the year. This is the only historically investable record, labelled "walk-forward procedure evaluation".
- **Untouched data.** No untouched historical period exists: all data to 2026-09-30 was used in the e94c0ae development runs. Returns after the frozen snapshot are fetched once, after the final run is tagged, into a separate dated snapshot, and shown only as "post-snapshot monitoring, n days, descriptive" with the exact binomial probability of the breach count and no traffic light.
- Kupiec, Christoffersen independence, conditional coverage; traffic light at 99% on the last 250 forecasts and on rolling 250-day windows; binomial p-values at 90/95%.
- **Done when:** tests reproduce known breach sequences, edge cases pass, a future-data perturbation test shows no look-ahead, and a mismatched weight hash is refused.

### Phase 5: stress, macro and risk budgeting (8.6)
- Historical replays, buy-and-hold, SPY peak to trough: GFC 9 Oct 2007 - 9 Mar 2009; COVID 19 Feb - 23 Mar 2020; rate shock 3 Jan - 12 Oct 2022.
- Hypothetical: stocks and bonds falling together (inflation shock), for example SPY -25%, AGG -10%, GLD 0%, other assets filled in by conditional mean under a stressed covariance.
- Reverse stress test: the smallest shock that breaches the 20% drawdown limit.
- Per-asset impact, largest contributors, policy-limit breaches.
- Macro add-on (half a day, core): rolling 252-day SPY-AGG correlation showing the 2022 flip; portfolio sensitivity to DGS10 changes.
- Diversification in stress (owner's idea, core): co-exceedance, the share of SPY's worst 1% days on which AGG and GLD also lost, against each asset's base rate of losing days with a binomial interval; ES diversification benefit in USD: the sum of each position's standalone dollar ES (each with its own worst-tail selection, same scenarios and confidence) minus portfolio dollar ES, non-negative by subadditivity. This is not the component decomposition, which uses one shared tail.
- Real-capital survival (core, about 1 day): monthly asset simple returns and monthly CPI ratios resampled jointly in non-circular 12-month blocks, each block one simulated year; 10,000 paths, fixed seed; quarterly rebalancing at the stated cost; spending applied once at each block end per section 15. Report the probability that NAV after spending ends below the real-capital target USD 10m × CPI_T / CPI_0 at 5 and 10 years, and the median real surplus or shortfall against that same target, with Monte Carlo standard errors. Spending is never added to the target. W_rec plus the 40/60 and permanent-portfolio benchmarks; labelled illustrative (about 260 months of history; the blocks include the retrospective period). Fallback if time runs out: the deterministic comparison of expected geometric return after costs with h.
- Component ES as the primary risk allocation, from joint historical scenarios with multivariate-t Monte Carlo as a check, labelled "historical attribution". FHS, the primary backtest model, is fitted to portfolio returns and reports attribution as unavailable; the memo states that the budget is the policy measure (unconditional ES) and FHS is the monitoring and backtest model. Parametric Euler VaR as a cross-check; risk budget versus capital weight; resulting allocation changes.
- **Done when:** every stress scenario reports return, USD loss and attribution; asset ES contributions from joint scenarios sum to the matching portfolio dollar ES using identical tail weights, including fractional boundary mass and ties. Negative contributions remain visible; portfolio-only models without consistent joint asset scenarios explicitly report attribution as unavailable.

### Phase 6: full app
- All six mandatory elements plus recommendation, candidate table, risk contributions and provenance.
- App reads frozen `results/<run_id>/`. Portfolio choice defaults to a dropdown of precomputed portfolios (W_rec, W_train, the A1-A5 alternatives, the de-risk portfolio and the benchmarks), all with matching results. Free weights live in a labelled "Explore" mode.
- Result states (AGENTS.md section 13): each panel either loads precomputed results whose key matches all material inputs, computes a cheap result live for exactly these inputs (labelled "computed in app, not part of frozen run"), or shows "unavailable - rerun required" with the command. Cheap: weights, replay return and drawdown, KPIs, historical/normal/t VaR and ES, small fixed-seed Monte Carlo, stress replays, historical component ES. Expensive (precomputed or unavailable only): rolling forecasts, Kupiec/Christoffersen/traffic light, bootstrap intervals, EVT threshold uncertainty, the real-capital bootstrap, the walk-forward check and the verdict. The traffic light shows colour only for a matched result, otherwise grey with its label.
- A separate fixed "Frozen recommendation" panel always shows W_rec, its weight hash, run ID, verdict and traffic light, whatever the sidebar says.
- `streamlit.testing.AppTest` smoke test.
- **Done when:** `streamlit run app.py` works from a fresh clone; editing any weight in Explore mode turns the backtest, intervals and verdict to "rerun required", and returning to W_rec restores the matched results (AppTest).

### Phase 7: minimum viable submission (milestone, about 60% of the time)
- Memo v1 (D3), tear sheet (D4a), one-page committee memo (D4b), AI disclosure, README, full app.
- Memo additions from the owner's ideas: an "alternatives considered" paragraph (pairs trading and market-neutral rejected, section 19); one figure of rebalanced versus buy-and-hold returns over 2017 to the snapshot end after costs (retrospective), labelled as a policy cost/benefit, not alpha; a sidebar mapping the five capital-budgeting steps onto the investment policy statement and the pipeline.
- Pitch deck outline (12 slides mirroring D4b) and the Q&A bank.
- **Done when:** a complete, submittable package exists.

### Phase 8: innovation (only after phase 7)
- Already in core and credited as innovation: FHS / GARCH-EVT regime-conditioned forecasts as the backtested model; EVT threshold-rule comparison; reverse stress test.
- Stretch: regime-conditioned risk budget (calm vs stress weights); ES-based equal risk contribution (cvxpy, 1-1.5 days); drawdown-control overlay within the seven ETFs. (The spending-sustainability analysis moved into phase 5 as the shortfall-against-hurdle test.)

### Phase 9: final run, documents and defence
- Lock config; one command `python -m quanedge.pipeline --config config/final.yaml` writes `results/<run_id>/` with input hashes, weight hashes, git SHA and package versions; the pipeline refuses data dated after the snapshot end. Tag the commit `final-run-<run_id>`, then fetch the post-snapshot monitoring data (phase 4).
- Generate memo and tear-sheet tables and figures from the run; a script checks every number in the documents against it.
- Fresh clone → install → pipeline → app. Deploy to Streamlit Community Cloud if practical; confirm judges can access the repository.
- Full pitch deck after the shortlist; rehearse the Q&A bank.

**Cut list (first to go if time runs short):** World Bank context, KPSS, multi-day views, ES-based risk parity, simulated-null and Forbes-Rigobon conditional correlations, the DTB3 cash-leg benchmark, the second alternative optimiser, extra EVT threshold rules, the real-capital bootstrap (fall back to the deterministic hurdle comparison), the T10YIE reasonableness check, Holm-adjusted p-values for descriptive models, deployment (local one-command run is allowed). Never cut: the six app elements, the three questions, the macro add-on, formal backtests of W_rec's own forecasts, the walk-forward procedure check, the verdict rule and freeze tag, the hurdle test, the permanent-portfolio benchmark, time under water.

## 15. Technical conventions (defence-critical)

- **Evaluation labels.** Every result carries exactly one. (1) *Retrospective portfolio evaluation*: how a fixed allocation would have performed historically. The owner has seen all of 2005-2026 and the policy was written knowing 2008, 2011-2015 and 2022, so any replay of any weights is retrospective, even when the optimiser saw only 2005-2016. (2) *Sequential risk-forecast evaluation*: each day-t forecast for a stated weight vector uses only returns to t-1; the label states the allocation's data cut-off ("allocation chosen with data through D") and the daily-rebalanced replay. (3) *Untouched evaluation*: data excluded from policy, allocation and model selection; here only post-snapshot returns qualify (phase 4). The brief's "out-of-sample backtesting" is met by label (2). "Genuinely out of sample" is not used. A portfolio never inherits another portfolio's traffic light.
- **Inflation:** π over [t0, t1] = CPI_t1 / CPI_t0 - 1 from CPIAUCSL index levels; annualised (CPI_t1 / CPI_t0)^(12/m) - 1 over m months. The CPI level is never used as a rate. The forward hurdle uses the assumed π*; retrospective comparisons use realised π.
- **Costs:** adjusted closes are already net of each ETF's expense ratio, so it is not deducted again from historical returns. Expected returns built from historical ETF returns are net; a CAPM-equilibrium view built from index premia is gross, so subtract the weighted expense ratio (a config assertion names which applies). Extra cost c is rebalancing at 5 bp one-way per unit of turnover. "After costs" means after c, and every return compared with h is after costs.
- **Spending:** s = 4% of NAV once a year, at each anniversary, after that year's returns and costs: NAV_y = NAV_{y-1} × (1 + R_y,net) × (1 - s), draw D_y = s × NAV_{y-1} × (1 + R_y,net). Real endowments smooth spending (for example a 12-quarter average); listed under Limitations.
- **Hurdle:** h = (1 + π*) / (1 - s) - 1, after costs and before spending; 1.025 / 0.96 - 1 = 6.77%. It is the exact break-even: (1 + R_net)(1 - s) ≥ 1 + π if and only if R_net ≥ h. h is a compound rate, so compare it with the expected geometric return (exp of the mean annual log return, minus 1, or about μ - σ²/2), never the arithmetic mean; the candidate table shows both.
- **Real-capital target:** Target_T = USD 10m × CPI_T / CPI_0, compared with NAV_T after the year-T draw. Shortfall probability = P(NAV_T < Target_T); median real surplus = median(NAV_T × CPI_0 / CPI_T) - USD 10m, in today's dollars.
- **Losses:** positive L is a loss; L = -log(1 + R_p), with R_p the weighted sum of asset simple returns.
- **VaR / ES:** VaR is the loss quantile; ES is the quantile integral over [a, 1] divided by 1 - a, with fractional mass at ties; dollar ES averages dollar losses.
- **Kupiec / Christoffersen:** use 0·log 0 = 0 for zero breaches or no consecutive breaches, with tests; conditional coverage against chi-squared with 2 degrees of freedom.
- **Traffic light:** 250 days at 99%: green 0-4 exceptions, yellow 5-9, red 10 or more; also shown on rolling 250-day windows. At 90% and 95%, show "Basel zones not applicable" and the exact binomial p-value.
- **EVT at 90%:** if the selected threshold sits above the 90th percentile, the GPD tail does not cover 90%; show the empirical-body estimate and flag it.
- **KPIs:** SPY is the CAPM market for beta, Treynor and Jensen's alpha; Information ratio against the 40/60 benchmark (tracking error stated); Sortino with a 0% target and downside deviation over all days; Calmar = CAGR / |MDD| over a stated window; annualise from simple returns; DTB3 converted to bond-equivalent yield, then daily.
- **Component risk (dollar ES):** for each joint historical day or simulated scenario s, asset dollar loss is `-V * w_i * R_i,s`, using simple returns, and portfolio dollar loss is the sum across assets. Select the worst portfolio-loss scenarios with probability mass exactly `1-alpha`, including fractional boundary observations, and normalize the selected masses to tail weights summing to one. Allocate remaining mass at a tied boundary proportionally to the tied scenarios' original probabilities (equally for equally probable scenarios). Average every asset's losses with these same tail weights. Asset contributions must sum to portfolio dollar ES computed from the same scenarios and tail weights, not to log-unit ES or a separately fitted model's estimate. Negative contributions are valid and must not be clipped. Attribution requires joint asset scenarios: a portfolio-return-only model cannot provide asset contributions by itself. Test reconciliation, fractional tail counts, ties, negative contributions and unavailable attribution; see AGENTS.md section 11 for the formula contract.
- **Diversification ratio:** DR = Σ w_i σ_i / √(w'Σw) (Choueifaty-Coignard), same covariance and window as the optimiser; tests: one asset gives 1, N equal-volatility uncorrelated assets at equal weight give √N.
- **Money-weighted return:** XIRR (actual/365) of -USD 10m at the start, +D_y at each anniversary and +NAV at the end date (before any draw on that date). Draws are investor cash flows, so it is compared with the realised-inflation hurdle h_real = (1 + π_ann) / (1 - s) - 1 on the same after-cost basis, as is time-weighted CAGR. Tests: a constant annual net return R with draws gives an IRR of exactly R; no draws gives IRR = CAGR. Never computed from expected returns.
- **Constraint effect:** solve A = the frozen procedure under the original constraints; solve B = the identical setup with one limit changed (GLD 15% → 40%, where the single-ETF cap takes over, with 20% and 25% also shown; equity 55% → 65%, 60% as sensitivity; AGG floor 25% → 0%; AGG cap 70% → 100%; B 2.5% → 3.0%). Hold everything else fixed: training data, the same scenario matrix (identical rows), estimators, costs, objective, solver and tolerances. Report the change in the objective, expected arithmetic and geometric return, ES99 in USD, the weight changes, whether the limit binds in A (if not, the effect is exactly 0), and the linear programme's dual value as a local cross-check. Call it the "estimated effect of relaxing the [X] cap (in-sample, estimator-dependent)". A gap between the recommendation and a benchmark such as the permanent portfolio is an overall comparison and isolates no constraint.
- **Time under water:** trading days from the pre-crisis peak to the trough and from the trough back to that peak; "not recovered by [date]" if the sample ends first.
- **Volatility risk parity:** test w ∝ 1/σ for a diagonal covariance and equal contributions within 1e-6.

## 16. Risks and Q&A bank

| Risk | Mitigation |
|---|---|
| Solo entry not eligible | Request written confirmation in phase 0; preparation can continue, but resolve eligibility before submission. Do not assume approval or change the solo workload |
| Unknown deadline | Confirm immediately; timebox phases as shares of time left |
| App arrives last | Thin slice at 15%, minimum viable submission at 60% |
| Overfitting the allocation | Frozen, tagged procedure; W_train (2005-2016) shown beside W_rec; walk-forward procedure check; every replay labelled retrospective |
| Verdict tuned after seeing results | Section 13a checks, adjustment set and values frozen at `prereg-v1` before any post-2016 result |
| App showing results for the wrong weights | Results keyed by weight hash; expensive panels "rerun required" until matched; separate frozen-recommendation panel |
| EVT instability | Threshold sensitivity, minimum exceedances, visible failures |
| Look-ahead | Future-data perturbation tests; in-window threshold choice |
| Numbers drift between app and documents | One frozen run feeds everything; checker script |
| Defending AI-written code | Restore only what is used; owner summaries and hand tests; disclosure |
| yfinance blocked on Streamlit Cloud | App reads frozen results only |

**Questions to prepare with numeric answers:** Why not 100% AGG or minimum variance? AGG lost about 13% in 2022 alongside equities; what protects the fund? Why a 1-day VaR for a perpetual fund, and how many 99% breaches per year should the committee expect (about 2.5)? What does a GFC repeat cost in dollars, and in years of scholarships? Why USD and US CPI for a Sri Lankan endowment? How is EVT shown at 90%? What happens when a limit is breached? Who chose the weights, you or the AI? What costs and expense ratios are assumed? Why does the primary model differ from the simplest one? Why cap gold at 15% when the permanent portfolio holds 25% (no income, a drawdown of about 45% in 2011-2015, single-commodity concentration, and the estimated effect of relaxing the gold cap from the controlled re-solve)? Why not pairs trading or market-neutral (section 19)? Is gold negatively correlated with stocks (no: roughly uncorrelated, which still diversifies)? Is 2017 onward really out of sample (no: the allocation evaluation is retrospective; the risk forecasts are sequential; here is the walk-forward check)? Why trust FHS when it failed Kupiec in the development runs (the disclosed evidence and the pre-named challenger)? Your budget comes from a model you did not backtest? (The budget is the policy measure, unconditional historical ES; FHS is the monitoring and backtest model; both are reported.) Why 6.77% and not CPI + 4% (spending comes out of a grown NAV, so the rates compound)?

## 17. Review record: how the critics' disagreements were settled

| Issue | Judge view | Engineer view | Decision |
|---|---|---|---|
| Drawdown limit | Hard policy limit | Ex-post check only | Not in the optimiser; a pass/fail test in the verdict rule |
| ES test in verdict | Strict | Point estimate; intervals would always force Adjust | Point estimate, interval shown beside it |
| Backtest weights | Training weights out of sample | Today's weights (bank practice) | Superseded (section 20): each allocation has its own sequential backtest; W_rec's results drive the app and verdict, W_train's are supporting evidence |
| Restoring old code | Only what feeds outputs | Restore all with tests | Only what feeds outputs, each reviewed and hand-tested |
| Pitch deck | Skeleton before submission | After shortlist | Outline and Q&A before submission; full deck after shortlist |
| AGG cap | 25-70% | At least 25%, no cap | Revised in the second review: AGG 25-70%, exempt from the 40% single-ETF cap (the first version capped AGG at 40% by accident, which forced at least 45% equity) |
| Macro | Core, including CPI betas | Half day; CPI regression too thin | Half-day core: rolling stock-bond correlation and DGS10 sensitivity |
| Spending Monte Carlo | Innovation #1 | Stretch | Superseded: core real-capital survival test (phase 5) |

## 18. Requirement checklist

- [ ] Solo eligibility and deadline confirmed in writing
- [ ] Horizon, allocation, return objective, risk constraints defined and defended
- [ ] Suitability for a conservative investor shown; income (yield) reported
- [ ] Return vs risk trade-off quantified (candidate table, controlled constraint effects)
- [ ] Assumptions stated
- [ ] Markowitz + CAPM; Sharpe, Sortino, Treynor, Jensen, IR, MDD, Calmar
- [ ] Three VaR methods at 95% and 99%; disagreement explained
- [ ] ES with rationale
- [ ] EVT with justified threshold; stressed-period performance
- [ ] Sequential risk-forecast Kupiec, Christoffersen and traffic light for the recommended weights (own forecast file); walk-forward procedure check; evaluation label on every result
- [ ] Marginal/component VaR/ES risk budgeting and position sizing
- [ ] Three historical stresses + one hypothetical (+ reverse stress)
- [ ] Optional macro risks (stock-bond correlation, rates)
- [ ] Policy values, checks C1-C5 and adjustment set A1-A5 frozen and tagged `prereg-v1` before post-2016 results; verdict computed by the 13a rule
- [ ] App: precomputed-portfolio dropdown, result states keyed by weight hash, frozen-recommendation panel
- [ ] App: sidebar, portfolio, risk dashboard, backtest, stress, Assumptions & Limitations
- [ ] Data rules: adjusted close, calendars, log returns, flags, ADF, reproducible
- [ ] Repo, one-command app, 7-15 page memo, tear sheet, one-page committee memo, pitch deck
- [ ] AI disclosure
- [ ] Three questions answered: what can go wrong, how bad, how confident
- [ ] Owner's ideas (section 19): hurdle test, permanent-portfolio benchmark, risk parity, co-exceedance, time under water, alternatives considered

## 19. Owner's ideas ("Quant Edge - thoughts")

Source: the owner's Google Doc, which lists diversification techniques and four NIBM "Session 5" capital-budgeting slides. The owner is recorded as the originator of these ideas in the decision log, which is evidence for brief 8.7 that the analysis is our own. They earn marks under investment decision-making ("alternatives considered"), not innovation. Budget: about 2 days of core work inside phases 2, 5 and 7; no new phase.

The owner's guiding caveat goes into the memo word for word: buying negatively correlated assets can reduce losses, but it does not guarantee a profit.

| Idea | Decision | Where | Core / cut |
|---|---|---|---|
| Negative-correlation diversification | Adopt, stated honestly: within the seven ETFs, GLD is roughly uncorrelated with stocks and AGG's correlation depends on the regime (it turned positive in 2022). Measured by co-exceedance on SPY's worst 1% days against base rates, ES diversification benefit in USD, and diversification ratio | Phases 2 and 5 | Core; simulated-null and Forbes-Rigobon conditional correlations are cut-list |
| Modern Portfolio Theory | Already required (Layer 1) | Phase 2 | Core |
| Risk parity | Adapt: volatility equal risk contribution, constrained by policy ("near-parity", dispersion reported) as a candidate; unconstrained version as a benchmark | Phase 2 | Core; ES-based parity is stretch |
| Pairs trading | Reject: short positions carry borrow cost, margin and unbounded loss unsuited to a loss-averse committee; no stable cointegrated pair among seven ETFs (pairs are factor bets such as SPY/XLK); turnover breaks the static-weight backtest. Long-only cousin kept: rebalancing sells relative winners, shown as rebalanced versus buy-and-hold after costs | Phase 7 memo | Memo text plus one figure |
| Market-neutral investing | Reject: removes the market return the fund needs; earns roughly cash minus costs, below the hurdle h. The low-beta alternative is the existing minimum-variance candidate | Phase 7 memo, Q&A | Memo text only |
| Permanent portfolio | Adapt as a benchmark: SPY 25 / AGG 50 / GLD 25 (Browne 1987; no long-Treasury or cash fund in the universe), outside policy, plus in-policy 35/50/15; an overall comparison only (the gold-cap effect comes from the controlled re-solve, section 15) | Section 13, phase 2 | Core; cash-leg variant is cut-list |
| Capital budgeting (definition, types, five steps) | Adapt as framing, not structure: candidates are mutually exclusive investments; step 3 "cost of capital" becomes the hurdle h = (1 + π*) / (1 - s) - 1; step 5 "reviewing prior decisions" becomes the backtest and escalation ladder. One sidebar in the memo maps the steps onto the investment policy statement | Sections 13 and 13a, phase 7 | Core (memo text) |
| Payback period | Adapt as time under water in each crisis | Phase 2 | Core |
| Accounting rate of return | Adapt as distribution yield (income over average NAV) | Phase 2 | Core (already a KPI) |
| IRR | Adapt as money-weighted return under the spending rule, against the realised-inflation hurdle, retrospective (2017 to snapshot end) | Phase 2 | Core |
| Threshold "winner to loser" rebalancing (sell an ETF after a 10% rise, buy the ETF that fell most) | Reject as a trading rule; keep as tested evidence for the existing quarterly-plus-drift rebalancing. No reversal signal, and its apparent gains come from drift outside policy limits (19a) | Phase 7 memo, Q&A | Memo text only; no policy change |
| NPV, profitability index | Drop: for a fairly priced liquid fund, NPV computed in advance only restates expected return, and realised NPV at h is a dollar transform of money-weighted return minus h; PI = 1 + NPV / USD 10m adds nothing. The dollar view survives as the median real surplus over the real-capital target | - | Dropped |

### 19a. Correlation study and the "winner to loser" rule (exploratory, 30 October 2026)

Reproduce with `python scripts/correlation_rebalancing_study.py` (offline, `data/clean`, 2005-01-04 to 2026-09-30, 5,469 daily returns). Retrospective portfolio evaluation: the owner has seen the full sample. Descriptive only: it changes no frozen value, weight or verdict at `prereg-v1`.

**Correlations.** The seven ETFs form two blocks.

| Pair | Daily log-return corr. | Monthly | Rolling 252-day range | Note |
|---|---|---|---|---|
| SPY-XLK | 0.91 | 0.89 | 0.76 to 0.97 | Near-duplicate exposure |
| SPY-EFA | 0.88 | 0.86 | - | |
| SPY-EEM | 0.82 | 0.75 | 0.55 to 0.93 | Never negative |
| SPY-XLE | 0.71 | 0.61 | -0.18 to 0.95 | |
| SPY-AGG | 0.00 (95% CI -0.02 to 0.03) | 0.24 | -0.60 to 0.41 | Negative 55% of the time |
| SPY-GLD | 0.07 | 0.10 | -0.35 to 0.44 | |
| AGG-GLD | 0.21 | 0.36 | -0.13 to 0.67 | |

- One common factor explains 58% of daily variance (first eigenvalue 4.08 of 7). Equity correlations rise in crises: SPY-EEM 0.93 and SPY-XLK 0.98 in February to April 2020.
- On SPY's worst 5% of days the equity ETFs lost 2.9% to 3.5% on average, AGG gained 0.04% and GLD lost 0.09%. AGG and GLD carry the portfolio's diversification.
- The stock-bond hedge depends on the regime. SPY-AGG was -0.27 in 2010-2019, then +0.32 in 2022 and +0.18 in 2023-2026. This supports the owner's caveat above: correlation can reduce losses but guarantees nothing.

**Rule tested.** Each ETF's price is tracked from its last trade. When a held ETF is 10% above that reference, two variants were tested: trim it back to target, or sell only the 10% gain. In both variants the proceeds go to the held ETF with the largest fall since its own reference, and both references reset. The rule runs alongside buy-and-hold, quarterly and 5-point drift-band rebalancing, at 5 bp on buy plus sell notional, as in `portfolio.replay`.

| Adjusted recommendation SPY 15 / AGG 70 / GLD 15, 2005-2026 | CAGR | Volatility | Max drawdown | Max GLD weight | Min AGG weight |
|---|---|---|---|---|---|
| Quarterly rebalance | 5.46% | 5.82% | -16.8% | 18% | 67% |
| 5-point drift band | 5.67% | 5.85% | -16.9% | 20% | 65% |
| Rule: trim to target | 5.73% | 6.56% | -17.6% | 31% | 51% |
| Rule: sell the gain | 7.95% | 8.38% | -16.6% | 52% | 20% |

- The higher "sell the gain" return is a drift effect, not timing. Gold rose to 52% against the 15% cap and AGG fell to 20% against the 25% minimum, moving toward the buy-and-hold mix (6.63% CAGR, 7.30% volatility).
- On the equal-weight seven-ETF portfolio, both rule variants did worse than the drift band: 9.83% and 9.53% CAGR against 10.32%. They traded about twice as much (0.12 against 0.06 of NAV a year) and made 165 rule trades.
- The 2017-2026 window and the original selected weights give the same picture.

**Premise test.** After a 10% rise over three months, the following three months showed no significant underperformance for any ETF. Using non-overlapping triggers, t-statistics ranged from -1.48 (XLE) to +1.36 (EEM). Cross-sectionally, past 1-, 3- and 12-month winners slightly *outperformed* the next month (rank correlations +0.03 to +0.06, t-statistics 1.1 to 1.9). That is weak momentum, the opposite of the reversal the rule needs.

**Decision.** Keep quarterly-plus-5-point-drift rebalancing. It already sells relative winners and buys relative losers, and it stays inside policy limits. Any trigger rule should be weight-based and rebalance all assets to target, not move proceeds into the single worst performer, because that concentrates risk. Adopting a different rule would be a logged mandate change, and the new rule would need its own weight-hashed forecasts and backtest. Memo and Q&A answer: "We tested it; there is no reversal signal in these ETFs, and the rule's extra return came from breaking the gold cap and the bond minimum."

Review record (second critic pair): both agreed the hurdle must come from the spending need, which also fixed a circularity in the first version of section 13 that made Reject impossible, and they found the accidental 40% cap on AGG. They differed on keeping a realised NPV (dropped as redundant), on the AGG ceiling (60% vs 70%; 70% chosen, with its constraint effect reported) and on co-exceedance versus a simulated-null correlation test (co-exceedance chosen as plainer and cheaper; the simulated null is on the cut list).

## 20. External audit: accounting, validation and decision rules

Source: an audit supplied by the owner with seven recommendations, reviewed by a third pair of critics (committee view and implementation view) who cross-critiqued. All seven were adopted; item 1 (dollar ES contributions) had already been applied (AGENTS.md DOC-005).

| Audit item | Where it now lives |
|---|---|
| 1. Dollar ES contributions with shared tail weights | Section 15 component risk; phase 5; AGENTS.md section 11 |
| 2. Retrospective vs sequential vs untouched evaluation; no inherited traffic light | Section 15 evaluation labels; phases 2b and 4 |
| 3. Spending counted once; CPI as an inflation rate; hurdle on a stated cost basis | Sections 13 and 15; phase 5 real-capital survival |
| 4. Mutually exclusive Accept / Adjust / Reject; frozen adjustment set; "evaluation incomplete" | Section 13a; phase 2a freeze |
| 5. Normal Monte Carlo convergence wording | Phase 3; AGENTS.md sections 8 and 14 |
| 6. App result states for edited weights | Section 5; phase 6; AGENTS.md section 13 |
| 7. Gold-cap effect by controlled re-solve | Section 15 constraint effect; section 19 |

How the critics' disagreements were settled:

| Issue | Committee view | Implementation view | Decision |
|---|---|---|---|
| Untouched historical holdout | Sealed final 250 days at first, then withdrawn | None exists; later proposed a code-enforced holdout labelled "previously viewed" | No historical holdout: all data to 2026-09-30 was seen at e94c0ae. Untouched means post-snapshot monitoring only; the walk-forward check carries the anti-overfitting case |
| Freeze point | Before phase 4 | Before any post-2016 result | Before any post-2016 result: phase 2 split into 2a, tag `prereg-v1`, 2b |
| Forward inflation | T10YIE at first, then a fixed 2.5% | Fixed 2.5% at first, then T10YIE at the snapshot | Fixed π* = 2.5% (reproducible, cannot drift with the snapshot date); T10YIE and trailing CPI as a check |
| Gold cap as adjustment | At most 20% (25% is the permanent-portfolio weight we argue against) | 25% at first | 20% as adjustment A2; 20%, 25% and 40% all reported as constraint effects |
| Adjustment order | Re-weight, gold, spending, risk budget, all together | Risk budget earlier | Committee order (raise risk last), made finite: A1-A5 |
| Backtest gate | Green zone | Not red; failed model ≠ failed mandate | Not red plus coverage tests; challenger once; both fail → evaluation incomplete, never Reject |
| Selection objective | Maximise geometric return | Not a linear programme | Maximise arithmetic return under CVaR ≤ B; C3 tests geometric return |
| App weights | Dropdown of precomputed portfolios | Free weights under a state machine | Both: dropdown by default, free weights in Explore mode under the state machine |
| Run ID in cache key (audit item 6) | - | Exclude; scope lookups to the run | Excluded; run ID shown as provenance |

Points the audit missed that are now fixed: no named selection rule; the "minimum CVaR under the ES budget" candidate was contradictory (now the de-risk portfolio); ES budget model unstated; expense ratios double-counted on adjusted prices; arithmetic vs geometric return against a compound hurdle; Basel window undefined over a 2,400-day sample; FHS cannot attribute risk to assets; the de-risk portfolio needed its own validation; section 17 still called the spending Monte Carlo a stretch. Open owner decision: confirm FHS or swap to GARCH-EVT as the primary model before the tag (phase 4 disclosure).
