"""Investment committee interface. Start: python -m streamlit run app.py."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from quanedge.config import ROOT,TICKERS
from quanedge.portfolio import canonical_weights,weight_hash,replay,kpis
from quanedge.results import artifact_key,result_state
from quanedge.backtest import assess
from quanedge.risk import fit_models,risk_table,load_forecasts
from quanedge.stress import stress_tests,hypothetical,attribution

st.set_page_config(page_title="Ghosted | Endowment committee",layout="wide")
st.title("Serendib University Endowment")
st.caption("USD 10 million mandate · Ghosted solo entry · Owner review pending")


@st.cache_data
def read_run(run):
    folder=ROOT/"results"/run
    return json.loads((folder/"submission.json").read_text(encoding="utf-8")),json.loads((folder/"index.json").read_text(encoding="utf-8"))


latest=ROOT/"results/latest.txt"
if not latest.exists():
    st.info("No completed analytical run is available. Run the documented data, training and final pipeline commands first.")
    st.code("python -m quanedge.pipeline --config config/final.yaml")
    st.subheader("Assumptions & Limitations")
    st.write("No allocation has a validated recommendation yet. Solo eligibility, deadline and independent human review remain pending.")
    st.stop()
run=latest.read_text(encoding="utf-8").strip();folder=ROOT/"results"/run
bundle,index=read_run(run);meta=bundle["metadata"];cfg=bundle["policy"];portfolios=bundle["portfolios"]
rec=portfolios["selected"]
with st.expander("Frozen recommendation",expanded=True):
    st.write(f"Run {run} · weights {rec.get('weight_hash','unavailable')[:8]}")
    st.write(f"Verdict: {bundle['decision']['outcome']} — {bundle['decision']['action']}")
    if rec.get("weights"):
        st.dataframe(pd.Series(rec["weights"],name="Allocation").mul(100).rename("Allocation %"))
        primary=next((r for r in rec.get("validation",[]) if r["method"]==rec.get("model_used") and r["alpha"]==.99),{})
        st.write(f"Frozen traffic light: {primary.get('zone','unavailable')}")
    st.caption("The algorithm's proposal requires the owner's independent investment review.")
choices=[name for name,p in portfolios.items() if p.get("weights")]
if not choices:st.error("No feasible allocation available.");st.stop()
name=st.sidebar.selectbox("Portfolio",choices)
mode=st.sidebar.radio("Mode",["Precomputed","Explore"])
alpha=st.sidebar.selectbox("Confidence",[.90,.95,.99],index=2,format_func=lambda a:f"{a:.0%}")
method=st.sidebar.selectbox("VaR methodology",["historical","normal","student_t","mc_normal","mc_t","evt","fhs","garch_evt"],index=6)
dates=st.sidebar.date_input("Backtest dates",value=(pd.Timestamp(cfg["evaluation_start"]).date(),pd.Timestamp(cfg["snapshot_end"]).date()))
page=st.sidebar.radio("Page",["Recommendation","Portfolio","Risk","Backtesting","Stress & contributions","Assumptions & Limitations","Provenance"])
original=portfolios[name];weights=original["weights"].copy();valid=True
if mode=="Explore":
    weights={t:st.sidebar.number_input(t,min_value=0.,max_value=100.,value=100*weights[t],step=.1)/100 for t in TICKERS}
    if abs(sum(weights.values())-1)>.0001:
        st.error("Weights must sum to 100% within 0.01 percentage point.");valid=False
    elif sum(weights.values())!=1:
        weights={t:v/sum(weights.values()) for t,v in weights.items()}
if not valid:st.stop()
wh=weight_hash(weights)
key=artifact_key(wh,method,meta["data_hash"],meta["config_hash"],meta["code_rev"])
state=result_state({"artifact_key":key},index)
matched=state=="MATCHED"
matched_name=index[key]["portfolio"] if matched else None
result=portfolios[matched_name] if matched else None
st.caption(f"run {run}, weights {wh[:8]} · {state} · data through {cfg['snapshot_end']}")
from quanedge.portfolio import feasible
if not feasible(weights,cfg):st.warning("This allocation is outside the original investment policy.")
if not matched:
    st.info("Grey traffic light · unavailable for these weights — rerun required. No verdict is available.")
    st.code("python -m quanedge.pipeline --config config/final.yaml")


@st.cache_data
def inputs(data_hash):
    prices=pd.read_csv(ROOT/"data/clean/prices_clean.csv",index_col=0,parse_dates=True)
    import hashlib
    if hashlib.sha256((ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()!=data_hash:
        raise ValueError("Current data differs from loaded run; restore the run's snapshot")
    return prices,prices.pct_change().dropna()


prices,returns=inputs(meta["data_hash"])
if page=="Recommendation":
    if matched:st.write(bundle["decision"] if matched_name=="selected" else {"checks":result["checks"],"note":"Candidate checks; frozen decision concerns W_rec."})
    st.write("What can go wrong: equity crashes, joint stock/bond losses, unstable correlations and spending exceeding sustainable real returns.")
    if matched:
        worst=max((x.get("loss_usd",0) for x in result["stress"]),default=0)
        st.write(f"How bad: largest specified scenario loss ${worst:,.0f}; losses outside these scenarios can be worse.")
    st.write("How confident: inspect forecast coverage, exception tests, model failures and uncertainty. Passing tests does not guarantee protection.")
elif page=="Portfolio":
    st.bar_chart(pd.Series(weights,name="Weight %")*100)
    p=replay(returns,weights,cfg["cost"],cfg["drift"])
    st.line_chart(p[["wealth"]].rename(columns={"wealth":"Wealth per initial USD, after trading costs"}))
    wealth=pd.concat([pd.Series([1.],index=[p.index[0]-pd.Timedelta(days=1)]),p.wealth])
    st.line_chart((wealth/wealth.cummax()-1).rename("Drawdown"))
    if matched:st.json(result["performance"])
    st.caption("Retrospective portfolio evaluation; quarterly or 5-point drift rebalancing, 5 bp one-way costs. Chart excludes spending.")
elif page=="Risk":
    if matched:
        table=pd.read_csv(folder/matched_name/"risk.csv")
    else:
        table=risk_table(fit_models(np.log1p(returns),weights,methods=["historical","normal","student_t","mc_normal","mc_t"],n_sim=20000,seed=cfg["seed"]),value=cfg["value"])
        st.caption("Computed in app, not part of frozen run. EVT/conditional models and uncertainty require precomputation.")
    selected=table.loc[(table.alpha==alpha)&table.method.isin([method,"evt"])]
    st.dataframe(selected[["method","alpha","var_pct","es_pct","var_usd","es_usd","basis","status"]],hide_index=True)
    st.caption("One trading day. Percent columns are percentage points; dollar ES averages dollar tail losses.")
    uncertainty=folder/(matched_name or "")/"uncertainty.csv"
    if matched and uncertainty.exists():st.dataframe(pd.read_csv(uncertainty),hide_index=True)
    else:st.info("Bootstrap intervals unavailable for this portfolio — rerun required.")
elif page=="Backtesting":
    if matched:
        fc=load_forecasts(folder/matched_name/"forecasts.csv")
        start,end=dates if len(dates)==2 else (None,None)
        assessment=assess(fc,wh,method,alpha,start,end)
        st.write("Traffic light: "+assessment.get("zone","unavailable"));st.json(assessment)
        col=f"var_{method}_{alpha*100:g}"
        if col in fc:
            show=fc.loc[start:end];st.line_chart(pd.DataFrame({"Realised log loss":-show["return"],"VaR log loss":show[col]}))
        st.caption("Sequential risk-forecast evaluation. Allocation selected using its stated estimation cutoff. Strict breach: loss > VaR. Basel colours apply only to 250 observations at 99%.")
elif page=="Stress & contributions":
    stresses=result["stress"] if matched else stress_tests(prices,weights,cfg["value"])+[hypothetical(returns.loc[:cfg["training_end"]],weights,cfg["value"])]
    st.dataframe(pd.DataFrame([{k:v for k,v in s.items() if not isinstance(v,dict)} for s in stresses]),hide_index=True)
    att=attribution(returns,weights,alpha,cfg["value"])
    st.bar_chart(pd.Series(att["components"],name="Component ES USD"));st.json(att)
    st.caption("Historical attribution using shared portfolio tail weights. Negative contributions are retained. Attribution unavailable for portfolio-only FHS.")
elif page=="Assumptions & Limitations":
    st.write("The endowment is perpetual; strategic review is every five years. Policy limits and inflation/spending assumptions are chosen policy, not organiser rules.")
    st.write("All historical portfolio evaluations are retrospective. Forecasts use only earlier daily returns, but allocation and model choices have seen historical crises. No historical period is untouched.")
    st.write("Adjusted prices include distributions and expense ratios. No expense ratio is deducted again. Revised FRED data and approximate publication lags are not historical data vintages.")
    st.write("VaR is not maximum loss. ES is not a loss cap. Sparse extremes, model specification, liquidity, tax, execution impact and changing regimes remain risks.")
    st.write("Risk forecasts use daily constant weights without costs; implementation uses quarterly/drift rebalancing and trading costs. USD and US CPI omit Sri Lankan currency and spending risks.")
    st.write("AI assisted implementation and documents. Independent owner validation, organiser solo eligibility and deadline confirmation remain pending.")
else:
    st.json(meta)
    st.download_button("Download run manifest",(folder/"manifest.json").read_bytes(),file_name="manifest.json")
