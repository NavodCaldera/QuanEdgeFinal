# Investment memorandum

## Investment memorandum

Serendib University Endowment Fund. USD 10,000,000. Data: 3 January 2005 through 2026-09-30. Run final-20261027.

Algorithmic recommendation: Adjust. Adopt A1_min_cvar only after owner review of the stated trade-off. Reported allocation and numbers: A1_min_cvar, weight hash a4698cec361f.

The original allocation's GFC path drawdown was -23.38%, exceeding the 20% limit. The adjusted portfolio's GFC path drawdown is -14.74%. Expected geometric return changes from 9.34% to 8.02%; historical ES99 changes from $250,000 to $141,417. These are estimator-dependent trade-offs, not guaranteed future outcomes.

Illustrative after-spending real-capital shortfall probabilities: 5 years 60.92% (Monte Carlo SE 0.49%); 10 years 67.41% (Monte Carlo SE 0.47%). These resampled-history outcomes do not gate the frozen verdict, but they are a material spending-sustainability concern for owner review.

This is a solo submission prepared with AI assistance. The owner approved the policy assumptions and FHS/GARCH-EVT model order; independent review of implementation and the investment judgement is pending.

Capital preservation takes priority over maximising gains. A perpetual endowment must fund today's scholarship obligations while protecting future purchasing power. The strategic review period is five years; daily risk measurement serves monitoring rather than defining the investment horizon.

What can go wrong: equities can fall together, bonds can lose with equities during inflation shocks, and gold can fail to protect over the committee's chosen period. Spending and inflation can overwhelm returns even when daily risk looks modest.

How bad: the stress section reports conditional dollar losses, not a worst possible outcome. How confident: forecast coverage, failure counts and bootstrap intervals qualify each point estimate.

## Policy and allocation

Annual spending is 4.00% after returns and costs; assumed inflation is 2.50%. The exact after-cost, before-spending break-even hurdle is 6.77%.

The portfolio is long-only and fully invested. AGG is 25-70%, total equity at most 55%, gold at most 15%, XLE/XLK at most 10% each, and other individual ETFs at most 40%. These are chosen policy assumptions, not organiser rules.

The binding risk budget is historical one-day ES99 of USD 250,000 on the allocation's estimation sample. The stress/drawdown limit is 20%. No daily estimate guarantees this multi-period loss limit.

Rebalance quarterly or when any weight drifts more than five percentage points. Trading cost is five basis points one-way per unit of traded NAV. Expected-return comparisons reserve five basis points annually for the frozen one-times-NAV turnover assumption. ETF expense ratios are embedded in adjusted prices.

## Data and provenance

Yahoo Finance via yfinance supplies dividend/split-adjusted ETF closes. Their total-return interpretation assumes distribution reinvestment; distributions must not be added to adjusted-close returns again. Separate unadjusted closes and distributions support income yield.

The fresh snapshot has 5,470 common price dates and 5,469 returns. All 242 flagged price-return moves remain. The pipeline records stale prices, sharp reversals, calendar closures, volatility shifts and missing observations. Event labels are analyst-compiled date associations rather than verified per-asset causal explanations.

FRED DTB3 discount quotes are converted to bond-equivalent yield and daily rates. CPI inflation is computed from index ratios. Monthly release-lag approximations and daily forward fills are logged; revised contemporary data is not a point-in-time vintage archive.

ADF checks address unit roots; fixed-lag ADF, KPSS and ARCH-LM checks provide complementary diagnostics. Rejection does not establish stable parameters or validate any tail distribution. The selected allocation has its own return-series stationarity report.

Clean price file SHA-256: 76bac76cbc98b5ce62291bd6257600047cc20857943d363edd1f807f743d4d0d. Weight SHA-256: a4698cec361f42b3f9b23598dcaba6ad09e21328a7dd894cc66c1f2a988fc897. Configuration SHA-256: c0bc0983242a703d50b9a9bb5c2ad7227d60ac6574c55da29eb6a4c6c9ef9d3d. File identity does not prove economic correctness.

Source retrieval metadata accompanies prices and distributions. Legacy source ingestion records macro snapshot write times rather than exact HTTP retrieval timestamps; that limitation is explicit.

## Construction and alternatives

The frozen selection maximises arithmetic expected return subject to historical CVaR99 and allocation constraints. A second LP minimises CVaR within 1e-8 of the optimal return. Failed solves remain unavailable. Sample annual arithmetic means are shrunk 50% toward their cross-asset mean; Ledoit-Wolf covariance supports the variance-based candidates.

