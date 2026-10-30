"""Exploratory study: ETF correlations and the owner's "+10% winner to biggest loser" rebalancing rule.

Retrospective on data/clean (owner has seen the full sample); descriptive only, not part of the frozen
run and not a policy change. Run from the repository root: python scripts/correlation_rebalancing_study.py
"""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

print("="*30, "1. Correlations", "="*30)
import numpy as np, pandas as pd
from scipy import stats
pd.set_option("display.width",220); pd.set_option("display.precision",2); pd.set_option("display.max_columns",20)
r=pd.read_csv("data/clean/log_returns.csv",index_col=0,parse_dates=True)
T=list(r.columns); print(r.index[0].date(),r.index[-1].date(),len(r))
print("\n== Daily Pearson correlation, full sample ==");C=r.corr();print(C)
n=len(r); t=C*np.sqrt((n-2)/(1-C.clip(-.9999,.9999)**2)); p=2*stats.t.sf(abs(t),n-2)
print("max p-value off-diagonal:",p[~np.eye(7,dtype=bool)].max().round(4))
print("\n== Spearman (rank) ==");print(r.corr("spearman"))
m=r.resample("ME").sum();print("\n== Monthly log-return correlation ==");print(m.corr())
print("\nFisher 95% CI (daily) for selected pairs")
for a,b in [("SPY","AGG"),("SPY","GLD"),("AGG","GLD"),("SPY","XLK"),("SPY","EFA"),("XLE","XLK")]:
    z=np.arctanh(C.loc[a,b]);s=1/np.sqrt(n-3);print(f" {a}-{b}: {C.loc[a,b]:.3f} [{np.tanh(z-1.96*s):.3f},{np.tanh(z+1.96*s):.3f}]")
print("\n== Correlation by regime (daily) ==")
per={"2005-07":("2005","2007"),"GFC 2008-09":("2008","2009"),"2010-19":("2010","2019"),"COVID Feb-Apr20":("2020-02-15","2020-04-30"),"2022 hikes":("2022","2022"),"2023-26":("2023","2026")}
pairs=[("SPY","AGG"),("SPY","GLD"),("AGG","GLD"),("SPY","EEM"),("SPY","XLE"),("SPY","XLK"),("XLE","XLK")]
print(pd.DataFrame({k:[r.loc[s:e].corr().loc[a,b] for a,b in pairs] for k,(s,e) in per.items()},index=[f"{a}-{b}" for a,b in pairs]))
print("\n== Rolling 1y (252d) correlation range ==")
for a,b in pairs:
    x=r[a].rolling(252).corr(r[b]).dropna();print(f" {a}-{b}: min {x.min():.2f} median {x.median():.2f} max {x.max():.2f}; % time negative {100*(x<0).mean():.0f}%")
print("\n== Tail co-movement: corr on SPY's worst 5% days vs rest ==")
bad=r.SPY<=r.SPY.quantile(.05)
print(pd.DataFrame({"worst5%":r[bad].corr()["SPY"],"other95%":r[~bad].corr()["SPY"],"mean ret on SPY worst5% (%)":100*r[bad].mean()}))
ev=np.linalg.eigvalsh(C)[::-1];print("\nEigenvalues:",ev.round(2),"-> first factor explains",f"{100*ev[0]/7:.0f}% of variance")

