"""Evidence shown to the owner in conversation on 30 October 2026, saved for the deliverables (task PORT-021).

Four-ETF universe (SPY, XLE, AGG, GLD), frozen panel data/clean/prices_clean.csv.
  1. Correlations of daily log returns since 2020: full calendar years (all six pairs), and the
     calendar quarters and months with a pair below -0.3 and -0.5, with each ETF's simple return
     for that month or quarter (month-end/quarter-end adjusted closes, dividends included).
  2. "Buy low, sell high" evidence: for each ETF, the first close 30% below its running peak since
     2005, the deepest later fall and the 1-year return after that date; and the mean next-12-month
     return after a +20% trailing-12-month return versus all dates.
  3. Rebalancing-frequency evidence: GJR-GARCH(1,1) Student-t persistence (alpha + gamma/2 + beta)
     and volatility half-life per ETF (full-sample fit), share of a shock left after 5/21/63 days,
     and the EWMA lambda 0.97 half-life, effective sample and share of new information.
All results are descriptive and retrospective; none changes policy, W_rec, a frozen run or a verdict.
Run from the repository root: python scripts/session_evidence_study.py
"""
import hashlib, itertools, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from arch import arch_model

FOUR = ["SPY", "XLE", "AGG", "GLD"]
OUT = "results/session-evidence-r1"
SRC = "data/clean/prices_clean.csv"


def correlations(prices):
    lr = np.log(prices).diff().dropna().loc["2020":]
    pairs = list(itertools.combinations(FOUR, 2))
    corr = lambda g: pd.DataFrame({f"{a}-{b}": g.apply(lambda d: d[a].corr(d[b])) for a, b in pairs})
    yearly = corr(lr.groupby(lr.index.year)).rename_axis("year")
    out = {"yearly": yearly}
    for freq, name in (("Q", "quarter"), ("M", "month")):
        c = corr(lr.groupby(lr.index.to_period(freq)))
        ends = prices.groupby(prices.index.to_period(freq)).last()
        ret = (100*ends.pct_change()).loc[c.index]
        rows = []
        for period, row in c.iterrows():
            for pair, v in row.items():
                if v < -.3:
                    rows.append({name: str(period), "pair": pair, "corr": round(v, 4),
                                 **{f"{t}_return_pct": round(ret.loc[period, t], 2) for t in FOUR}})
        out[name] = pd.DataFrame(rows)
    return out


def buy_low(prices):
    rows = []
    for c in FOUR:
        p = prices[c]; dd = p/p.cummax()-1; hit = dd[dd <= -.3]
        fwd = p.shift(-252)/p-1; up = p/p.shift(252)-1
        row = {"etf": c, "next12m_after_plus20_pct": 100*fwd[up > .2].mean(), "next12m_all_pct": 100*fwd.mean(),
               "n_plus20_days": int((up > .2).sum())}
        if len(hit):
            d = hit.index[0]; later = p.loc[d:]
            row |= {"first_30pct_fall": str(d.date()), "deepest_later_fall_pct": 100*dd.loc[d:].min(),
                    "deepest_date": str(dd.loc[d:].idxmin().date()),
                    "return_1y_after_pct": 100*(p.asof(d+pd.Timedelta(days=365))/p[d]-1)}
        rows.append(row)
    return pd.DataFrame(rows)


def frequency(prices):
    r = 100*np.log(prices).diff().dropna(); rows = []
    for c in FOUR:
        f = arch_model(r[c], vol="GARCH", p=1, o=1, q=1, dist="t").fit(disp="off").params
        pers = f["alpha[1]"]+f["gamma[1]"]/2+f["beta[1]"]
        rows.append({"etf": c, "persistence": pers, "half_life_days": np.log(.5)/np.log(pers),
                     **{f"shock_left_{k}d": pers**k for k in (5, 21, 63)}})
    lam = .97
    ewma = {"lambda": lam, "half_life_days": np.log(.5)/np.log(lam), "effective_sample_days": (1+lam)/(1-lam),
            **{f"new_information_{k}d": 1-lam**k for k in (5, 21, 63)}}
    return pd.DataFrame(rows), ewma


def main():
    prices = pd.read_csv(SRC, index_col=0, parse_dates=True)[FOUR]
    os.makedirs(OUT, exist_ok=True)
    c = correlations(prices)
    c["yearly"].round(4).to_csv(f"{OUT}/corr_yearly_2020_2026.csv")
    for name in ("quarter", "month"):
        c[name].to_csv(f"{OUT}/corr_below_-0.3_by_{name}.csv", index=False)
    c["month"][c["month"]["corr"] < -.5].to_csv(f"{OUT}/corr_below_-0.5_by_month.csv", index=False)
    buy_low(prices).round(3).to_csv(f"{OUT}/buy_low_sell_high.csv", index=False)
    garch, ewma = frequency(prices)
    garch.round(4).to_csv(f"{OUT}/volatility_half_life.csv", index=False)
    json.dump({"task": "PORT-021", "source": SRC, "source_sha256": hashlib.sha256(open(SRC, "rb").read()).hexdigest(),
               "ewma_memory": ewma, "garch": "GJR-GARCH(1,1), Student-t, arch package, full sample 2005-2026, percent log returns",
               "label": "descriptive; retrospective; shown to the owner in conversation"},
              open(f"{OUT}/metadata.json", "w"), indent=2)
    print(open(f"{OUT}/buy_low_sell_high.csv").read()); print(garch.round(3)); print(ewma)
    print(len(c["quarter"]), "quarter rows,", len(c["month"]), "month rows below -0.3")


if __name__ == "__main__":
    main()
