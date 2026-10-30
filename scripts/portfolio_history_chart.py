"""Chart: USD 10m from January 2005 in the candidate portfolios of run final-v3-20261030.

Retrospective replay (PORT-013, exploratory): quarterly rebalancing with a 5-point drift
trigger, zero cost, no cash-reserve withdrawals; fixed weights were estimated on the full
sample. Dynamic EWMA risk parity re-estimates monthly from prior data and joins in
January 2007 at the static risk-parity value. Writes results/charts/portfolio_history_2005.png
and prints the summary table.  Run: python scripts/portfolio_history_chart.py
"""
import json, numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mt, sys
from pathlib import Path
from scipy.optimize import minimize
ROOT=str(Path(__file__).resolve().parents[1])+"/"
sys.path.insert(0,ROOT)
from quanedge.portfolio import replay
R=np.expm1(pd.read_csv(ROOT+"data/clean/log_returns.csv",index_col=0,parse_dates=True))

def ewma_cov(x, lam):
    w = lam**np.arange(len(x))[::-1]; w /= w.sum(); d = x - w@x
    return (d*w[:, None]).T@d


def risk_parity(cov):
    """Equal volatility risk contributions (Spinu 2013 convex form), long-only."""
    S = cov/np.mean(np.diag(cov)); k = len(S)
    f = lambda y: (0.5*y@S@y - np.log(y).sum()/k, S@y - 1/(k*y))
    y = minimize(f, np.ones(k), jac=True, bounds=[(1e-10, None)]*k, method="L-BFGS-B",
                 options={"ftol": 1e-15, "gtol": 1e-12}).x
    return y/y.sum()


def dynamic_ewma_risk_parity(R, start="2007-01-02", lam=.97, window=750):
    """Month-end targets from data up to that close; drift within the month; zero cost."""
    sub = R.loc[start:]; month_ends = sub.groupby(sub.index.to_period("M")).tail(1).index
    first = R.index[R.index < start][-1]
    target = lambda d: risk_parity(ewma_cov(R.loc[:d].to_numpy()[-window:], lam))
    pos = target(first); out = []
    for d, row in sub.iterrows():
        old = pos.sum(); pos = pos*(1 + row.to_numpy())
        if d in month_ends and d != sub.index[-1]: pos = target(d)*pos.sum()
        out.append((d, pos.sum()/old - 1))
    return pd.Series(dict(out))

ports=[("W_rec / min CVaR (5.8/88/6/0.2)","selected"),("Static risk parity (14/61/16/9)","near_parity"),
       ("Balanced 35/50/15","balanced_35_50_15"),("Permanent 25/50/25","permanent"),
       ("Max Sharpe (13/79/8.5)","max_sharpe"),("60/40 SPY/AGG","60_40")]
RUN=ROOT+"results/final-v3-20261030/"
T=["SPY","AGG","GLD","XLE"]
C=["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4","#008300","#6250d6"]
W={}
for name,key in ports:
    w=json.load(open(RUN+key+"/weights.json"))["weights"]
    W[name]=1e7*replay(R,w,cost=0.,drift=.05)["wealth"]
# dynamic EWMA risk parity from the study script (monthly, cost 0), joins Jan 2007 at static RP's value
s=dynamic_ewma_risk_parity(R[T])
base=W["Static risk parity (14/61/16/9)"]; start=s.index[0]; prev=base.loc[:start].iloc[-2]
W["Dynamic EWMA risk parity (from 2007)"]=prev*(1+s).cumprod()
df=pd.DataFrame(W)
fig,(a1,a2)=plt.subplots(2,1,figsize=(13,9),sharex=True,gridspec_kw={"height_ratios":[2.2,1],"hspace":.08})
for ax in (a1,a2):
    ax.set_facecolor("#fcfcfb"); ax.grid(axis="y",color="#e6e5e0",lw=.8); ax.tick_params(colors="#52514e",labelsize=9)
    for sp in ax.spines.values(): sp.set_visible(False)
    for (a,b),lab in zip([("2007-10-09","2009-03-09"),("2020-02-19","2020-03-23"),("2022-01-03","2022-10-12")],["GFC","COVID","2022 rates"]):
        ax.axvspan(pd.Timestamp(a),pd.Timestamp(b),color="#d9d8d2",alpha=.45,lw=0)
        if ax is a1: ax.text(pd.Timestamp(a),1.003,lab,transform=ax.get_xaxis_transform(),fontsize=8.5,color="#52514e",va="bottom")
