"""Exploratory study: six weighting methods replayed through every crisis episode identified so far.

Methods and weights are the full-sample (2005-2026) four-ETF comparison shown to the owner on
30 October 2026 (rounded to whole percentages; minimum CVaR is the exact mandate v3 W_rec). Each crisis
is replayed buy-and-hold from its start date with no trades, costs or reserve withdrawals, matching
quanedge.stress.stress_tests. Episode dates come from results/charts/etf_top3_drawdowns.csv (deepest
drawdowns of each ETF) plus the frozen stress scenarios. Retrospective and descriptive only: the weights
were estimated on data that include these crises. No change to policy, W_rec, the frozen run or the
verdict. Run from the repository root: python scripts/crisis_methods_study.py
"""
import hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from quanedge.config import TICKERS
from quanedge.portfolio import canonical_weights, weight_hash
from quanedge.stress import hypothetical

FOUR = ["SPY", "XLE", "AGG", "GLD"]
VALUE = 1e7
OUT = "results/crisis-methods-r1"
METHODS = {
    "Inverse variance (1/var)": {"SPY": .07, "XLE": .03, "AGG": .83, "GLD": .07},
    "Inverse volatility (1/vol)": {"SPY": .16, "XLE": .10, "AGG": .57, "GLD": .17},
    "Risk parity (ERC)": {"SPY": .14, "XLE": .09, "AGG": .61, "GLD": .16},
    "Minimum variance": {"SPY": .06, "XLE": .01, "AGG": .91, "GLD": .02},
    "Minimum CVaR (v2/v3 W_rec)": {"SPY": .058, "XLE": .002, "AGG": .88, "GLD": .06},
    "Maximum Sharpe": {"SPY": .13, "XLE": 0., "AGG": .78, "GLD": .09},
}
# (name, start, end, why it is on the list)
CRISES = [
    ("GFC", "2007-10-09", "2009-03-09", "Frozen stress scenario; SPY's deepest drawdown"),
    ("Lehman liquidity shock", "2008-09-09", "2008-10-10", "AGG's 2nd-deepest drawdown (nested in GFC)"),
    ("Gold bear market", "2011-08-22", "2015-12-17", "GLD's deepest drawdown"),
    ("Oil collapse", "2014-06-23", "2016-01-20", "XLE's deepest episode, to its 2016 oil trough"),
    ("2018 trade tensions", "2018-01-26", "2018-12-24", "EFA/EEM episode start to SPY's Dec-2018 trough"),
    ("COVID crash", "2020-02-19", "2020-03-23", "Frozen stress scenario; SPY's 3rd-deepest drawdown"),
    ("COVID dash for cash", "2020-03-06", "2020-03-18", "AGG's 3rd-deepest drawdown (nested in COVID)"),
    ("Bond bear market", "2020-08-04", "2022-10-20", "AGG's deepest drawdown, still unrecovered"),
    ("China / global tightening", "2021-02-17", "2022-10-24", "EEM's 2nd-deepest drawdown"),
    ("Rates 2022", "2022-01-03", "2022-10-12", "Frozen stress scenario; XLK's 2nd-deepest drawdown"),
    ("Gold correction 2026", "2026-01-29", "2026-07-16", "GLD's 3rd-deepest drawdown, unrecovered"),
]
UNAVAILABLE = [("Dot-com bust", "2000-03-24", "2002-10-09",
                "Cannot be replayed: AGG starts 2003-09-29 and GLD 2004-11-18")]


def replay(prices, w, start, end):
    p = prices.loc[start:end]
    if p.empty or str(p.index[0].date()) != start or str(p.index[-1].date()) != end:
        raise ValueError(f"incomplete coverage for {start} to {end}")
    growth = p / p.iloc[0]
    v = np.array([w.get(t, 0.) for t in prices.columns])
    wealth = growth.to_numpy() @ v
    contrib = v * (growth.iloc[-1].to_numpy() - 1)
    return float(contrib.sum()), float((wealth / np.maximum.accumulate(wealth) - 1).min()), dict(zip(prices.columns, contrib))


def pct(x): return f"{100 * x:+.1f}%"


