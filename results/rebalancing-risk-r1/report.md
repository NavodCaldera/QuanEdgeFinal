# Rebalancing rules and the risk carried

Frozen panel 2005-01-03 to 2026-09-30, USD 9.6m, 0% cost, no reserve withdrawals. Risk measured on each rule's own daily path. Retrospective and descriptive.

Weights drift between trades: w_i,t = w_i,t-1 (1+R_i,t)/(1+R_p,t). A trade restores the target and turns over sum_i |target_i - w_i,t| of NAV. Equity risk share = sum over SPY, XLE of w_i (S w)_i / (w'S w), with S the trailing 252-day covariance at each month end. Max drift = largest gap between any ETF's weight and its target, in percentage points.

## Minimum CVaR (W_rec)

| Rule | Vol % | 1-day ES99 $ | Worst month % | Worst year % | Max fall % | GFC fall % | Max drift pt | Max equity wt % | Max equity risk share % | Trades/yr | Turnover x/yr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Daily | 5.1 | 124,433 | -12.2 | -16.0 | -17.0 | -13.2 | 0.0 | 6.0 | 15.9 | 251.61 | 0.39 |
| Monthly | 5.1 | 124,751 | -12.3 | -16.0 | -17.0 | -13.3 | 2.0 | 6.8 | 15.9 | 12.01 | 0.08 |
| Quarterly | 5.1 | 124,891 | -12.4 | -16.0 | -17.0 | -13.4 | 2.6 | 7.3 | 15.9 | 4.00 | 0.05 |
| Quarterly + 5-pt band (current) | 5.1 | 124,891 | -12.4 | -16.0 | -17.0 | -13.4 | 2.6 | 7.3 | 15.9 | 4.00 | 0.05 |
| Annual | 5.1 | 124,856 | -12.1 | -16.1 | -17.0 | -13.2 | 3.6 | 8.0 | 18.5 | 1.01 | 0.03 |
| Band only, 5 pt | 5.1 | 125,920 | -12.3 | -16.1 | -17.1 | -13.3 | 5.0 | 10.9 | 29.9 | 0.18 | 0.02 |
| Band only, 10 pt | 5.1 | 126,000 | -11.3 | -16.1 | -17.1 | -13.4 | 10.0 | 15.8 | 51.6 | 0.14 | 0.03 |
| Never (buy-and-hold) | 5.6 | 139,376 | -11.3 | -15.8 | -17.0 | -13.4 | 29.7 | 20.7 | 37.7 | 0.00 | 0.00 |

## Risk parity

| Rule | Vol % | 1-day ES99 $ | Worst month % | Worst year % | Max fall % | GFC fall % | Max drift pt | Max equity wt % | Max equity risk share % | Trades/yr | Turnover x/yr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Daily | 7.0 | 169,180 | -15.2 | -12.9 | -18.9 | -18.9 | 0.0 | 22.9 | 76.6 | 251.61 | 1.15 |
| Monthly | 6.9 | 164,464 | -14.8 | -13.4 | -19.1 | -19.1 | 5.5 | 26.7 | 76.6 | 12.01 | 0.24 |
| Quarterly | 6.9 | 161,897 | -13.7 | -13.4 | -19.1 | -19.1 | 7.0 | 28.6 | 79.4 | 4.00 | 0.14 |
| Quarterly + 5-pt band (current) | 7.0 | 165,273 | -13.9 | -13.5 | -19.1 | -19.1 | 4.7 | 28.1 | 79.4 | 4.14 | 0.15 |
| Annual | 6.8 | 160,640 | -13.7 | -12.7 | -18.4 | -18.4 | 9.0 | 29.8 | 81.2 | 1.01 | 0.08 |
| Band only, 5 pt | 7.0 | 166,086 | -13.9 | -12.3 | -17.9 | -17.9 | 5.0 | 29.6 | 80.7 | 0.60 | 0.07 |
| Band only, 10 pt | 6.8 | 161,898 | -13.7 | -12.4 | -18.0 | -18.0 | 10.0 | 31.1 | 83.6 | 0.23 | 0.05 |
| Never (buy-and-hold) | 8.5 | 209,206 | -15.5 | -15.5 | -21.4 | -21.4 | 36.2 | 42.8 | 81.8 | 0.00 | 0.00 |

## Inverse variance

| Rule | Vol % | 1-day ES99 $ | Worst month % | Worst year % | Max fall % | GFC fall % | Max drift pt | Max equity wt % | Max equity risk share % | Trades/yr | Turnover x/yr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Daily | 5.2 | 127,538 | -12.8 | -14.1 | -15.3 | -14.8 | 0.0 | 10.0 | 37.1 | 251.61 | 0.58 |
| Monthly | 5.2 | 127,443 | -12.9 | -14.1 | -15.4 | -14.9 | 3.0 | 11.7 | 37.1 | 12.01 | 0.12 |
| Quarterly | 5.2 | 127,027 | -13.0 | -14.1 | -15.3 | -14.9 | 3.9 | 12.9 | 37.1 | 4.00 | 0.07 |
| Quarterly + 5-pt band (current) | 5.2 | 127,027 | -13.0 | -14.1 | -15.3 | -14.9 | 3.9 | 12.9 | 37.1 | 4.00 | 0.07 |
| Annual | 5.2 | 126,478 | -12.6 | -13.8 | -15.1 | -14.6 | 4.9 | 13.4 | 47.2 | 1.01 | 0.04 |
| Band only, 5 pt | 5.2 | 127,220 | -12.5 | -13.6 | -14.9 | -14.9 | 5.0 | 16.1 | 46.4 | 0.28 | 0.03 |
| Band only, 10 pt | 5.3 | 127,884 | -12.2 | -13.9 | -15.7 | -15.7 | 10.0 | 20.2 | 72.8 | 0.14 | 0.03 |
| Never (buy-and-hold) | 5.9 | 146,431 | -12.2 | -13.4 | -15.7 | -15.7 | 32.7 | 28.6 | 55.8 | 0.00 | 0.00 |
