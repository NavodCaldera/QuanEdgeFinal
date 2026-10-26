# QuantEdgeFinal: competition plan

Single-owner plan for the SAIFA Quant Edge 1.0 final challenge (Team Ghosted). One person builds and defends everything; AI assistants help with implementation under the disclosure rules in section 9. `AGENTS.md` holds the build specification and the progress record; this file holds the competition facts, the policy choices and the ordered plan.

Status: final draft, 26 October 2026. Draft 1 was reviewed by two critics (a judge/committee view and a one-person-delivery engineering view) who critiqued each other's findings; section 17 records how their disagreements were settled.

## 1. Sources and precedence

| Rank | Source | Pages | Status |
|---|---|---|---|
| 1 | `Quant edge 1.0 Final Challenge 1.pdf` (Competition Brief, Oct 2026) | 10 | Authoritative. Wins every conflict. |
| 2 | `EDGEFORGE_Polished_Finance_First_Masterclass_2026.pdf` (+ PPTX with speaker notes) | 99 | Teaching material built from an earlier draft of the brief. Use for judging expectations, not rules. |
| 3 | `Advanced_Risk_Management_English_final.pdf` (+ PPTX) | 28 | Teaching deck (VaR, ES, EVT, copulas, wavelets). All numbers are synthetic. |

The three files sit in `Final competition/`, beside this repository, and are not committed. The brief's section numbering skips section 4 (3 is followed by 5); no text is missing.

## 2. The competition in brief

- **Event:** Quant Edge 1.0, a national STEM quantitative investment research competition for undergraduates in Sri Lanka, informed by the CFA Program curriculum.
- **Theme:** "From Portfolio Theory to Value at Risk, Expected Shortfall and Extreme Value Theory".
- **Core idea:** successful investing means sustainable returns while protecting capital and managing downside risk, not maximising return.
- **Format:** the brief says "teams of five". This entry is run by one person. Solo eligibility must be confirmed in writing by the organisers before build work starts (phase 0).
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

Only these seven. No futures, options or FX overlays from the teaching decks. Treating the universe as excluding a cash sleeve is our reading of "eligible funds"; ask the organisers and state it as an interpretation. Long-only and full investment are our policy choices, not brief rules. Common history starts at GLD's inception (18 Nov 2004), so the sample covers the 2008 crisis.

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

Plus our additions: recommendation / "three questions" page, candidate comparison, risk contributions, data provenance.

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

**Approved sources only:** Yahoo Finance via yfinance (prices, dividend history); FRED (risk-free proxy such as the 3-month T-bill DTB3, CPI CPIAUCSL, 10-year yield DGS10); World Bank / IMF open data (macro context for the memo). An undisclosed or proprietary source is a rubric violation; judges must be able to reproduce the data.

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
| Technical rigour & correctness | 25% | Correct KPIs, VaR, ES, EVT, optional macro variables, statistically sound backtesting | Conventions in section 15; independent checks; honest failures; no look-ahead |
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

## 13. Investment policy (proposals to confirm in phase 2)

| Item | Policy | Notes |
|---|---|---|
| Investment horizon | Long-term (the endowment is perpetual); strategic review every 5 years | Defend with spending needs and intergenerational equity |
| Risk horizon | 1 trading day for VaR, ES and backtesting | Our choice, matched to the daily backtest. Multi-day views use overlapping historical returns, not square-root-of-time scaling |
| Return objective | Nominal return = US CPI (CPIAUCSL) + Y% a year over the long run, with Y read off the efficient frontier at the ES budget (expected about 3-4%) | Report the probability of falling short. If Y is too low for the spending need, the verdict is Adjust |
| Binding risk budget | 1-day 99% ES of at most about 2.5% of NAV (USD 250k), confirmed from candidate portfolios in phase 2 | Optimised directly (CVaR linear programme, Rockafellar-Uryasev) |
| Constraints | Long-only, fully invested, zero weights allowed; AGG at least 25%; equity (SPY+EFA+EEM+XLE+XLK) at most 55%; any single ETF at most 40%; GLD at most 15%; XLE and XLK at most 10% each | Report the shadow cost of the equity cap, GLD cap, AGG floor and ES budget (re-solve with each relaxed) |
| Drawdown limit | 20%, checked after the fact on the GFC replay and on bootstrapped 1-year paths | Not an optimiser constraint (path-dependent, overfits one crisis) |
| Rebalancing | Quarterly, or when a weight drifts more than 5 points; costs stated | Risk models assume daily rebalancing; state the mismatch |
| Governance | Drawdown 10% or a yellow backtest zone: review. Drawdown 15% or red zone: de-risk toward the minimum-ES portfolio | Escalation ladder for the memo |
| Benchmarks | 40/60 and 60/40 SPY/AGG; equal weight | Outside policy, for comparison only |