ends=[]
for (name,x0),c in zip(df.items(),C):
    x=x0.dropna(); dd=x/x.cummax()-1
    a1.plot(x.index,x/1e6,color=c,lw=2 if "W_rec" in name or "Dynamic" in name else 1.4,label=name)
    a2.plot(dd.index,dd*100,color=c,lw=1.2)
    ends.append((x.iloc[-1]/1e6,name,c))
# direct end labels, de-collided
ends.sort(); ys=[]
for v,name,c in ends:
    y=v
    if ys and y-ys[-1]<1.9: y=ys[-1]+1.9
    ys.append(y); a1.annotate(f"${v:.1f}m",(df.index[-1],v),xytext=(df.index[-1]+pd.Timedelta(days=60),y),fontsize=9,color="#0b0b0b",va="center",
        arrowprops=dict(arrowstyle="-",color=c,lw=1))
a1.set_ylabel("Portfolio value (USD m)",color="#52514e"); a1.yaxis.set_major_formatter(mt.FormatStrFormatter("%.0f"))
a1.axhline(10,color="#8a8984",lw=.8,ls=(0,(3,3)))
a1.set_title("USD 10m invested 3 Jan 2005: seven candidate portfolios to 30 Sep 2026",loc="left",fontsize=13,color="#0b0b0b",pad=22)
a1.legend(loc="upper left",frameon=False,fontsize=9,ncol=2)
a2.axhline(-20,color="#e34948",lw=1,ls=(0,(4,3))); a2.text(df.index[0],-20,"  20% drawdown limit",color="#52514e",fontsize=8.5,va="bottom")
a2.set_ylabel("Drawdown from peak (%)",color="#52514e"); a2.set_ylim(-37,2)
fig.text(.01,.01,"Retrospective replay, not a forecast. Quarterly rebalancing (plus 5-point drift trigger), 0% trading cost (mandate v3), no cash-reserve withdrawals.\n"
 "Fixed weights are from run final-v3-20261030 and were estimated on 2005-2026 data (hindsight). Dynamic risk parity re-estimates monthly from prior data only; it needs history, so it starts Jan 2007 at the static risk-parity value.\nShaded: project stress windows. Data: Yahoo adjusted closes.",
 fontsize=8,color="#52514e")
fig.patch.set_facecolor("#fcfcfb"); fig.subplots_adjust(left=.07,right=.9,top=.92,bottom=.1)
fig.savefig(ROOT+"results/charts/portfolio_history_2005.png",dpi=150)
# stats
rows=[]
for col in df:
    x=df[col].dropna(); r=x.pct_change().dropna(); yrs=(x.index[-1]-x.index[0]).days/365.25
    cg=(x.iloc[-1]/x.iloc[0])**(1/yrs)-1
    out={"Portfolio":col,"End value (USD m)":x.iloc[-1]/1e6 if "Dynamic" not in col else np.nan,"CAGR%":cg*100,"Real CAGR%":((1+cg)/1.0364-1)*100,"Vol%":r.std()*np.sqrt(252)*100,"MaxDD%":(x/x.cummax()-1).min()*100}
    for (a,b),lab in zip([("2007-10-09","2009-03-09"),("2020-02-19","2020-03-23"),("2022-01-03","2022-10-12")],["GFC","COVID","2022"]):
        y=x.loc[:b]; y=y[y.index>=pd.Timestamp(a)-pd.Timedelta(days=5)]
        out[lab+"%"]=(x.loc[:b].iloc[-1]/x.loc[:a].iloc[-2]-1)*100 if x.index[0]<pd.Timestamp(a) else np.nan
    rows.append(out)
print(pd.DataFrame(rows).round(2).to_string(index=False))
