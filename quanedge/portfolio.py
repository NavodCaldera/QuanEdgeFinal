"""Policy-constrained portfolio construction and explicit implementation accounting."""
from __future__ import annotations

import hashlib
import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize, brentq
from sklearn.covariance import LedoitWolf
from .config import TICKERS


def canonical_weights(weights):
    if set(weights) - set(TICKERS):
        raise ValueError("unknown asset")
    w = np.array([float(weights.get(t, 0)) for t in TICKERS])
    if not np.isfinite(w).all() or (w < 0).any() or abs(w.sum()-1) > 1e-6:
        raise ValueError("weights must be finite, nonnegative and sum to one")
    w = np.round(w, 6)
    w[w.argmax()] += round(1-w.sum(), 6)
    return dict(zip(TICKERS, w.tolist()))


def weight_hash(weights):
    w = canonical_weights(weights)
    raw = json.dumps({t: f"{w[t]:.6f}" for t in TICKERS}, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def hurdle(inflation=.025, spending=.04):
    if not -.1 < inflation < .5 or not 0 <= spending < 1:
        raise ValueError("inflation must be a decimal rate, not a CPI index level")
    return (1+inflation)/(1-spending)-1


def nominal_target(inflation, real):
    """Nominal geometric return needed for a real return under a stated inflation rate."""
    if not -.1 < inflation < .5:
        raise ValueError("inflation must be a decimal rate, not a CPI index level")
    return (1+inflation)*(1+real)-1


def real_return(nominal, inflation):
    return (1+nominal)/(1+inflation)-1


def reserve_schedule(cfg, years):
    """Cash set aside each 1 January, in USD: reserve_initial grown at reserve_growth."""
    return [cfg["reserve_initial"]*(1+cfg["reserve_growth"])**t for t in range(years)]


def return_check(expected_geometric, cfg):
    """C3: v2 compares expected real return with the floor; v1 with the spending hurdle."""
    if "real_return_floor" in cfg:
        return bool(real_return(expected_geometric, cfg["inflation"]) >= cfg["real_return_floor"])
    return bool(expected_geometric >= hurdle(cfg["inflation"], cfg["spending"]))


def spending_replay(returns, weights, cfg):
    """Replay with the mandate's withdrawal rule: v2 cash reserve, v1 percentage spending."""
    if "reserve_initial" in cfg:
        return replay(returns, weights, cfg["cost"], cfg["drift"],
                      reserve=(cfg["reserve_initial"]/cfg["fund_value"], cfg["reserve_growth"]))
    return replay(returns, weights, cfg["cost"], cfg["drift"], cfg["spending"])


def estimates(returns, cfg):
    mu = returns.mean().to_numpy()*252
    f = cfg["mean_shrinkage"]
    mu = (1-f)*mu + f*mu.mean()
    cov = LedoitWolf().fit(returns).covariance_*252
    return mu, cov


def bounds(cfg):
    return [(cfg["agg_min"],cfg["agg_max"]) if t == "AGG" else
            (0, min(cfg["single_cap"],cfg["gold_cap"])) if t == "GLD" else
            (0,min(cfg["single_cap"],cfg["sector_cap"])) if t in ("XLE","XLK") else
            (0,cfg["single_cap"]) for t in TICKERS]


def feasible(w, cfg):
    a=np.array([w.get(t,0) for t in TICKERS]); b=bounds(cfg)
    return bool(np.isfinite(a).all() and abs(a.sum()-1)<=1e-6 and
                all(lo-1e-6<=v<=hi+1e-6 for v,(lo,hi) in zip(a,b)) and
                a[[0,1,2,5,6]].sum()<=cfg["equity_cap"]+1e-6)


def tail_weights(losses, alpha=.99):
    """Equal scenario probabilities; share fractional boundary mass across all ties."""
    x=np.asarray(losses,float)
    if x.ndim!=1 or len(x)==0 or not np.isfinite(x).all() or not 0<alpha<1:
        raise ValueError("finite loss vector and probability required")
    mass=len(x)*(1-alpha)
    cutoff=np.sort(x)[::-1][min(int(np.ceil(mass))-1,len(x)-1)]
    above=x>cutoff; ties=x==cutoff
    out=above.astype(float)
    out[ties]=(mass-above.sum())/ties.sum()
    return out/mass


def es(returns,w,alpha=.99):
    losses=-np.asarray(returns)@np.array([w[t] for t in TICKERS])
    return float(tail_weights(losses,alpha)@losses)


def construct(returns,cfg,kind="selected"):
    """LP return/CVaR selection; SLSQP comparison candidates with explicit failures.
    With a real return target (mandate v2) "selected" minimises CVaR99 subject to the
    target and the ES budget; "max_return" keeps the mandate v1 rule for comparison."""
    if kind=="selected" and "real_return_target" in cfg:
        return target_selection(returns,cfg)
    if kind=="max_return":kind="selected"
    x=returns[TICKERS].to_numpy(); n,k=x.shape
    mu,cov=estimates(returns,cfg); equity=np.array([1,1,1,0,0,1,1.])
    if kind in ("selected","min_cvar"):
        # Variables: seven weights, unrestricted loss quantile, nonnegative excesses.
        from scipy.sparse import csr_matrix, eye, hstack, vstack
        tail=1/(n*.01)
        scenarios=hstack([csr_matrix(-x),csr_matrix(-np.ones((n,1))),-eye(n)],format="csr")
        eq=np.r_[np.ones(k),np.zeros(n+1)][None,:]
        risk=np.r_[np.zeros(k),1,np.full(n,tail)]
        rows=[scenarios,csr_matrix(np.r_[equity,np.zeros(n+1)][None,:])]
        rhs=[np.zeros(n),[cfg["equity_cap"]]]
        if kind=="selected":
            rows.append(csr_matrix(risk[None,:]));rhs.append([cfg["es_budget"]])
        objective=np.r_[-mu,np.zeros(n+1)] if kind=="selected" else risk
        A=vstack(rows,format="csr"); b=np.concatenate(rhs)
        vb=bounds(cfg)+[(None,None)]+[(0,None)]*n
        sol=linprog(objective,A_ub=A,b_ub=b,A_eq=eq,b_eq=[1],bounds=vb,method="highs")
        if not sol.success:
            return {"status":"infeasible", "reason":sol.message,"weights":None}
        if kind=="selected":
            A=vstack([A,csr_matrix(np.r_[-mu,np.zeros(n+1)][None,:])])
            b=np.r_[b,sol.fun+1e-8]
            sol=linprog(risk,A_ub=A,b_ub=b,A_eq=eq,b_eq=[1],bounds=vb,method="highs")
        duals=sol.ineqlin.marginals[-2:].tolist()
    else:
        def objective(w):
            vol=np.sqrt(w@cov@w)
            if kind=="min_variance": return vol**2
            if kind=="max_sharpe": return -(w@mu-.02)/vol
            rc=w*(cov@w)/(vol**2)
            return float(np.sum((rc-1/k)**2))
        constraints=[{"type":"eq","fun":lambda w:w.sum()-1},
                     {"type":"ineq","fun":lambda w:cfg["equity_cap"]-equity@w}]
        sol=minimize(objective,np.array([.2,.05,.05,.55,.15,0,0]),bounds=bounds(cfg),
                     constraints=constraints,method="SLSQP",options={"ftol":1e-12,"maxiter":1500})
        if not sol.success:return {"status":"failed","reason":sol.message,"weights":None}
        duals=[]
    w=canonical_weights(dict(zip(TICKERS,sol.x[:7])))
    if not feasible(w,cfg):return {"status":"failed","reason":"rounded weights violate constraints","weights":None}
    v=np.array(list(w.values())); variance=float(v@cov@v)
    net_mean=float(v@mu-cfg.get("expected_annual_turnover",1)*cfg["cost"])
    return {"status":"ok","weights":w,"weight_hash":weight_hash(w),"expected_arithmetic":net_mean,
            "expected_geometric":float(np.expm1(np.log1p(net_mean)-variance/2)),
            "volatility":np.sqrt(variance),"es99":es(x,w),"duals":duals,
            "scenario_hash":hashlib.sha256(x.tobytes()).hexdigest()}


def cvar_lp(x,mu,cfg,minimum_return=None):
    """Minimum historical CVaR99 subject to the ES budget and optional arithmetic return floor."""
    from scipy.sparse import csr_matrix, eye, hstack, vstack
    n,k=x.shape;tail=1/(n*.01);equity=np.array([1,1,1,0,0,1,1.])
    risk=np.r_[np.zeros(k),1,np.full(n,tail)]
    rows=[hstack([csr_matrix(-x),csr_matrix(-np.ones((n,1))),-eye(n)],format="csr"),
          csr_matrix(np.r_[equity,np.zeros(n+1)][None,:]),csr_matrix(risk[None,:])]
    rhs=[np.zeros(n),[cfg["equity_cap"]],[cfg["es_budget"]]]
    if minimum_return is not None:
        rows.append(csr_matrix(np.r_[-mu,np.zeros(n+1)][None,:]));rhs.append([-minimum_return])
    return linprog(risk,A_ub=vstack(rows,format="csr"),b_ub=np.concatenate(rhs),
                   A_eq=np.r_[np.ones(k),np.zeros(n+1)][None,:],b_eq=[1],
                   bounds=bounds(cfg)+[(None,None)]+[(0,None)]*n,method="highs")


def target_selection(returns,cfg,iterations=60):
    """Lowest-CVaR99 allocation whose expected geometric return reaches the real target.
    The LP is linear in the arithmetic mean, so the smallest arithmetic floor meeting the
    geometric target is found by bisection. A non-binding target returns minimum CVaR."""
    x=returns[TICKERS].to_numpy();mu,cov=estimates(returns,cfg)
    cost=cfg.get("expected_annual_turnover",0)*cfg["cost"]
    goal=nominal_target(cfg["inflation"],cfg["real_return_target"])
    def geometric(w):return float(np.expm1(np.log1p(w@mu-cost)-w@cov@w/2))
    base=cvar_lp(x,mu,cfg)
    if not base.success:return {"status":"infeasible","reason":base.message,"weights":None}
    w=base.x[:7];binding=geometric(w)<goal
    if binding:
        best=construct(returns,cfg,"max_return")
        if best["weights"] is None:return best
        lo=float(w@mu);hi=float(np.array(list(best["weights"].values()))@mu)-1e-9
        top=cvar_lp(x,mu,cfg,hi)
        if not top.success or geometric(top.x[:7])<goal:
            return {"status":"infeasible","reason":"real return target unreachable within the ES budget","weights":None}
        w=top.x[:7]
        for _ in range(iterations):
            mid=(lo+hi)/2;sol=cvar_lp(x,mu,cfg,mid)
            if sol.success and geometric(sol.x[:7])>=goal:hi,w=mid,sol.x[:7]
            else:lo=mid
    weights=canonical_weights(dict(zip(TICKERS,w)))
    if not feasible(weights,cfg):return {"status":"failed","reason":"rounded weights violate constraints","weights":None}
    v=np.array(list(weights.values()));variance=float(v@cov@v);net=float(v@mu-cost)
    nominal=float(np.expm1(np.log1p(net)-variance/2))
    return {"status":"ok","weights":weights,"weight_hash":weight_hash(weights),"expected_arithmetic":net,
            "expected_geometric":nominal,"expected_real":real_return(nominal,cfg["inflation"]),
            "nominal_target":goal,"target_binding":bool(binding),"volatility":np.sqrt(variance),"es99":es(x,weights),
            "duals":[],"scenario_hash":hashlib.sha256(x.tobytes()).hexdigest()}


def replay(returns,weights,cost=.0005,drift=.05,spending=0.,buy_hold=False,reserve=None):
    """Returns enter before period-end rebalancing; annual spending after net returns.
    reserve=(initial, growth) instead withdraws a cash reserve, as a fraction of the initial
    fund, before the first trading day of each year; a depleted fund stays at zero."""
    target=np.array([weights[t] for t in returns.columns]); positions=target.copy()
    nav=1.; rows=[]; dates=returns.index; year=-1
    for i,(date,row) in enumerate(returns.iterrows()):
        draw=0.
        if reserve and (i==0 or dates[i-1].year!=date.year):
            year+=1;draw=min(nav,reserve[0]*(1+reserve[1])**year)
            positions*=(nav-draw)/nav if nav>0 else 0.;nav-=draw
        if nav<=0:
            rows.append((date,0.,0.,0.,draw));continue
        old=nav; positions*=1+row.to_numpy(); gross=positions.sum()
        current=positions/gross; turnover=0.
        quarter_end=i==len(dates)-1 or dates[i+1].quarter!=date.quarter
        if not buy_hold and (quarter_end or np.max(abs(current-target))>drift):
            turnover=float(np.abs(target-current).sum())
            positions=target*gross*(1-cost*turnover)
        net=positions.sum()
        year_end=i==len(dates)-1 or dates[i+1].year!=date.year
        if spending and year_end and date.month==12:
            draw=spending*net;positions*=1-spending
        nav=float(positions.sum())
        rows.append((date,net/old-1,nav,turnover,draw))
    return pd.DataFrame(rows,columns=["date","return","wealth","turnover","spending"]).set_index("date")


def kpis(r,rf,market,benchmark):
    frame=pd.concat([r.rename("r"),rf.rename("rf"),market.rename("m"),benchmark.rename("b")],axis=1).dropna()
    if len(frame)<2:return {"status":"insufficient aligned history"}
    x=frame.r; years=(frame.index[-1]-frame.index[0]).days/365.25
    wealth=pd.concat([pd.Series([1.]),(1+x).cumprod().reset_index(drop=True)],ignore_index=True)
    dd=wealth/wealth.cummax()-1; mdd=float(dd.min());cagr=float((1+x).prod()**(1/years)-1)
    excess=x-frame.rf; me=frame.m-frame.rf
    beta=float(np.cov(excess,me,ddof=1)[0,1]/me.var()) if me.var()>0 else np.nan
    def ratio(a,b):return float(a/b) if b>1e-12 else None
    downside=np.sqrt(np.mean(np.minimum(x,0)**2))*np.sqrt(252)
    active=x-frame.b
    underwater=dd<0; longest=current=0
    for flag in underwater:
        current=current+1 if flag else 0;longest=max(longest,current)
    return {"cagr":cagr,"cumulative_return":float((1+x).prod()-1),"annual_volatility":float(x.std()*np.sqrt(252)),
            "sharpe":ratio(excess.mean()*252,excess.std()*np.sqrt(252)),"sortino":ratio(x.mean()*252,downside),
            "beta":beta,"treynor":float(excess.mean()*252/beta) if np.isfinite(beta) and abs(beta)>.05 else None,
            "jensen_alpha":float((excess.mean()-beta*me.mean())*252),
            "information_ratio":ratio(active.mean()*252,active.std()*np.sqrt(252)),
            "maximum_drawdown":mdd,"calmar":ratio(cagr,abs(mdd)),"max_underwater_days":longest,
            "recovered_at_end":bool(dd.iloc[-1]>=-1e-10),"observations":len(x)}


def money_weighted(path,value=1e7,start_date=None):
    dates=path.index
    origin=pd.Timestamp(start_date) if start_date is not None else dates[0]-pd.Timedelta(days=1)
    times=(dates-origin).days/365.0
    cf=path.spending.to_numpy()*value;cf[-1]+=path.wealth.iloc[-1]*value
    def npv(rate):return float(-value+np.sum(cf/(1+rate)**times))
    try:return brentq(npv,-.95,10)
    except ValueError:return None
