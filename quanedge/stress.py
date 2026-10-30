"""Historical buy-and-hold stress and scenario-consistent dollar attribution."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .portfolio import tail_weights
from .config import TICKERS

SCENARIOS={"GFC":("2007-10-09","2009-03-09"),"COVID":("2020-02-19","2020-03-23"),
           "Rates 2022":("2022-01-03","2022-10-12")}


def attribution(returns,weights,alpha=.99,value=1e7):
    w=np.array([weights[t] for t in returns.columns]);losses=-value*returns.to_numpy()*w
    total=losses.sum(axis=1);tw=tail_weights(total,alpha);components=tw@losses
    marginal=tw@(-returns.to_numpy())
    standalone=np.array([tail_weights(losses[:,i],alpha)@losses[:,i] for i in range(len(w))])
    return {"source":"historical attribution","alpha":alpha,"es_usd":float(tw@total),
            "components":dict(zip(returns.columns,components.tolist())),
            "marginal_es_usd_per_dollar":dict(zip(returns.columns,marginal.tolist())),
            "derivative_basis":"independent dollar exposures; boundary ties give the shared-tail subgradient",
            "risk_budget_share":dict(zip(returns.columns,(components/(tw@total)).tolist())) if tw@total>0 else None,
            "residual_usd":float(components.sum()-tw@total),
            "diversification_benefit_usd":float(standalone.sum()-tw@total)}


def stress_tests(prices,weights,value=1e7):
    w=np.array([weights[t] for t in prices.columns]);rows=[]
    for name,(start,end) in SCENARIOS.items():
        p=prices.loc[start:end]
        if p.empty or str(p.index[0].date())!=start or str(p.index[-1].date())!=end:
            rows.append({"scenario":name,"status":"incomplete data coverage"});continue
        growth=p/p.iloc[0];wealth=growth.to_numpy()@w
        contrib=w*(growth.iloc[-1].to_numpy()-1)
        dd=wealth/np.maximum.accumulate(wealth)-1
        rows.append({"scenario":name,"status":"ok","start":start,"end":end,"return":float(contrib.sum()),
                     "loss_usd":float(-value*contrib.sum()),"drawdown":float(dd.min()),
                     "breach":bool(-contrib.sum()>.20 or -dd.min()>.20),
                     "contributions_usd":dict(zip(prices.columns,(-value*contrib).tolist())),
                     "assumption":"buy-and-hold from scenario start, no trades or transaction costs"})
    return rows


def hypothetical(training,weights,value=1e7):
    # Joint conditional expectation under covariance estimated on SPY's worst decile.
    stressed=training.loc[training.SPY<=training.SPY.quantile(.1)]
    cov=stressed.cov().to_numpy();mean=stressed.mean().to_numpy()
    known=[0,3,4];other=[1,2,5,6];shock=np.zeros(7);shock[known]=[-.25,-.10,0]
    shock[other]=mean[other]+cov[np.ix_(other,known)]@np.linalg.pinv(cov[np.ix_(known,known)])@(shock[known]-mean[known])
    # Deterministic simple returns cannot imply negative asset wealth.
    if (shock<=-1).any():return {"status":"failed: conditional shocks imply nonpositive wealth"}
    contributions=-value*np.array([weights[t] for t in TICKERS])*shock
    return {"scenario":"Hypothetical joint inflation shock","status":"ok","shocks":dict(zip(TICKERS,shock.tolist())),
            "return":float(-contributions.sum()/value),"loss_usd":float(contributions.sum()),
            "contributions_usd":dict(zip(TICKERS,contributions.tolist())),"breach":bool(contributions.sum()>.2*value),
            "assumption":"deterministic, no calibrated probability; stressed training covariance conditional mean"}


def reverse_stress(training,weights,limit=.20):
    """Minimum Mahalanobis joint simple-return shock breaching a one-step loss limit."""
    cov=training.cov().to_numpy();inv=np.linalg.pinv(cov);w=np.array([weights[t] for t in TICKERS])
    sol=minimize(lambda x:float(x@inv@x),np.full(7,-limit),method="SLSQP",bounds=[(-.999,2)]*7,
                 constraints={"type":"ineq","fun":lambda x:-w@x-limit},options={"maxiter":1000,"ftol":1e-8})
    return {"status":"ok" if sol.success else "failed","shocks":dict(zip(TICKERS,sol.x.tolist())),
            "loss_fraction":float(-w@sol.x),"distance_squared":float(sol.fun),
            "interpretation":"minimum covariance-distance one-step shock; not a probability or multi-day drawdown forecast"}


def reserve_survival(monthly,weights,cfg,years=None):
    """Fixed real cash reserve paid each 1 January before returns (mandate v2).
    Joint non-circular 12-month blocks; quarterly/drift rebalancing; real values deflate
    by the policy inflation assumption, matching the reserve's growth."""
    years=years or cfg["survival_years"];x=monthly[TICKERS].dropna().to_numpy()
    if len(x)<24:return {"status":"unavailable: insufficient monthly data"}
    n=cfg["survival_paths"];rng=np.random.default_rng(cfg["seed"]);fund=cfg["fund_value"]
    w=np.array([weights[t] for t in TICKERS],float);positions=np.tile(w,(n,1))
    depleted=np.full(n,0);out=[]
    for year in range(1,years+1):
        need=cfg["reserve_initial"]*(1+cfg["reserve_growth"])**(year-1)/fund
        nav=positions.sum(axis=1);short=(nav<need)&(depleted==0)
        depleted[short]=year
        positions*=np.where(depleted==0,(nav-need)/np.where(nav>0,nav,1),0.)[:,None]
        starts=rng.integers(0,len(x)-11,n)
        for month in range(12):
            positions*=1+x[starts+month]
            total=positions.sum(axis=1);current=positions/np.where(total>0,total,1)[:,None]
            trade=np.full(n,(month+1)%3==0)|(np.max(abs(current-w),axis=1)>cfg["drift"])
            turnover=np.abs(current-w).sum(axis=1);nav=total*(1-cfg["cost"]*turnover)
            positions[trade]=nav[trade,None]*w
        if year in (10,years):
            real=positions.sum(axis=1)*fund/(1+cfg["inflation"])**year
            funded=float((depleted==0).mean())
            out.append({"year":year,"all_payments_funded":funded,"mc_se":float(np.sqrt(funded*(1-funded)/n)),
                        "real_capital_preserved":float((real>=fund).mean()),
                        "median_real_balance_usd":float(np.median(real)),
                        "p10_real_balance_usd":float(np.quantile(real,.1)),
                        "median_depletion_year":float(np.median(depleted[depleted>0])) if (depleted>0).any() else None})
    return {"status":"illustrative","paths":n,"block":"non-circular joint 12 months","horizon_years":years,
            "schedule":"USD reserve_initial x (1+reserve_growth)^(t-1) withdrawn each 1 January; cash earns 0","results":out}