The hurdle tests geometric return after the fixed turnover-cost reserve. The lognormal moment approximation is (1 + net arithmetic return) exp(-variance/2) - 1. Estimation choices and constraints drive the result; expected return is uncertain and is not a realised performance promise.

Shrinking toward one cross-asset mean can overstate expected bond returns by pulling them toward equity returns. Fixed-weight sensitivity across shrinkage strengths and five-year, ten-year and full-history windows is exported separately; the frozen recommendation is not re-tuned to these results.

Markowitz comparisons use constrained minimum variance, maximum Sharpe and near-parity volatility contributions. Minimum CVaR is the precomputed de-risk portfolio. SPY is the CAPM market proxy for beta and Jensen alpha; the 40/60 SPY/AGG portfolio is the active-return benchmark.

The adapted permanent portfolio uses 25% SPY, 50% AGG and 25% gold; AGG substitutes imperfectly for long Treasuries and cash. It is outside policy and is a comparison only. Constraint effects are isolated by identical-scenario re-solves changing one limit.

Pairs trading and short market-neutral strategies introduce borrow, margin and implementation risks beyond this long-only policy. The retained long-only mechanism is rebalancing relative winners and losers. Diversification can reduce losses without guaranteeing a profit.

## Performance and accounting

All historical allocation evaluations are retrospective. W_train is estimated through 2016, W_rec through the snapshot end, and neither erases prior exposure to the crises used when writing the policy. The annual walk-forward procedure uses only earlier data for each year's weights; policy design remains historically informed.

Wealth compounds simple portfolio returns; asset simple returns aggregate before conversion to log. Implementation performance includes quarterly/drift turnover costs. Risk forecasts instead replay daily constant weights without costs, a disclosed implementation mismatch.

Sharpe uses daily excess return and sample volatility; Sortino uses a zero target and downside deviation over all days. Treynor is unavailable for near-zero beta. Jensen alpha uses SPY excess returns. Information ratio uses 40/60 active returns and tracking error. Calmar uses CAGR and drawdown over the same dates.

Annual spending is deducted once after net returns. The real-capital target is initial NAV multiplied by the CPI ratio; spending is not added to this target. Money-weighted return includes distributions as investor cash flows and remaining NAV, while time-weighted CAGR measures the investment path.

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

At 10% drawdown or a yellow zone, review the portfolio and model. At 15% drawdown or a red zone, consider the independently evaluated minimum-CVaR allocation. No automatic trade or guarantee is implied. Lowering annual spending by 0.5 percentage point reduces initial annual support by USD 50,000.

## Decision, limitations and disclosure

Frozen-rule outcome: Adjust. Adopt A1_min_cvar only after owner review of the stated trade-off. Checks: {"C1": true, "C2": true, "C3": true, "C4": true, "C5": true}.

The original mandate passes only if feasibility, ES budget, expected geometric hurdle, validated risk model and stress checks all pass. Otherwise evaluate A1 alternative in-policy candidates in training ES order, A2 gold cap 20%, A3 spending 3.5%, A4 the frozen capped risk-budget increase, then A5 their combination. Missing evidence blocks a final verdict.

Historical dependence, estimated means/covariances, sparse extremes, threshold uncertainty, changing regimes and conditional-filter specification limit inference. The analysis omits tax, detailed liquidity/price impact and Sri Lankan FX/spending risk. Revised macro data limits historical information claims.

The real-capital simulation resamples joint monthly asset/CPI observations in non-circular 12-month blocks, applies quarterly/drift trades and annual spending, and compares after-spending NAV with inflation-adjusted initial capital. These are illustrative paths from a limited sample, not reliable forward probabilities.

AI disclosure: Codex assisted restoration, portfolio/validation/stress implementation, integration, tests, application and document generation. Earlier source records identify Claude Code and Antigravity assistance. Automated independent numerical examples are software checks, not an independent human audit. Human reviewer/date: pending. The owner remains responsible for understanding, revising and defending every material result.

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

Portfolio A1_min_cvar, weights a4698cec361f. Retrospective daily-return path from 2005 through 2026-09-30, after quarterly/drift trading costs and before spending.

These paths describe historical behaviour. The annual walk-forward procedure and daily risk forecasts answer different questions and are exported separately.