### 13a. Verdict rule (fixed in the decision log before phase 4 runs)

- **Accept the mandate as proposed** if all hold: point estimate of 1-day ES99 within the budget (bootstrap interval reported beside it); primary backtest in the green zone with conditional-coverage p > 0.05; worst historical stress loss and the GFC replay drawdown within 20%; return objective met.
- **Adjust the risk limit** (stating the new limit or weights) if any one test fails or the zone is yellow.
- **Reject** only if the return objective cannot be met by any portfolio within the risk tolerance.

## 14. Work plan

Fix phase timeboxes as shares of the time left once the deadline is known. Two milestones are hard: the **thin slice** at about 15% of the time and the **minimum viable submission** at about 60%.

### Phase 0: setup and decisions (day 1)
- Get written organiser confirmation of solo eligibility and the deadline; record both.
- Ask whether a cash sleeve counts as eligible.
- Python environment, pinned `requirements.txt` (with streamlit and plotly), package skeleton, `pytest`.
- Execute D-01 (section 12). Start the AI-use log and the decision log.
- **Done when:** `python -m pytest` passes on the restored modules and the deadline is recorded.

### Phase 1: data
- Fresh snapshot: adjusted prices and dividends for the seven ETFs; DTB3, CPIAUCSL, DGS10 from FRED.
- Pipeline rebuilds clean data from snapshots with one command; quality logs; ADF per asset and for the portfolio.
- **Done when:** clean data rebuilds offline from snapshots and tests cover the return identity and calendar handling.

### Phase 1.5: thin end-to-end slice (milestone, about 15% of the time)
Snapshot data → provisional policy weights → historical VaR/ES → Kupiec → one stress replay → `results/<run_id>/` → a stub app with all six mandatory pages, including Assumptions & Limitations.
- **Done when:** one command produces a run folder and the app opens on it.

### Phase 2: portfolio construction (Layer 1)
- Expected returns with shrinkage or a CAPM equilibrium view; sample and shrinkage covariance; correlations.
- Efficient frontier under policy; candidates: minimum variance, constrained maximum Sharpe, risk parity, minimum CVaR under the ES budget, plus the benchmarks.
- KPIs, defined in section 15, including distribution yield.
- Selection on the training period (2005-2016) only; record the effective date.
- **Candidate table (required artifact):** expected return, volatility, ES99 USD, maximum drawdown, worst stress USD, yield, shadow costs, and "each +1% expected return costs USD X of ES99".
- **Done when:** weights are feasible, KPIs match hand calculations, the trade-off is quantified, and the return objective and ES budget are confirmed.

### Phase 3: risk measurement (Layers 2-4)
- VaR at 90/95/99%: historical, parametric normal (Student-t as a variant), Monte Carlo with multivariate t as the primary simulation (normal Monte Carlo only reproduces the parametric result).
- ES for each, with dollar ES averaged from dollar losses.
- EVT: peaks over threshold with GPD; threshold from mean excess, parameter stability and goodness of fit; compare at least two threshold rules (innovation).
- Disagreement analysis: why methods differ (fat tails, sample extremes, distribution assumptions).
- Stress-eve views: models fitted on data up to 1 Sep 2008 and 19 Feb 2020 versus realised losses (Layer 4 "performance under stressed conditions").
- Uncertainty: block-bootstrap intervals; EVT shape interval.
- **Done when:** every model matches independent calculations on known distributions and the risk table states units, basis and status.

