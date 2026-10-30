# Six weighting methods through every crisis found so far

Buy-and-hold from each crisis start, USD 10m, no rebalancing, costs or reserve withdrawals. Weights are the full-sample 2005-2026 estimates, so every crisis below was in the estimation data: retrospective portfolio evaluation, not a test. Prices: data/clean/prices_clean.csv.

## Weights

| Method | SPY | XLE | AGG | GLD |
|---|---:|---:|---:|---:|
| Inverse variance (1/var) | 7.0% | 3.0% | 83.0% | 7.0% |
| Inverse volatility (1/vol) | 16.0% | 10.0% | 57.0% | 17.0% |
| Risk parity (ERC) | 14.0% | 9.0% | 61.0% | 16.0% |
| Minimum variance | 6.0% | 1.0% | 91.0% | 2.0% |
| Minimum CVaR (v2/v3 W_rec) | 5.8% | 0.2% | 88.0% | 6.0% |
| Maximum Sharpe | 13.0% | 0.0% | 78.0% | 9.0% |

## Portfolio return over each crisis window (best method in bold)

| Crisis | Window | Inverse variance | Inverse volatility | Risk parity | Minimum variance | Minimum CVaR | Maximum Sharpe |
|---|---|---:|---:|---:|---:|---:|---:|
| GFC | 2007-10-09 to 2009-03-09 | +2.5% | -5.3% | -3.7% | +3.4% | **+4.6%** | +0.7% |
| Lehman liquidity shock | 2008-09-09 to 2008-10-10 | -12.9% | -13.4% | -13.1% | -13.5% | **-12.4%** | -12.8% |
| Gold bear market | 2011-08-22 to 2015-12-17 | +12.1% | +14.1% | +13.0% | +14.1% | +11.7% | **+16.4%** |
| Oil collapse | 2014-06-23 to 2016-01-20 | +0.6% | -5.6% | -4.8% | **+2.7%** | +2.3% | +1.3% |
| 2018 trade tensions | 2018-01-26 to 2018-12-24 | -1.9% | -6.2% | -5.5% | **-0.8%** | -0.8% | -2.2% |
| COVID crash | 2020-02-19 to 2020-03-23 | -5.4% | -12.4% | -11.2% | -3.9% | **-3.5%** | -5.8% |
| COVID dash for cash | 2020-03-06 to 2020-03-18 | -11.4% | -14.7% | -14.2% | -10.5% | **-10.3%** | -10.9% |
| Bond bear market | 2020-08-04 to 2022-10-20 | -11.1% | **+3.8%** | +1.4% | -14.8% | -16.3% | -14.3% |
| China / global tightening | 2021-02-17 to 2022-10-24 | -11.5% | **-0.8%** | -2.4% | -14.5% | -15.1% | -14.0% |
| Rates 2022 | 2022-01-03 to 2022-10-12 | -12.8% | **-8.9%** | -9.4% | -14.3% | -14.4% | -15.1% |
| Gold correction 2026 | 2026-01-29 to 2026-07-16 | -0.9% | -1.7% | -1.7% | **+0.1%** | -1.1% | -1.3% |
| Hypothetical joint inflation shock | deterministic | -11.1% | -13.1% | -12.7% | -10.9% | **-10.3%** | -11.1% |

## Deepest fall inside each window (peak-to-trough, buy-and-hold)

| Crisis | Inverse variance | Inverse volatility | Risk parity | Minimum variance | Minimum CVaR | Maximum Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| GFC | -14.4% | -19.0% | -18.2% | -13.6% | -13.1% | -14.3% |
| Lehman liquidity shock | -13.5% | -16.0% | -15.5% | -13.5% | -12.6% | -13.4% |
| Gold bear market | -4.5% | -7.2% | -6.6% | -4.3% | -4.6% | -4.5% |
| Oil collapse | -3.0% | -6.4% | -5.8% | -2.6% | -2.7% | -2.8% |
| 2018 trade tensions | -2.6% | -6.2% | -5.5% | -2.4% | -2.5% | -2.7% |
| COVID crash | -11.0% | -15.5% | -14.6% | -10.4% | -10.2% | -10.8% |
| COVID dash for cash | -11.4% | -14.7% | -14.2% | -10.5% | -10.3% | -10.9% |
| Bond bear market | -14.1% | -12.5% | -12.2% | -16.4% | -17.1% | -17.5% |
| China / global tightening | -14.6% | -12.6% | -12.6% | -16.6% | -17.0% | -17.3% |
| Rates 2022 | -13.7% | -12.8% | -12.8% | -14.6% | -14.7% | -15.3% |
| Gold correction 2026 | -3.3% | -4.2% | -4.1% | -2.9% | -3.5% | -4.2% |

