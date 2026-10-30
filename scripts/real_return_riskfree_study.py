"""Exploratory study: real return (FRED CPI) and reward for risk over the 3-month T-bill (FRED DTB3) (task PORT-013).

Approved sources only (brief section 9.1): ETF prices from Yahoo Finance, CPIAUCSL and DTB3 from
FRED, all from the frozen snapshot in data/clean (2005-01-03 to 2026-09-30).

- Inflation: ratio of CPIAUCSL index levels as published by each date (data/clean/macro_clean.csv
  already lags CPI to its release), never the index level as a rate.
- Real return: (1 + nominal) / (1 + inflation) - 1 over the same dates.
- Risk-free: rf_daily_effective, DTB3 converted from discount basis to bond-equivalent yield and
  then to a daily rate (quanedge.data); compounded daily for the T-bill wealth path.
- Excess return: portfolio CAGR minus T-bill CAGR; Sharpe = annualised mean daily excess return /
  annualised volatility of daily excess return (quanedge.portfolio.kpis convention).

Portfolios are held at fixed weights with quarterly plus 5-point drift rebalancing, 0% cost (v3),
no reserve withdrawals. Retrospective and descriptive; no change to policy, W_rec, runs or verdict.
Run from the repository root: python scripts/real_return_riskfree_study.py
"""
import hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from quanedge.config import TICKERS
from quanedge.portfolio import canonical_weights, weight_hash, replay, tail_weights

OUT = "results/real-return-rf-r1"
RUN = "results/final-v3-20261030"
FOUR = ["SPY", "XLE", "AGG", "GLD"]
PORTFOLIOS = {
    "Min CVaR (v3 W_rec)": json.load(open(f"{RUN}/selected/weights.json"))["weights"],
    "Risk parity": json.load(open(f"{RUN}/A1_near_parity/weights.json"))["weights"],
    "SPY 25 / AGG 50 / GLD 25": {"SPY": .25, "AGG": .50, "GLD": .25},
    "SPY 35 / AGG 50 / GLD 15": {"SPY": .35, "AGG": .50, "GLD": .15},
    "SPY 28 / AGG 42 / GLD 30 (4% real, raw means)": {"SPY": .28, "AGG": .42, "GLD": .30},
    "60/40 SPY/AGG": {"SPY": .60, "AGG": .40},
    "100% SPY": {"SPY": 1.}, "100% AGG": {"AGG": 1.}, "100% GLD": {"GLD": 1.},
}
PERIODS = {"2005-2026": ("2005-01-03", "2026-09-30"), "2017-2026": ("2017-01-01", "2026-09-30")}
YEARLY = ["Min CVaR (v3 W_rec)", "Risk parity", "SPY 25 / AGG 50 / GLD 25"]


def annualise(growth, start, end):
    return float(growth**(365.25/(pd.Timestamp(end)-pd.Timestamp(start)).days)-1)


def summary(r, rf, cpi, start, end):
    r, rf = r.loc[start:end], rf.loc[start:end]
    first, last = r.index[0], r.index[-1]
    base = cpi.loc[:first].iloc[-2] if len(cpi.loc[:first]) > 1 else cpi.iloc[0]   # CPI at the prior close
    nominal = annualise((1+r).prod(), first-pd.Timedelta(days=1), last)
    bill = annualise((1+rf).prod(), first-pd.Timedelta(days=1), last)
    inflation = annualise(cpi.loc[last]/base, first-pd.Timedelta(days=1), last)
    excess = r-rf; wealth = (1+r).cumprod(); loss = -r.to_numpy()
    downside = np.sqrt(np.mean(np.minimum(excess, 0)**2))*np.sqrt(252)
    return {"nominal_cagr": nominal, "us_cpi_inflation": inflation, "real_cagr": (1+nominal)/(1+inflation)-1,
            "tbill_cagr": bill, "real_tbill": (1+bill)/(1+inflation)-1, "excess_over_tbill": nominal-bill,
            "volatility": float(r.std()*np.sqrt(252)),
            "sharpe": float(excess.mean()*252/(excess.std()*np.sqrt(252))),
            "sortino_vs_tbill": float(excess.mean()*252/downside),
            "max_drawdown": float((wealth/wealth.cummax()-1).min()), "es99_1d": float(tail_weights(loss) @ loss),
            "excess_per_drawdown": (nominal-bill)/abs(float((wealth/wealth.cummax()-1).min())),
            "years_beating_tbill": None}


