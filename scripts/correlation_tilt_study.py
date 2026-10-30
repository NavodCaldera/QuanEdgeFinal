"""Exploratory study: risk parity with a correlation-threshold tilt into gold (task PORT-017).

Owner's proposal: start from risk parity (volatility + correlation); when the stock-bond
correlation leaves +/-0.3, change the proportions, e.g. sell SPY and buy GLD in 2022 Q1.

Rule fixed in this docstring before the first run (four ETFs, mandate v3 universe):
  Base     Long-only equal-risk-contribution weights on the sample covariance of the last 750
           daily simple returns (fewer at the start), re-estimated at each quarter-end close
           from data through that close. First decision at the close of 2006-12-29 (500 days).
  Signal   63-day correlation of SPY and AGG daily returns at the same close.
  Tilt     rho > +0.3 (bonds stop hedging): move 10 points from SPY to GLD (all SPY if less).
           Two-sided variant also acts on rho < -0.3 (bonds hedge well): move 10 points GLD -> SPY.
  Trading  Targets set at the decision close apply from the next day; weights drift in between;
           0% cost (mandate v3), no reserve withdrawals, so paths are comparable.
Comparisons: the same base without tilt, and the v3 static near-parity weights (full-sample
estimate, quarterly + 5-point drift via portfolio.replay) from the same start date.
A threshold/window/size grid is reported only to show how fragile the result is; no variant
from it is selected.

Retrospective portfolio evaluation: the owner has seen 2022 and the whole sample, and the
proposal was prompted by 2022. No change to policy, W_rec, the frozen run or any verdict.
Run from the repository root: python scripts/correlation_tilt_study.py
"""
import hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from quanedge.comparison import risk_parity
from quanedge.portfolio import replay, tail_weights, canonical_weights, weight_hash

FOUR = ["SPY", "XLE", "AGG", "GLD"]
OUT = "results/correlation-tilt-r1"
RUN = "results/final-v3-20261030"
WINDOW, MIN_HISTORY = 750, 500
CRISES = {"GFC": ("2007-10-09", "2009-03-09"), "COVID": ("2020-02-19", "2020-03-23"),
          "2022": ("2022-01-03", "2022-10-12")}


def simulate(R, threshold=.3, corr_window=63, size=.10, two_sided=False, tilt=True):
    """Daily path; returns (returns, events) where events lists each quarter-end decision."""
    x = R.to_numpy(); dates = R.index; s, a, g = (FOUR.index(c) for c in ("SPY", "AGG", "GLD"))
    q = dates.to_period("Q"); decide = np.r_[q[1:] != q[:-1], False]
    def target(i):
        w = risk_parity(np.cov(x[max(0, i+1-WINDOW):i+1].T)); rho = np.corrcoef(x[i+1-corr_window:i+1, [s, a]].T)[0, 1]
        move = 0.
        if tilt and rho > threshold:
            move = min(size, w[s]); w[s] -= move; w[g] += move
        elif tilt and two_sided and rho < -threshold:
            move = -min(size, w[g]); w[g] += move; w[s] -= move
        return w, rho, move
    w, rho, move = target(MIN_HISTORY-1); pos = w.copy(); rets, events = [], [(dates[MIN_HISTORY-1], rho, move, *w)]
    for i in range(MIN_HISTORY, len(x)):
        old = pos.sum(); pos = pos*(1+x[i]); rets.append(pos.sum()/old-1)
        if decide[i]:
            w, rho, move = target(i); pos = w*pos.sum(); events.append((dates[i], rho, move, *w))
    return (pd.Series(rets, dates[MIN_HISTORY:]),
            pd.DataFrame(events, columns=["date", "rho_spy_agg", "spy_to_gld", *FOUR]).set_index("date"))


def metrics(r):
    w = (1+r).cumprod(); years = (r.index[-1]-r.index[0]).days/365.25; loss = -r.to_numpy()
    out = {"CAGR %": 100*(w.iloc[-1]**(1/years)-1), "Vol %": 100*r.std()*np.sqrt(252),
           "Max fall %": 100*(w/w.cummax()-1).min(), "ES99 1d %": 100*tail_weights(loss) @ loss}
    for k, (a, b) in CRISES.items():
        out[f"{k} %"] = 100*((1+r.loc[a:b]).prod()-1)
    return out


