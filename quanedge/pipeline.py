"""Reproducible competition orchestration. All outputs belong to one immutable run."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
from importlib.metadata import version
import numpy as np
import pandas as pd
import yaml
from scipy.stats import binomtest
from .config import ROOT,TICKERS
from .portfolio import construct,canonical_weights,weight_hash,hurdle,replay,kpis,feasible,money_weighted,estimates
from .backtest import assess,model_pass,verdict
from .stress import stress_tests,hypothetical,attribution,reverse_stress,survival
from .results import digest,artifact_key
from .risk import fit_models,risk_table,portfolio_log_returns,rolling_forecasts,save_forecasts
from .risk.uncertainty import bootstrap_intervals,with_intervals
from .risk.evt import threshold_scan
from .risk.validation import check_dated_history


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


def write_json(path,obj):
    def clean(x):
        if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
        if isinstance(x,(list,tuple)):return [clean(v) for v in x]
        if isinstance(x,np.ndarray):return clean(x.tolist())
        if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
        if isinstance(x,np.integer):return int(x)
        if isinstance(x,np.bool_):return bool(x)
        if isinstance(x,(Path,pd.Timestamp,datetime)):return str(x)
        return x
    Path(path).write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+"\n",encoding="utf-8")


def load_inputs(cfg):
    from .data import load_clean_prices,load_macro_data
    prices=load_clean_prices();check_dated_history(prices)
    if prices.index.max()>pd.Timestamp(cfg["snapshot_end"]):
        raise ValueError("post-snapshot prices refused")
    if prices.index.max()<pd.Timestamp(cfg["snapshot_end"]):
        raise ValueError(f"snapshot ends {prices.index.max().date()}, required {cfg['snapshot_end']}; incomplete data cannot be final")
    returns=prices.pct_change().dropna();macro=load_macro_data()
    return prices,returns,macro


def make_candidates(x,cfg):
    result={name:construct(x,cfg,kind) for name,kind in
            [("selected","selected"),("min_cvar","min_cvar"),("min_variance","min_variance"),
             ("near_parity","near_parity"),("max_sharpe","max_sharpe")]}
    for name,w in {"40_60":{"SPY":.4,"AGG":.6},"60_40":{"SPY":.6,"AGG":.4},
                   "equal_weight":{t:1/7 for t in TICKERS},"permanent":{"SPY":.25,"AGG":.5,"GLD":.25},
                   "in_policy":{"SPY":.35,"AGG":.5,"GLD":.15}}.items():
        w=canonical_weights(w);result[name]={"status":"benchmark","weights":w,"weight_hash":weight_hash(w)}
    _,cov=estimates(x,cfg)
    from scipy.optimize import minimize
    def rp(w):
        rc=w*(cov@w)/(w@cov@w)
        return np.sum((rc-1/7)**2)
    sol=minimize(rp,np.ones(7)/7,bounds=[(0,1)]*7,constraints={"type":"eq","fun":lambda w:w.sum()-1},
                 options={"ftol":1e-12,"maxiter":1000})
    if sol.success:
        w=canonical_weights(dict(zip(TICKERS,sol.x)));result["unconstrained_parity"]={"status":"benchmark","weights":w,"weight_hash":weight_hash(w)}
    return result


def adjustments(train,full,cfg):
    # A1 ordering is frozen by training ES, even for full-estimation candidate weights.
    training=make_candidates(train,cfg);current=make_candidates(full,cfg)
    order=sorted([n for n in ("min_cvar","min_variance","near_parity","max_sharpe")
                  if training[n]["weights"] is not None],key=lambda n:training[n]["es99"])
    alts=[("A1_"+n,current[n],cfg) for n in order]
    benchmark=canonical_weights({"SPY":.6,"AGG":.4})
    from .portfolio import es
    raised=max(cfg["es_budget"],min(.03,es(train,benchmark)))
    for name,changes in [("A2",{"gold_cap":.20}),("A3",{"spending":.035}),
                         ("A4",{"es_budget":raised}),("A5",{"gold_cap":.20,"spending":.035,"es_budget":raised})]:
        policy=dict(cfg,**changes);alts.append((name,construct(full,policy),policy))
    return alts,raised


def constraint_effects(x,cfg):
    baseline=construct(x,cfg);rows=[]
    for field,values in [("gold_cap",[.20,.25,.4]),("equity_cap",[.60,.65]),("agg_min",[0.]),("agg_max",[1.]),("es_budget",[.03])]:
        for value in values:
            alternative=construct(x,dict(cfg,**{field:value}))
            row={"constraint":field,"from":cfg[field],"to":value,"status":alternative["status"],
                 "baseline":baseline,"relaxed":alternative,"label":"in-sample, estimator-dependent controlled re-solve"}
            if baseline["weights"] and alternative["weights"]:
                row["objective_change"]=alternative["expected_arithmetic"]-baseline["expected_arithmetic"]
                row["same_scenarios"]=baseline["scenario_hash"]==alternative["scenario_hash"]
            rows.append(row)
    return rows


def evaluate(name,candidate,cfg,prices,returns,macro,out,meta,cache,full=True):
    if candidate.get("weights") is None:
        return dict(candidate,checks={"C1":False,"C2":None,"C3":None,"C4":None,"C5":None})
    w=candidate["weights"];wh=weight_hash(w);folder=out/name;folder.mkdir(parents=True)
    print(f"Evaluating {name} {wh[:8]}",flush=True)
    write_json(folder/"weights.json",dict(weights=w,weight_hash=wh,effective_date=cfg["snapshot_end"],
                estimation_end=candidate.get("estimation_end",cfg["snapshot_end"])))
    series=replay(returns,w,cfg["cost"],cfg["drift"]);series.to_csv(folder/"performance.csv")
    draw=replay(returns,w,cfg["cost"],cfg["drift"],cfg["spending"])
    draw.to_csv(folder/"spending.csv")
    benchmark=replay(returns,canonical_weights({"SPY":.4,"AGG":.6}),cfg["cost"],cfg["drift"])["return"]
    rf=macro.rf_daily_effective.reindex(returns.index)
    performance=kpis(series["return"],rf,returns.SPY,benchmark)
    performance["money_weighted_return"]=money_weighted(draw)
    historical=stress_tests(prices,w,cfg["value"])
    hyp=hypothetical(returns.loc[:cfg["training_end"]],w,cfg["value"])
    component=attribution(returns,w,value=cfg["value"])
    logs=np.log1p(returns);r=portfolio_log_returns(logs,w)
    if wh not in cache:
        models=fit_models(logs,w,n_sim=cfg["n_sim"],seed=cfg["seed"])
        table=risk_table(models,value=cfg["value"])
        print(f"  rolling forecasts {name}",flush=True)
        forecasts=rolling_forecasts(r,methods=["historical","normal","evt","fhs","garch_evt"],window=cfg["window"],refit=cfg["refit"])
        failures=forecasts.attrs.get("fit_failures",[])
        forecasts["weight_hash"]=wh;forecasts["data_hash"]=meta["data_hash"]
        forecasts["evaluation_label"]="sequential risk-forecast evaluation"
        forecasts["allocation_cutoff"]=candidate.get("estimation_end",cfg["snapshot_end"])
        forecasts["config_hash"]=meta["config_hash"]
        forecasts["code_rev"]=meta["code_rev"]
        cache[wh]=(table,forecasts,failures,{n:{"status":m.status,"params":m.params} for n,m in models.items()})
    table,forecasts,failures,model_params=cache[wh]
    table.to_csv(folder/"risk.csv",index=False);save_forecasts(forecasts,folder/"forecasts.csv")
    assessments=[assess(forecasts,wh,m,a,cfg["evaluation_start"],cfg["snapshot_end"])
                 for m in ["historical","normal","evt","fhs","garch_evt"] for a in [.90,.95,.99]]
    primary=next(v for v in assessments if v["method"]==cfg["primary"] and v["alpha"]==.99)
    challenger=next(v for v in assessments if v["method"]==cfg["challenger"] and v["alpha"]==.99)
    model_ok=model_pass(primary) or model_pass(challenger)
    estimation=returns.loc[:candidate.get("estimation_end",cfg["snapshot_end"])]
    from .portfolio import es
    policy_es=es(estimation,w)
    checks={"C1":feasible(w,cfg),"C2":policy_es<=cfg["es_budget"]+1e-6,
            "C3":candidate.get("expected_geometric",-1)>=hurdle(cfg["inflation"],cfg["spending"]),
            "C4":bool(model_ok),"C5":bool(all(s.get("status")=="ok" for s in historical) and
             all(s.get("loss_usd",np.inf)<=cfg["drawdown_limit"]*cfg["value"] for s in historical) and
             -historical[0].get("drawdown",-1)<=cfg["drawdown_limit"])}
    result={**candidate,"weight_hash":wh,"checks":checks,"policy":cfg,"performance":performance,
            "stress":historical+[hyp],"attribution":component,"policy_es99_usd":policy_es*cfg["value"],
            "validation":assessments,"model_used":cfg["primary"] if model_pass(primary) else cfg["challenger"] if model_pass(challenger) else None,
            "model_parameters":model_params,"fit_failures":failures,
            "risk_replay":"daily rebalanced without costs; differs from quarterly implementation",
            "evaluation_label":"retrospective portfolio evaluation"}
    write_json(folder/"summary.json",result)
    return result


def walk_forward(returns,cfg):
    pieces=[];weights=[]
    for year in range(2017,returns.index[-1].year+1):
        train=returns.loc[returns.index<pd.Timestamp(f"{year}-01-01")]
        result=construct(train,cfg);weights.append({"year":year,**result})
        if result.get("weights"):
            # Annual fixed allocation held buy-and-hold; explicit annual trade cost.
            p=replay(returns.loc[str(year)],result["weights"],buy_hold=True)
            p.iloc[0,p.columns.get_loc("return")]-=2*cfg["cost"]
            pieces.append(p[["return"]])
    return (pd.concat(pieces) if pieces else pd.DataFrame()),weights


def run(cfg_path,stage="final",run_id=None):
    cfg=yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    if stage=="final":
        frozen=yaml.safe_load(git("show","prereg-v1:config/final.yaml"))
        if cfg!=frozen:raise ValueError("policy/config differs from prereg-v1; log a mandate change explicitly")
    prices,returns,macro=load_inputs(cfg);train=returns.loc[:cfg["training_end"]]
    candidates=make_candidates(train,cfg)
    if stage=="training":
        out=ROOT/"results/training";out.mkdir(parents=True,exist_ok=True)
        write_json(out/"candidates.json",candidates)
        write_json(out/"constraint_effects.json",constraint_effects(train,cfg))
        from .portfolio import es
        write_json(out/"freeze_values.json",{"A4_budget":max(cfg["es_budget"],min(.03,es(train,canonical_weights({"SPY":.6,"AGG":.4})))),
                    "policy":cfg,"hurdle":hurdle(cfg["inflation"],cfg["spending"]),"training_end":cfg["training_end"]})
        print(out);return out
    run_id=run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out=ROOT/"results"/("."+run_id+".staging");out.mkdir(parents=True,exist_ok=False)
    final=ROOT/"results"/run_id
    if final.exists():raise ValueError("run already exists")
    meta={"schema_version":1,"run_id":run_id,"data_hash":hashlib.sha256((ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest(),
          "config_hash":digest(cfg),"code_rev":git("rev-parse","HEAD"),"snapshot_end":cfg["snapshot_end"],
          "created_at":datetime.now(timezone.utc).isoformat(),"versions":{p:version(p) for p in
          ["numpy","pandas","scipy","arch","statsmodels","streamlit","scikit-learn"]},
          "source":"Yahoo Finance adjusted prices; FRED macro; revised modern data with approximate release lags",
          "human_validation":"pending","solo_eligibility":"pending","deadline":"unknown"}
    write_json(out/"manifest.json",meta)
    full_candidates=make_candidates(returns,cfg);allocations={};cache={};index={}
    for name,candidate in full_candidates.items():
        allocations[name]=evaluate(name,candidate,cfg,prices,returns,macro,out,meta,cache)
    for name,candidate in candidates.items():
        if name!="selected":continue
        allocations["W_train"]=evaluate("W_train",dict(candidate,estimation_end=cfg["training_end"]),cfg,prices,returns,macro,out,meta,cache)
    alternatives,a4=adjustments(train,returns,cfg);alt_checks=[]
    for name,candidate,policy in alternatives:
        allocations[name]=evaluate(name,candidate,policy,prices,returns,macro,out,meta,cache)
        alt_checks.append((name,allocations[name]["checks"]))
    decision=verdict(allocations["selected"]["checks"],alt_checks)
    selected=allocations["selected"]
    if selected.get("weights"):
        w=selected["weights"];print("Bootstrap uncertainty",flush=True)
        intervals=bootstrap_intervals(np.log1p(returns),w,methods=["historical","normal","evt"],
                    reps=cfg["bootstrap_reps"],block=cfg["bootstrap_block"],seed=cfg["seed"])
        intervals.to_csv(out/"selected/uncertainty.csv",index=False)
        selected["reverse_stress"]=reverse_stress(train,w)
        selected["conditional_attribution"]="unavailable: FHS is fitted to portfolio returns"
        monthly=(1+returns).resample("ME").prod()-1
        cpi=macro.CPIAUCSL.resample("ME").last().pct_change()
        write_json(out/"survival.json",{n:survival(monthly,cpi,allocations[n]["weights"],cfg) for n in ["selected","40_60","permanent"]})
        scans=threshold_scan(-portfolio_log_returns(np.log1p(returns),w).to_numpy())
        scans.to_csv(out/"selected/evt_thresholds.csv",index=False)
        from .robustness import additional_evidence
        additional_evidence(returns,macro,w,cfg,out/"selected/robustness")
    wf,annual=walk_forward(returns,cfg);wf.to_csv(out/"walk_forward.csv")
    write_json(out/"walk_forward_weights.json",annual)
    macro_table=pd.DataFrame({"spy_agg_correlation_252":returns.SPY.rolling(252).corr(returns.AGG),
                              "dgs10_change":macro.DGS10.diff().reindex(returns.index)})
    macro_table.to_csv(out/"macro.csv")
    for name,result in allocations.items():
        if not result.get("weights"):continue
        for method in ["historical","normal","student_t","mc_normal","mc_t","evt","fhs","garch_evt"]:
            key=artifact_key(result["weight_hash"],method,meta["data_hash"],meta["config_hash"],meta["code_rev"])
            index[key]={"portfolio":name,"path":name,"weight_hash":result["weight_hash"]}
    write_json(out/"index.json",index)
    write_json(out/"submission.json",{"metadata":meta,"policy":cfg,"portfolios":allocations,"decision":decision,"A4_budget":a4})
    from .evidence import complete,seal
    complete(out)
    from .reporting import generate
    generate(out)
    meta["files"]={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob("*") if p.is_file() and p.name!="manifest.json"}
    seal(out)
    out.rename(final)
    (ROOT/"results/latest.txt").write_text(run_id,encoding="utf-8")
    print(f"Completed {final}: {decision['outcome']}",flush=True)
    return final


def main():
    p=argparse.ArgumentParser();p.add_argument("--config",default="config/final.yaml")
    p.add_argument("--stage",choices=["training","final"],default="final");p.add_argument("--run-id")
    args=p.parse_args();run(args.config,args.stage,args.run_id)


if __name__=="__main__":main()
