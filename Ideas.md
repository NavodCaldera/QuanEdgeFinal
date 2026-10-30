# Owner ideas for the investment report and executive tear sheet

Read this file before creating or revising the technical report/investment
memorandum or the one-page executive tear sheet. Explain adopted ideas and their
evidence consistently across both documents. Do not describe proposed analysis as
already computed, and do not overwrite frozen results or silently change policy.

## 1. A 25-year spending baseline

Recorded: 29 October 2026. Source: owner's idea in the project conversation.
Status: owner-requested proposal for discussion and future analysis. This is not
an amendment to the existing preregistered policy or an evaluated 25-year result.

### Owner's reasoning

An initial USD 10,000,000 fund divided by USD 400,000 of annual spending gives:

    USD 10,000,000 / USD 400,000 per year = 25 years

Use this as an intuitive baseline: can the investment strategy fund the same
university spending for 25 years and still leave money afterwards?

Proposed assumptions:

- First annual spending release is USD 400,000 on January 1 of year 1.
- Subsequent releases occur every January 1, increasing by 3.64% per year.
- Baseline inflation is a constant 3.64% per year, so the spending schedule
  maintains USD 400,000 per year in initial purchasing power.
- Baseline investments earn exactly 3.64% every year, after any costs/taxes
  included in the comparison. If 3.64% is a gross return, costs must be deducted
  and the 25-year equality no longer holds exactly.
- There are no new contributions. The baseline has no uncertain returns or
  inflation. Define an actual starting year/date before implementing it.

The 3.64% figure is currently an owner-proposed illustrative assumption. Its
economic source, observation period and calculation have not been established.
Do not label it a verified historical inflation estimate or forecast.

### Exact interpretation and withdrawal timing

For years t = 1, ..., 25, define:

    P_0 = 10,000,000
    C_t = 400,000 * (1.0364)^(t - 1)
    P_t = (P_(t-1) - C_t) * (1 + r_t)

Here C_t is withdrawn at the beginning of year t; P_t is the remaining nominal
balance at that year's end; r_t is the year's net return. A simulated strategy
fails to fund a payment if its balance before withdrawal is less than C_t.
Do not borrow or silently truncate spending to manufacture success.

In the deterministic baseline r_t = 0.0364. Divide the balance by accumulated
inflation to obtain initial-dollar purchasing power:

    Real balance at year-end t = P_t / (1.0364)^t
                               = 10,000,000 - 400,000 * t

The baseline supports 25 annual releases and leaves zero after the 25th release.
Because spending is paid in advance, the final release occurs at the start of
year 25 (24 years after the first release), and pays for year 25. The fund is
exhausted at that point, rather than only at the end of that year.

This is a deterministic capital-depletion baseline with zero real investment
return. It is not evidence that an uncertain strategy will survive 25 years.
With variable returns, early losses can impair later spending capacity even if
the long-run average return matches inflation (sequence-of-returns risk).

### Fixed real spending versus a percentage-of-balance rule

USD 400,000 equals 4% of the INITIAL USD 10 million. Under this proposal,
withdrawals follow the fixed inflation-linked schedule above, independently of
the fund's current balance. This is different from withdrawing 4% of the CURRENT
fund balance annually, where payments shrink after losses. Never describe the
two policies as interchangeable.

### Meaning of money left after 25 years

Describe the remaining fund as "residual capital after spending" or "surplus
relative to the depletion baseline". Report both nominal dollars and dollars of
initial purchasing power. A positive balance can include unspent original
capital and is not automatically pure investment profit.

Distinguish these questions:

1. Were all 25 scheduled university payments funded in full and on time?
2. Was any capital left after funding them?
3. Was the initial USD 10 million preserved in real terms after spending?

The third is stronger than the second. Real-capital preservation requires a
terminal nominal balance at least equal to the inflation-adjusted initial fund,
not merely a positive remaining balance. Define valuation at year 25's end.

### How to present the horizon in the report

Suggested wording, subject to owner review:

