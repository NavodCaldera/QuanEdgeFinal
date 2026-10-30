"""Exploratory study: risk parity estimated on long versus recent history (task PORT-015).

Equal-risk-contribution (ERC) weights for SPY, XLE, AGG and GLD from six covariance windows:
all history (expanding), 10, 5, 3 and 1 year (Ledoit-Wolf, annualised) and an EWMA with a
one-year half-life. Walk-forward: weights for year Y use data up to 31 December Y-1 only, then
are held at fixed weights through year Y.

Solver: the convex Maillard-Roncalli-Teiletche form, min 0.5 y'Sy - (1/k) sum log y, w = y/sum(y),
which has a unique strictly positive solution. The squared-gap objective used by
quanedge.portfolio.construct(kind="near_parity") can stop at a corner: on 2007-only data it
returns AGG 0% with three ETFs at one third of risk each. The comparison is exported. The frozen
v2/v3 runs and PORT-011 walk-forward weights all match the convex solution.

Retrospective and descriptive. Run from the repository root: python scripts/risk_parity_window_study.py
"""
import hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

SOURCE = "data/clean/prices_clean.csv"
OUT = "results/risk-parity-window-r1"
F = ["SPY", "XLE", "AGG", "GLD"]
WINDOWS = {"All history (expanding)": None, "10 years": 2520, "5 years": 1260, "3 years": 756,
           "1 year": 252, "EWMA half-life 1y": "ewma"}


def erc(S):
    """Convex ERC: unique positive weights with equal risk contributions."""
    k = len(S); f = lambda y: .5*y@S@y-np.sum(np.log(y))/k; g = lambda y: S@y-1/(k*y)
    y = minimize(f, np.ones(k), jac=g, bounds=[(1e-10, None)]*k, method="L-BFGS-B",
                 options={"ftol": 1e-15, "gtol": 1e-12}).x
    return y/y.sum()


def erc_squared_gap(S):
    """The squared-gap objective of portfolio.construct(near_parity), for comparison."""
    k = len(S); f = lambda w: np.sum((w*(S@w)/(w@S@w)-1/k)**2)
    return minimize(f, np.ones(k)/k, bounds=[(0, 1)]*k, constraints={"type": "eq", "fun": lambda w: w.sum()-1},
                    method="SLSQP", options={"ftol": 1e-14, "maxiter": 2000}).x


def cov(x, window):
    if window == "ewma":
        lam = .5**(1/252); wts = lam**np.arange(len(x))[::-1]; wts /= wts.sum()
        d = x-x.T@wts; return (d*wts[:, None]).T@d*252
    return LedoitWolf().fit(x).covariance_*252


def past(R, end, window):
    x = R.loc[:end].to_numpy()
    if window not in (None, "ewma"):
        if len(x) < window: return None
        x = x[-window:]
    return x


def shares(w, S): return w*(S@w)/(w@S@w)