def main():
    prices = pd.read_csv("data/clean/prices_clean.csv", index_col=0, parse_dates=True)[TICKERS]
    method_rows, contrib_rows, etf_rows = [], [], []
    for name, start, end, why in CRISES:
        for method, w in METHODS.items():
            ret, dd, c = replay(prices, w, start, end)
            worst = min(FOUR, key=lambda t: c[t]); best = max(FOUR, key=lambda t: c[t])
            method_rows.append(dict(crisis=name, start=start, end=end, method=method, return_pct=100 * ret,
                                    max_drawdown_pct=100 * dd, loss_usd=-VALUE * ret,
                                    largest_loss_contributor=worst, largest_gain_contributor=best))
            contrib_rows += [dict(crisis=name, method=method, ticker=t, contribution_usd=VALUE * c[t]) for t in FOUR]
        for t in TICKERS:
            ret, dd, _ = replay(prices, {t: 1.}, start, end)
            etf_rows.append(dict(crisis=name, start=start, end=end, ticker=t, in_universe=t in FOUR,
                                 return_pct=100 * ret, max_drawdown_pct=100 * dd))
    training = prices.pct_change().dropna().loc[:"2016-12-31"]  # simple returns, as in pipeline.py
    hyp = {}
    for method, w in METHODS.items():
        h = hypothetical(training, canonical_weights(w), VALUE)
        hyp[method] = h
        method_rows.append(dict(crisis="Hypothetical joint inflation shock", start="", end="", method=method,
                                return_pct=100 * h["return"], max_drawdown_pct=None, loss_usd=h["loss_usd"],
                                largest_loss_contributor=max(FOUR, key=lambda t: h["contributions_usd"][t]),
                                largest_gain_contributor=min(FOUR, key=lambda t: h["contributions_usd"][t])))
    shocks = next(iter(hyp.values()))["shocks"]
    for t in TICKERS:
        etf_rows.append(dict(crisis="Hypothetical joint inflation shock", start="", end="", ticker=t,
                             in_universe=t in FOUR, return_pct=100 * shocks[t], max_drawdown_pct=None))

    os.makedirs(OUT, exist_ok=True)
    M, E, C = pd.DataFrame(method_rows), pd.DataFrame(etf_rows), pd.DataFrame(contrib_rows)
    M.to_csv(f"{OUT}/crisis_by_method.csv", index=False)
    E.to_csv(f"{OUT}/etf_by_crisis.csv", index=False)
    C.to_csv(f"{OUT}/contributions_usd.csv", index=False)
    source = "data/clean/prices_clean.csv"
    meta = dict(source=source, source_sha256=hashlib.sha256(open(source, "rb").read()).hexdigest(),
                weights={m: dict(weights=canonical_weights(w), weight_hash=weight_hash(canonical_weights(w))) for m, w in METHODS.items()},
                crises=[dict(name=n, start=s, end=e, reason=r) for n, s, e, r in CRISES],
                unavailable=[dict(name=n, start=s, end=e, reason=r) for n, s, e, r in UNAVAILABLE],
                assumption="buy-and-hold from crisis start; no rebalancing, costs or reserve withdrawals; USD 10m",
                hypothetical="quanedge.stress.hypothetical on 2005-2016 training simple returns (as pipeline.py); deterministic, no probability",
                label="retrospective portfolio evaluation; weights estimated on a sample that contains these crises")
    with open(f"{OUT}/metadata.json", "w") as f: json.dump(meta, f, indent=2)

    order = [c[0] for c in CRISES] + ["Hypothetical joint inflation shock"]
    short = {m: m.split(" (")[0] if not m.startswith("Minimum CVaR") else "Minimum CVaR" for m in METHODS}
    ret = M.pivot(index="crisis", columns="method", values="return_pct").loc[order, list(METHODS)]
    dd = M.pivot(index="crisis", columns="method", values="max_drawdown_pct").loc[order[:-1], list(METHODS)]
    lines = ["# Six weighting methods through every crisis found so far", "",
             "Buy-and-hold from each crisis start, USD 10m, no rebalancing, costs or reserve withdrawals. Weights are the full-sample 2005-2026 estimates, so every crisis below was in the estimation data: retrospective portfolio evaluation, not a test. Prices: data/clean/prices_clean.csv.", "",
             "## Weights", "", "| Method | " + " | ".join(FOUR) + " |", "|---|" + "---:|" * 4]
    for m, w in METHODS.items():
        lines.append(f"| {m} | " + " | ".join(f"{100 * w[t]:.1f}%" for t in FOUR) + " |")
    lines += ["", "## Portfolio return over each crisis window (best method in bold)", "",
              "| Crisis | Window | " + " | ".join(short[m] for m in METHODS) + " |", "|---|---|" + "---:|" * len(METHODS)]
    windows = {n: f"{s} to {e}" for n, s, e, _ in CRISES}
    for c in order:
        best = ret.loc[c].idxmax()
        cells = [f"**{pct(ret.loc[c, m] / 100)}**" if m == best else pct(ret.loc[c, m] / 100) for m in METHODS]
        lines.append(f"| {c} | {windows.get(c, 'deterministic')} | " + " | ".join(cells) + " |")
    lines += ["", "## Deepest fall inside each window (peak-to-trough, buy-and-hold)", "",
              "| Crisis | " + " | ".join(short[m] for m in METHODS) + " |", "|---|" + "---:|" * len(METHODS)]
    for c in order[:-1]:
        lines.append(f"| {c} | " + " | ".join(pct(dd.loc[c, m] / 100) for m in METHODS) + " |")
    wins = ret.idxmax(axis=1).value_counts(); losses = ret.idxmin(axis=1).value_counts()
    lines += ["", "## Scorecard across the 12 scenarios", "", "| Method | Best of six | Worst of six | Average return | Worst return |", "|---|---:|---:|---:|---:|"]
    for m in METHODS:
        lines.append(f"| {m} | {wins.get(m, 0)} | {losses.get(m, 0)} | {pct(ret[m].mean() / 100)} | {pct(ret[m].min() / 100)} |")
    lines += ["", "## Which ETFs held up and which lost in each crisis", "",
              "Each ETF on its own, buy-and-hold over the same window. EFA, EEM and XLK are outside the mandate v3 universe and shown for context only (marked *).", "",
              "| Crisis | Best | Worst | " + " | ".join(t + ("" if t in FOUR else "*") for t in TICKERS) + " |", "|---|---|---|" + "---:|" * len(TICKERS)]
    for c in order:
        e = E[E.crisis == c].set_index("ticker").return_pct
        u = e[FOUR]
        lines.append(f"| {c} | {u.idxmax()} ({pct(u.max() / 100)}) | {u.idxmin()} ({pct(u.min() / 100)}) | " + " | ".join(pct(e[t] / 100) for t in TICKERS) + " |")
    lines += ["", "Best/Worst are within the four-ETF universe.", "",
              "## Not replayable", ""] + [f"- {n} ({s} to {e}): {r}." for n, s, e, r in UNAVAILABLE]
    open(f"{OUT}/report.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
