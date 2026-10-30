"""Exploratory study: how the rebalancing rule changes the risk the endowment carries (task PORT-012).

The question is risk, not return. Three four-ETF allocations are each run under eight
rebalancing rules over the frozen panel (2005-01-03 to 2026-09-30), USD 9.6m invested,
0% cost (mandate v3), no reserve withdrawals so that the paths are comparable.

Weight drift between rebalances (simple returns R):
    w_i,t = w_i,t-1 * (1 + R_i,t) / (1 + R_p,t),   R_p,t = sum_i w_i,t-1 * R_i,t
Turnover at a rebalance = sum_i |target_i - w_i,t|  (fraction of NAV traded, both sides).
Risk share of asset i at weights w and covariance S:  w_i (S w)_i / (w' S w).
S is the sample covariance of the previous 252 daily returns, so the risk share uses only
data available at that date.

Retrospective and descriptive. No change to policy, W_rec, the frozen run or the verdict.
Run from the repository root: python scripts/rebalancing_risk_study.py
"""
import hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from quanedge.portfolio import canonical_weights, weight_hash, tail_weights

FOUR = ["SPY", "XLE", "AGG", "GLD"]
EQUITY = ["SPY", "XLE"]
VALUE = 9.6e6
OUT = "results/rebalancing-risk-r1"
RUN = "results/final-v3-20261030"
PORTFOLIOS = {
    "Minimum CVaR (W_rec)": json.load(open(f"{RUN}/selected/weights.json"))["weights"],
    "Risk parity": json.load(open(f"{RUN}/A1_near_parity/weights.json"))["weights"],
    "Inverse variance": {"SPY": .07, "XLE": .03, "AGG": .83, "GLD": .07},
}
# name: (calendar period or None, drift band or None); "never" is buy-and-hold.
RULES = {
    "Daily": ("D", None), "Monthly": ("M", None), "Quarterly": ("Q", None),
    "Quarterly + 5-pt band (current)": ("Q", .05), "Annual": ("Y", None),
    "Band only, 5 pt": (None, .05), "Band only, 10 pt": (None, .10), "Never (buy-and-hold)": (None, None),
}
CRISES = {"GFC": ("2007-10-09", "2009-03-09"), "COVID": ("2020-02-19", "2020-03-23"),
          "Rates 2022": ("2022-01-03", "2022-10-12")}


def simulate(R, target, period, band):
    """Returns enter first, then the rule trades at that close (as portfolio.replay)."""
    t = np.array([target[c] for c in R.columns]); w = t.copy(); dates = R.index
    rets, weights, turnover = np.empty(len(R)), np.empty((len(R), len(t))), np.zeros(len(R))
    end = {"D": lambda i: True,
           "M": lambda i: i == len(dates)-1 or dates[i+1].month != dates[i].month,
           "Q": lambda i: i == len(dates)-1 or dates[i+1].quarter != dates[i].quarter,
           "Y": lambda i: i == len(dates)-1 or dates[i+1].year != dates[i].year}
    x = R.to_numpy()
    for i in range(len(R)):
        rp = float(w @ x[i]); rets[i] = rp
        w = w*(1+x[i])/(1+rp)
        if (period and end[period](i)) or (band and np.max(abs(w-t)) > band):
            turnover[i] = np.abs(t-w).sum(); w = t.copy()
        weights[i] = w
    return pd.Series(rets, dates), pd.DataFrame(weights, dates, R.columns), pd.Series(turnover, dates)


def window_drawdown(wealth, start, end):
    g = wealth.loc[start:end]; g = g/g.iloc[0]
    return float((g/g.cummax()-1).min())


def risk_shares(R, W):
    """Equity share of portfolio variance at month ends, trailing-252-day covariance."""
    out = {}
    month_ends = R.index.to_series().groupby(R.index.to_period("M")).max()
    x = R.to_numpy(); pos = {d: i for i, d in enumerate(R.index)}
    eq = [R.columns.get_loc(c) for c in EQUITY]
    for d in month_ends:
        i = pos[d]
        if i < 252: continue
        S = np.cov(x[i-251:i+1].T); w = W.iloc[i].to_numpy(); v = w @ S @ w
        out[d] = float((w*(S@w))[eq].sum()/v)
    return pd.Series(out)


def metrics(r, W, turn, target, R):
    wealth = (1+r).cumprod(); years = (r.index[-1]-r.index[0]).days/365.25
    loss = -r.to_numpy(); tw = tail_weights(loss)
    drift = (W-np.array([target[c] for c in W.columns])).abs().max(axis=1)
    eq = W[EQUITY].sum(axis=1); shares = risk_shares(R, W)
    roll = lambda n: float(((1+r).rolling(n).apply(np.prod, raw=True)-1).min())
    return {"annual_vol_pct": 100*r.std()*np.sqrt(252),
            "VaR99_1d_usd": VALUE*float(np.quantile(loss, .99)), "ES99_1d_usd": VALUE*float(tw @ loss),
            "worst_day_pct": 100*r.min(), "worst_month_pct": 100*roll(21), "worst_year_pct": 100*roll(252),
            "max_drawdown_pct": 100*float((wealth/wealth.cummax()-1).min()),
            **{f"{k}_drawdown_pct": 100*window_drawdown(wealth, *v) for k, v in CRISES.items()},
            "avg_drift_pt": 100*float(drift.mean()), "max_drift_pt": 100*float(drift.max()),
            "equity_weight_min_pct": 100*float(eq.min()), "equity_weight_max_pct": 100*float(eq.max()),
            "equity_risk_share_avg_pct": 100*float(shares.mean()), "equity_risk_share_max_pct": 100*float(shares.max()),
            "rebalances_per_year": float((turn > 0).sum()/years), "turnover_per_year": float(turn.sum()/years),
            "cagr_pct": 100*float(wealth.iloc[-1]**(1/years)-1)}


