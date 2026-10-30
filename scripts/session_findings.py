"""Reproduce the conversation-only findings of 30 October 2026 (task DOC-009) as saved evidence.

Writes results/session-findings-r1/ (all retrospective portfolio evaluations on the frozen
data snapshot through 2026-09-30, 0% cost, no cash-reserve withdrawals unless stated):
  regime_risk.csv         per-ETF risk, normal days vs the three pooled stress windows
  regime_correlation.csv  SPY/AGG/GLD/XLE correlations, normal vs crisis
  dynamic_strategies.csv  monthly re-estimated strategies 2007-2026 (PORT-013 study)
  model_scores.csv        FZ0 joint VaR/ES99 score of each risk model, 2017-2026, run final-v3-20261030
  four_etf_returns.csv    portfolios holding all four ETFs: CAGR, CPI and 3.64% real CAGR, T-bill excess, Sharpe
Run from the repository root: python scripts/session_findings.py
"""
import json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from scipy.optimize import minimize, linprog
from scipy.sparse import csr_matrix, eye, hstack
from quanedge.portfolio import replay, canonical_weights
from quanedge.stress import SCENARIOS
from quanedge.comparison import ewma_cov, risk_parity, dynamic_parity_path
from quanedge.risk.var_es import historical, Normal

OUT = "results/session-findings-r1"; RUN = "results/final-v3-20261030"; T = ["SPY", "AGG", "GLD", "XLE"]
os.makedirs(OUT, exist_ok=True)
logr = pd.read_csv("data/clean/log_returns.csv", index_col=0, parse_dates=True)
R = np.expm1(logr); macro = pd.read_csv("data/clean/macro_clean.csv", index_col=0, parse_dates=True)

# 1. Regime risk: normal days vs pooled GFC, COVID and 2022 windows
crisis = pd.Series(False, index=logr.index)
for a, b in SCENARIOS.values():
    crisis |= (logr.index >= a) & (logr.index <= b)
rows = []
for regime, mask in (("normal", ~crisis), ("crisis", crisis), ("full", crisis | ~crisis)):
    X = R.loc[mask, T]
    for t in T:
        x = logr.loc[mask, t]; h, n = historical(x), Normal(x)
        rows.append({"regime": regime, "etf": t, "days": len(x), "ann_vol_pct": x.std()*np.sqrt(252)*100,
                     "downside_dev_pct": np.sqrt((np.minimum(x, 0)**2).mean()*252)*100,
                     "hist_var95_pct": -np.expm1(-h.var(.95))*100, "hist_var99_pct": -np.expm1(-h.var(.99))*100,
                     "hist_es95_pct": h.es_fraction(.95)*100, "hist_es99_pct": h.es_fraction(.99)*100,
                     "normal_var99_pct": -np.expm1(-n.var(.99))*100, "worst_day_pct": -X[t].min()*100,
                     "excess_kurtosis": x.kurt(), "beta_spy": np.cov(X[t], X.SPY)[0, 1]/X.SPY.var(), "corr_spy": X[t].corr(X.SPY)})
pd.DataFrame(rows).to_csv(f"{OUT}/regime_risk.csv", index=False, float_format="%.4f")
pd.concat({"normal": R.loc[~crisis, T].corr(), "crisis": R.loc[crisis, T].corr()}).to_csv(f"{OUT}/regime_correlation.csv", float_format="%.3f")

# 2. Monthly re-estimated strategies, decisions from data up to each month-end close, 2007-2026
def minvar(cov):
    k = len(cov)
    return minimize(lambda w: w@cov@w*1e4, np.full(k, 1/k), bounds=[(0, 1)]*k,
                    constraints=[{"type": "eq", "fun": lambda w: w.sum()-1}], method="SLSQP", options={"ftol": 1e-14}).x
def mincvar(x, a=.99):
    n, k = x.shape; c = np.r_[np.zeros(k), 1, np.full(n, 1/(n*(1-a)))]
    A = hstack([csr_matrix(-x), csr_matrix(-np.ones((n, 1))), -eye(n)])
    return linprog(c, A_ub=A, b_ub=np.zeros(n), A_eq=np.r_[np.ones(k), np.zeros(n+1)][None, :], b_eq=[1],
                   bounds=[(0, 1)]*k+[(None, None)]+[(0, None)]*n, method="highs").x[:k]
r4 = R[T]; start = "2007-01-02"
month_ends = r4.loc[start:].groupby(r4.loc[start:].index.to_period("M")).tail(1).index
decisions = [r4.index[r4.index < start][-1]] + list(month_ends[:-1])
wrec = json.load(open(f"{RUN}/selected/weights.json"))["weights"]; rp = json.load(open(f"{RUN}/near_parity/weights.json"))["weights"]
rules = {"Static W_rec (full-sample weights)": lambda h: np.array([wrec[t] for t in T]),
         "Static risk parity (full-sample weights)": lambda h: np.array([rp[t] for t in T]),
         "Dynamic risk parity, 1-year sample covariance": lambda h: risk_parity(np.cov(h[-252:].T)),
         "Dynamic risk parity, EWMA 0.97": lambda h: risk_parity(ewma_cov(h[-750:], .97)),
         "Dynamic min-variance, EWMA 0.97": lambda h: minvar(ewma_cov(h[-750:], .97)),
         "Dynamic min-CVaR99, trailing 3 years": lambda h: mincvar(h[-756:])}