print("\n"+"="*30, "2. Rebalancing rule backtest", "="*30)
import numpy as np, pandas as pd, json
pd.set_option("display.width",220); pd.set_option("display.precision",3)
R=pd.read_csv("data/clean/simple_returns.csv",index_col=0,parse_dates=True)
COST=.0005; EQ=["SPY","EFA","EEM","XLE","XLK"]
def run(R,w,mode,th=.10,drift=.05):
    T=list(R.columns); tgt=np.array([w.get(t,0) for t in T]); held=tgt>0
    pos=tgt.copy(); ref=np.ones(len(T)); px=np.ones(len(T)); nav=[];trades=0;turn=0.;maxeq=0;maxw=0;minagg=1
    for i,(d,row) in enumerate(R.iterrows()):
        g=row.to_numpy(); pos=pos*(1+g); px=px*(1+g); V=pos.sum(); traded=0.
        if mode=="quarterly" and (i==len(R)-1 or R.index[i+1].quarter!=d.quarter):
            traded=np.abs(tgt*V-pos).sum(); pos=tgt*V
        elif mode=="band":
            if np.max(abs(pos/V-tgt))>drift: traded=np.abs(tgt*V-pos).sum(); pos=tgt*V
        elif mode in("rule_gain","rule_trim"):
            up=held&(px>=ref*(1+th))
            for k in np.where(up)[0]:
                chg=px/ref-1; cand=np.where(held&(np.arange(len(T))!=k))[0]
                j=cand[np.argmin(chg[cand])]
                if chg[j]>=0: ref[k]=px[k]; continue   # nothing went down: just reset
                amt=pos[k]*(1-ref[k]/px[k]) if mode=="rule_gain" else max(pos[k]-tgt[k]*V,0)
                pos[k]-=amt; pos[j]+=amt; traded+=2*amt; ref[k]=px[k]; ref[j]=px[j]; trades+=1
        if traded: pos=pos*(1-COST*traded/V)  # 5 bp on buy plus sell notional, as in portfolio.replay
        turn+=traded/2/V; V2=pos.sum(); wts=pos/V2
        maxeq=max(maxeq,wts[[T.index(e) for e in EQ]].sum()); maxw=max(maxw,wts[T.index("GLD")]); minagg=min(minagg,wts[T.index("AGG")])
        nav.append(V2)
    s=pd.Series(nav,R.index); r=s.pct_change().fillna(s.iloc[0]-1); yrs=(R.index[-1]-R.index[0]).days/365.25
    dd=(s/s.cummax()-1).min()
    return {"CAGR%":100*(s.iloc[-1]**(1/yrs)-1),"Vol%":100*r.std()*np.sqrt(252),"MaxDD%":100*dd,
            "Ret/Vol":(s.iloc[-1]**(1/yrs)-1)/(r.std()*np.sqrt(252)),"Calmar":(s.iloc[-1]**(1/yrs)-1)/-dd,
            "turnover/yr":turn/yrs,"rule trades":trades,"max equity wt%":100*maxeq,"max GLD wt%":100*maxw,"min AGG wt%":100*minagg,
            "final wts":" ".join(f"{t}{100*x:.0f}" for t,x in zip(R.columns,pos/pos.sum()) if x>.005)}
P={"Adjusted rec (A1_min_cvar)":{"SPY":.15,"AGG":.70,"GLD":.15},
   "Original selected":json.load(open("results/final-20261027/selected/weights.json"))["weights"],
   "Equal weight 7":{t:1/7 for t in R.columns}}
modes={"buy_hold":"Buy & hold","quarterly":"Quarterly rebalance","band":"5pt drift band","rule_trim":"Owner rule: +10% -> trim to target, give to biggest loser","rule_gain":"Owner rule: +10% -> sell the gain, give to biggest loser"}
for per,(a,b) in {"Full 2005-01 to 2026-09":("2005","2026"),"Evaluation 2017-01 to 2026-09":("2017","2026")}.items():
    for pn,w in P.items():
        print(f"\n### {pn} | {per}")
        print(pd.DataFrame({modes[m]:run(R.loc[a:b],w,m) for m in modes}).T.to_string())

print("\n"+"="*30, "3. Does a +10% rise predict a fall?", "="*30)
import numpy as np, pandas as pd
pd.set_option("display.width",220); pd.set_option("display.precision",2); pd.set_option("display.max_columns",20)
P=pd.read_csv("data/clean/prices_clean.csv",index_col=0,parse_dates=True)
rows=[]
for t in P:
    p=P[t]; past=p/p.shift(63)-1; fwd=p.shift(-63)/p-1
    ev=past>=.10; d=(fwd[ev]-fwd.mean()).dropna()
    # non-overlapping: take first trigger then skip 63 days
    idx=[];last=-999
    for i,(dt,f) in enumerate(ev.items()):
        if f and i-last>=63 and not np.isnan(fwd.iloc[i]): idx.append(i);last=i
    x=fwd.iloc[idx]-fwd.mean(); se=x.std()/np.sqrt(len(x))
    rows.append({"ETF":t,"triggers (non-overlap)":len(idx),"fwd 3m after +10% (%)":100*fwd.iloc[idx].mean(),"fwd 3m all days (%)":100*fwd.mean(),"diff (%)":100*x.mean(),"t-stat":x.mean()/se})
print("Does a +10% rise over 3 months predict a weaker next 3 months?");print(pd.DataFrame(rows).set_index("ETF"))
m=P.resample("ME").last().pct_change()
for L in (1,3,12):
    past=P.resample("ME").last().pct_change(L); rk=past.rank(axis=1); nxt=m.shift(-1).rank(axis=1)
    ic=rk.corrwith(nxt,axis=1,method="spearman").dropna()
    print(f"Cross-sectional rank corr: past {L}m return vs next month return = {ic.mean():+.3f} (t={ic.mean()/ic.std()*np.sqrt(len(ic)):.2f}, n={len(ic)})")
