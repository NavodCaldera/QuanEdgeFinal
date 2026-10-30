"""Exploratory study: rebalance risk parity on a negative-correlation trigger (task PORT-019).

Owner's proposal: when two ETFs move against each other (correlation below -0.5), sell the
one that went up and buy the one that went down, and rebalance the risk-parity weights.

Rules fixed in this docstring before the first run. Target = v3 static near parity
(SPY 14.0 / AGG 60.9 / GLD 16.3 / XLE 8.8, results/final-v3-20261030/A1_near_parity).
Trigger: at a month-end close, the correlation of daily log returns within that calendar
month is below -0.5 for at least one of the six pairs. Trades happen at that close and the
new weights apply from the next day. 0% cost, no reserve withdrawals, weights drift between trades.
  Normal          Quarter-end rebalance to target, plus any day an ETF drifts 5 points (portfolio.replay rule).
  Trigger only    Rebalance to target only at triggered month-ends (this sells the winners and buys the losers).
  Normal+trigger  Normal rule, plus a rebalance to target at triggered month-ends.
  Contrarian tilt Normal rule; at a triggered month-end, for each pair below -0.5, also move 5 points
                  from the pair's better month-return ETF to the worse one (beyond target), held until the
                  next normal rebalance.
  Buy-and-hold    Never rebalance (reference).
Weights are full-sample estimates, so every path is a retrospective portfolio evaluation.
Run from the repository root: python scripts/negcorr_rebalance_study.py
"""
import hashlib, itertools, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from quanedge.portfolio import tail_weights, canonical_weights, weight_hash

FOUR = ["SPY", "XLE", "AGG", "GLD"]
OUT = "results/negcorr-rebalance-r1"
RUN = "results/final-v3-20261030"
THRESHOLD, TILT, BAND = -.5, .05, .05
CRISES = {"GFC": ("2007-10-09", "2009-03-09"), "COVID": ("2020-02-19", "2020-03-23"),
          "2022": ("2022-01-03", "2022-10-12")}


def triggers(prices):
    """Month-end date -> list of (winner, loser, corr) for pairs below THRESHOLD in that month."""
    lr = np.log(prices).diff().dropna(); simple = prices.pct_change()
    out = {}
    for m, d in lr.groupby(lr.index.to_period("M")):
        end = d.index[-1]; month_ret = (1+simple.loc[d.index]).prod()-1; hits = []
        for a, b in itertools.combinations(FOUR, 2):
            c = d[a].corr(d[b])
            if c < THRESHOLD:
                hits.append((a, b, c) if month_ret[a] >= month_ret[b] else (b, a, c))
        if hits:
            out[end] = hits
    return out


def simulate(R, target, rule, trig):
    t = np.array([target[c] for c in FOUR]); w = t.copy(); x = R.to_numpy(); dates = R.index
    rets, turn = np.empty(len(R)), np.zeros(len(R))
    for i in range(len(R)):
        rp = float(w @ x[i]); rets[i] = rp; w = w*(1+x[i])/(1+rp); new = None
        quarter = i == len(dates)-1 or dates[i+1].quarter != dates[i].quarter
        normal = quarter or np.max(np.abs(w-t)) > BAND
        hit = dates[i] in trig
        if rule == "Normal" and normal: new = t.copy()
        elif rule == "Trigger only" and hit: new = t.copy()
        elif rule == "Normal+trigger" and (normal or hit): new = t.copy()
        elif rule == "Contrarian tilt":
            if normal: new = t.copy()
            if hit:
                new = (new if new is not None else w).copy()
                for win, lose, _ in trig[dates[i]]:
                    mv = min(TILT, new[FOUR.index(win)]); new[FOUR.index(win)] -= mv; new[FOUR.index(lose)] += mv
        if new is not None:
            turn[i] = np.abs(new-w).sum(); w = new
    return pd.Series(rets, dates), pd.Series(turn, dates)


def metrics(r, turn):
    w = (1+r).cumprod(); years = (r.index[-1]-r.index[0]).days/365.25; loss = -r.to_numpy()
    out = {"CAGR %": 100*(w.iloc[-1]**(1/years)-1), "Vol %": 100*r.std()*np.sqrt(252),
           "Max fall %": 100*(w/w.cummax()-1).min(), "ES99 1d %": 100*tail_weights(loss) @ loss}
    for k, (a, b) in CRISES.items():
        if r.index[0] <= pd.Timestamp(a):
            out[f"{k} %"] = 100*((1+r.loc[a:b]).prod()-1)
    out |= {"Trades/yr": (turn > 0).sum()/years, "Turnover x/yr": turn.sum()/years}
    return out


def main():
    prices = pd.read_csv("data/clean/prices_clean.csv", index_col=0, parse_dates=True)[FOUR]
    R = prices.pct_change().dropna()
    raw = json.load(open(f"{RUN}/A1_near_parity/weights.json"))["weights"]
    target = {c: raw[c] for c in FOUR}
    trig = triggers(prices)
    rules = ["Normal", "Trigger only", "Normal+trigger", "Contrarian tilt", "Buy-and-hold"]
    tables = {}
    for label, start in (("2005-2026", "2005"), ("2020-2026", "2020")):
        sub = R.loc[start:]
        tables[label] = pd.DataFrame({rule: metrics(*simulate(sub, target, rule, trig)) for rule in rules}).T
    os.makedirs(OUT, exist_ok=True)
    for k, v in tables.items():
        v.to_csv(f"{OUT}/summary_{k}.csv")
    pd.DataFrame([(d.date(), win, lose, round(c, 4)) for d, h in trig.items() for win, lose, c in h],
                 columns=["month_end", "went_up_more", "went_down_more", "corr"]).to_csv(f"{OUT}/triggers.csv", index=False)
    cw = canonical_weights(target)
    json.dump({"task": "PORT-019", "source_sha256": hashlib.sha256(open("data/clean/prices_clean.csv", "rb").read()).hexdigest(),
               "target": cw, "weight_hash": weight_hash(cw), "threshold": THRESHOLD, "tilt": TILT, "band": BAND,
               "trigger_months": len(trig), "cost": 0.0, "reserve": "not withdrawn",
               "label": "retrospective portfolio evaluation; full-sample weights, rule proposed after seeing 2020-2026 correlations"},
              open(f"{OUT}/metadata.json", "w"), indent=2)
    pd.set_option("display.width", 220)
    print(f"Trigger months: {len(trig)} of {R.index.to_period('M').nunique()}")
    for k, v in tables.items():
        print(f"\n{k}\n", v.round(2))


if __name__ == "__main__":
    main()