> We use a 25-year spending evaluation horizon because the initial USD 10 million
> represents 25 annual payments of USD 400,000 in today's purchasing power. In an
> illustrative baseline where net returns and inflation are both 3.64% annually,
> beginning-of-year inflation-linked withdrawals exhaust the initial real
> capital with the 25th payment. We assess whether the proposed strategy can fund
> the same payments and retain capital. Any residual is capital remaining after
> spending, not automatically pure profit.

A 25-year evaluation window does not establish that the university endowment's
mandate ends in year 25. The current policy treats it as perpetual. The baseline
is transparent and understandable, but dividing capital by spending is not by
itself a justification for limiting a perpetual institution's planning needs.

### Reconciliation required before implementation or numerical claims

The existing frozen run uses a perpetual mandate, 4% annual spending under its
existing balance-based convention, a 2.5% inflation assumption, and spending
after returns/costs. Its saved spending-sustainability results use their own
documented horizons and must not be relabelled as this new experiment.

Changing to fixed real spending, a 25-year evaluation horizon, 3.64% inflation
and January 1 withdrawals materially changes the experiment. Before analysing:

- Record whether this is an additional scenario or an explicit mandate change
  in PLAN.md/AGENTS.md, with an effective date and owner-approved assumptions.
- Confirm and document the inflation assumption, first withdrawal date, cost
  treatment, terminal valuation and whether principal preservation is required.
- Implement and evaluate the new spending schedule in a separately identified
  run. Include depleted paths, timing, costs, uncertainty and inflation sensitivity.
- Report full-spending success, depletion timing, nominal/real terminal capital
  and the probability of preserving initial real capital as distinct outcomes.
- Review consequences for allocation selection and validation if the objective
  or portfolio changes. Do not inherit another allocation's risk assessments.
- Update the report and one-page tear sheet together only when matching evidence
  exists. Until then, describe this as a proposed baseline without numerical
  strategy-performance or success-probability claims.

Relevant sources: PLAN.md sections 13, 13a and 15; config/final.yaml;
quanedge/portfolio.py; quanedge/stress.py; results/final-20261027/survival.json;
results/final-20261027/documents/investment_memorandum.pdf.

## 2. Recovery time and time under water for each ETF

Recorded: 30 October 2026. Source: owner's proposed research idea.
Status: existing descriptive recovery calculations identified; broader use in
selection or dynamic allocation is proposed and has not been evaluated.

Owner's question: after an ETF falls from a previous high, how long does it take
to regain that high? Can this help assess suitability for university spending?

Existing implementation:

- quanedge/portfolio.py kpis reports maximum time under water and recovery status
  for a supplied portfolio-return series.
- quanedge/evidence.py records portfolio recovery relative to the selected crisis
  start value. This is not automatically an all-time-high recovery measure.
- quanedge/context.py drawdown identifies the largest ETF drawdown and its peak,
  trough, first subsequent recovery and unrecovered status. The application now
  displays contextual drawdown tables. Inspect the current outputs before
  claiming coverage or numerical results.
- Recovery duration is not part of the frozen minimum-CVaR objective or a direct
  allocation constraint. Existing analysis must not be described as selecting
  15/70/15 by recovery speed.

Definitions for any extension:

- Drawdown: decline from the running peak of an adjusted-price/total-return path.
- Peak-to-recovery duration: total time from a peak through the decline and back
  to that peak (time under water).
- Trough-to-recovery duration: time from the low point to that same prior peak.
- Report both trading observations and elapsed calendar time with clear units.
- If the prior high has not been regained by the snapshot end, report "not yet
  recovered" and elapsed time, not zero or a known completed recovery duration.
- Distinguish nominal total-return recovery, inflation-adjusted recovery and
  recovery of a spending portfolio. Withdrawals can prevent the fund recovering
  even when the underlying ETF has recovered.
- Compare both common-period and full-history evidence. For an all-episode
  extension, define non-overlapping episodes and any materiality filter before
  inspecting rankings; disclose incomplete episodes and the chosen convention.

Interpretation: historical recovery duration adds useful information about
liquidity/spending vulnerability and patience required. It is not a forecast or
guarantee of the next recovery time. A seemingly quick recovery does not imply
an ETF is safe, and different history lengths make naive rankings misleading.

