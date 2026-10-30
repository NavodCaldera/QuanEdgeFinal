"""Exploratory study: a SPY/AGG/GLD/XLE portfolio under the frozen policy, plus risk-mitigation overlays.

Weights come from the repository's own estimator and optimiser (quanedge.portfolio.construct) with
EFA, EEM and XLK forced to zero. Retrospective and descriptive: not part of the frozen run, no change to
policy or W_rec. Run from the repository root: python scripts/four_etf_study.py
"""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd, yaml
from scipy.optimize import minimize
import quanedge.portfolio as qp
from quanedge.config import TICKERS
from quanedge.stress import stress_tests
pd.set_option("display.width",250); pd.set_option("display.max_columns",30); pd.set_option("display.precision",2)

cfg=yaml.safe_load(open("config/final.yaml")); FOUR=["SPY","AGG","GLD","XLE"]
prices=pd.read_csv("data/clean/prices_clean.csv",index_col=0,parse_dates=True)[TICKERS]
R=prices.pct_change().dropna(); train=R.loc[:cfg["training_end"]]; evalr=R.loc[cfg["evaluation_start"]:]
H=qp.hurdle(cfg["inflation"],cfg["spending"])

_bounds=qp.bounds
def four_bounds(c):  # policy limits, with the three dropped ETFs fixed at zero
    return [b if t in FOUR else (0,0) for t,b in zip(TICKERS,_bounds(c))]
qp.bounds=four_bounds

def parity(x,c):
    """Volatility risk parity across the four ETFs within policy bounds (equal risk shares of 1/4)."""
    _,cov=qp.estimates(x,c); idx=[TICKERS.index(t) for t in FOUR]; S=cov[np.ix_(idx,idx)]
    b=[four_bounds(c)[i] for i in idx]
    f=lambda w:np.sum((w*(S@w)/(w@S@w)-.25)**2)
    s=minimize(f,np.array([.2,.6,.12,.08]),bounds=b,constraints={"type":"eq","fun":lambda w:w.sum()-1},method="SLSQP",options={"ftol":1e-14,"maxiter":2000})
    w=qp.canonical_weights(dict(zip(FOUR,s.x))); v=np.array(list(w.values())); mu,cov=qp.estimates(x,c)
    net=float(v@mu-c["expected_annual_turnover"]*c["cost"]);var=float(v@cov@v)
    return {"status":"ok" if s.success else "failed","weights":w,"expected_geometric":float(np.expm1(np.log1p(net)-var/2)),"volatility":var**.5,"es99":qp.es(x[TICKERS].to_numpy(),w)}

def candidates(x,c):
    out={k:qp.construct(x,c,k) for k in ("selected","min_cvar","min_variance","max_sharpe")}
    out["risk_parity_4"]=parity(x,c)
    return out

def show(w): return " / ".join(f"{t} {100*w[t]:.0f}" for t in FOUR if w[t]>5e-4)
def summary(name,res,x):
    w=res["weights"]
    if w is None: return {"candidate":name,"weights":res.get("reason","failed")}
    st={s["scenario"]:s for s in stress_tests(prices,w,cfg["value"])}
    return {"candidate":name,"weights":show(w),"exp. geometric %":100*res["expected_geometric"],"vs hurdle 6.77%":"pass" if res["expected_geometric"]>=H else "FAIL",
            "exp. vol %":100*res["volatility"],"ES99 1-day % (est. sample)":100*qp.es(x[TICKERS].to_numpy(),w),
            "GFC drawdown %":100*st["GFC"]["drawdown"],"COVID %":100*st["COVID"]["return"],"2022 %":100*st["Rates 2022"]["return"],
            "C1 policy":qp.feasible(w,cfg),"C2 ES<=2.5%":qp.es(x[TICKERS].to_numpy(),w)<=cfg["es_budget"]+1e-6,"C5 GFC<=20%":-st["GFC"]["drawdown"]<=cfg["drawdown_limit"]}

current={"status":"ok","weights":qp.canonical_weights({"SPY":.15,"AGG":.70,"GLD":.15})}
for label,x in [("TRAINING estimation 2005-2016 (weights used for the 2017-2026 test)",train),("FULL estimation 2005-2026-09 (what you would hold today)",R)]:
    cands=candidates(x,cfg); mu,cov=qp.estimates(x,cfg); v=np.array(list(current["weights"].values()))
    net=float(v@mu-cfg["expected_annual_turnover"]*cfg["cost"]); current.update(expected_geometric=float(np.expm1(np.log1p(net)-v@cov@v/2)),volatility=float(np.sqrt(v@cov@v)))
    rows=[summary(k,r,x) for k,r in cands.items()]+[summary("current A1 (SPY15/AGG70/GLD15)",current,x)]
    print(f"\n=== Candidates, policy limits, {label} ===");print(pd.DataFrame(rows).set_index("candidate").to_string())
    if x is train: TRAIN=cands
    else: FULL=cands

