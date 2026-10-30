"""Correlation tables by period, as reviewed with the owner on 30 October 2026.

Daily log-return Pearson correlations from data/clean (2005-01-04 to 2026-09-30):
- yearly_2020_2026.csv: all 21 pairs by calendar year, simple average of 2020-2026 and full 2005-2026;
- halfyear_2020_2026.csv: all 21 pairs by half-year (H1 Jan-Jun, H2 Jul-Dec) and their average;
- quarterly_four_etf.csv: pairs among SPY, AGG, GLD and XLE by quarter 2020Q1-2026Q3, with summary rows
  for 2020-2026 and 2005-2026 (average of quarterly correlations, negative quarters, lowest, highest).
2026 is January-September only. Averages are simple means of period correlations, which weight calm and
crisis periods equally; one correlation over all days can differ. Descriptive and retrospective only.
Run from the repository root: python scripts/correlation_periods.py
"""
import os, sys, json, itertools, hashlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pathlib import Path
import pandas as pd

SRC = Path("data/clean/log_returns.csv")
r = pd.read_csv(SRC, index_col=0, parse_dates=True)
out = Path("results/correlation-periods-r1"); out.mkdir(parents=True, exist_ok=True)
pairs = list(itertools.combinations(r.columns, 2))
four = [("AGG", "XLE"), ("GLD", "XLE"), ("SPY", "GLD"), ("SPY", "AGG"), ("AGG", "GLD"), ("SPY", "XLE")]
name = lambda a, b: f"{a}-{b}"


def by_period(x, keys, labels, ps):
    return pd.DataFrame({labels(k): {name(a, b): g.corr().loc[a, b] for a, b in ps} for k, g in x.groupby(keys)})


recent = r.loc["2020":"2026"]
full = {name(a, b): r.corr().loc[a, b] for a, b in pairs}

yearly = by_period(recent, recent.index.year, str, pairs)
yearly["avg_2020_2026"] = yearly.mean(axis=1); yearly["full_2005_2026"] = pd.Series(full)
yearly.round(4).to_csv(out / "yearly_2020_2026.csv")

half = by_period(recent, [recent.index.year, (recent.index.month > 6) + 1], lambda k: f"{k[0]}H{k[1]}", pairs)
half["avg_2020_2026"] = half.mean(axis=1)
half.round(4).to_csv(out / "halfyear_2020_2026.csv")

quarters = by_period(r, [r.index.year, r.index.quarter], lambda k: f"{k[0]}Q{k[1]}", four).T
q_recent = quarters.loc[[i for i in quarters.index if i >= "2020"]]
summary = {}
for label, q in [("2020-2026", q_recent), ("2005-2026", quarters)]:
    summary[f"avg {label} ({len(q)} quarters)"] = q.mean()
    summary[f"negative quarters {label}"] = (q < 0).sum()
    summary[f"lowest quarter {label}"] = q.min()
    summary[f"highest quarter {label}"] = q.max()
pd.concat([q_recent, pd.DataFrame(summary).T]).round(4).to_csv(out / "quarterly_four_etf.csv")

(out / "metadata.json").write_text(json.dumps({
    "source": str(SRC), "source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
    "first_date": str(r.index[0].date()), "last_date": str(r.index[-1].date()),
    "measure": "Pearson correlation of daily log returns",
    "notes": ["2026 covers January-September only (2026Q3 and 2026H2 have 64 trading days)",
              "averages are simple means of period correlations",
              "about +/-0.18 (half-years) and +/-0.25 (quarters) is needed to differ from zero at 5%",
              "descriptive and retrospective; not part of any frozen run"]}, indent=1))
print(f"Wrote {out}: yearly {yearly.shape}, half-year {half.shape}, quarterly {q_recent.shape[0]} quarters + summary")
