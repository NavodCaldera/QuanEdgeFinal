"""Exploratory study: relative-band rebalancing and a capped dip-buying ladder (task PORT-020).

Owner's request: "buy low, sell high" on the risk-parity portfolio; test relative bands
(option 1) and relative bands plus a capped ladder (option 2). Rules fixed in this
docstring before the first run.

Target T = v3 static near parity (results/final-v3-20261030/A1_near_parity), four ETFs.
Trades happen at the close of the day the condition is seen; weights drift in between.
  Normal            Quarter-end rebalance, plus any day an ETF is more than 5 points from target.
  Relative band     Quarter-end rebalance, plus any day an ETF is outside T_i * (1 +/- 20%).
  Band only         Relative band without the quarter-end calendar rebalance.
  Band + ladder     Relative band, with ladder-adjusted targets T':
                    for SPY, GLD and XLE, drawdown d = price / 756-day high - 1 at the close.
                    d <= -30% adds 2.5 points to the target; d <= -45% adds 5 points (cap).
                    The added weight is taken from the other ETF furthest above its own target
                    at that close (never below zero) and returned when the extra is removed.
                    The extra is removed when the price recovers half of the fall from the
                    high at the first trigger to the lowest close since. Any change in T'
                    triggers a rebalance to T' at that close.
  Buy-and-hold      Never rebalance (reference).
Added at the owner's request after the first run: dynamic EWMA risk parity
(quanedge.comparison.dynamic_parity_path, lambda 0.97, 750-day window, month-end targets).
"Dynamic RP (from 2005)" uses a 63-day warm-up so that it starts in April 2005;
"Dynamic RP (v4d, from 2007)" is the pre-registered 500-day version (starts 2006-12-28).
Owner request after that: every method starts on the same date. The full-period table now starts
all methods at the dynamic warm-up decision close (2005-04-05; first return 2005-04-06), with the
fixed rules starting at target on that close; the v4d row, which cannot start then, is dropped.
Weekly and quarterly versions of dynamic RP (same lambda, window and warm-up) added on request.
Their 2020-2026 rows are slices of the full-history paths (targets keep using pre-2020 data).
0% cost (mandate v3) for the main columns; "CAGR @5bp" charges 5 bp per unit of one-way
turnover as in portfolio.replay. No reserve withdrawals. Weights are full-sample estimates
and the thresholds were proposed after the 2005-2026 drawdowns were shown, so every path is a
retrospective portfolio evaluation.
Run from the repository root: python scripts/band_ladder_study.py
"""
import hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from quanedge.portfolio import tail_weights, canonical_weights, weight_hash
from quanedge.comparison import dynamic_parity_path

FOUR = ["SPY", "XLE", "AGG", "GLD"]
LADDER = ["SPY", "XLE", "GLD"]
OUT = "results/band-ladder-r1"
RUN = "results/final-v3-20261030"
ABS_BAND, REL_BAND, HIGH_DAYS = .05, .20, 756
STEPS = ((-.45, .05), (-.30, .025))
CRISES = {"GFC": ("2007-10-09", "2009-03-09"), "COVID": ("2020-02-19", "2020-03-23"),
          "2022": ("2022-01-03", "2022-10-12")}


def simulate(prices, target, rule, cost=0.):
    R = prices.pct_change().dropna(); P = prices.loc[R.index].to_numpy()
    high = prices.rolling(HIGH_DAYS, min_periods=1).max().loc[R.index].to_numpy()
    x = R.to_numpy(); dates = R.index; n = len(FOUR)
    T = np.array([target[c] for c in FOUR]); Tp = T.copy(); w = T.copy()
    extra = np.zeros(n); funded = [None]*n; trough = np.full(n, np.nan); peak = np.full(n, np.nan)
    rets, turn, eff = np.empty(len(R)), np.zeros(len(R)), np.empty((len(R), n)); events = []
    for i in range(len(R)):
        rp = float(w @ x[i]); w = w*(1+x[i])/(1+rp)
        quarter = i == len(dates)-1 or dates[i+1].quarter != dates[i].quarter
        changed = False
        if rule == "Band + ladder":
            for k in (FOUR.index(c) for c in LADDER):
                d = P[i, k]/high[i, k]-1
                want = next((s for th, s in STEPS if d <= th), 0.)
                if extra[k] > 0:
                    trough[k] = min(trough[k], P[i, k])
                    if P[i, k] >= trough[k] + .5*(peak[k]-trough[k]):
                        want = 0.
                    else:
                        want = max(want, extra[k])
                if want != extra[k]:
                    if extra[k] == 0:
                        peak[k], trough[k] = high[i, k], P[i, k]
                        others = [j for j in range(n) if j != k]
                        funded[k] = max(others, key=lambda j: w[j]-Tp[j])
                    j = funded[k]; delta = min(want-extra[k], Tp[j])
                    Tp[k] += delta; Tp[j] -= delta; extra[k] += delta; changed = True
                    events.append((dates[i].date(), FOUR[k], round(d, 4), round(extra[k], 4), FOUR[j]))
                    if extra[k] <= 1e-12:
                        extra[k] = 0.; funded[k] = None
        if rule == "Normal":
            trade = quarter or np.max(np.abs(w-T)) > ABS_BAND
        elif rule in ("Relative band", "Band + ladder"):
            trade = changed or quarter or np.any(np.abs(w-Tp) > REL_BAND*Tp)
        elif rule == "Band only":
            trade = np.any(np.abs(w-T) > REL_BAND*T)
        else:
            trade = False
        if trade:
            turn[i] = np.abs(Tp-w).sum(); rp = (1+rp)*(1-cost*turn[i])-1; w = Tp.copy()
        rets[i] = rp; eff[i] = Tp
    return pd.Series(rets, dates), pd.Series(turn, dates), pd.DataFrame(eff, dates, FOUR), events