### Phase 4: validation (Layer 5)
- Name the primary model in the decision log before running: FHS at 99%, with GARCH-EVT as challenger.
- Rolling one-day forecasts: 750-day window, refit every 21 days, EVT threshold re-chosen inside each window, no future data.
- **Primary backtest:** training-period weights over the test period 2017 onward (genuinely out of sample). **Secondary:** final weights as hypothetical P&L over the full rolling period, labelled "in-sample allocation, out-of-sample risk forecast". The app's traffic light shows the primary test.
- Kupiec, Christoffersen independence, conditional coverage; traffic light at 99%; binomial p-values at 90/95%.
- **Done when:** tests reproduce known breach sequences, edge cases pass, and a future-data perturbation test shows no look-ahead.

### Phase 5: stress, macro and risk budgeting (8.6)
- Historical replays, buy-and-hold, SPY peak to trough: GFC 9 Oct 2007 - 9 Mar 2009; COVID 19 Feb - 23 Mar 2020; rate shock 3 Jan - 12 Oct 2022.
- Hypothetical: stocks and bonds falling together (inflation shock), for example SPY -25%, AGG -10%, GLD 0%, other assets filled in by conditional mean under a stressed covariance.
- Reverse stress test: the smallest shock that breaches the 20% drawdown limit.
- Per-asset impact, largest contributors, policy-limit breaches.
- Macro add-on (half a day, core): rolling 252-day SPY-AGG correlation showing the 2022 flip; portfolio sensitivity to DGS10 changes.
- Component ES as the primary risk allocation, parametric Euler VaR as a cross-check; risk budget versus capital weight; resulting allocation changes.
- **Done when:** every scenario reports return, USD loss and attribution, and component ES sums to the total.

### Phase 6: full app
- All six mandatory elements plus recommendation, candidate table, risk contributions and provenance.
- App reads frozen `results/<run_id>/`; recomputes only cheap items on sidebar changes with `st.cache_data`.
- `streamlit.testing.AppTest` smoke test.
- **Done when:** `streamlit run app.py` works from a fresh clone and every control changes the right outputs.

### Phase 7: minimum viable submission (milestone, about 60% of the time)
- Memo v1 (D3), tear sheet (D4a), one-page committee memo (D4b), AI disclosure, README, full app.
- Pitch deck outline (12 slides mirroring D4b) and the Q&A bank.
- **Done when:** a complete, submittable package exists.

### Phase 8: innovation (only after phase 7)
- Already in core and credited as innovation: FHS / GARCH-EVT regime-conditioned forecasts as the backtested model; EVT threshold-rule comparison; reverse stress test.
- Stretch: regime-conditioned risk budget (calm vs stress weights); spending-sustainability Monte Carlo (probability that real NAV after a 4% annual spend is below its start after 5 and 10 years); drawdown-control overlay within the seven ETFs.

### Phase 9: final run, documents and defence
- Lock config; one command `python -m quanedge.pipeline --config config/final.yaml` writes `results/<run_id>/` with input hashes, git SHA and package versions.
- Generate memo and tear-sheet tables and figures from the run; a script checks every number in the documents against it.
- Fresh clone → install → pipeline → app. Deploy to Streamlit Community Cloud if practical; confirm judges can access the repository.
- Full pitch deck after the shortlist; rehearse the Q&A bank.

**Cut list (first to go if time runs short):** World Bank context, KPSS, multi-day views, spending Monte Carlo, the second alternative optimiser, extra EVT threshold rules, deployment (local one-command run is allowed). Never cut: the six app elements, the three questions, the macro add-on, formal backtests, the verdict rule.

## 15. Technical conventions (defence-critical)

- **Losses:** positive L is a loss; L = -log(1 + R_p), with R_p the weighted sum of asset simple returns.
- **VaR / ES:** VaR is the loss quantile; ES is the quantile integral over [a, 1] divided by 1 - a, with fractional mass at ties; dollar ES averages dollar losses.
- **Kupiec / Christoffersen:** use 0·log 0 = 0 for zero breaches or no consecutive breaches, with tests; conditional coverage against chi-squared with 2 degrees of freedom.
- **Traffic light:** 250 days at 99%: green 0-4 exceptions, yellow 5-9, red 10 or more; also shown on rolling 250-day windows. At 90% and 95%, show "Basel zones not applicable" and the exact binomial p-value.
- **EVT at 90%:** if the selected threshold sits above the 90th percentile, the GPD tail does not cover 90%; show the empirical-body estimate and flag it.
- **KPIs:** SPY is the CAPM market for beta, Treynor and Jensen's alpha; Information ratio against the 40/60 benchmark (tracking error stated); Sortino with a 0% target and downside deviation over all days; Calmar = CAGR / |MDD| over a stated window; annualise from simple returns; DTB3 converted to bond-equivalent yield, then daily.
- **Component risk:** component ES = E[w_i L_i | L ≥ VaR], tested to reconcile to total ES.