print("\n=== Controlled re-solve: XLE sector cap 10% -> 20% / 40% (full estimation, everything else fixed) ===")
for cap in (.10,.20,.40):
    r=qp.construct(R,dict(cfg,sector_cap=cap)); print(f" sector_cap {cap:.0%}: {show(r['weights'])}  exp.geo {100*r['expected_geometric']:.2f}%  ES99 {100*r['es99']:.2f}%")

# ---------- risk-mitigation overlays, 2017-2026, weights fixed from training estimation ----------
def defensive(w,share):
    """Move `share` of equity (SPY, XLE) into AGG up to 70%, then GLD up to 15%; anything left stays in equity."""
    w=dict(w); free=share*(w["SPY"]+w["XLE"]); eq=w["SPY"]+w["XLE"]
    to_agg=min(free,cfg["agg_max"]-w["AGG"]); to_gld=min(free-to_agg,cfg["gold_cap"]-w["GLD"]); moved=to_agg+to_gld
    if eq>0:
        for t in ("SPY","XLE"): w[t]-=moved*w[t]/eq
    w["AGG"]+=to_agg; w["GLD"]+=to_gld; return w

def simulate(base,R,P,mode,cost=cfg["cost"]):
    """Monthly re-targeting on signals known at the prior month end; daily drift in between; cost on traded notional."""
    T=list(R.columns); pos=None; nav=1.; out=[]; turn=0.; months=0
    me=R.index.to_series().groupby(R.index.to_period("M")).max()
    spy=P["SPY"]; sma=spy.rolling(210).mean(); vol=np.log(spy).diff().rolling(63).std()*np.sqrt(252)
    for d,row in R.iterrows():
        if pos is None or d in prev_me:
            ref=prev if pos is not None else R.index[0]-pd.Timedelta(days=1)
            tgt=dict(base)
            if pos is not None and mode=="trend" and spy.loc[:ref].iloc[-1]<sma.loc[:ref].iloc[-1]: tgt=defensive(base,1.0)
            if pos is not None and mode=="voltarget":
                v=vol.loc[:ref].iloc[-1]; tgt=defensive(base,max(0.,1-0.15/v)) if v>0.15 else tgt
            t=np.array([tgt[k] for k in T])
            if pos is None: pos=t*nav
            else:
                V=pos.sum(); tr=np.abs(t*V-pos).sum(); pos=t*V*(1-cost*tr/V); turn+=tr/V/2; months+=1
        pos=pos*(1+row.to_numpy()); out.append((d,pos.sum())); prev=d
    s=pd.Series(dict(out)); return s,turn
idx=R.index; prev_me={idx[i] for i in range(1,len(idx)) if idx[i].month!=idx[i-1].month}

def metrics(s,label,turn=None):
    r=s.pct_change().dropna(); yrs=(s.index[-1]-s.index[0]).days/365.25; cagr=(s.iloc[-1]/s.iloc[0])**(1/yrs)-1
    dd=(s/s.cummax()-1); x=-r.to_numpy(); tw=qp.tail_weights(x,.99)
    seg=lambda a,b:100*((s.loc[a:b].iloc[-1]/s.loc[:a].iloc[-2])-1) if len(s.loc[a:b]) else np.nan
    return {"strategy":label,"CAGR %":100*cagr,"vol %":100*r.std()*np.sqrt(252),"max DD %":100*dd.min(),"Calmar":cagr/-dd.min(),
            "ES99 1-day %":100*tw@x,"COVID 2/19-3/23 %":seg("2020-02-19","2020-03-23"),"2022 %":seg("2022-01-03","2022-10-12"),"turnover/yr":(turn/yrs) if turn is not None else np.nan}

E=prices.loc[:"2026-09-30"]; Rev=R.loc["2017-01-01":]
picks={"4-ETF selected (max return, ES99<=2.5%)":TRAIN["selected"]["weights"],"4-ETF min CVaR":TRAIN["min_cvar"]["weights"],
       "4-ETF risk parity":TRAIN["risk_parity_4"]["weights"],"current A1 SPY15/AGG70/GLD15":current["weights"]}
print("\n=== Risk-mitigation overlays, evaluation 2017-01-03 to 2026-09-30 (training-estimated weights) ===")
for name,w in picks.items():
    rows=[]
    bh=qp.replay(Rev,w,cfg["cost"],cfg["drift"],buy_hold=True); rows.append(metrics(bh["wealth"],"buy & hold"))
    qd=qp.replay(Rev,w,cfg["cost"],cfg["drift"]); rows.append(metrics(qd["wealth"],"quarterly + 5pt drift band (policy)",qd["turnover"].sum()/2))
    for mode,lab in [("static","monthly rebalance"),("trend","+ trend filter: SPY<210d avg -> equity to AGG/GLD"),("voltarget","+ vol target: cut equity when SPY 63d vol>15%")]:
        s,t=simulate(w,Rev,E,mode); rows.append(metrics(s,lab,t))
    print(f"\n-- {name}: {show(w)}"); print(pd.DataFrame(rows).set_index("strategy").to_string())