def main():
    R = pd.read_csv(SOURCE, index_col=0, parse_dates=True)[F].pct_change().dropna()
    today = {n: dict(zip(F, erc(cov(past(R, R.index[-1], v), v)))) for n, v in WINDOWS.items()}
    rows, common = [], []
    for n, v in WINDOWS.items():
        gaps, errors, paths = [], [], []
        for y in range(2008, R.index[-1].year+1):
            x = past(R, f"{y-1}-12-31", v)
            if x is None: continue
            S = cov(x, v); w = erc(S); nxt = R.loc[str(y)].to_numpy(); realised = np.cov(nxt.T)*252
            gaps.append(np.abs(shares(w, realised)-1/len(F)).max())
            errors.append(abs(np.sqrt(w@realised@w)/np.sqrt(w@S@w)-1))
            paths.append(pd.Series(nxt@w, R.loc[str(y)].index))
        s = pd.concat(paths); c = s.loc["2016":]
        def stats(r):
            wealth = (1+r).cumprod(); loss = np.sort(-r.values)[::-1]
            return {"vol_pct": 100*r.std()*np.sqrt(252), "es99_pct": 100*loss[:int(len(loss)*.01)].mean(),
                    "max_fall_pct": 100*(wealth/wealth.cummax()-1).min(), "cagr_pct": 100*(wealth.iloc[-1]**(252/len(r))-1)}
        rows.append({"window": n, "test_years": f"{s.index[0].year}-{s.index[-1].year}",
                     "avg_worst_share_gap_pt": 100*np.mean(gaps), "max_share_gap_pt": 100*np.max(gaps),
                     "avg_vol_forecast_error_pct": 100*np.mean(errors), **stats(s)})
        common.append({"window": n, **stats(c)})
    S07 = cov(R.loc["2007"].to_numpy(), None)
    solver = {"data": "2007 only, Ledoit-Wolf",
              "convex": {"weights": dict(zip(F, erc(S07))), "risk_shares": dict(zip(F, shares(erc(S07), S07)))},
              "squared_gap": {"weights": dict(zip(F, erc_squared_gap(S07))), "risk_shares": dict(zip(F, shares(erc_squared_gap(S07), S07)))}}
    os.makedirs(OUT, exist_ok=True)
    pd.DataFrame(today).T.to_csv(f"{OUT}/weights_today.csv", float_format="%.4f")
    pd.DataFrame(rows).to_csv(f"{OUT}/walk_forward_by_window.csv", index=False, float_format="%.4f")
    pd.DataFrame(common).to_csv(f"{OUT}/common_period_2016_2026.csv", index=False, float_format="%.4f")
    json.dump({"task": "PORT-015", "source": SOURCE, "source_sha256": hashlib.sha256(open(SOURCE, "rb").read()).hexdigest(),
               "windows": {k: str(v) for k, v in WINDOWS.items()}, "solver_check": solver,
               "label": "retrospective portfolio evaluation; walk-forward weights use only earlier data"},
              open(f"{OUT}/metadata.json", "w"), indent=2, default=float)
    p = lambda v: f"{v:.1f}"
    lines = ["# Risk parity: long versus recent correlation windows", "",
             "Convex ERC solver; walk-forward yearly re-estimation on earlier data; fixed weights within each year; 0% cost.", "",
             "## Weights today (data to 2026-09-30)", "", "| Window | " + " | ".join(F) + " |", "|---|" + "---:|"*4]
    lines += [f"| {n} | " + " | ".join(p(100*w[t]) for t in F) + " |" for n, w in today.items()]
    lines += ["", "## Risk taken 2016-2026 (same period for every window)", "", "| Window | Vol % | ES99 % | Max fall % | CAGR % |", "|---|---:|---:|---:|---:|"]
    lines += [f"| {r['window']} | {r['vol_pct']:.1f} | {r['es99_pct']:.2f} | {r['max_fall_pct']:.1f} | {r['cagr_pct']:.1f} |" for r in common]
    lines += ["", "## Forecast quality (each window's own test years)", "", "| Window | Years | Avg worst risk-share gap, next year (pt) | Max gap (pt) | Avg vol forecast error % |", "|---|---|---:|---:|---:|"]
    lines += [f"| {r['window']} | {r['test_years']} | {r['avg_worst_share_gap_pt']:.1f} | {r['max_share_gap_pt']:.1f} | {r['avg_vol_forecast_error_pct']:.1f} |" for r in rows]
    lines += ["", "## Solver check on 2007 data", "", "| Method | " + " | ".join(F) + " |", "|---|" + "---:|"*4]
    for k in ("convex", "squared_gap"):
        lines.append(f"| {k} weights % | " + " | ".join(p(100*solver[k]["weights"][t]) for t in F) + " |")
        lines.append(f"| {k} risk shares % | " + " | ".join(p(100*solver[k]["risk_shares"][t]) for t in F) + " |")
    open(f"{OUT}/report.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