def metrics(r, turn, r_cost):
    w = (1+r).cumprod(); years = (r.index[-1]-r.index[0]).days/365.25; loss = -r.to_numpy(); dd = w/w.cummax()-1
    out = {"CAGR %": 100*(w.iloc[-1]**(1/years)-1), "CAGR @5bp %": 100*((1+r_cost).prod()**(1/years)-1),
           "Vol %": 100*r.std()*np.sqrt(252), "Max fall %": 100*dd.min(),
           "Days beyond 20% fall": int((dd < -.20).sum()), "ES99 1d %": 100*tail_weights(loss) @ loss}
    for k, (a, b) in CRISES.items():
        if r.index[0] <= pd.Timestamp(a):
            out[f"{k} %"] = 100*((1+r.loc[a:b]).prod()-1)
    return out | {"Trades/yr": (turn > 0).sum()/years, "Turnover x/yr": turn.sum()/years}


def main():
    prices = pd.read_csv("data/clean/prices_clean.csv", index_col=0, parse_dates=True)[FOUR]
    raw = json.load(open(f"{RUN}/A1_near_parity/weights.json"))["weights"]
    target = {c: raw[c] for c in FOUR}
    rules = ["Normal", "Relative band", "Band only", "Band + ladder", "Buy-and-hold"]
    tables, ladder_events = {}, None
    common = prices.index[63]  # close of the 63rd return: dynamic RP's first decision
    for label, start in (("2005-2026", common), ("2020-2026", "2019-12-31")):
        p = prices.loc[start:]
        rows = {}
        for rule in rules:
            r, turn, eff, ev = simulate(p, target, rule)
            rows[rule] = metrics(r, turn, simulate(p, target, rule, cost=.0005)[0])
            if rule == "Band + ladder" and label == "2005-2026":
                ladder_events = ev; rows[rule]["Max ladder extra pt"] = 100*float((eff[LADDER]-np.array([target[c] for c in LADDER])).max().max())
        for name, warm, fq in (("Dynamic RP monthly", 63, "M"), ("Dynamic RP weekly", 63, "W"), ("Dynamic RP quarterly", 63, "Q")):
            R = prices.pct_change().dropna()
            path, path_c = (dynamic_parity_path(R, fq, .97, 750, warm, c) for c in (0., .0005))
            path, path_c = path.loc[p.index[1]:], path_c.loc[p.index[1]:]
            rows[name] = metrics(path["return"], path["turnover"], path_c["return"])
            rows[name]["Start"] = str(path.index[0].date())
        tables[label] = pd.DataFrame(rows).T
    os.makedirs(OUT, exist_ok=True)
    for k, v in tables.items():
        v.to_csv(f"{OUT}/summary_{k}.csv")
    pd.DataFrame(ladder_events, columns=["date", "etf", "drawdown_from_756d_high", "extra_weight", "funded_from"]).to_csv(f"{OUT}/ladder_events.csv", index=False)
    cw = canonical_weights(target)
    json.dump({"task": "PORT-020", "source_sha256": hashlib.sha256(open("data/clean/prices_clean.csv", "rb").read()).hexdigest(),
               "target": cw, "weight_hash": weight_hash(cw), "abs_band": ABS_BAND, "rel_band": REL_BAND,
               "ladder": {"etfs": LADDER, "high_window_days": HIGH_DAYS, "steps": STEPS, "exit": "half recovery from trough"},
               "cost": "0% main; 5 bp one-way sensitivity", "reserve": "not withdrawn",
               "label": "retrospective portfolio evaluation; thresholds proposed after the drawdowns were shown"},
              open(f"{OUT}/metadata.json", "w"), indent=2)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    for k, v in tables.items():
        print(f"\n{k}\n", v.round(2).to_string())
    print("\nLadder events:"); [print(e) for e in ladder_events]


if __name__ == "__main__":
    main()