def path(rule):
    targets = {d: rule(r4.loc[:d].to_numpy()) for d in decisions}
    pos = targets[decisions[0]].copy(); nxt = iter(decisions[1:]); d1 = next(nxt, None); out, turn, agg = [], [], []
    for d, row in r4.loc[start:].iterrows():
        old = pos.sum(); pos = pos*(1+row.to_numpy()); t = 0.
        if d1 is not None and d == d1:
            new = targets[d]; t = np.abs(new-pos/pos.sum()).sum(); pos = new*pos.sum(); d1 = next(nxt, None)
        out.append(pos.sum()/old-1); turn.append(t); agg.append(pos[1]/pos.sum())
    return pd.Series(out, r4.loc[start:].index), pd.Series(turn, r4.loc[start:].index), pd.Series(agg, r4.loc[start:].index)
def stats(r, turn, agg, lo=None):
    x = r.loc[lo:]; w = (1+x).cumprod(); yrs = len(x)/252; cagr = w.iloc[-1]**(1/yrs)-1
    L = np.sort(-x.to_numpy())[::-1]; m = len(L)*.01; k = int(m)
    out = {"cagr_pct": cagr*100, "real_cagr_364_pct": ((1+cagr)/1.0364-1)*100, "vol_pct": x.std()*np.sqrt(252)*100,
           "max_drawdown_pct": (w/w.cummax()-1).min()*100, "es99_daily_pct": (L[:k].sum()+(m-k)*L[k])/m*100,
           "turnover_per_year": turn.loc[lo:].sum()/yrs, "agg_min_pct": agg.loc[lo:].min()*100, "agg_max_pct": agg.loc[lo:].max()*100}
    for name, (a, b) in SCENARIOS.items():
        if pd.Timestamp(a) >= x.index[0]:
            out[f"{name}_pct"] = ((1+x.loc[a:b]).prod()-1)*100
    return out
rows = []
for name, rule in rules.items():
    r, turn, agg = path(rule)
    rows += [{"strategy": name, "period": "2007-2026", **stats(r, turn, agg)},
             {"strategy": name, "period": "2017-2026", **stats(r, turn, agg, "2017-01-01")}]
pd.DataFrame(rows).to_csv(f"{OUT}/dynamic_strategies.csv", index=False, float_format="%.3f")

# 3. FZ0 score (Patton, Ziegel and Chen 2019) of 99% VaR/ES forecasts, 2017-2026; lower is better
rows = []
for p in ["selected", "near_parity", "max_sharpe", "min_variance", "permanent", "balanced_35_50_15", "40_60"]:
    f = pd.read_csv(f"{RUN}/{p}/forecasts.csv", parse_dates=["Date"]); f = f[f.Date >= "2017-01-01"]; y = f["return"].to_numpy()
    for m in ["historical", "normal", "evt", "fhs", "garch_evt"]:
        v, e = -f[f"var_{m}_99"].to_numpy(), -f[f"es_{m}_99"].to_numpy(); ok = np.isfinite(v) & np.isfinite(e) & (e < 0)
        yy, vv, ee = y[ok], v[ok], e[ok]
        rows.append({"portfolio": p, "model": m, "fz0": float(np.mean(-(1/(.01*ee))*(yy <= vv)*(vv-yy)+vv/ee+np.log(-ee)-1))})
s = pd.DataFrame(rows); s["gap_to_best"] = s.fz0-s.groupby("portfolio").fz0.transform("min")
s.to_csv(f"{OUT}/model_scores.csv", index=False, float_format="%.5f")

# 4. Portfolios holding all four ETFs: actual CPI and 3-month T-bill (FRED, frozen snapshot)
perf = lambda k: pd.read_csv(f"{RUN}/{k}/performance.csv", index_col=0, parse_dates=True)["return"]
dyn = lambda n: pd.read_csv(f"results/dynamic-parity-r1/{n}_path.csv", index_col=0, parse_dates=True)["return"]
P = {"W_rec (min CVaR)": perf("selected"), "Min variance": perf("min_variance"),
     "Inverse variance (7/83/7/3)": replay(R, canonical_weights({"SPY": .07, "AGG": .83, "GLD": .07, "XLE": .03}), 0., .05)["return"],
     "Dynamic risk parity weekly (v4e)": dyn("v4e_weekly"), "Dynamic risk parity monthly (v4d)": dyn("v4d_monthly"),
     "Risk parity (static)": perf("near_parity"),
     "v4c risk parity + overlay": pd.read_csv("results/parity-overlay-r1/overlay_path.csv", index_col=0, parse_dates=True)["return"],
     "Equal weight": perf("equal_weight")}
rows = []
for name, r in P.items():
    a, b = r.index[0], r.index[-1]; yrs = (b-a).days/365.25; cagr = (1+r).prod()**(1/yrs)-1
    cpi = macro.CPIAUCSL; infl = (cpi.loc[:b].iloc[-1]/cpi.loc[:a].iloc[-2 if a > cpi.index[0] else -1])**(1/yrs)-1
    rf = macro.rf_daily_effective.reindex(r.index); tb = (1+rf).prod()**(1/yrs)-1
    rows.append({"portfolio": name, "start": a.date(), "cagr_pct": cagr*100, "cpi_inflation_pct": infl*100,
                 "real_cagr_cpi_pct": ((1+cagr)/(1+infl)-1)*100, "real_cagr_364_pct": ((1+cagr)/1.0364-1)*100,
                 "tbill_cagr_pct": tb*100, "excess_over_tbill_pct": ((1+cagr)/(1+tb)-1)*100,
                 "real_tbill_pct": ((1+tb)/(1+infl)-1)*100, "sharpe": (r-rf).mean()/r.std()*np.sqrt(252)})
pd.DataFrame(rows).to_csv(f"{OUT}/four_etf_returns.csv", index=False, float_format="%.3f")
print("written", sorted(os.listdir(OUT)))