def yearly(r, rf, cpi):
    rows = []
    for y in sorted(set(r.index.year)):
        x, b = r.loc[str(y)], rf.loc[str(y)]
        prior = cpi.loc[:x.index[0]].iloc[-2] if len(cpi.loc[:x.index[0]]) > 1 else cpi.iloc[0]
        ret, bill, infl = float((1+x).prod()-1), float((1+b).prod()-1), float(cpi.loc[x.index[-1]]/prior-1)
        rows.append({"year": y, "return": ret, "us_cpi": infl, "real": (1+ret)/(1+infl)-1, "tbill": bill, "excess": ret-bill})
    return pd.DataFrame(rows).set_index("year")


def main():
    prices = pd.read_csv("data/clean/prices_clean.csv", index_col=0, parse_dates=True)[TICKERS]
    macro = pd.read_csv("data/clean/macro_clean.csv", index_col=0, parse_dates=True)
    R = prices.pct_change().dropna()
    rf = macro.rf_daily_effective.reindex(R.index); cpi = macro.CPIAUCSL.reindex(prices.index)
    if rf.isna().any() or cpi.isna().any():
        raise ValueError("macro series do not cover every trading date")
    rows, years, paths = [], {}, {}
    for name, w in PORTFOLIOS.items():
        w = canonical_weights(w); r = replay(R, w, cost=0., drift=.05)["return"]; paths[name] = r
        y = yearly(r, rf, cpi)
        for label, (s, e) in PERIODS.items():
            row = summary(r, rf, cpi, s, e)
            yy = y.loc[pd.Timestamp(s).year:pd.Timestamp(e).year]
            row["years_beating_tbill"] = f"{int((yy.excess > 0).sum())}/{len(yy)}"
            row["years_real_negative"] = f"{int((yy.real < 0).sum())}/{len(yy)}"
            rows.append({"portfolio": name, "period": label, **row})
        if name in YEARLY:
            years[name] = y
    M = pd.DataFrame(rows); os.makedirs(OUT, exist_ok=True)
    M.to_csv(f"{OUT}/summary.csv", index=False, float_format="%.6g")
    pd.concat(years, names=["portfolio"]).to_csv(f"{OUT}/yearly.csv", float_format="%.6g")
    sources = {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in ("data/clean/prices_clean.csv", "data/clean/macro_clean.csv")}
    json.dump({"task": "PORT-013", "sources_sha256": sources,
               "series": {"inflation": "FRED CPIAUCSL, index ratio as published by each date",
                          "risk_free": "FRED DTB3, bond-equivalent yield, daily (rf_daily_effective)",
                          "prices": "Yahoo Finance adjusted close"},
               "weights": {k: {"weights": canonical_weights(v), "weight_hash": weight_hash(canonical_weights(v))} for k, v in PORTFOLIOS.items()},
               "assumptions": "quarterly + 5-pt drift rebalancing, 0% cost, no reserve; partial 2026 to 30 September",
               "label": "retrospective portfolio evaluation"}, open(f"{OUT}/metadata.json", "w"), indent=2)

    pct = lambda v: f"{100*v:.2f}%"
    lines = ["# Real return (US CPI) and reward over the 3-month T-bill", "",
             "Sources: Yahoo Finance adjusted closes; FRED CPIAUCSL (as published); FRED DTB3. Fixed weights, quarterly + 5-pt band rebalancing, 0% cost, no reserve. Retrospective.", ""]
    for label in PERIODS:
        lines += [f"## {label}", "", "| Portfolio | Nominal CAGR | Real CAGR | Excess over T-bill | Volatility | Sharpe | Max fall | ES99 1-day | Years beating T-bill | Years with negative real return |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        sub = M[M.period == label]
        first = sub.iloc[0]
        for _, r in sub.iterrows():
            lines.append(f"| {r.portfolio} | {pct(r.nominal_cagr)} | {pct(r.real_cagr)} | {pct(r.excess_over_tbill)} | {pct(r.volatility)} | {r.sharpe:.2f} | {pct(r.max_drawdown)} | {pct(r.es99_1d)} | {r.years_beating_tbill} | {r.years_real_negative} |")
        lines += ["", f"US CPI inflation {pct(first.us_cpi_inflation)} a year; T-bill {pct(first.tbill_cagr)} a year ({pct(first.real_tbill)} real).", ""]
    for name, y in years.items():
        lines += [f"## Year by year: {name}", "", "| Year | Return | US CPI | Real | T-bill | Excess |", "|---|---:|---:|---:|---:|---:|"]
        for yr, r in y.iterrows():
            lines.append(f"| {yr}{'*' if yr == 2026 else ''} | {pct(r['return'])} | {pct(r.us_cpi)} | {pct(r.real)} | {pct(r.tbill)} | {pct(r.excess)} |")
        lines.append("")
    lines.append("\\*2026 to 30 September.")
    open(f"{OUT}/report.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
