# Risk parity: long versus recent correlation windows

Convex ERC solver; walk-forward yearly re-estimation on earlier data; fixed weights within each year; 0% cost.

## Weights today (data to 2026-09-30)

| Window | SPY | XLE | AGG | GLD |
|---|---:|---:|---:|---:|
| All history (expanding) | 14.0 | 8.8 | 60.9 | 16.3 |
| 10 years | 15.4 | 10.4 | 54.9 | 19.3 |
| 5 years | 17.3 | 13.6 | 51.9 | 17.2 |
| 3 years | 18.5 | 15.7 | 50.8 | 15.0 |
| 1 year | 21.0 | 18.1 | 51.7 | 9.2 |
| EWMA half-life 1y | 15.7 | 13.8 | 58.9 | 11.7 |

## Risk taken 2016-2026 (same period for every window)

| Window | Vol % | ES99 % | Max fall % | CAGR % |
|---|---:|---:|---:|---:|
| All history (expanding) | 6.7 | 1.72 | -15.0 | 6.6 |
| 10 years | 6.9 | 1.78 | -14.6 | 6.9 |
| 5 years | 7.1 | 1.84 | -15.4 | 7.4 |
| 3 years | 7.3 | 1.90 | -15.9 | 7.6 |
| 1 year | 7.7 | 2.04 | -17.3 | 7.4 |
| EWMA half-life 1y | 7.0 | 1.82 | -15.3 | 6.9 |

## Forecast quality (each window's own test years)

| Window | Years | Avg worst risk-share gap, next year (pt) | Max gap (pt) | Avg vol forecast error % |
|---|---|---:|---:|---:|
| All history (expanding) | 2008-2026 | 16.6 | 38.7 | 40.6 |
| 10 years | 2016-2026 | 17.4 | 46.0 | 39.4 |
| 5 years | 2011-2026 | 18.2 | 42.3 | 33.2 |
| 3 years | 2009-2026 | 16.3 | 39.8 | 32.3 |
| 1 year | 2008-2026 | 18.3 | 43.3 | 50.2 |
| EWMA half-life 1y | 2008-2026 | 16.7 | 37.5 | 42.2 |

## Solver check on 2007 data

| Method | SPY | XLE | AGG | GLD |
|---|---:|---:|---:|---:|
| convex weights % | 13.0 | 7.3 | 68.6 | 11.2 |
| convex risk shares % | 25.0 | 25.0 | 25.0 | 25.0 |
| squared_gap weights % | 38.9 | 23.0 | 0.0 | 38.1 |
| squared_gap risk shares % | 33.3 | 33.3 | -0.0 | 33.3 |