def main():
    prices = pd.read_csv("data/clean/prices_clean.csv", index_col=0, parse_dates=True)[FOUR]
    R = prices.pct_change().dropna()
    rows = []
    for pname, w in PORTFOLIOS.items():
        target = {c: float(w.get(c, 0.)) for c in FOUR}
        static_shares = None
        for rname, (period, band) in RULES.items():
            r, W, turn = simulate(R, target, period, band)
            rows.append({"portfolio": pname, "rule": rname, **metrics(r, W, turn, target, R)})
            print(f"{pname:22s} {rname:32s} done", flush=True)
    M = pd.DataFrame(rows); os.makedirs(OUT, exist_ok=True); M.to_csv(f"{OUT}/rebalancing_risk.csv", index=False)

    # GFC worked example for risk parity: drift under buy-and-hold vs quarterly.
    target = {c: float(PORTFOLIOS["Risk parity"].get(c, 0.)) for c in FOUR}
    sub = R.loc["2007-10-09":"2009-03-09"].iloc[1:]
    ex = {k: simulate(sub, target, *v) for k, v in (("Never", (None, None)), ("Quarterly", ("Q", None)))}
    trough = "2009-03-09"
    example = {k: {c: float(v[1].loc[trough, c]) for c in FOUR} for k, v in ex.items()}
    example["target"] = target
    for k, v in ex.items():
        example[k + "_return_pct"] = 100*float((1+v[0]).prod()-1)

    meta = {"task": "PORT-012", "source": "data/clean/prices_clean.csv",
            "source_sha256": hashlib.sha256(open("data/clean/prices_clean.csv", "rb").read()).hexdigest(),
            "weights": {k: {"weights": canonical_weights({c: float(w.get(c, 0.)) for c in FOUR}),
                            "weight_hash": weight_hash(canonical_weights({c: float(w.get(c, 0.)) for c in FOUR}))}
                        for k, w in PORTFOLIOS.items()},
            "rules": {k: {"calendar": v[0], "band": v[1]} for k, v in RULES.items()},
            "value_usd": VALUE, "cost": 0.0, "reserve": "not withdrawn (paths comparable across rules)",
            "risk_measures": "historical 1-day VaR/ES99 on the rule's own daily path, full 2005-2026 sample",
            "gfc_example_trough_weights": example,
            "label": "retrospective portfolio evaluation; descriptive, not a validation of any risk model"}
    json.dump(meta, open(f"{OUT}/metadata.json", "w"), indent=2)

    cols = {"annual_vol_pct": "Vol %", "ES99_1d_usd": "1-day ES99 $", "worst_month_pct": "Worst month %",
            "worst_year_pct": "Worst year %", "max_drawdown_pct": "Max fall %", "GFC_drawdown_pct": "GFC fall %",
            "max_drift_pt": "Max drift pt", "equity_weight_max_pct": "Max equity wt %",
            "equity_risk_share_max_pct": "Max equity risk share %", "rebalances_per_year": "Trades/yr",
            "turnover_per_year": "Turnover x/yr"}
    lines = ["# Rebalancing rules and the risk carried", "",
             "Frozen panel 2005-01-03 to 2026-09-30, USD 9.6m, 0% cost, no reserve withdrawals. Risk measured on each rule's own daily path. Retrospective and descriptive.", "",
             "Weights drift between trades: w_i,t = w_i,t-1 (1+R_i,t)/(1+R_p,t). A trade restores the target and turns over sum_i |target_i - w_i,t| of NAV. "
             "Equity risk share = sum over SPY, XLE of w_i (S w)_i / (w'S w), with S the trailing 252-day covariance at each month end. "
             "Max drift = largest gap between any ETF's weight and its target, in percentage points.", ""]
    for p in PORTFOLIOS:
        sub = M[M.portfolio == p].set_index("rule")[list(cols)].rename(columns=cols)
        lines += [f"## {p}", "", "| Rule | " + " | ".join(cols.values()) + " |", "|---|" + "---:|"*len(cols)]
        for rule, row in sub.iterrows():
            lines.append(f"| {rule} | " + " | ".join(f"{v:,.0f}" if "$" in c else f"{v:.2f}" if "x/yr" in c or "Trades" in c else f"{v:.1f}" for c, v in row.items()) + " |")
        lines.append("")
    open(f"{OUT}/report.md", "w").write("\n".join(lines))
    print("\n".join(lines)); print(json.dumps(example, indent=1))


if __name__ == "__main__":
    main()