## 16. Risks and Q&A bank

| Risk | Mitigation |
|---|---|
| Solo entry not eligible | Written confirmation in phase 0, before any build |
| Unknown deadline | Confirm immediately; timebox phases as shares of time left |
| App arrives last | Thin slice at 15%, minimum viable submission at 60% |
| Overfitting the allocation | Select on 2005-2016; primary backtest on 2017 onward |
| EVT instability | Threshold sensitivity, minimum exceedances, visible failures |
| Look-ahead | Future-data perturbation tests; in-window threshold choice |
| Numbers drift between app and documents | One frozen run feeds everything; checker script |
| Defending AI-written code | Restore only what is used; owner summaries and hand tests; disclosure |
| yfinance blocked on Streamlit Cloud | App reads frozen results only |

**Questions to prepare with numeric answers:** Why not 100% AGG or minimum variance? AGG lost about 13% in 2022 alongside equities; what protects the fund? Why a 1-day VaR for a perpetual fund, and how many 99% breaches per year should the committee expect (about 2.5)? What does a GFC repeat cost in dollars, and in years of scholarships? Why USD and US CPI for a Sri Lankan endowment? How is EVT shown at 90%? What happens when a limit is breached? Who chose the weights, you or the AI? What costs and expense ratios are assumed? Why does the primary model differ from the simplest one?

## 17. Review record: how the critics' disagreements were settled

| Issue | Judge view | Engineer view | Decision |
|---|---|---|---|
| Drawdown limit | Hard policy limit | Ex-post check only | Not in the optimiser; a pass/fail test in the verdict rule |
| ES test in verdict | Strict | Point estimate; intervals would always force Adjust | Point estimate, interval shown beside it |
| Backtest weights | Training weights out of sample | Today's weights (bank practice) | Both; the training-weight test is primary |
| Restoring old code | Only what feeds outputs | Restore all with tests | Only what feeds outputs, each reviewed and hand-tested |
| Pitch deck | Skeleton before submission | After shortlist | Outline and Q&A before submission; full deck after shortlist |
| AGG cap | 25-70% | At least 25%, no cap | At least 25%; the ES budget limits risk |
| Macro | Core, including CPI betas | Half day; CPI regression too thin | Half-day core: rolling stock-bond correlation and DGS10 sensitivity |
| Spending Monte Carlo | Innovation #1 | Stretch | Stretch |

## 18. Requirement checklist

- [ ] Solo eligibility and deadline confirmed in writing
- [ ] Horizon, allocation, return objective, risk constraints defined and defended
- [ ] Suitability for a conservative investor shown; income (yield) reported
- [ ] Return vs risk trade-off quantified (candidate table, shadow costs)
- [ ] Assumptions stated
- [ ] Markowitz + CAPM; Sharpe, Sortino, Treynor, Jensen, IR, MDD, Calmar
- [ ] Three VaR methods at 95% and 99%; disagreement explained
- [ ] ES with rationale
- [ ] EVT with justified threshold; stressed-period performance
- [ ] Out-of-sample Kupiec, Christoffersen, traffic light
- [ ] Marginal/component VaR/ES risk budgeting and position sizing
- [ ] Three historical stresses + one hypothetical (+ reverse stress)
- [ ] Optional macro risks (stock-bond correlation, rates)
- [ ] Verdict rule fixed before testing; accept / adjust / reject given
- [ ] App: sidebar, portfolio, risk dashboard, backtest, stress, Assumptions & Limitations
- [ ] Data rules: adjusted close, calendars, log returns, flags, ADF, reproducible
- [ ] Repo, one-command app, 7-15 page memo, tear sheet, one-page committee memo, pitch deck
- [ ] AI disclosure
- [ ] Three questions answered: what can go wrong, how bad, how confident
