"""Side-by-side history of precomputed allocations (retrospective portfolio evaluation).

Fixed allocations use portfolio.replay (quarterly or drift rebalancing). The optional
dynamic EWMA risk parity re-estimates the covariance at each month-end close from data
up to that close, holds the target until the next month-end and is exploratory: it is
not a frozen candidate, has no weight hash and no sequential risk forecasts.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .portfolio import replay
from .stress import SCENARIOS


def ewma_cov(x, lam=.97):
    """Exponentially weighted covariance of the rows of x, the last row weighted most."""
    x = np.asarray(x, float)
    w = lam**np.arange(len(x))[::-1]; w /= w.sum(); d = x - w@x
    return (d*w[:, None]).T@d


def risk_parity(cov):
    """Long-only weights with equal volatility risk contributions (Spinu 2013 convex form)."""
    S = np.asarray(cov, float); S = S/np.mean(np.diag(S)); k = len(S)
    f = lambda y: (0.5*y@S@y - np.log(y).sum()/k, S@y - 1/(k*y))
    y = minimize(f, np.ones(k), jac=True, bounds=[(1e-10, None)]*k, method="L-BFGS-B",
                 options={"ftol": 1e-15, "gtol": 1e-12}).x
    return y/y.sum()


def dynamic_parity_path(returns, freq="M", lam=.97, window=750, min_history=500, cost=0.):
    """Daily path of EWMA risk parity re-estimated at each month-end ("M") or week-end ("W") close.

    The first target uses the first min_history days; each later target uses data through its
    decision close only. Columns: return, wealth, turnover, rebalanced, then end-of-day holdings
    and the target in force (target_<ticker>). Empty if history is too short."""
    if len(returns) <= min_history:
        return pd.DataFrame()
    x = returns.to_numpy(); dates = returns.index; cols = list(returns.columns)
    target = lambda i: risk_parity(ewma_cov(x[max(0, i+1-window):i+1], lam))
    period = dates.to_period(freq)
    # the last row decides too when it closes its period on the business-day calendar
    last = (dates[-1] + pd.offsets.BDay(1)).to_period(freq) != period[-1]
    decision = np.r_[period[1:] != period[:-1], last]
    tgt = target(min_history-1); pos = tgt.copy(); rows = []
    for i in range(min_history, len(x)):
        old = pos.sum(); pos = pos*(1 + x[i]); turnover = 0.
        if decision[i]:
            tgt = target(i); turnover = float(np.abs(tgt - pos/pos.sum()).sum())
            pos = tgt*pos.sum()*(1 - cost*turnover)
        rows.append([pos.sum()/old - 1, turnover, decision[i], *(pos/pos.sum()), *tgt])
    frame = pd.DataFrame(rows, index=dates[min_history:],
                         columns=["return", "turnover", "rebalanced", *cols, *[f"target_{c}" for c in cols]])
    frame.insert(1, "wealth", (1 + frame["return"]).cumprod())
    return frame


def dynamic_risk_parity(returns, lam=.97, window=750, min_history=500, cost=0., freq="M"):
    """Daily simple returns of dynamic_parity_path (empty series if history is too short)."""
    path = dynamic_parity_path(returns, freq, lam, window, min_history, cost)
    return path["return"].rename("return") if len(path) else pd.Series(dtype=float)


def wealth_paths(returns, allocations, cost=0., drift=.05, value=1e7):
    """USD wealth of each fixed allocation (name -> weights over returns' columns)."""
    return pd.DataFrame({name: value*replay(returns, w, cost, drift)["wealth"] for name, w in allocations.items()})


def summary(wealth, inflation=None):
    """Per-column end value, CAGR, volatility, maximum drawdown and stress-window returns."""
    rows = []
    for name, x in wealth.items():
        x = x.dropna()
        if len(x) < 2:
            continue
        r = x.pct_change().dropna(); years = (x.index[-1] - x.index[0]).days/365.25
        cagr = (x.iloc[-1]/x.iloc[0])**(1/years) - 1
        row = {"Portfolio": name, "Start": x.index[0].date(), "End value (USD m)": x.iloc[-1]/1e6,
               "CAGR %": 100*cagr}
        if inflation is not None:
            row["Real CAGR %"] = 100*((1 + cagr)/(1 + inflation) - 1)
        row |= {"Volatility %": 100*r.std()*np.sqrt(252), "Max drawdown %": 100*(x/x.cummax() - 1).min()}
        for label, (a, b) in SCENARIOS.items():
            before = x.loc[:pd.Timestamp(a) - pd.Timedelta(days=1)]
            row[f"{label} %"] = 100*(x.loc[:b].iloc[-1]/before.iloc[-1] - 1) if len(before) and x.index[-1] >= pd.Timestamp(b) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
