"""Exploratory study: year-by-year correlations of daily log returns for the four v3 ETFs (task PORT-024).

Frozen panel data/clean/log_returns.csv (Yahoo Finance adjusted closes), 2005-01-04 to 2026-09-30;
2026 is partial (to 30 September). Pearson correlation of daily log returns within each calendar year.
Descriptive only. Run from the repository root: python scripts/yearly_correlation_study.py
"""
import hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import pandas as pd

SOURCE = "data/clean/log_returns.csv"
OUT = "results/yearly-correlation-r1"
PAIRS = [("AGG", "XLE"), ("GLD", "XLE"), ("SPY", "GLD"), ("SPY", "AGG"), ("AGG", "GLD"), ("SPY", "XLE")]


def table(r):
    rows = [{"year": y, **{f"{a}-{b}": g[a].corr(g[b]) for a, b in PAIRS}, "trading_days": len(g)}
            for y, g in r.groupby(r.index.year)]
    rows.append({"year": "full sample", **{f"{a}-{b}": r[a].corr(r[b]) for a, b in PAIRS}, "trading_days": len(r)})
    return pd.DataFrame(rows).set_index("year")


def main():
    r = pd.read_csv(SOURCE, index_col=0, parse_dates=True)
    t = table(r); os.makedirs(OUT, exist_ok=True)
    t.to_csv(f"{OUT}/yearly_correlation.csv", float_format="%.4f")
    json.dump({"task": "PORT-024", "source": SOURCE, "source_sha256": hashlib.sha256(open(SOURCE, "rb").read()).hexdigest(),
               "method": "Pearson correlation of daily log returns within each calendar year",
               "partial_year": "2026 to 2026-09-30", "label": "descriptive"}, open(f"{OUT}/metadata.json", "w"), indent=2)
    cols = [f"{a}-{b}" for a, b in PAIRS]
    lines = ["# Year-by-year correlation of daily log returns", "",
             "Yahoo Finance adjusted closes, frozen panel. 2026 to 30 September (*).", "",
             "| Year | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for y, row in t.iterrows():
        label = f"**{y}**" if y == "full sample" else f"{y}{'*' if y == 2026 else ''}"
        lines.append(f"| {label} | " + " | ".join(f"{row[c]:.2f}" for c in cols) + " |")
    open(f"{OUT}/report.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