def main():
    prices = pd.read_csv("data/clean/prices_clean.csv", index_col=0, parse_dates=True)[FOUR]
    R = prices.pct_change().dropna()
    paths = {"Risk parity, no tilt": simulate(R, tilt=False),
             "Tilt SPY->GLD when rho > 0.3": simulate(R),
             "Two-sided tilt (+/-0.3)": simulate(R, two_sided=True)}
    start = paths["Risk parity, no tilt"][0].index[0]
    static = json.load(open(f"{RUN}/A1_near_parity/weights.json"))["weights"]
    rows = [{"Strategy": k, **metrics(v[0])} for k, v in paths.items()]
    rows.append({"Strategy": "Static near parity (v3, full-sample weights)",
                 **metrics(replay(R.loc[start:], {c: static[c] for c in FOUR}, cost=0.)["return"])})
    table = pd.DataFrame(rows).set_index("Strategy")

    # Each tilt decision and what the next quarter did (tilt P&L ~ size * (GLD - SPY)).
    ev = paths["Two-sided tilt (+/-0.3)"][1]
    nxt = prices.loc[ev.index].pct_change().shift(-1)
    ev = ev.assign(next_q_SPY=nxt["SPY"], next_q_GLD=nxt["GLD"])
    ev["tilt_pnl_pct"] = 100*ev["spy_to_gld"]*(ev["next_q_GLD"]-ev["next_q_SPY"])
    fired = ev[ev["spy_to_gld"] != 0]

    base = metrics(paths["Risk parity, no tilt"][0])
    grid = []
    for th in (.2, .3, .4):
        for cw in (63, 126):
            for size in (.05, .10, .20):
                m = metrics(simulate(R, th, cw, size)[0])
                grid.append({"threshold": th, "corr_window": cw, "size": size,
                             "dCAGR_pt": m["CAGR %"]-base["CAGR %"], "dMaxFall_pt": m["Max fall %"]-base["Max fall %"],
                             "d2022_pt": m["2022 %"]-base["2022 %"]})
    grid = pd.DataFrame(grid)

    os.makedirs(OUT, exist_ok=True)
    table.to_csv(f"{OUT}/summary.csv"); ev.to_csv(f"{OUT}/decisions.csv"); grid.to_csv(f"{OUT}/sensitivity.csv", index=False)
    sw = canonical_weights({c: static[c] for c in FOUR})
    json.dump({"task": "PORT-017", "source": "data/clean/prices_clean.csv",
               "source_sha256": hashlib.sha256(open("data/clean/prices_clean.csv", "rb").read()).hexdigest(),
               "start": str(start.date()), "end": str(R.index[-1].date()),
               "rule": {"base": f"ERC on sample covariance, last {WINDOW} days, quarterly", "signal": "63-day corr(SPY, AGG)",
                        "threshold": .3, "size": .10, "trade_timing": "decision close, applies next day"},
               "static_comparison": {"weights": sw, "weight_hash": weight_hash(sw)},
               "cost": 0.0, "reserve": "not withdrawn",
               "label": "retrospective portfolio evaluation; exploratory, prompted by 2022"},
              open(f"{OUT}/metadata.json", "w"), indent=2)
    pd.set_option("display.width", 200)
    print(table.round(2)); print("\nDecisions with a tilt:\n", fired.round(3))
    print("\n2021-2023 decisions:\n", ev.loc["2021":"2023", ["rho_spy_agg", "spy_to_gld", "next_q_SPY", "next_q_GLD"]].round(3))
    print("\nSensitivity vs no tilt:\n", grid.round(2))
    print(f"\nTilt quarters: {len(fired)}, helped in {(fired.tilt_pnl_pct > 0).sum()}, total {fired.tilt_pnl_pct.sum():.2f} pt")


if __name__ == "__main__":
    main()