def survival(monthly,monthly_inflation,weights,cfg,years=10):
    """Joint non-circular 12-month blocks; annual spending, quarterly rebalancing."""
    data=monthly.join(monthly_inflation.rename("inflation")).dropna()
    x=data.to_numpy();n=cfg["survival_paths"];rng=np.random.default_rng(cfg["seed"])
    w=np.array([weights[t] for t in monthly.columns]);positions=np.tile(w,(n,1));cpi=np.ones(n);out=[]
    if len(x)<24: return {"status":"unavailable: insufficient joint monthly data"}
    for year in range(1,years+1):
        starts=rng.integers(0,len(x)-11,n)
        for month in range(12):
            row=x[starts+month];positions*=1+row[:,:7];cpi*=1+row[:,7]
            current=positions/positions.sum(axis=1)[:,None]
            trade=np.full(n,(month+1)%3==0) | (np.max(abs(current-w),axis=1)>cfg["drift"])
            turnover=np.abs(current-w).sum(axis=1)
            nav=positions.sum(axis=1)*(1-cfg["cost"]*turnover)
            positions[trade]=nav[trade,None]*w
        positions*=1-cfg["spending"]
        if year in (5,10):
            real=positions.sum(axis=1)/cpi;p=float((real<1).mean())
            out.append({"year":year,"shortfall_probability":p,"mc_se":float(np.sqrt(p*(1-p)/n)),
                        "median_real_surplus_usd":float((np.median(real)-1)*cfg["value"])})
    return {"status":"illustrative","paths":n,"block":"non-circular joint 12 months","results":out}
