"""Investment committee interface. Start: python -m streamlit run app.py."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from quanedge.config import ROOT,TICKERS
from quanedge.portfolio import canonical_weights,weight_hash,replay,kpis,hurdle,nominal_target
from quanedge.results import artifact_key,result_state,digest
from quanedge.backtest import assess
from quanedge.risk import fit_models,risk_table,load_forecasts
from quanedge.stress import stress_tests,hypothetical,attribution

st.set_page_config(page_title="Ghosted | Endowment committee",layout="wide")
st.title("Serendib University Endowment")
st.caption("USD 10 million endowment · Ghosted solo entry · Owner review pending")


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
v2="real_return_target" in cfg
if v2:
    st.caption(f"Mandate {cfg['mandate']}: "+(f"universe {', '.join(cfg['universe'])} only · " if "universe" in cfg else "")+f"no ETF percentage limits · zero trading cost · 1 January cash reserve USD {cfg['reserve_initial']:,.0f} "
               f"growing {cfg['reserve_growth']:.2%} a year · target 1-3% real after {cfg['inflation']:.2%} inflation")
rec=portfolios["selected"]
with st.expander("Frozen recommendation",expanded=True):
    st.write(f"Run {run} · weights {rec.get('weight_hash','unavailable')[:8]}")
    st.write(f"Verdict: {bundle['decision']['outcome']} — {bundle['decision']['action']}")
    if rec.get("weights"):
        st.write(" · ".join(f"{t} {v:.2%}" for t,v in rec["weights"].items() if v))
        primary=next((r for r in rec.get("validation",[]) if r["method"]==rec.get("model_used") and r["alpha"]==.99),{})
        st.write(f"Frozen traffic light: {primary.get('zone','unavailable')}")
    st.caption("The algorithm's proposal requires the owner's independent investment review.")
    if bundle["decision"].get("alternative"):
        adjusted=bundle["decision"]["alternative"]
        st.write(f"Proposed adjustment: {adjusted}")
        st.write(" · ".join(f"{t} {v:.2%}" for t,v in portfolios[adjusted]["weights"].items() if v))
choices=[name for name,p in portfolios.items() if p.get("weights")]
if not choices:st.error("No feasible allocation available.");st.stop()
default=bundle["decision"].get("alternative","selected")
name=st.sidebar.selectbox("Portfolio",choices,index=choices.index(default) if default in choices else 0)
mode=st.sidebar.radio("Mode",["Precomputed","Explore"])
alpha=st.sidebar.selectbox("Confidence",[.90,.95,.99],index=2,format_func=lambda a:f"{a:.0%}")
method=st.sidebar.selectbox("VaR methodology",["historical","normal","student_t","mc_normal","mc_t","evt","fhs","garch_evt"],index=6)
dates=st.sidebar.date_input("Backtest dates",value=(pd.Timestamp(cfg["evaluation_start"]).date(),pd.Timestamp(cfg["snapshot_end"]).date()))
page=st.sidebar.radio("Page",["Recommendation","Portfolio","ETF charts","Risk","Backtesting","Stress & contributions","Assumptions & Limitations","Provenance"])
original=portfolios[name];weights=original["weights"].copy();valid=True
if mode=="Explore":
    weights={t:st.sidebar.number_input(t,min_value=0.,max_value=100.,value=100*weights[t],step=.1)/100 for t in TICKERS}
    if abs(sum(weights.values())-1)>.0001:
        st.error("Weights must sum to 100% within 0.01 percentage point.");valid=False
    elif sum(weights.values())!=1:
        weights={t:v/sum(weights.values()) for t,v in weights.items()}
if not valid:st.stop()
wh=weight_hash(weights)
active_config_hash=digest(original["policy"]) if "policy" in original else meta["config_hash"]
key=artifact_key(wh,method,meta["data_hash"],active_config_hash,meta["code_rev"])
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
    if hashlib.sha256((ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()!=meta.get("price_hash",data_hash):
        raise ValueError("Current data differs from loaded run; restore the run's snapshot")
    return prices,prices.pct_change().dropna()


import hashlib
ui_changed=False
for source,expected in {**meta.get("input_hashes",{}),**meta.get("source_file_hashes",{})}.items():
    path=ROOT/source
    content=path.read_bytes() if path.exists() else b""
    if source in meta.get("source_file_hashes",{}):content=content.replace(b"\r\n",b"\n")
    if not path.exists() or hashlib.sha256(content).hexdigest()!=expected:
        # The viewer can evolve independently of the frozen numerical run.
        # Retain the original manifest and enforce every analytical input/code hash.
        if source=="app.py" and source not in meta.get("input_hashes",{}) and path.exists():
            ui_changed=True
            continue
        st.error(f"Run input changed: {source}. Restore frozen inputs or produce a new run.");st.stop()
if ui_changed:
    st.caption("Updated application interface displaying frozen results from the recorded analysis revision.")
prices,returns=inputs(meta["data_hash"])
if page=="Recommendation":
    if matched:st.write(bundle["decision"] if matched_name=="selected" else {"checks":result["checks"],"note":"Candidate checks; frozen decision concerns W_rec."})
    st.write("What can go wrong: equity crashes, joint stock/bond losses, unstable correlations and spending exceeding sustainable real returns.")
    if matched:
        worst=max((x.get("loss_usd",0) for x in result["stress"]),default=0)
        st.write(f"How bad: largest specified scenario loss ${worst:,.0f}; losses outside these scenarios can be worse.")
    st.write("How confident: inspect forecast coverage, exception tests, model failures and uncertainty. Passing tests does not guarantee protection.")
    if matched and result.get("real_capital_survival"):
        st.write("Illustrative spending sustainability")
        st.dataframe(pd.DataFrame(result["real_capital_survival"]["results"]),hide_index=True)
        st.warning("These resampled-history shortfall probabilities do not gate the frozen verdict. They are a material spending-sustainability concern for owner review, rather than calibrated forecasts.")
    st.subheader("Return objective (C3) depends on the return estimator")
    sensitivity=pd.read_csv(folder/"estimator_sensitivity.csv") if (folder/"estimator_sensitivity.csv").exists() else pd.DataFrame()
    reported=bundle["decision"].get("reported_portfolio",default)
    reported_hash=portfolios[reported]["weight_hash"]
    if sensitivity.empty or set(sensitivity.weight_hash)!={reported_hash} or weight_hash(portfolios[reported]["weights"])!=reported_hash:
        st.info("Estimator sensitivity is unavailable or does not match the reported allocation's weight hash.")
    else:
        h=nominal_target(cfg["inflation"],cfg["real_return_floor"]) if v2 else hurdle(cfg["inflation"],cfg["spending"])
        shown=sensitivity.loc[sensitivity.mean_shrinkage.isin([0.,cfg["mean_shrinkage"]])].copy()
        shown["estimate"]=shown.mean_shrinkage.map({0.:"Raw historical means",cfg["mean_shrinkage"]:f"Frozen {cfg['mean_shrinkage']:.0%} shrinkage"})
        shown["window"]=shown.lookback_years.map(lambda y:"Full sample" if y=="all" else f"{y} years")
        pivot=shown.pivot(index="window",columns="estimate",values="expected_geometric").loc[["5 years","10 years","Full sample"]]
        st.write(f"{reported} ({' · '.join(f'{t} {v:.0%}' for t,v in portfolios[reported]['weights'].items() if v)}), weights {reported_hash[:8]}. "+
                 (f"Expected nominal geometric annual return against the {h:.2%} floor (1% real) and the "
                  f"{nominal_target(cfg['inflation'],cfg['real_return_target']):.2%} target (3% real)." if v2 else
                  f"Expected geometric annual return after the {cfg['cost']*cfg['expected_annual_turnover']:.2%} cost reserve, against the {h:.2%} hurdle."))
        fig=go.Figure([go.Bar(name=c,x=pivot.index,y=100*pivot[c]) for c in pivot.columns])
        fig.add_hline(y=100*h,line_dash="dash",annotation_text=f"{'Floor, 1% real' if v2 else 'Hurdle'} {h:.2%}")
        if v2:
            goal=nominal_target(cfg["inflation"],cfg["real_return_target"])
            fig.add_hline(y=100*goal,line_dash="dot",annotation_text=f"Target, 3% real {goal:.2%}")
        fig.update_layout(barmode="group",height=360,yaxis_title="Expected geometric return (%)",margin=dict(l=15,r=20,t=25,b=15))
        st.plotly_chart(fig,use_container_width=True,config={"displaylogo":False})
        st.dataframe((100*pivot).round(2).rename(columns=lambda c:c+" (%)"))
        raw_fails=bool((pivot["Raw historical means"]<h).all())
        st.warning(("C3 passes under the frozen estimator, but on raw historical means this allocation's expected return is below the "+("1% real floor" if v2 else "hurdle")+" in every displayed window. " if raw_fails else
                    "Expected return varies materially with the estimation assumption. ")+
                   f"The frozen estimator moves each ETF's annual mean {cfg['mean_shrinkage']:.0%} of the way toward the seven-ETF average. That average is pulled up by equities, so AGG's estimate rises; "
                   f"with {portfolios[reported]['weights']['AGG']:.0%} in AGG, the portfolio's estimated return rises with it. Raw means are an alternative estimate, not the truth. The recorded C3 result and verdict are unchanged.")
        st.caption(f"Source: {run}/estimator_sensitivity.csv (fixed reported allocation; descriptive, not re-selection). Shrinkage 0.25, 0.75 and 1.0 are in the file.")
    survival_rows=portfolios[reported].get("real_capital_survival",{}).get("results",[])
    if survival_rows:
        if matched_name!=reported:                 # otherwise the table is already shown above
            st.dataframe(pd.DataFrame(survival_rows).rename(columns={"shortfall_probability":"probability below inflation-adjusted USD 10m"}),hide_index=True)
        if v2:st.caption(f"Illustrative reserve sustainability for {reported}: share of resampled-history paths that pay every inflation-linked 1 January reserve, share keeping the initial USD 10 million in real terms, and real balances. A reserve of 4% of the initial fund exceeds the 1-3% real return objective, so real capital is expected to decline.")
        else:st.caption(f"Illustrative spending sustainability for {reported}. Real-capital shortfall means the fund ends below USD 10 million grown with CPI after spending, under the documented resampled-history simulation. It does not mean the fund is exhausted.")
elif page=="Portfolio":
    st.bar_chart(pd.Series(weights,name="Weight %")*100)
    p=replay(returns,weights,cfg["cost"],cfg["drift"])
    st.line_chart(p[["wealth"]].rename(columns={"wealth":"Wealth per initial USD, after trading costs"}))
    wealth=pd.concat([pd.Series([1.],index=[p.index[0]-pd.Timedelta(days=1)]),p.wealth])
    st.line_chart((wealth/wealth.cummax()-1).rename("Drawdown"))
    if matched:st.json(result["performance"])
    else:
        macro=pd.read_csv(ROOT/"data/clean/macro_clean.csv",index_col=0,parse_dates=True)
        benchmark=replay(returns,canonical_weights({"SPY":.4,"AGG":.6}),cfg["cost"],cfg["drift"])["return"]
        st.json(kpis(p["return"],macro.rf_daily_effective,returns.SPY,benchmark))
        st.caption("Computed in app, not part of frozen run.")
    st.caption(f"Retrospective portfolio evaluation; quarterly or 5-point drift rebalancing, {cfg['cost']*1e4:g} bp one-way costs. Chart excludes "+("cash-reserve withdrawals." if v2 else "spending."))
elif page=="ETF charts":
    st.subheader("ETF price comparison")
    from quanedge import context
    full=context.load()
    sources=["Frozen common panel (run data)"]+(["Standalone full history (context)"] if full is not None else [])
    source=st.radio("Data",sources,index=1 if full is not None else 0,horizontal=True,key="etf_chart_data_max_history")
    if full is None:
        st.info("Standalone full-history context is unavailable or failed its hash check; showing the frozen common panel. Build it with: python -m quanedge.context --download")
    if source.startswith("Standalone"):
        st.warning(context.LABEL)
        chart_source=full
    else:
        st.caption("Interactive charts use the verified adjusted-price snapshot loaded with this run. Drag to zoom, hover for values, or use the range controls below the chart.")
        chart_source=prices
    chart_tickers=st.multiselect("ETFs to display",TICKERS,default=TICKERS,key="etf_chart_tickers")
    y_titles={"Indexed comparison (start = 100)":"Indexed value (first common day = 100)",
              "Indexed from each ETF's own first date":"Indexed value (each ETF's first observed day = 100)",
              "Adjusted prices (USD)":"Adjusted price (USD)","Drawdown from running peak":"Drawdown from running peak (%)"}
    chart_type=st.radio("View",list(y_titles),index=1 if source.startswith("Standalone") else 0,
                        horizontal=True,key="etf_chart_view_max_history");y_title=y_titles[chart_type]
    if not chart_tickers:
        st.info("Select at least one ETF to draw the chart.")
    else:
        chart_prices=chart_source[chart_tickers].dropna(how="all")
        common=chart_prices.dropna().index
        if chart_type.startswith("Indexed comparison") and not len(common):
            st.info("The selected ETFs have no common date.")
        fig=go.Figure()
        for ticker in chart_tickers:
            series=chart_prices[ticker].dropna()
            if chart_type.startswith("Indexed comparison"):
                series=series.loc[common[0]:]/series.loc[common[0]]*100 if len(common) else series.iloc[:0]
            elif chart_type.startswith("Indexed from"):
                series=series/series.iloc[0]*100
            elif chart_type.startswith("Drawdown"):
                series=(series/series.cummax()-1)*100
            fig.add_trace(go.Scatter(x=series.index,y=series,name=ticker,mode="lines",connectgaps=False))
        fig.update_layout(
            height=620,margin=dict(l=15,r=20,t=25,b=15),hovermode="x unified",
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0),
            xaxis=dict(title=None,rangeslider=dict(visible=True),rangeselector=dict(
                buttons=[
                    dict(count=1,label="1Y",step="year",stepmode="backward"),
                    dict(count=5,label="5Y",step="year",stepmode="backward"),
                    dict(count=10,label="10Y",step="year",stepmode="backward"),
                    dict(step="all",label="All"),
                ]
            )),
            yaxis_title=y_title,
        )
        st.plotly_chart(fig,use_container_width=True,config={"scrollZoom":True,"displaylogo":False})
        st.caption(f"Available history: {chart_prices.index.min():%d %b %Y} to {chart_prices.index.max():%d %b %Y}. Values before an ETF's first price are not filled or estimated. Adjusted prices include dividends and splits.")
        if chart_type.startswith("Indexed from"):
            st.caption("Series start on different dates, so their end values are not a fair performance ranking. Use the common-period view to compare like with like.")
        if source.startswith("Standalone"):
            st.caption("Maximum available history is shown for each ETF in this contextual snapshot, ending 30 Sep 2026. In the common-period view, earlier dates are intentionally excluded so all selected ETFs start together.")
    tables=context.out_dir()
    if (tables/"coverage.csv").exists():
        st.markdown("**Coverage of each ETF's own history** · "+context.LABEL)
        st.dataframe(pd.read_csv(tables/"coverage.csv"),hide_index=True)
        st.markdown("**Maximum drawdown: full history versus the frozen sample's start (2005)**")
        st.dataframe(pd.read_csv(tables/"drawdowns.csv"),hide_index=True)
        st.caption("Drawdowns use adjusted closes on each ETF's own trading days; time under water runs from the peak to recovery, or to 30 Sep 2026 if unrecovered. Crisis windows are project-chosen dates.")
elif page=="Risk":
    if matched:
        table=pd.read_csv(folder/matched_name/"risk.csv")
    else:
        table=risk_table(fit_models(np.log1p(returns),weights,methods=["historical","normal","student_t","mc_normal","mc_t"],n_sim=20000,seed=cfg["seed"]),value=cfg["value"])
        st.caption("Computed in app, not part of frozen run. EVT/conditional models and uncertainty require precomputation.")
    selected=table.loc[(table.alpha==alpha)&table.method.isin([method,"evt"])]
    chosen_row=selected.loc[selected.method==method]
    evt_row=selected.loc[selected.method=="evt"]
    for column,label,frame,field in zip(st.columns(3),[f"VaR · {method}",f"ES · {method}","EVT VaR"],
                                       [chosen_row,chosen_row,evt_row],["var_usd","es_usd","var_usd"]):
        value=frame.iloc[0][field] if len(frame) else np.nan
        column.metric(label,f"${value:,.0f}" if np.isfinite(value) else "Unavailable")
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
        zone=assessment.get("zone","unavailable")
        {"green":st.success,"yellow":st.warning,"red":st.error}.get(zone,st.info)("Traffic light: "+zone)
        st.json(assessment)
        col=f"var_{method}_{alpha*100:g}"
        if col in fc:
            show=fc.loc[start:end];st.line_chart(pd.DataFrame({"Realised log loss":-show["return"],"VaR log loss":show[col]}))
        st.caption("Sequential risk-forecast evaluation. Allocation selected using its stated estimation cutoff. Strict breach: loss > VaR. Basel colours apply only to 250 observations at 99%.")
elif page=="Stress & contributions":
    stresses=result["stress"] if matched else stress_tests(prices,weights,cfg["value"])+[hypothetical(returns.loc[:cfg["training_end"]],weights,cfg["value"])]
    st.dataframe(pd.DataFrame([{k:v for k,v in s.items() if not isinstance(v,dict)} for s in stresses]),hide_index=True)
    for scenario in stresses:
        if scenario.get("contributions_usd"):
            with st.expander(scenario["scenario"]+" asset impacts"):
                impacts=scenario["contributions_usd"]
                st.dataframe(pd.Series(impacts,name="USD loss contribution"))
                st.write("Largest weighted damage contributor: "+max(impacts,key=impacts.get))
                if scenario.get("shocks"):st.json(scenario["shocks"])
    att=attribution(returns,weights,alpha,cfg["value"])
    st.bar_chart(pd.Series(att["components"],name="Component ES USD"));st.json(att)
    st.caption("Historical attribution using shared portfolio tail weights. Negative contributions are retained. Attribution unavailable for portfolio-only FHS.")
elif page=="Assumptions & Limitations":
    st.write("The endowment is perpetual; strategic review is every five years. Policy limits and inflation/spending assumptions are chosen policy, not organiser rules.")
    if v2:
        if "universe" in cfg:
            st.write(f"Only {', '.join(cfg['universe'])} may be held. EFA, EEM and XLK are left out because they move almost in step with SPY (daily correlation 0.82-0.91). "
                     "XLE is the least SPY-correlated equity ETF but still moves with it (0.70 daily, 0.76 on SPY's worst days); AGG and GLD are the diversifiers.")
        st.write(f"Mandate {cfg['mandate']} (owner change): no ETF percentage limits; trading cost assumed zero, so spreads and market impact are ignored; "
                 f"each 1 January USD {cfg['reserve_initial']:,.0f} growing {cfg['reserve_growth']:.2%} a year is withdrawn as cash for the university and earns nothing. "
                 f"The {cfg['inflation']:.2%} inflation figure is an owner assumption whose source has not been verified.")
        st.write("The reserve (4% of the initial fund in real terms) exceeds the 1-3% real return objective, so the fund is expected to shrink in real terms. "
                 "The selected allocation is mostly AGG because 50% mean shrinkage lifts AGG's expected return; on raw historical means it falls short of the 1% real floor.")
    st.write("All historical portfolio evaluations are retrospective. Forecasts use only earlier daily returns, but allocation and model choices have seen historical crises. No historical period is untouched.")
    st.write("Adjusted prices include distributions and expense ratios. No expense ratio is deducted again. Revised FRED data and approximate publication lags are not historical data vintages.")
    st.write("VaR is not maximum loss. ES is not a loss cap. Sparse extremes, model specification, liquidity, tax, execution impact and changing regimes remain risks.")
    st.write("Risk forecasts use daily constant weights without costs; implementation uses quarterly/drift rebalancing and trading costs. USD and US CPI omit Sri Lankan currency and spending risks.")
    st.write("AI assisted implementation and documents. Independent owner validation, organiser solo eligibility and deadline confirmation remain pending.")
else:
    st.json(meta)
    st.download_button("Download run manifest",(folder/"manifest.json").read_bytes(),file_name="manifest.json")