## Scorecard across the 12 scenarios

| Method | Best of six | Worst of six | Average return | Worst return |
|---|---:|---:|---:|---:|
| Inverse variance (1/var) | 0 | 0 | -5.3% | -12.9% |
| Inverse volatility (1/vol) | 3 | 6 | -5.4% | -14.7% |
| Risk parity (ERC) | 0 | 1 | -5.4% | -14.2% |
| Minimum variance | 3 | 1 | -5.2% | -14.8% |
| Minimum CVaR (v2/v3 W_rec) | 5 | 3 | -5.5% | -16.3% |
| Maximum Sharpe | 1 | 1 | -5.7% | -15.1% |

## Which ETFs held up and which lost in each crisis

Each ETF on its own, buy-and-hold over the same window. EFA, EEM and XLK are outside the mandate v3 universe and shown for context only (marked *).

| Crisis | Best | Worst | SPY | EFA* | EEM* | AGG | GLD | XLE | XLK* |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| GFC | GLD (+23.9%) | SPY (-55.2%) | -55.2% | -60.2% | -59.1% | +7.4% | +23.9% | -47.9% | -51.4% |
| Lehman liquidity shock | GLD (+8.8%) | XLE (-31.2%) | -27.8% | -28.0% | -30.5% | -12.8% | +8.8% | -31.2% | -25.4% |
| Gold bear market | SPY (+98.3%) | GLD (-45.6%) | +98.3% | +32.4% | -10.5% | +9.9% | -45.6% | +5.0% | +105.9% |
| Oil collapse | AGG (+4.0%) | XLE (-46.7%) | -2.3% | -20.8% | -32.0% | +4.0% | -16.9% | -46.7% | +5.1% |
| 2018 trade tensions | AGG (+0.6%) | XLE (-28.4%) | -16.7% | -22.1% | -25.1% | +0.6% | -6.3% | -28.4% | -15.5% |
| COVID crash | AGG (-1.3%) | XLE (-56.1%) | -33.7% | -32.6% | -30.8% | -1.3% | -3.6% | -56.1% | -31.2% |
| COVID dash for cash | AGG (-9.6%) | XLE (-43.6%) | -19.3% | -24.0% | -23.0% | -9.6% | -10.7% | -43.6% | -16.1% |
| Bond bear market | XLE (+153.8%) | GLD (-20.1%) | +14.4% | -4.5% | -18.3% | -18.4% | -20.1% | +153.8% | +8.8% |
| China / global tightening | XLE (+103.0%) | AGG (-16.8%) | -1.0% | -19.8% | -39.8% | -16.8% | -7.6% | +103.0% | -6.6% |
| Rates 2022 | XLE (+44.5%) | SPY (-24.5%) | -24.5% | -28.1% | -29.0% | -14.4% | -7.3% | +44.5% | -33.1% |
| Gold correction 2026 | XLE (+14.4%) | GLD (-26.4%) | +8.7% | +3.7% | +6.8% | -0.1% | -26.4% | +14.4% | +21.2% |
| Hypothetical joint inflation shock | GLD (+0.0%) | XLE (-34.1%) | -25.0% | -28.6% | -28.9% | -10.0% | +0.0% | -34.1% | -19.0% |

Best/Worst are within the four-ETF universe.

## Not replayable

- Dot-com bust (2000-03-24 to 2002-10-09): Cannot be replayed: AGG starts 2003-09-29 and GLD 2004-11-18.
