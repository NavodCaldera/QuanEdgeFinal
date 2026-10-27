# Data dictionary

Dates use ISO 8601; ticker order SPY, EFA, EEM, AGG, GLD, XLE, XLK.

| File | Rows | Meaning / units |
|---|---:|---|
| anomaly_log.csv | 242 | Retained flagged observations and date-level contextual labels |
| calendar_audit.csv | 203 | Missing weekdays classified by market closures |
| data_quality_checks.csv | 3 | Quality rule/count summary |
| data_quality_log.csv | 36 | Stale, reversal and volatility-shift findings |
| log_returns.csv | 5,469 | Daily natural-log returns; asset statistical inputs |
| macro_clean.csv | 5,470 | FRED aligned levels/percent quotes and derived decimal daily risk-free rates |
| macro_ffill_log.csv | 78 | Explicit macro carry-forward and source-date records |
| prices_clean.csv | 5,470 | Dividend/split-adjusted USD close; positive, common calendar |
| simple_returns.csv | 5,469 | Daily simple fractional returns; cross-asset aggregation and P&L |
| stationarity_tests.csv | 22 | ADF, fixed-lag ADF, KPSS, ARCH diagnostics; placeholder row is not recommended weights |
| worldbank_macro.csv | 66 | Annual World Bank US macro percentages |

Adjusted prices already incorporate distributions and expenses. Separate raw/distributions.csv contains unadjusted close and cash dividend per share, used only for yield. No expense ratio is deducted again.
Macro levels are revised modern series with approximate publication lags, not historical vintages. CPI inflation is the ratio of index levels minus one. Dates before macro release availability remain unavailable.
Price retrieval time is in the cache sidecar. Macro HTTP retrieval time was not separately captured; source_inventory.json records snapshot file-write times explicitly.
