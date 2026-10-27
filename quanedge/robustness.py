"""Independent risk evidence and sensitivity; no allocation tuning."""
import numpy as np
import pandas as pd
from scipy.stats import binomtest,norm
from .portfolio import tail_weights
from .risk import fit_models,risk_table,portfolio_log_returns
from .risk.var_es import monte_carlo,Normal,batch_se
from .risk.uncertainty import bootstrap_intervals
from .data.stationarity import test_portfolio_return_series
from .stress import attribution


def additional_evidence(returns,macro,w,cfg,folder):
    folder.mkdir(exist_ok=True,parents=True);logs=np.log1p(returns);r=portfolio_log_returns(logs,w)
    test_portfolio_return_series(r,name="W_rec").to_csv(folder/"stationarity.csv",index=False)
    loss=-returns.SPY;tail=loss>=loss.quantile(.99);co=[]
    for ticker in ["AGG","GLD"]:
        k=int((returns.loc[tail,ticker]<0).sum());n=int(tail.sum())
        ci=binomtest(k,n).proportion_ci()
        co.append({"ticker":ticker,"tail_days":n,"joint_loss_days":k,"co_loss_rate":k/n,
                   "base_loss_rate":float((returns[ticker]<0).mean()),"ci_low":ci.low,"ci_high":ci.high})
    pd.DataFrame(co).to_csv(folder/"co_exceedance.csv",index=False)
    rates=macro.DGS10.diff().reindex(r.index)
    data=pd.concat([pd.Series(np.expm1(r),index=r.index,name="portfolio"),rates.rename("rate")],axis=1).dropna()
    coef=np.polyfit(data.rate,data.portfolio,1)
    pd.DataFrame([{"slope_per_percentage_point_yield_change":coef[0],"intercept":coef[1],
                   "note":"descriptive contemporaneous association, not causal rate duration"}]).to_csv(folder/"rate_sensitivity.csv",index=False)
    x=returns.to_numpy();weights=np.array([w[t] for t in returns.columns]);losses=-x@weights;derivatives=[]
    for step in [1e-3,1e-4,1e-5]:
        marginal=[]
        for j,t in enumerate(returns.columns):
            direction=np.eye(len(weights))[j]*step
            deriv=(np.quantile(-x@(weights+direction),.99)-np.quantile(-x@(weights-direction),.99))/(2*step)
            marginal.append(deriv)
            derivatives.append({"asset":t,"step":step,"marginal_var_fraction":deriv,
                                "component_var_usd":cfg["value"]*weights[j]*deriv,
                                "derivative":"independent dollar exposure; no renormalisation"})
        derivatives.append({"asset":"Euler residual","step":step,"component_var_usd":cfg["value"]*(weights@np.array(marginal)-np.quantile(losses,.99))})
    pd.DataFrame(derivatives).to_csv(folder/"marginal_var.csv",index=False)
    joint=fit_models(logs,w,methods=["mc_t"],n_sim=cfg["n_sim"],seed=cfg["seed"])["mc_t"]
    if hasattr(joint,"scenarios"):
        scenarios=pd.DataFrame(np.expm1(joint.scenarios),columns=joint.assets)
        from .pipeline import write_json
        out=attribution(scenarios,w,value=cfg["value"]);out["source"]="joint multivariate-t Monte Carlo attribution check"
        write_json(folder/"mc_attribution.json",out)
    thresholds=[]
    for cutoff in [.90,.95]:
        models=fit_models(logs,w,methods=["evt"],evt_threshold_q=cutoff)
        t=risk_table(models,value=cfg["value"]);t["threshold_percentile"]=cutoff;thresholds.append(t)
    pd.concat(thresholds).to_csv(folder/"threshold_sensitivity.csv",index=False)
    from .risk import conditional
    from .risk.validation import ModelFitError
    try:
        filt=conditional.fit_filter(r)
        residual=[]
        for cutoff in [.85,.90,.95]:
            try:
                model=conditional.garch_evt(filt,cutoff)
                table=risk_table({"garch_evt":model},value=cfg["value"])
                table["residual_threshold_percentile"]=cutoff;residual.append(table)
            except ModelFitError as err:
                residual.append(pd.DataFrame([{"residual_threshold_percentile":cutoff,"status":str(err)}]))
        pd.concat(residual).to_csv(folder/"residual_threshold_sensitivity.csv",index=False)
        from statsmodels.stats.diagnostic import acorr_ljungbox,het_arch
        tests=acorr_ljungbox(filt.z,lags=[10,20],return_df=True)
        tests["squared_residual_p"]=acorr_ljungbox(filt.z**2,lags=[10,20],return_df=True).lb_pvalue
        tests["arch_lm_p"]=het_arch(filt.z,nlags=10)[1]
        tests.to_csv(folder/"conditional_residual_checks.csv")
    except ModelFitError as err:
        (folder/"conditional_residual_checks.txt").write_text("unavailable: "+str(err),encoding="utf-8")
    intervals=[]
    for block in [10,40]:
        ci=bootstrap_intervals(logs,w,methods=["historical","normal","evt"],reps=100,block=block,seed=cfg["seed"])
        ci["block_length"]=block;intervals.append(ci)
    pd.concat(intervals).to_csv(folder/"block_sensitivity.csv",index=False)
    eve=[]
    for date in ["2008-09-01","2020-02-19"]:
        hist=logs.loc[:date];models=fit_models(hist,w,n_sim=cfg["n_sim"],seed=cfg["seed"])
        t=risk_table(models,value=cfg["value"]);t["fit_through"]=date;eve.append(t)
    pd.concat(eve).to_csv(folder/"stress_eve.csv",index=False)
    # Matching distribution independent normal formula versus empirical simulation.
    sample=logs[["SPY"]];analytical=Normal(sample.SPY);rows=[]
    for n in [10000,100000,1000000]:
        for seed in [cfg["seed"],cfg["seed"]+1,cfg["seed"]+2]:
            m=monte_carlo(sample,{"SPY":1},n_sim=n,seed=seed)
            for a in [.95,.99]:
                se_v,se_e=batch_se(m,a,n_batches=10)
                rows.append({"n_sim":n,"seed":seed,"alpha":a,"var_error":m.var(a)-analytical.var(a),
                             "es_error":m.es(a)-analytical.es(a),"var_mc_se":se_v,"es_mc_se":se_e,
                             "var_within_4se":abs(m.var(a)-analytical.var(a))<=4*se_v,
                             "es_within_4se":abs(m.es(a)-analytical.es(a))<=4*se_e})
    pd.DataFrame(rows).to_csv(folder/"mc_convergence.csv",index=False)
