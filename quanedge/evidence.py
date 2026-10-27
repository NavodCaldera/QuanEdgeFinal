"""Complete descriptive evidence and seal all material inputs of a local run."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .config import ROOT,TICKERS
from .portfolio import replay,kpis,money_weighted,canonical_weights,estimates
from .results import digest,artifact_key
from .risk import load_forecasts,save_forecasts


def complete(run):
    from .pipeline import write_json,git
    run=Path(run);bundle=json.loads((run/"submission.json").read_text(encoding="utf-8"));cfg=bundle["policy"]
    meta=bundle["metadata"]
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"data").rglob("*") if p.is_file()}
    meta["price_hash"]=hashlib.sha256((ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()
    meta["input_hashes"]=inputs;meta["data_hash"]=digest(inputs)
    def source_hash(p):return hashlib.sha256(p.read_bytes().replace(b"\r\n",b"\n")).hexdigest()
    sources={p.relative_to(ROOT).as_posix():source_hash(p) for p in (ROOT/"quanedge").rglob("*.py")}
    for p in [ROOT/"app.py",ROOT/"config/final.yaml",ROOT/"requirements.txt",ROOT/"requirements.lock.txt"]:
        if p.exists():sources[p.relative_to(ROOT).as_posix()]=source_hash(p)
    for p in (ROOT/"scripts").glob("*.mjs"):sources[p.relative_to(ROOT).as_posix()]=source_hash(p)
    meta["source_hash_convention"]="SHA-256 after CRLF-to-LF normalization; data hashes use exact bytes"
    meta["source_file_hashes"]=sources;meta["source_tree_hash"]=digest(sources)
    meta.setdefault("analysis_initial_revision",meta.get("git_revision",meta["code_rev"].split("+source:")[0]))
    meta["git_revision"]=git("rev-parse","HEAD")
    meta["code_rev"]=meta["git_revision"]+"+source:"+meta["source_tree_hash"][:16]
    prices=pd.read_csv(ROOT/"data/clean/prices_clean.csv",index_col=0,parse_dates=True)
    returns=prices.pct_change().dropna();macro=pd.read_csv(ROOT/"data/clean/macro_clean.csv",index_col=0,parse_dates=True)
    distributions=pd.read_csv(ROOT/"data/raw/distributions.csv",parse_dates=["date"])
    end=pd.Timestamp(cfg["snapshot_end"]);yield_by_asset={}
    for t,g in distributions.groupby("ticker"):
        g=g.sort_values("date");recent=g[(g.date>end-pd.Timedelta(days=365))&(g.date<=end)]
        yield_by_asset[t]=float(recent.dividend.sum()/g.loc[g.date<=end,"close"].iloc[-1])
    bench=replay(returns,canonical_weights({"SPY":.4,"AGG":.6}),cfg["cost"],cfg["drift"])["return"]
    index={}
    candidate_rows=[]
    for name,result in bundle["portfolios"].items():
        if not result.get("weights"):continue
        w=result["weights"];folder=run/name;wh=result["weight_hash"]
        result["distribution_yield"]=sum(w[t]*yield_by_asset[t] for t in TICKERS)
        _,cov=estimates(returns.loc[:result.get("estimation_end",cfg["snapshot_end"])],cfg)
        mu,_=estimates(returns.loc[:result.get("estimation_end",cfg["snapshot_end"])],cfg)
        v=np.array([w[t] for t in TICKERS]);variance=float(v@cov@v)
        if "expected_arithmetic" not in result:
            arithmetic=float(v@mu-result["policy"].get("expected_annual_turnover",1)*cfg["cost"])
            result["expected_arithmetic"]=arithmetic
            result["expected_geometric"]=float(np.expm1(np.log1p(arithmetic)-variance/2))
            from .portfolio import hurdle
            result["checks"]["C3"]=bool(result["expected_geometric"]>=hurdle(cfg["inflation"],cfg["spending"]))
        result["volatility"]=float(np.sqrt(variance))
        result["performance"]["distribution_yield"]=result["distribution_yield"]
        rc=v*(cov@v)/variance
        result["diversification_ratio"]=float(v@np.sqrt(np.diag(cov))/np.sqrt(variance))
        result["volatility_risk_contributions"]=dict(zip(TICKERS,rc.tolist()))
        result["risk_contribution_dispersion"]=float(rc.std())
        path=pd.read_csv(folder/"performance.csv",index_col=0,parse_dates=True)
        full_spending=pd.read_csv(folder/"spending.csv",index_col=0,parse_dates=True)
        result["performance"]["money_weighted_return"]=money_weighted(full_spending,start_date=prices.index[0])
        period=path.loc[cfg["evaluation_start"]:]
        result["retrospective_2017_onward"]=kpis(period["return"],macro.rf_daily_effective,returns.SPY,bench)
        spending=replay(returns.loc[cfg["evaluation_start"]:],w,cfg["cost"],cfg["drift"],result["policy"]["spending"])
        origin=prices.loc[prices.index<spending.index[0]].index[-1]
        result["retrospective_2017_onward"]["money_weighted_return"]=money_weighted(spending,start_date=origin)
        cpi=macro.CPIAUCSL.loc[period.index].dropna();inflation=(cpi.iloc[-1]/cpi.iloc[0])**(365.25/(cpi.index[-1]-cpi.index[0]).days)-1
        from .portfolio import hurdle
        result["retrospective_2017_onward"]["realised_inflation_hurdle"]=hurdle(float(inflation),result["policy"]["spending"])
        recovery=[]
        for scenario in result["stress"][:3]:
            if scenario.get("status")!="ok":continue
            start=scenario["start"];local=path.wealth.loc[start:];peak=float(local.iloc[0]);trough_date=local.loc[:scenario["end"]].idxmin()
            hit=local.loc[trough_date:];hit=hit[hit>=peak]
            recovery.append({"scenario":scenario["scenario"],"peak":start,"trough":str(trough_date.date()),
                             "peak_to_trough_days":int((local.loc[:trough_date]).shape[0]-1),
                             "trough_to_recovery_days":int(local.loc[trough_date:hit.index[0]].shape[0]-1) if len(hit) else None,
                             "recovery":str(hit.index[0].date()) if len(hit) else f"not recovered by {cfg['snapshot_end']}"})
        result["crisis_recovery"]=recovery
        candidate_rows.append({"portfolio":name,"weight_hash":wh,"expected_arithmetic":result["expected_arithmetic"],
            "expected_geometric":result["expected_geometric"],"volatility":result["volatility"],
            "es99_usd":result["policy_es99_usd"],"distribution_yield":result["distribution_yield"],
            "diversification_ratio":result["diversification_ratio"],"risk_contribution_dispersion":result["risk_contribution_dispersion"],
            "max_drawdown":result["performance"]["maximum_drawdown"],"worst_scenario_usd":max(s.get("loss_usd",0) for s in result["stress"]),
            "feasible":result["checks"]["C1"],"validated_model":result.get("model_used"),"evaluation_label":"retrospective portfolio evaluation"})
        fc=load_forecasts(folder/"forecasts.csv");fc["data_hash"]=meta["data_hash"]
        fc["source_tree_hash"]=meta["source_tree_hash"]
        fc["config_hash"]=digest(result["policy"])
        fc["code_rev"]=meta["code_rev"];save_forecasts(fc,folder/"forecasts.csv")
        write_json(folder/"summary.json",result)
        for method in result.get("model_parameters",{}):
            key=artifact_key(wh,method,meta["data_hash"],digest(result["policy"]),meta["code_rev"])
            index[key]={"portfolio":name,"path":name,"weight_hash":wh}
    chosen=bundle["decision"].get("alternative","selected")
    pd.DataFrame(candidate_rows).to_csv(run/"candidate_table.csv",index=False)
    bundle["decision"]["reported_portfolio"]=chosen
    bundle["decision"]["reported_weight_hash"]=bundle["portfolios"][chosen].get("weight_hash")
    write_json(run/"index.json",index);write_json(run/"submission.json",bundle)
    # A directly comparable rebalancing chart/table, clearly retrospective.
    if bundle["portfolios"][chosen].get("weights"):
        w=bundle["portfolios"][chosen]["weights"]
        x=returns.loc[cfg["evaluation_start"]:]
        pd.DataFrame({"quarterly_or_drift_after_costs":replay(x,w,cfg["cost"],cfg["drift"]).wealth,
                      "buy_and_hold":replay(x,w,buy_hold=True).wealth}).to_csv(run/"rebalancing_comparison.csv")
        # An adjusted recommendation gets its own uncertainty and robustness, never W_rec's.
        chosen_folder=run/chosen
        if not (chosen_folder/"uncertainty.csv").exists():
            print(f"Uncertainty for reported portfolio {chosen}",flush=True)
            from .risk.uncertainty import bootstrap_intervals
            bootstrap_intervals(np.log1p(returns),w,methods=["historical","normal","evt"],
                    reps=cfg["bootstrap_reps"],block=cfg["bootstrap_block"],seed=cfg["seed"]).to_csv(chosen_folder/"uncertainty.csv",index=False)
        if not (chosen_folder/"robustness/mc_convergence.csv").exists():
            from .robustness import additional_evidence
            additional_evidence(returns,macro,w,cfg,chosen_folder/"robustness")
        from .stress import survival,reverse_stress
        monthly=(1+returns).resample("ME").prod()-1
        cpi=macro.CPIAUCSL.resample("ME").last().pct_change()
        result=bundle["portfolios"][chosen]
        result["real_capital_survival"]=survival(monthly,cpi,w,result["policy"])
        result["reverse_stress"]=reverse_stress(returns.loc[:cfg["training_end"]],w)
        write_json(chosen_folder/"summary.json",result);write_json(run/"submission.json",bundle)
    return bundle


def seal(run):
    from .pipeline import write_json
    run=Path(run);bundle=json.loads((run/"submission.json").read_text(encoding="utf-8"));meta=bundle["metadata"].copy()
    meta["files"]={p.relative_to(run).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob("*") if p.is_file() and p.name!="manifest.json"}
    write_json(run/"manifest.json",meta)


if __name__=="__main__":
    import sys
    p=Path(sys.argv[1]);complete(p)
    from .reporting import generate
    generate(p);seal(p)
