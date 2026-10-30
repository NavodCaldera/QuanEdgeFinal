# Investment memorandum

## Investment memorandum

Serendib University Endowment Fund. USD 10,000,000. Data: 3 January 2005 through 2026-09-30. Run final-v3-20261030.

Algorithmic recommendation: evaluation incomplete. Complete matching evidence or validate a risk model before committing capital. Reported allocation and numbers: selected, weight hash bd13d8979ea9.

The original allocation is reported; its outcome follows the frozen checks rather than a discretionary override.

Illustrative 25-year reserve sustainability: 10 years: all payments funded in 100.00% of paths, initial real capital preserved in 0.33%, median real balance $6,499,836; 25 years: all payments funded in 67.44% of paths, initial real capital preserved in 0.00%, median real balance $682,854. A fixed real reserve of 4% of the initial fund exceeds the 1-3% real return objective, so real capital is expected to decline by design; these resampled-history outcomes do not gate the verdict.

Mandate v3 (owner change, 30 October 2026, tagged prereg-v3): the portfolio may hold only SPY, AGG, GLD, XLE. EFA, EEM and XLK are excluded because their daily return correlations with SPY are 0.88, 0.82 and 0.91 (2005-2026), so they add little diversification. XLE is the least SPY-correlated equity ETF but still moves with SPY (0.70 daily, 0.76 on SPY's worst 5% of days); AGG and GLD are close to uncorrelated with SPY (0.00 and 0.07). All other v2 rules are unchanged.

Mandate v2 (owner change, 30 October 2026, tagged prereg-v2): no ETF percentage limits; zero trading cost; each 1 January a cash reserve for the university is withdrawn (USD 400,000 in year 1, growing 3.64% a year (year 2 USD 414,560)); target real return 1-3% a year after 3.64% assumed inflation. It supersedes mandate v1 (run final-20261027), whose results remain unchanged.

This is a solo submission prepared with AI assistance. The owner approved the policy assumptions and FHS/GARCH-EVT model order; independent review of implementation and the investment judgement is pending.

Capital preservation takes priority over maximising gains. A perpetual endowment must fund today's scholarship obligations while protecting future purchasing power. The strategic review period is five years; daily risk measurement serves monitoring rather than defining the investment horizon.

What can go wrong: equities can fall together, bonds can lose with equities during inflation shocks, and gold can fail to protect over the committee's chosen period. Spending and inflation can overwhelm returns even when daily risk looks modest.

How bad: the stress section reports conditional dollar losses, not a worst possible outcome. How confident: forecast coverage, failure counts and bootstrap intervals qualify each point estimate.

## Policy and allocation

Cash reserve: USD 400,000 in year 1, growing 3.64% a year (year 2 USD 414,560), withdrawn from the portfolio on the first trading day of each year and paid to the university. The reserve earns nothing and is not an investment; it is not part of the seven-ETF universe. Year 1 invests USD 9,600,000 of the USD 10,000,000 fund.

Return objective: 1-3% real a year. With the owner's 3.64% inflation assumption (described by the owner as an average world rate; its source and period are not yet verified) the nominal geometric target is 6.75% and the acceptance floor is 4.68%. USD 400,000 is 4% of the initial fund, so the reserve schedule exceeds the real return objective and real capital is expected to decline.

Universe: SPY, AGG, GLD, XLE only; the other three eligible ETFs are held at zero by owner choice. Constraints: long-only and fully invested, with no per-ETF, equity, gold or sector percentage limits. The binding risk budget is historical one-day ES99 of 2.5% of invested NAV (USD 240,000 at inception) on the allocation's estimation sample. The stress/drawdown limit is 20%.

Rebalance quarterly or when any weight drifts more than five percentage points. Trading cost is assumed to be zero (owner assumption), so bid-ask spreads and market impact are not modelled. ETF expense ratios are embedded in adjusted prices.

## Data and provenance

Yahoo Finance via yfinance supplies dividend/split-adjusted ETF closes. Their total-return interpretation assumes distribution reinvestment; distributions must not be added to adjusted-close returns again. Separate unadjusted closes and distributions support income yield.

The fresh snapshot has 5,470 common price dates and 5,469 returns. All 242 flagged price-return moves remain. The pipeline records stale prices, sharp reversals, calendar closures, volatility shifts and missing observations. Event labels are analyst-compiled date associations rather than verified per-asset causal explanations.

FRED DTB3 discount quotes are converted to bond-equivalent yield and daily rates. CPI inflation is computed from index ratios. Monthly release-lag approximations and daily forward fills are logged; revised contemporary data is not a point-in-time vintage archive.

ADF checks address unit roots; fixed-lag ADF, KPSS and ARCH-LM checks provide complementary diagnostics. Rejection does not establish stable parameters or validate any tail distribution. The selected allocation has its own return-series stationarity report.

Clean price file SHA-256: 76bac76cbc98b5ce62291bd6257600047cc20857943d363edd1f807f743d4d0d. Weight SHA-256: bd13d8979ea90bd195fc97c16af6d8923a6a8537159887b9ffb110953163d87f. Configuration SHA-256: 40ea58f7aaf1a15e376c5c78ddb592624ea3c44c1c1f416f8d2014f7c0f50cbd. File identity does not prove economic correctness.

Source retrieval metadata accompanies prices and distributions. Legacy source ingestion records macro snapshot write times rather than exact HTTP retrieval timestamps; that limitation is explicit.

## Construction and alternatives

Selection rule (mandate v2): minimise historical CVaR99 subject to the ES budget and an expected geometric return of at least 6.75% (3% real). The LP is linear in arithmetic return, so the smallest arithmetic floor meeting the geometric target is found by bisection. If the minimum-CVaR allocation already meets the target, the target does not bind and minimum CVaR is selected.

Expected returns use the frozen estimator: sample annual means shrunk 50% toward the cross-asset mean, with Ledoit-Wolf covariance. The owner kept this estimator after seeing that it decides the outcome: shrinkage lifts AGG's expected return toward the equity average. On raw historical means the reported allocation's expected return is materially lower (estimator sensitivity is exported); the same rule with raw means would instead select roughly AGG 65 / GLD 17 / XLK 18.

The mandate v1 rule (maximise return within the ES budget) is kept as the max_return comparison candidate. Without ETF limits it concentrates in AGG, GLD and XLK. Markowitz comparisons use minimum variance, maximum Sharpe and volatility risk parity without percentage limits. SPY is the CAPM market proxy; 40/60 SPY/AGG is the active-return benchmark.

The adapted permanent portfolio uses 25% SPY, 50% AGG and 25% gold; AGG substitutes imperfectly for long Treasuries and cash. Constraint effects are isolated by identical-scenario re-solves changing the ES budget or the real return target.

Pairs trading and short market-neutral strategies introduce borrow, margin and implementation risks beyond this long-only policy. Diversification can reduce losses without guaranteeing a profit.

## Performance and accounting

All historical allocation evaluations are retrospective. W_train is estimated through 2016, W_rec through the snapshot end, and neither erases prior exposure to the crises used when writing the policy. The annual walk-forward procedure uses only earlier data for each year's weights; policy design remains historically informed.

Wealth compounds simple portfolio returns; asset simple returns aggregate before conversion to log. Implementation performance includes quarterly/drift turnover costs. Risk forecasts instead replay daily constant weights without costs, a disclosed implementation mismatch.

Sharpe uses daily excess return and sample volatility; Sortino uses a zero target and downside deviation over all days. Treynor is unavailable for near-zero beta. Jensen alpha uses SPY excess returns. Information ratio uses 40/60 active returns and tracking error. Calmar uses CAGR and drawdown over the same dates.

The cash reserve is withdrawn before the first trading day's return each year; a fund that cannot pay the full reserve is depleted and stays at zero. Real values deflate by the policy inflation assumption, the same rate that grows the reserve.

## VaR, Expected Shortfall and EVT

All estimates use one trading day and the same allocation/NAV. VaR is a quantile, not maximum loss. ES averages the worst 1-alpha probability mass. Historical VaR uses NumPy linear interpolation; empirical ES uses the step-distribution quantile integral with fractional boundary mass.

Monetary VaR transforms the log-loss quantile. Monetary ES averages transformed tail losses; transforming mean log ES is generally wrong. Historical ES cannot extrapolate past the worst observed scenario. Normal assumptions can miss skew, clustering and tails.

Monte Carlo simulates joint normal and covariance-matched Student-t asset log returns and aggregates simple returns. A common t scale shock preserves joint tail dependence. The normal asset simulation and fitted portfolio-normal distribution are different models; analytical convergence is checked in a matching one-asset case.

EVT fits GPD loss exceedances. Its threshold scan uses mean excess, shape/modified-scale stability, counts and goodness of fit, with visible failures. The rule is a heuristic. Lower-confidence estimates below the threshold use an empirical-body hybrid. Shape >=1 implies infinite log ES, distinct from bounded monetary losses under positive wealth.

Block-bootstrap intervals resample whole asset rows in circular 20-day blocks. The default is 500 replicates. Fixed threshold percentile bootstrap omits full threshold-selection uncertainty; intervals do not protect against model misspecification.

## Sequential forecast validation

Each forecast uses only observations through the previous day. Historical/normal models refit daily; slower models refit every 21 observations on a 750-observation window. Conditional volatility updates daily between refits. Forecast files preserve training cutoffs, parameters' refit date, failures and portfolio hashes.

FHS is the preregistered primary model; GARCH-EVT is the challenger. Earlier equal-weight development forecasts were seen: FHS had 65 versus 47.2 expected breaches and Kupiec p about 0.014; GARCH-EVT had 52 and p about 0.49. The choice was therefore not historically blind.

Kupiec tests exception frequency; Christoffersen independence tests clustering and conditional coverage combines them. Degenerate transitions are inconclusive. Missing forecasts are disclosed and excluded from numerical denominators without connecting transitions across gaps.

Traditional Basel colours apply to the final 250 complete observations at 99%: 0-4 green, 5-9 yellow, 10+ red. Other levels receive binomial assessments. These supervisory categories are a monitoring analogy, not a regulatory capital calculation for the fund.

C4 requires at least 95% coverage, a non-red final zone, and Kupiec/conditional-coverage p-values above 0.05 for 2017 onward. The challenger is used once if the primary fails. If both fail the investment evaluation is incomplete, rather than rejected on economic grounds.

## Stress, attribution and governance

Historical stress paths hold positions buy-and-hold from SPY peak to trough: 9 October 2007-9 March 2009; 19 February-23 March 2020; 3 January-12 October 2022. The start-day close is the initial valuation, so its earlier daily return is excluded. No intervening trade cost is assumed.

The hypothetical inflation shock sets SPY -25%, AGG -10% and GLD 0%. Other equity shocks use conditional means under the covariance of training-period SPY worst-decile days. This extrapolation is uncertain and has no calibrated probability. Reverse stress measures covariance distance to a 20% one-step loss, not a path probability.

Historical dollar ES components use the same joint scenarios and shared normalised portfolio tail weights, including proportional sharing at tied boundaries. Negative contributions remain visible and sum to that scenario-based ES. Portfolio-only FHS cannot supply asset attribution.

Bonds and gold may diversify some equity losses and fail during other shocks. Stock-bond rolling correlation and Treasury-rate sensitivity contextualise that instability. Risk budgets must distinguish capital weights from contributions to the portfolio's bad days.

At 10% drawdown or a yellow zone, review the portfolio and model. At 15% drawdown or a red zone, consider the independently evaluated minimum-CVaR allocation. No automatic trade or guarantee is implied. Each USD 50,000 less in the first-year reserve reduces the whole inflation-linked schedule by 12.5%.

## Decision, limitations and disclosure

Frozen-rule outcome: evaluation incomplete. Complete matching evidence or validate a risk model before committing capital. Checks: {"C1": true, "C2": true, "C3": true, "C4": false, "C5": true}.

The mandate passes only if feasibility (C1), the ES budget (C2), an expected real return of at least 1% (C3), a validated risk model (C4) and the stress limits (C5) all pass. Otherwise evaluate A1, the alternative candidates in training ES order, then A2, the ES budget raised to the frozen training-sample value. The reserve schedule and the 1% real floor are client needs and are not relaxed. Missing evidence blocks a final verdict.

Historical dependence, estimated means/covariances, sparse extremes, threshold uncertainty, changing regimes and conditional-filter specification limit inference. The analysis omits tax, detailed liquidity/price impact and Sri Lankan FX/spending risk. Revised macro data limits historical information claims.

The reserve simulation resamples joint monthly asset returns in non-circular 12-month blocks for 25 years, pays the inflation-linked reserve each January, rebalances quarterly or on drift and reports full-payment success, depletion timing and real balances. These are illustrative paths from a limited sample, not reliable forward probabilities.

AI disclosure: Codex assisted restoration, portfolio/validation/stress implementation, integration, tests, application and document generation. Earlier source records identify Claude Code and Antigravity assistance; Claude Code implemented the mandate v2 rule change, cash-reserve accounting and rerun. Automated independent numerical examples are software checks, not an independent human audit. Human reviewer/date: pending. The owner remains responsible for understanding, revising and defending every material result.

Submission dependencies: written acceptance of a solo entry and the deadline remain unconfirmed. Repository access, publication and deployment require separate authorisation. This local package is prepared for review, not represented as submitted.

## Evidence and references

Evidence files include canonical weights, risk tables, per-allocation forecasts, formal tests, scenario attribution, uncertainty, walk-forward allocations, source manifests and environment versions. The Streamlit app reads this same run and invalidates expensive results for changed weights.

Policy and procedure were frozen before current post-training portfolio evaluation. All historical data through the snapshot had been seen in earlier development, so the freeze documents the current procedure rather than manufacturing an untouched holdout.

Competition brief: Quant edge 1.0 Final Challenge 1.pdf, sections 3, 5-10

Basel calibration: https://www.bis.org/committees/bcbs/basel-framework/standard/mar/99/inforce/2019-12-15/published/2019-12-15

CVaR optimisation: https://uryasev.github.io/publications/

Approved prices: https://finance.yahoo.com/

Risk-free series: https://fred.stlouisfed.org/series/DTB3

Inflation series: https://fred.stlouisfed.org/series/CPIAUCSL

Academic foundations retained in the implementation: Markowitz mean-variance construction; CAPM excess-return beta; Rockafellar-Uryasev CVaR optimisation; peaks-over-threshold GPD; Kupiec frequency and Christoffersen independence likelihood-ratio tests. The local teaching decks use synthetic illustrations and do not supply empirical estimates.

## Historical wealth and drawdown

Portfolio selected, weights bd13d8979ea9. Retrospective daily-return path from 2005 through 2026-09-30, after quarterly/drift trading costs and before reserve withdrawals.

These paths describe historical behaviour. The annual walk-forward procedure and daily risk forecasts answer different questions and are exported separately.