## 3. Declining equity allocation / glide path during the spending horizon

Recorded: 30 October 2026. Source: owner's idea to start with higher equity
exposure and gradually increase bonds as time passes and capital is spent.
Status: separate research proposal. No schedule, starting weights, return
improvement or spending-success result has been established. The existing
frozen allocation and policy are not amended by recording it.

Purpose: investigate whether greater early growth exposure followed by reduced
equity exposure can support the proposed 25-year withdrawal plan better than a
constant-weight allocation. The fund is not guaranteed to shrink; growth,
withdrawals and market losses jointly determine its balance.

Important risks and distinctions:

- Spending begins immediately, so this is a withdrawal-phase strategy from day
  one, not an accumulation phase followed by retirement. Early equity losses
  can force sales at low prices and damage later spending capacity.
- A predetermined calendar-based glide path differs from reducing equities
  whenever wealth falls. The second can sell after a crash and miss recovery;
  specify any trigger using information available at the decision date.
- More AGG does not guarantee capital protection: its interest-rate, credit and
  inflation exposures remain. Lower growth may worsen spending shortfalls.
- ETF recovery does not guarantee recovery of a fund making withdrawals.
- Current equity/AGG/gold limits remain applicable unless explicitly changed in
  a separately recorded mandate. A path exceeding those limits is a policy
  change, not an alternative operating inside the original policy.

If later authorised for implementation:

1. Define the 25-year schedule, January 1 first withdrawal of USD 400,000 before
   investing USD 9.6 million, subsequent inflation-linked fixed-real payments,
   first date, costs and required terminal capital. Confirm the inflation input.
2. Specify a small set of simple allocation paths and a fixed-weight comparator
   before reviewing their results. Select no dates or triggers using future
   observations or realised future recovery dates.
3. Compare all strategies under identical withdrawals, return/inflation paths,
   costs and valuation dates. Use joint asset rows to preserve dependence.
4. Report full-payment success, depletion timing, worst drawdown, recovery/time
   under water, turnover and nominal/real terminal balances. Distinguish positive
   residual capital from preservation of the initial real fund.
5. Include adverse early-return sequences and sensitivity to start dates and
   assumptions. These are retrospective/illustrative comparisons, not untouched
   historical evidence or guaranteed future probabilities.
6. A changing-weight strategy needs its own realised return path and prior-data
   risk evaluation. It cannot inherit a static portfolio's forecasts, traffic
   light or verdict. Preserve the original frozen evidence separately.

Current view: recovery analysis is a useful explanatory addition. The glide path
is a testable idea, not an established improvement, especially because payments
start immediately. Evaluate both against the actual spending objective.

### Owner refinement: prioritise SPY/EFA early, increase AGG later

Recorded: 30 October 2026. Owner proposes prioritising SPY and EFA early in the
25-year horizon for growth, then shifting toward AGG, while paying USD 400,000
initially and increasing that payment by 3.64% annually. This is a proposed
declining-equity glide path, not adopted weights or a computed success result.

The proposed rationale that both equities recover faster than AGG is not
established by the available recovery table. For the largest observed drawdown,
SPY recovered in 4.85 years, EFA in 6.60 years, and AGG remained unrecovered after
6.15 years at 2026-09-30. AGG's completed duration is unknown, and these episodes
occurred in different market conditions. Completed-only top-three averages omit
AGG's largest episode and cannot fairly rank recovery prospects.

A long terminal horizon does not make all capital long term: withdrawals begin
immediately and recur annually. Higher early equity exposure increases exposure
to adverse early sequences. A declining-equity schedule should be compared with
a fixed allocation and, if justified, a schedule with stronger early protection
under identical assumptions. Specify calendar-based weights in advance, not a
retrospective shift after known recovery dates. Retain the existing policy limits
unless separately amended; SPY and EFA together count toward the 55% equity cap.

No claimed improved spending success, future recovery time or optimal SPY/EFA
split exists until this distinct withdrawal-phase strategy is evaluated.
