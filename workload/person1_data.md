# Person 1: Data

**Mission:** deliver a frozen, reproducible, documented data set that everyone else builds on. If the data is wrong, every downstream number is wrong. This role goes first.

## Code and files owned

| Path | Purpose |
|---|---|
| `quanedge/data/sources.py` | Downloads from approved sources (yfinance, FRED, World Bank) |
| `quanedge/data/cleaning.py` | Price validation, NYSE calendar audit, returns, DTB3 conversion, macro alignment |
| `quanedge/data/anomalies.py` | Stale prices, jumps, reversals, volatility regime shifts, data-quality log |
| `quanedge/data/stationarity.py` | ADF, KPSS, ARCH-LM tests per asset and for the portfolio |
| `quanedge/data/manifest.py` | SHA-256 manifest of every data file |
| `quanedge/data/run.py`, `enrich.py` | One-command data rebuild |
| `quanedge/data/__init__.py` | Loader functions used by everyone else (`load_log_returns`, `load_risk_free_rate`, ...) |
| `data/raw/`, `data/cache/`, `data/clean/` | Frozen snapshots and clean outputs |
| `data/data_dictionary.md` | Data dictionary |
| `results/data/data_summary.md`, `top_tail_events.md` | Data-quality report |

## Tasks

### 1. Collect ETF and macroeconomic data
- Download adjusted close prices for the seven ETFs: SPY, EFA, EEM, AGG, GLD, XLE, XLK.
- Download dividend history separately (adjusted prices hide income; Person 2 needs it for the distribution-yield KPI).
- Download FRED series: DTB3 (risk-free proxy), CPIAUCSL (inflation), DGS10 (10-year yield), FEDFUNDS, VIXCLS. Use T10YIE only as a reasonableness check if time allows.
- Download World Bank macro context for the memo (`data/raw/worldbank_usa.csv`).
- Use **approved sources only**. Record each source in `data/raw/source_inventory.json`.
- Save each download as a dated snapshot with retrieval time and SHA-256 hash (`*.meta.json`). The app must never call yfinance at runtime.
- Snapshot end is **2026-09-30** (`snapshot_end` in `config/final.yaml`). Data after that date belongs only in `monitoring/`.

### 2. Clean prices, dividends and dates
- Validate prices: no non-positive values, no duplicate dates, monotonic index (`validate_price_data`).
- Align trading calendars across all seven ETFs before building portfolio returns. Document NYSE holidays and any non-overlapping days in `data/clean/calendar_audit.csv`.
- Convert DTB3 from discount basis to bond-equivalent yield before turning it into a daily rate (`discount_to_bond_equivalent_yield`).
- Align monthly and daily macro series to the trading calendar. Log every forward-fill in `data/clean/macro_ffill_log.csv`.
- **Flag, never silently delete.** Stale or flat prices, implausible jumps, sharp reversals and structural breaks go into `data/clean/anomaly_log.csv` and `data_quality_log.csv` with the handling decision.
- No manual edits to downloaded files. Every cleaning step must be reproducible from code.

### 3. Calculate returns
- Produce `simple_returns.csv` and `log_returns.csv` from adjusted prices.
- Log returns are used for statistical work. Portfolio returns are aggregated across assets in simple returns, then converted to log. Write down where and why each is used so Persons 2 and 3 apply it the same way.
- Run stationarity tests (at least ADF; KPSS and ARCH-LM as extras) on every asset and on the portfolio return series. Save to `stationarity_tests.csv`.

### 4. Data dictionary and data-quality report
- `data/data_dictionary.md`: every file, column, unit, frequency, source, transformation and date range.
- `results/data/data_summary.md`: row counts, date coverage, missing values, anomalies found and how each was handled, ADF results.
- `results/data/top_tail_events.md`: largest daily losses per asset with dates, so the team can sanity-check them against known events (2008, March 2020, 2022).
- `data/clean/data_manifest.json` and `price_provenance.json`: hashes that `verify.py` checks.

## Handoffs

| To | What | When |
|---|---|---|
| Person 2 | Clean simple/log returns, risk-free rate, dividend history | After the snapshot is frozen |
| Person 3 | Clean log returns, VIX, DGS10 for rate sensitivity, list of known anomalies | Same time |
| Person 4 | Loader functions, manifest, `python -m quanedge.data.run --check-only` | Same time |
| Person 5 | Data dictionary, data-quality report, source list for the report's data section | Before report draft |

## Tests to keep green
- `tests/test_data_pipeline.py`: return identity, calendar handling, rebuild from snapshots.
- `tests/test_data_quality.py`: anomaly flags, stale-price detection.
- `tests/test_data_robustness.py`: edge cases (gaps, duplicates, missing dates).

## Done when
- [ ] `python -m quanedge.data.run` rebuilds every clean file offline from snapshots.
- [ ] `python -m quanedge.data.run --check-only` passes and the manifest hashes match.
- [ ] Every anomaly is flagged and documented, none silently removed.
- [ ] ADF results are reported for every modelled series.
- [ ] Data dictionary and data-quality report are complete and reviewed by Person 5.

## Questions you must answer in Q&A
- Why adjusted close and not raw close? How are dividends handled?
- Why log returns for statistics but simple returns for portfolio aggregation?
- How did you convert DTB3 and why does it matter?
- What did you do with outliers? Show one flagged event and its handling.
- Can a judge reproduce your data exactly? How (snapshots plus hashes)?
- What do the ADF results say, and why does stationarity matter for VaR?
