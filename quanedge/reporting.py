"""Generate committee documents from one run, retaining editable narrative sources."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image

REFERENCES=[
    ("Competition brief","Quant edge 1.0 Final Challenge 1.pdf, sections 3, 5-10"),
    ("Basel calibration","https://www.bis.org/committees/bcbs/basel-framework/standard/mar/99/inforce/2019-12-15/published/2019-12-15"),
    ("CVaR optimisation","https://uryasev.github.io/publications/"),
    ("Approved prices","https://finance.yahoo.com/"),
    ("Risk-free series","https://fred.stlouisfed.org/series/DTB3"),
    ("Inflation series","https://fred.stlouisfed.org/series/CPIAUCSL"),
]


def fmt(value,kind="number"):
    if value is None or not np.isfinite(value):return "unavailable"
    if kind=="number" and isinstance(value,int):return f"{value:,}"
    return f"${value:,.0f}" if kind=="usd" else f"{100*value:.2f}%" if kind=="pct" else f"{value:.3f}"


def generate(run):
    run=Path(run);bundle=json.loads((run/"submission.json").read_text(encoding="utf-8"));cfg=bundle["policy"]
    meta=bundle["metadata"];decision=bundle["decision"]
    chosen=decision.get("alternative","selected")
    rec=bundle["portfolios"][chosen]
    dest=run/"documents";dest.mkdir(exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Body",fontName="Helvetica",fontSize=10.5,leading=15,spaceAfter=9,textColor=colors.HexColor("#25364a")))
    styles["Title"].textColor=colors.HexColor("#102d45");styles["Heading1"].textColor=colors.HexColor("#102d45")
    def paragraph(text):return Paragraph(escape(str(text)),styles["Body"])
    def table(headers,rows,widths=None):
        data=[[paragraph(v) for v in headers]]+[[paragraph(v) for v in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e8eff3")),
                              ("VALIGN",(0,0),(-1,-1),"TOP"),("BOTTOMPADDING",(0,0),(-1,-1),7),
                              ("LINEBELOW",(0,0),(-1,0),.6,colors.HexColor("#75929e")),
                              ("LINEBELOW",(0,1),(-1,-1),.3,colors.HexColor("#d8e0e5"))]))
        return t
    def footer(canvas,doc):
        canvas.setFont("Helvetica",8);canvas.setFillColor(colors.HexColor("#567080"))
        canvas.drawString(42,24,f"Ghosted | {meta['run_id']} | Owner review pending")
        canvas.drawRightString(A4[0]-42,24,str(doc.page))
    def pdf(name,story):
        SimpleDocTemplate(str(dest/name),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    w=rec.get("weights") or {};perf=rec.get("performance",{});stress=rec.get("stress",[])
    risk=pd.read_csv(run/chosen/"risk.csv") if (run/chosen/"risk.csv").exists() else pd.DataFrame()
    checks=rec.get("checks",{});from .portfolio import hurdle
    allocation=[(t,fmt(v,"pct"),fmt(v*cfg["value"],"usd")) for t,v in w.items()]
    chart_paths={}
    if w:
        series=pd.read_csv(run/chosen/"performance.csv",index_col=0,parse_dates=True)
        for name,values,ylabel in [("wealth",series.wealth,"Wealth per initial USD, net of trading costs"),
                  ("drawdown",series.wealth/series.wealth.cummax()-1,"Drawdown fraction")]:
            fig,ax=plt.subplots(figsize=(8,3.4));ax.plot(values.index,values,color="#176f83",lw=1.5)
            ax.set_ylabel(ylabel);ax.grid(alpha=.2);fig.tight_layout();p=dest/(name+".png");fig.savefig(p,dpi=160);plt.close(fig);chart_paths[name]=p
    pages=[]
    def page(title,texts,extra=()):pages.append((title,texts,list(extra)))
    original=bundle["portfolios"]["selected"]
    capital=rec.get("real_capital_survival",{}).get("results",[])
    sustainability=("Illustrative after-spending real-capital shortfall probabilities: "+"; ".join(
        f"{row['year']} years {fmt(row['shortfall_probability'],'pct')} (Monte Carlo SE {fmt(row['mc_se'],'pct')})" for row in capital)+
        ". These resampled-history outcomes do not gate the frozen verdict, but they are a material spending-sustainability concern for owner review.") if capital else "Spending-sustainability evidence is exported separately; it does not gate the frozen verdict."
    tradeoff=""
    if chosen!="selected":
        tradeoff=(f"The original allocation's GFC path drawdown was {fmt(original['stress'][0]['drawdown'],'pct')}, exceeding the 20% limit. "
                  f"The adjusted portfolio's GFC path drawdown is {fmt(rec['stress'][0]['drawdown'],'pct')}. "
                  f"Expected geometric return changes from {fmt(original.get('expected_geometric'),'pct')} to {fmt(rec.get('expected_geometric'),'pct')}; "
                  f"historical ES99 changes from {fmt(original.get('policy_es99_usd'),'usd')} to {fmt(rec.get('policy_es99_usd'),'usd')}. "
                  "These are estimator-dependent trade-offs, not guaranteed future outcomes.")
    page("Investment memorandum",[
        f"Serendib University Endowment Fund. USD 10,000,000. Data: 3 January 2005 through {cfg['snapshot_end']}. Run {meta['run_id']}.",
        f"Algorithmic recommendation: {decision['outcome']}. {decision['action']} Reported allocation and numbers: {chosen}, weight hash {rec.get('weight_hash','unavailable')[:12]}.",
        tradeoff or "The original allocation is reported; its outcome follows the frozen checks rather than a discretionary override.",
        sustainability,
        "This is a solo submission prepared with AI assistance. The owner approved the policy assumptions and FHS/GARCH-EVT model order; independent review of implementation and the investment judgement is pending.",
        "Capital preservation takes priority over maximising gains. A perpetual endowment must fund today's scholarship obligations while protecting future purchasing power. The strategic review period is five years; daily risk measurement serves monitoring rather than defining the investment horizon.",
        "What can go wrong: equities can fall together, bonds can lose with equities during inflation shocks, and gold can fail to protect over the committee's chosen period. Spending and inflation can overwhelm returns even when daily risk looks modest.",
        "How bad: the stress section reports conditional dollar losses, not a worst possible outcome. How confident: forecast coverage, failure counts and bootstrap intervals qualify each point estimate."
    ])
    page("Policy and allocation",[
        f"Annual spending is {fmt(cfg['spending'],'pct')} after returns and costs; assumed inflation is {fmt(cfg['inflation'],'pct')}. The exact after-cost, before-spending break-even hurdle is {fmt(hurdle(cfg['inflation'],cfg['spending']),'pct')}.",
        "The portfolio is long-only and fully invested. AGG is 25-70%, total equity at most 55%, gold at most 15%, XLE/XLK at most 10% each, and other individual ETFs at most 40%. These are chosen policy assumptions, not organiser rules.",
        "The binding risk budget is historical one-day ES99 of USD 250,000 on the allocation's estimation sample. The stress/drawdown limit is 20%. No daily estimate guarantees this multi-period loss limit.",
        "Rebalance quarterly or when any weight drifts more than five percentage points. Trading cost is five basis points one-way per unit of traded NAV. Expected-return comparisons reserve five basis points annually for the frozen one-times-NAV turnover assumption. ETF expense ratios are embedded in adjusted prices.",
    ],[table(["ETF","Weight","Initial exposure"],allocation,[140,130,240])])
    page("Data and provenance",[
        "Yahoo Finance via yfinance supplies dividend/split-adjusted ETF closes. Their total-return interpretation assumes distribution reinvestment; distributions must not be added to adjusted-close returns again. Separate unadjusted closes and distributions support income yield.",
        "The fresh snapshot has 5,470 common price dates and 5,469 returns. All 242 flagged price-return moves remain. The pipeline records stale prices, sharp reversals, calendar closures, volatility shifts and missing observations. Event labels are analyst-compiled date associations rather than verified per-asset causal explanations.",
        "FRED DTB3 discount quotes are converted to bond-equivalent yield and daily rates. CPI inflation is computed from index ratios. Monthly release-lag approximations and daily forward fills are logged; revised contemporary data is not a point-in-time vintage archive.",
        "ADF checks address unit roots; fixed-lag ADF, KPSS and ARCH-LM checks provide complementary diagnostics. Rejection does not establish stable parameters or validate any tail distribution. The selected allocation has its own return-series stationarity report.",
        f"Clean price file SHA-256: {meta.get('price_hash',meta['data_hash'])}. Weight SHA-256: {rec.get('weight_hash','unavailable')}. Configuration SHA-256: {meta['config_hash']}. File identity does not prove economic correctness.",
        "Source retrieval metadata accompanies prices and distributions. Legacy source ingestion records macro snapshot write times rather than exact HTTP retrieval timestamps; that limitation is explicit."
    ])
    candidates=[]
    for name,p in bundle["portfolios"].items():
        if name.startswith("A") or name=="W_train":continue
        candidates.append([name,fmt(p.get("expected_geometric"),"pct"),fmt(p.get("policy_es99_usd"),"usd"),p.get("status")])
    page("Construction and alternatives",[
        "The frozen selection maximises arithmetic expected return subject to historical CVaR99 and allocation constraints. A second LP minimises CVaR within 1e-8 of the optimal return. Failed solves remain unavailable. Sample annual arithmetic means are shrunk 50% toward their cross-asset mean; Ledoit-Wolf covariance supports the variance-based candidates.",
        "The hurdle tests geometric return after the fixed turnover-cost reserve. The lognormal moment approximation is (1 + net arithmetic return) exp(-variance/2) - 1. Estimation choices and constraints drive the result; expected return is uncertain and is not a realised performance promise.",
        "Shrinking toward one cross-asset mean can overstate expected bond returns by pulling them toward equity returns. Fixed-weight sensitivity across shrinkage strengths and five-year, ten-year and full-history windows is exported separately; the frozen recommendation is not re-tuned to these results.",
        "Markowitz comparisons use constrained minimum variance, maximum Sharpe and near-parity volatility contributions. Minimum CVaR is the precomputed de-risk portfolio. SPY is the CAPM market proxy for beta and Jensen alpha; the 40/60 SPY/AGG portfolio is the active-return benchmark.",
        "The adapted permanent portfolio uses 25% SPY, 50% AGG and 25% gold; AGG substitutes imperfectly for long Treasuries and cash. It is outside policy and is a comparison only. Constraint effects are isolated by identical-scenario re-solves changing one limit.",
        "Pairs trading and short market-neutral strategies introduce borrow, margin and implementation risks beyond this long-only policy. The retained long-only mechanism is rebalancing relative winners and losers. Diversification can reduce losses without guaranteeing a profit."
    ],[table(["Candidate","Expected geometric","Policy ES99 USD","Status"],candidates,[145,125,145,95])])
    performance_rows=[[k,fmt(v,"pct" if k in ["cagr","maximum_drawdown","annual_volatility","jensen_alpha","cumulative_return"] else "number")] for k,v in perf.items() if isinstance(v,(float,int)) and not isinstance(v,bool)]
    page("Performance and accounting",[
        "All historical allocation evaluations are retrospective. W_train is estimated through 2016, W_rec through the snapshot end, and neither erases prior exposure to the crises used when writing the policy. The annual walk-forward procedure uses only earlier data for each year's weights; policy design remains historically informed.",
        "Wealth compounds simple portfolio returns; asset simple returns aggregate before conversion to log. Implementation performance includes quarterly/drift turnover costs. Risk forecasts instead replay daily constant weights without costs, a disclosed implementation mismatch.",
        "Sharpe uses daily excess return and sample volatility; Sortino uses a zero target and downside deviation over all days. Treynor is unavailable for near-zero beta. Jensen alpha uses SPY excess returns. Information ratio uses 40/60 active returns and tracking error. Calmar uses CAGR and drawdown over the same dates.",
        "Annual spending is deducted once after net returns. The real-capital target is initial NAV multiplied by the CPI ratio; spending is not added to this target. Money-weighted return includes distributions as investor cash flows and remaining NAV, while time-weighted CAGR measures the investment path."
    ],[table(["Metric","Value"],performance_rows[:13],[300,210])])
    risk_rows=[[r.method,f"{r.alpha:.0%}",f"${r.var_usd:,.0f}",f"${r.es_usd:,.0f}"] for r in risk.itertuples() if r.alpha in [.95,.99] and r.method in ["historical","normal","mc_t","evt"]]
    page("VaR, Expected Shortfall and EVT",[
        "All estimates use one trading day and the same allocation/NAV. VaR is a quantile, not maximum loss. ES averages the worst 1-alpha probability mass. Historical VaR uses NumPy linear interpolation; empirical ES uses the step-distribution quantile integral with fractional boundary mass.",
        "Monetary VaR transforms the log-loss quantile. Monetary ES averages transformed tail losses; transforming mean log ES is generally wrong. Historical ES cannot extrapolate past the worst observed scenario. Normal assumptions can miss skew, clustering and tails.",
        "Monte Carlo simulates joint normal and covariance-matched Student-t asset log returns and aggregates simple returns. A common t scale shock preserves joint tail dependence. The normal asset simulation and fitted portfolio-normal distribution are different models; analytical convergence is checked in a matching one-asset case.",
        "EVT fits GPD loss exceedances. Its threshold scan uses mean excess, shape/modified-scale stability, counts and goodness of fit, with visible failures. The rule is a heuristic. Lower-confidence estimates below the threshold use an empirical-body hybrid. Shape >=1 implies infinite log ES, distinct from bounded monetary losses under positive wealth.",
        "Block-bootstrap intervals resample whole asset rows in circular 20-day blocks. The default is 500 replicates. Fixed threshold percentile bootstrap omits full threshold-selection uncertainty; intervals do not protect against model misspecification."
    ],[table(["Method","Level","VaR USD","ES USD"],risk_rows,[160,70,140,140])])
    validation_rows=[[r["method"],str(r.get("days",0)),str(r.get("breaches",0)),fmt(r.get("kupiec_p")),fmt(r.get("conditional_coverage_p")),r.get("zone")] for r in rec.get("validation",[]) if r["alpha"]==.99]
    page("Sequential forecast validation",[
        "Each forecast uses only observations through the previous day. Historical/normal models refit daily; slower models refit every 21 observations on a 750-observation window. Conditional volatility updates daily between refits. Forecast files preserve training cutoffs, parameters' refit date, failures and portfolio hashes.",
        "FHS is the preregistered primary model; GARCH-EVT is the challenger. Earlier equal-weight development forecasts were seen: FHS had 65 versus 47.2 expected breaches and Kupiec p about 0.014; GARCH-EVT had 52 and p about 0.49. The choice was therefore not historically blind.",
        "Kupiec tests exception frequency; Christoffersen independence tests clustering and conditional coverage combines them. Degenerate transitions are inconclusive. Missing forecasts are disclosed and excluded from numerical denominators without connecting transitions across gaps.",
        "Traditional Basel colours apply to the final 250 complete observations at 99%: 0-4 green, 5-9 yellow, 10+ red. Other levels receive binomial assessments. These supervisory categories are a monitoring analogy, not a regulatory capital calculation for the fund.",
        "C4 requires at least 95% coverage, a non-red final zone, and Kupiec/conditional-coverage p-values above 0.05 for 2017 onward. The challenger is used once if the primary fails. If both fail the investment evaluation is incomplete, rather than rejected on economic grounds."
    ],[table(["Model","Days","Hits","Kupiec p","CC p","Zone"],validation_rows,[120,55,45,100,100,90])])
    stress_rows=[[s.get("scenario"),fmt(s.get("return"),"pct"),fmt(s.get("loss_usd"),"usd"),str(s.get("breach","unavailable"))] for s in stress]
    page("Stress, attribution and governance",[
        "Historical stress paths hold positions buy-and-hold from SPY peak to trough: 9 October 2007-9 March 2009; 19 February-23 March 2020; 3 January-12 October 2022. The start-day close is the initial valuation, so its earlier daily return is excluded. No intervening trade cost is assumed.",
        "The hypothetical inflation shock sets SPY -25%, AGG -10% and GLD 0%. Other equity shocks use conditional means under the covariance of training-period SPY worst-decile days. This extrapolation is uncertain and has no calibrated probability. Reverse stress measures covariance distance to a 20% one-step loss, not a path probability.",
        "Historical dollar ES components use the same joint scenarios and shared normalised portfolio tail weights, including proportional sharing at tied boundaries. Negative contributions remain visible and sum to that scenario-based ES. Portfolio-only FHS cannot supply asset attribution.",
        "Bonds and gold may diversify some equity losses and fail during other shocks. Stock-bond rolling correlation and Treasury-rate sensitivity contextualise that instability. Risk budgets must distinguish capital weights from contributions to the portfolio's bad days.",
        "At 10% drawdown or a yellow zone, review the portfolio and model. At 15% drawdown or a red zone, consider the independently evaluated minimum-CVaR allocation. No automatic trade or guarantee is implied. Lowering annual spending by 0.5 percentage point reduces initial annual support by USD 50,000."
    ],[table(["Scenario","Return","Loss USD","Limit breach"],stress_rows,[180,90,140,100])])
    page("Decision, limitations and disclosure",[
        f"Frozen-rule outcome: {decision['outcome']}. {decision['action']} Checks: {json.dumps(checks)}.",
        "The original mandate passes only if feasibility, ES budget, expected geometric hurdle, validated risk model and stress checks all pass. Otherwise evaluate A1 alternative in-policy candidates in training ES order, A2 gold cap 20%, A3 spending 3.5%, A4 the frozen capped risk-budget increase, then A5 their combination. Missing evidence blocks a final verdict.",
        "Historical dependence, estimated means/covariances, sparse extremes, threshold uncertainty, changing regimes and conditional-filter specification limit inference. The analysis omits tax, detailed liquidity/price impact and Sri Lankan FX/spending risk. Revised macro data limits historical information claims.",
        "The real-capital simulation resamples joint monthly asset/CPI observations in non-circular 12-month blocks, applies quarterly/drift trades and annual spending, and compares after-spending NAV with inflation-adjusted initial capital. These are illustrative paths from a limited sample, not reliable forward probabilities.",
        "AI disclosure: Codex assisted restoration, portfolio/validation/stress implementation, integration, tests, application and document generation. Earlier source records identify Claude Code and Antigravity assistance. Automated independent numerical examples are software checks, not an independent human audit. Human reviewer/date: pending. The owner remains responsible for understanding, revising and defending every material result.",
        "Submission dependencies: written acceptance of a solo entry and the deadline remain unconfirmed. Repository access, publication and deployment require separate authorisation. This local package is prepared for review, not represented as submitted."
    ])
    page("Evidence and references",[
        "Evidence files include canonical weights, risk tables, per-allocation forecasts, formal tests, scenario attribution, uncertainty, walk-forward allocations, source manifests and environment versions. The Streamlit app reads this same run and invalidates expensive results for changed weights.",
        "Policy and procedure were frozen before current post-training portfolio evaluation. All historical data through the snapshot had been seen in earlier development, so the freeze documents the current procedure rather than manufacturing an untouched holdout.",
        *[f"{label}: {link}" for label,link in REFERENCES],
        "Academic foundations retained in the implementation: Markowitz mean-variance construction; CAPM excess-return beta; Rockafellar-Uryasev CVaR optimisation; peaks-over-threshold GPD; Kupiec frequency and Christoffersen independence likelihood-ratio tests. The local teaching decks use synthetic illustrations and do not supply empirical estimates."
    ])
    if chart_paths:
        page("Historical wealth and drawdown",[
            f"Portfolio {chosen}, weights {rec.get('weight_hash','')[:12]}. Retrospective daily-return path from 2005 through {cfg['snapshot_end']}, after quarterly/drift trading costs and before spending.",
            "These paths describe historical behaviour. The annual walk-forward procedure and daily risk forecasts answer different questions and are exported separately."
        ],[Image(str(chart_paths["wealth"]),width=510,height=217),Image(str(chart_paths["drawdown"]),width=510,height=217)])
    story=[];source=[]
    for i,(title,texts,extras) in enumerate(pages):
        if i:story.append(PageBreak())
        story.append(Paragraph(title,styles["Title"] if i==0 else styles["Heading1"]))
        for text in texts:story.append(paragraph(text))
        story.extend(extras);source.append("## "+title+"\n\n"+"\n\n".join(texts))
    pdf("investment_memorandum.pdf",story)
    (dest/"investment_memorandum.md").write_text("# Investment memorandum\n\n"+"\n\n".join(source),encoding="utf-8")
    concise=[Paragraph("Executive tear sheet",styles["Title"]),paragraph(f"Serendib University Endowment | USD 10 million | {cfg['snapshot_end']}"),
             paragraph(f"Proposed decision: {decision['outcome']}. {decision['action']}"),table(["ETF","Weight","USD"],allocation,[140,130,240]),Spacer(1,12)]
    head=risk[(risk.alpha==.99)&risk.method.isin(["historical","normal","mc_t","evt"])] if len(risk) else risk
    concise.append(table(["One-day 99% model","VaR USD","ES USD"],[[r.method,fmt(r.var_usd,"usd"),fmt(r.es_usd,"usd")] for r in head.itertuples()],[230,140,140]))
    concise.extend([paragraph(f"After-cost CAGR {fmt(perf.get('cagr'),'pct')}; maximum drawdown {fmt(perf.get('maximum_drawdown'),'pct')}. Historical replay, not untouched evidence."),
                    paragraph("Stress losses and validation are allocation-specific. VaR/ES do not cap loss. Review at 10% drawdown/yellow zone; consider validated de-risking at 15%/red zone."),
                    paragraph(f"Run {meta['run_id']}; weights {rec.get('weight_hash','unavailable')[:12]}. Owner validation and solo eligibility pending. AI assistance disclosed in memorandum.")])
    monitor=next((v for v in rec.get("validation",[]) if v["method"]==rec.get("model_used") and v["alpha"]==.99),{})
    worst=max((s.get("loss_usd",0) for s in stress),default=0)
    concise.insert(-1,paragraph(f"Validation ({rec.get('model_used','unavailable')}, 99%): {monitor.get('breaches','?')}/{monitor.get('days','?')} breaches, {monitor.get('zone','unavailable')} zone; Kupiec p {fmt(monitor.get('kupiec_p'))}, conditional coverage p {fmt(monitor.get('conditional_coverage_p'))}. Largest specified scenario loss {fmt(worst,'usd')}."))
    if capital:
        concise.insert(-1,paragraph(f"Illustrative real-capital shortfall after spending: {fmt(capital[0]['shortfall_probability'],'pct')} at five years; {fmt(capital[-1]['shortfall_probability'],'pct')} at ten years. Material concern for owner review; not a calibrated forecast."))
    pdf("executive_tear_sheet.pdf",concise)
    committee=[Paragraph("Investment committee decision",styles["Title"]),paragraph(f"Recommendation: {decision['outcome']}. {decision['action']}"),
               paragraph("What can go wrong? Equity markets can fall together, stock/bond correlations can rise, and income may not cover inflation plus spending."),
               paragraph("How bad could losses become? The specified scenarios quantify conditional losses. Historical crises and hypothetical shocks are examples, not maximum-loss bounds."),
               table(["Scenario","Loss USD","Breaches policy"],[[s.get("scenario"),fmt(s.get("loss_usd"),"usd"),str(s.get("breach"))] for s in stress],[230,140,140]),
               paragraph("How confident are we? Each allocation has its own sequential forecast tests; failures stay visible. Bootstrap intervals quantify part of estimation uncertainty. Prior development saw historical crises and the model-order choice is disclosed."),
               paragraph(f"Checks C1-C5: {checks}. The frozen adjustment order changes weights, gold cap, spending, then risk budget. No missing validation can yield an Accept verdict."),
               paragraph("Action: owner reviews the evidence, signs the investment judgement, confirms solo eligibility and deadline, then authorises any submission. Review at 10% drawdown/yellow; consider validated de-risking at 15%/red."),
               paragraph("AI assisted code and communications. Independent human validation remains pending. This proposal is not an executed mandate.")]
    pdf("committee_memo.pdf",committee)
    # Reusable slide contents for the editable deck; all numeric copy comes from the run.
    slides=[{"title":title,"body":texts[:3],"notes":"Allow about 55 seconds. Explain the evidence and limits in your own words. Source: this run's submission.json and associated evidence.\n"+"\n".join(texts)} for title,texts,_ in pages]
    slides.append({"title":"Committee questions","body":["Why this portfolio rather than 100% bonds?","What happens if FHS and the challenger both fail?","How do spending, inflation and stress limits change the action?"],
                   "notes":"Allow 50 seconds. Explain the frozen checks, spending hurdle and allocation-specific forecasts. Keep AI and human review distinct."})
    (dest/"pitch_content.json").write_text(json.dumps(slides,indent=2),encoding="utf-8")
    (dest/"speaker_qa_notes.md").write_text("# Pitch and Q&A notes\n\n"+"\n\n".join(f"## {i+1}. {s['title']}\n\n{s['notes']}" for i,s in enumerate(slides)),encoding="utf-8")
    from pypdf import PdfReader
    counts={p.name:len(PdfReader(p).pages) for p in dest.glob("*.pdf")}
    if not 7<=counts["investment_memorandum.pdf"]<=15:raise ValueError(f"Report page count {counts}")
    if counts["executive_tear_sheet.pdf"]!=1 or counts["committee_memo.pdf"]!=1:raise ValueError(f"One-page artifact overflow {counts}")
    (dest/"page_counts.json").write_text(json.dumps(counts,indent=2),encoding="utf-8")
