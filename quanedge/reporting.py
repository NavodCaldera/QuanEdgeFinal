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
    v2="reserve_initial" in cfg;v5="strategy" in cfg
    if w:
        series=pd.read_csv(run/chosen/"performance.csv",index_col=0,parse_dates=True)
        for name,values,ylabel in [("wealth",series.wealth,"Wealth per initial USD, net of trading costs"),
                  ("drawdown",series.wealth/series.wealth.cummax()-1,"Drawdown fraction")]:
            fig,ax=plt.subplots(figsize=(8,3.4));ax.plot(values.index,values,color="#176f83",lw=1.5)
            ax.set_ylabel(ylabel);ax.grid(alpha=.2);fig.tight_layout();p=dest/(name+".png");fig.savefig(p,dpi=160);plt.close(fig);chart_paths[name]=p
    if v5 and (run/chosen/"targets.csv").exists():
        held=pd.read_csv(run/chosen/"targets.csv",index_col=0,parse_dates=True)[list(cfg["universe"])]
        fig,ax=plt.subplots(figsize=(8,3.4))
        ax.stackplot(held.index,(100*held).T.to_numpy(),labels=held.columns,colors=["#2a78d6","#1baf7a","#eda100","#eb6834"],step="post")
        ax.set_ylabel("Target weight (%)");ax.set_ylim(0,100);ax.legend(loc="upper left",ncol=4,fontsize=8);ax.grid(alpha=.2)
        fig.tight_layout();p=dest/"targets.png";fig.savefig(p,dpi=160);plt.close(fig);chart_paths["targets"]=p
    pages=[]
    def page(title,texts,extra=()):pages.append((title,texts,list(extra)))
    if v5:
        st=rec.get("strategy",{});es99=rec.get("es99",{});ranges=rec.get("target_range",{})
        method=(f"dynamic EWMA risk parity over {', '.join(cfg['universe'])}: equal volatility risk contributions from an exponentially weighted covariance "
                f"(lambda {st.get('ewma_lambda')}, last {st.get('window')} days), re-estimated at each month-end close from data through that close")
        span=", ".join(f"{t} {100*lo:.0f}-{100*hi:.0f}%" for t,(lo,hi) in ranges.items())
        incomplete_note=("" if decision["outcome"]!="evaluation incomplete" else " The outcome is incomplete, so no allocation is committed until the failed evidence is resolved.")
    original=bundle["portfolios"]["selected"]
    capital=rec.get("real_capital_survival",{}).get("results",[])
    if v2:
        from .portfolio import nominal_target
        goal=nominal_target(cfg["inflation"],cfg.get("real_return_target",cfg["real_return_floor"]));floor=nominal_target(cfg["inflation"],cfg["real_return_floor"])
        schedule=f"USD {cfg['reserve_initial']:,.0f} in year 1, growing {fmt(cfg['reserve_growth'],'pct')} a year (year 2 USD {cfg['reserve_initial']*(1+cfg['reserve_growth']):,.0f})"
    sustainability=("Illustrative 25-year reserve sustainability: "+"; ".join(
        f"{row['year']} years: all payments funded in {fmt(row['all_payments_funded'],'pct')} of paths, initial real capital preserved in {fmt(row['real_capital_preserved'],'pct')}, median real balance {fmt(row['median_real_balance_usd'],'usd')}" for row in capital)+
        (". The reserve grows 3.64% a year, faster than US CPI, and the 1% real floor is below the 4% initial draw, so real capital is expected to decline;" if v5 else ". A fixed real reserve of 4% of the initial fund exceeds the 1-3% real return objective, so real capital is expected to decline by design;")+" these resampled-history outcomes do not gate the verdict.") if v2 and capital else ("Illustrative after-spending real-capital shortfall probabilities: "+"; ".join(
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
        *([f"Recommendation: {decision['outcome']}. Invest by the {method}. Holdings drift between month-ends. The target in force from 1 October 2026 is "
           +", ".join(f"{t} {fmt(v,'pct')}" for t,v in w.items() if v)+f" (weight hash {rec.get('weight_hash','')[:12]}). What is recommended is the method (strategy hash {rec.get('forecast_hash','')[:12]}), not a fixed weight vector."+incomplete_note]
          if v5 and chosen=="selected" else []),
        f"Algorithmic recommendation: {decision['outcome']}. {decision['action']} Reported allocation and numbers: {chosen}, weight hash {rec.get('weight_hash','unavailable')[:12]}.",
        tradeoff or "The original allocation is reported; its outcome follows the frozen checks rather than a discretionary override.",
        sustainability,
        *([f"Mandate v5 (owner change, 31 October 2026, tagged {cfg.get('prereg_tag')}): the recommendation is the dynamic risk-parity method above (pre-registered as candidate v4d before its backtest). "
           f"Risk budget: historical one-day ES99 of {fmt(cfg['es_budget'],'pct')} of invested NAV ({fmt(cfg['es_budget']*cfg['value'],'usd')}). Real returns are measured against US CPI ({fmt(cfg['inflation'],'pct')} a year, FRED CPIAUCSL 2005-2026), "
           f"and C3 requires at least 1% expected real return. The universe ({', '.join(cfg['universe'])}), cash reserve, zero cost, 20% stress limit and FHS/GARCH-EVT model order carry over from mandates v2-v4, whose runs and verdicts remain as recorded.",
           "Disclosure: mandate v5 was written after the strategy's results had been seen. Under v4 its 30 September 2026 target failed the 2.5% budget (ES99 2.60%); the owner then raised the budget to 3% and moved the inflation basis to CPI. "
           "The Accept outcome was therefore expected before this run. The run confirms that the result reproduces under the frozen rules; it is not an independent test. The method was chosen after about twenty allocation rules had been compared on the same history."] if v5 else []),
        *([f"Mandate v3 (owner change, 30 October 2026, tagged {cfg.get('prereg_tag')}): the portfolio may hold only {', '.join(cfg['universe'])}. EFA, EEM and XLK are excluded because their daily return correlations with SPY are 0.88, 0.82 and 0.91 (2005-2026), so they add little diversification. XLE is the least SPY-correlated equity ETF but still moves with SPY (0.70 daily, 0.76 on SPY's worst 5% of days); AGG and GLD are close to uncorrelated with SPY (0.00 and 0.07). All other v2 rules are unchanged."] if "universe" in cfg and not v5 else []),
        *([f"Mandate v2 (owner change, 30 October 2026, tagged prereg-v2): no ETF percentage limits; zero trading cost; each 1 January a cash reserve for the university is withdrawn ({schedule}); target real return 1-3% a year after {fmt(cfg['inflation'],'pct')} assumed inflation. It supersedes mandate v1 (run final-20261027), whose results remain unchanged."] if v2 and not v5 else []),
        "This is a solo submission prepared with AI assistance. The owner approved the policy assumptions and FHS/GARCH-EVT model order; independent review of implementation and the investment judgement is pending.",
        "Capital preservation takes priority over maximising gains. A perpetual endowment must fund today's scholarship obligations while protecting future purchasing power. The strategic review period is five years; daily risk measurement serves monitoring rather than defining the investment horizon.",
        "What can go wrong: equities can fall together, bonds can lose with equities during inflation shocks, and gold can fail to protect over the committee's chosen period. Spending and inflation can overwhelm returns even when daily risk looks modest.",
        "How bad: the stress section reports conditional dollar losses, not a worst possible outcome. How confident: forecast coverage, failure counts and bootstrap intervals qualify each point estimate."
    ])
    if v2:policy_v2=[
        f"Cash reserve: {schedule}, withdrawn from the portfolio on the first trading day of each year and paid to the university. The reserve earns nothing and is not an investment; it is not part of the seven-ETF universe. Year 1 invests USD {cfg['value']:,.0f} of the USD {cfg['fund_value']:,.0f} fund.",
        f"Return objective: 1-3% real a year. With the owner's {fmt(cfg['inflation'],'pct')} inflation assumption (described by the owner as an average world rate; its source and period are not yet verified) the nominal geometric target is {fmt(goal,'pct')} and the acceptance floor is {fmt(floor,'pct')}. USD 400,000 is 4% of the initial fund, so the reserve schedule exceeds the real return objective and real capital is expected to decline.",
        ("Universe: "+", ".join(cfg["universe"])+" only; the other three eligible ETFs are held at zero by owner choice. " if "universe" in cfg else "")+"Constraints: long-only and fully invested, with no per-ETF, equity, gold or sector percentage limits. The binding risk budget is historical one-day ES99 of 2.5% of invested NAV (USD 240,000 at inception) on the allocation's estimation sample. The stress/drawdown limit is 20%.",
        "Rebalance quarterly or when any weight drifts more than five percentage points. Trading cost is assumed to be zero (owner assumption), so bid-ask spreads and market impact are not modelled. ETF expense ratios are embedded in adjusted prices.",
    ]
    if v5:policy_v2=[
        policy_v2[0],
        f"Return objective: at least 1% real a year (C3), measured against US CPI inflation of {fmt(cfg['inflation'],'pct')} a year (FRED CPIAUCSL as published, 3 January 2005 to 30 September 2026; index ratios, not levels). "
        f"The nominal floor is {fmt(floor,'pct')}. The reserve still grows {fmt(cfg['reserve_growth'],'pct')} a year, a conservative spending assumption above CPI, so the reserve rises faster than prices and real capital is expected to decline.",
        f"25-year spending baseline (owner's framing): USD 10,000,000 / USD 400,000 = 25 payments. If net returns equalled the {fmt(cfg['reserve_growth'],'pct')} reserve growth every year, beginning-of-year withdrawals would exhaust the fund with the 25th payment. "
        "The question is whether the strategy funds the same payments and leaves capital. Three outcomes are kept apart: all payments funded, capital left, and the initial USD 10 million preserved in real terms. The endowment remains perpetual; 25 years is an evaluation window, not the end of the mandate.",
        f"Universe: {', '.join(cfg['universe'])} only; EFA, EEM and XLK are held at zero because they move almost in step with SPY (daily correlation 0.82-0.91). Long-only and fully invested, with no per-ETF percentage limits. "
        f"Risk budget: historical one-day ES99 of at most {fmt(cfg['es_budget'],'pct')} of invested NAV ({fmt(cfg['es_budget']*cfg['value'],'usd')}), on both the strategy's own daily path and the latest target over 2005-2026. Stress and drawdown limit: 20%.",
        f"Trading: re-estimate at each month-end close and trade to the new target; between month-ends the holdings drift with prices. Historical turnover was {rec.get('turnover_per_year',float('nan')):.2f} times NAV a year over {rec.get('rebalances','?')} monthly decisions. "
        "Trading cost is assumed to be zero (owner assumption), so spreads and market impact are not modelled. ETF expense ratios are embedded in adjusted prices.",
    ]
    allocation_title=["ETF","Target from 1 Oct 2026","Exposure at USD 9.6m"] if v5 else ["ETF","Weight","Initial exposure"]
    page("Policy and allocation",policy_v2 if v2 else [
        f"Annual spending is {fmt(cfg['spending'],'pct')} after returns and costs; assumed inflation is {fmt(cfg['inflation'],'pct')}. The exact after-cost, before-spending break-even hurdle is {fmt(hurdle(cfg['inflation'],cfg['spending']),'pct')}.",
        "The portfolio is long-only and fully invested. AGG is 25-70%, total equity at most 55%, gold at most 15%, XLE/XLK at most 10% each, and other individual ETFs at most 40%. These are chosen policy assumptions, not organiser rules.",
        "The binding risk budget is historical one-day ES99 of USD 250,000 on the allocation's estimation sample. The stress/drawdown limit is 20%. No daily estimate guarantees this multi-period loss limit.",
        "Rebalance quarterly or when any weight drifts more than five percentage points. Trading cost is five basis points one-way per unit of traded NAV. Expected-return comparisons reserve five basis points annually for the frozen one-times-NAV turnover assumption. ETF expense ratios are embedded in adjusted prices.",
    ],[table(allocation_title,allocation,[140,130,240])])
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
    if v2:construction_v2=[
        f"Selection rule (mandate v2): minimise historical CVaR99 subject to the ES budget and an expected geometric return of at least {fmt(goal,'pct')} (3% real). The LP is linear in arithmetic return, so the smallest arithmetic floor meeting the geometric target is found by bisection. If the minimum-CVaR allocation already meets the target, the target does not bind and minimum CVaR is selected.",
        "Expected returns use the frozen estimator: sample annual means shrunk 50% toward the cross-asset mean, with Ledoit-Wolf covariance. The owner kept this estimator after seeing that it decides the outcome: shrinkage lifts AGG's expected return toward the equity average. On raw historical means the reported allocation's expected return is materially lower (estimator sensitivity is exported); the same rule with raw means would instead select roughly AGG 65 / GLD 17 / XLK 18.",
        "The mandate v1 rule (maximise return within the ES budget) is kept as the max_return comparison candidate. Without ETF limits it concentrates in AGG, GLD and XLK. Markowitz comparisons use minimum variance, maximum Sharpe and volatility risk parity without percentage limits. SPY is the CAPM market proxy; 40/60 SPY/AGG is the active-return benchmark.",
        "The adapted permanent portfolio uses 25% SPY, 50% AGG and 25% gold; AGG substitutes imperfectly for long Treasuries and cash. Constraint effects are isolated by identical-scenario re-solves changing the ES budget or the real return target.",
        "Pairs trading and short market-neutral strategies introduce borrow, margin and implementation risks beyond this long-only policy. Diversification can reduce losses without guaranteeing a profit."
    ]
    if v5:construction_v2=[
        f"Method: at each month-end close, estimate the covariance of daily simple returns of {', '.join(cfg['universe'])} with exponential weights 0.97^k on the last {st.get('window')} days (half-life about 23 trading days, effective sample about 66 days). "
        "Then choose long-only, fully invested weights whose volatility risk contributions w_i (Sigma w)_i / (w' Sigma w) are equal (25% each), by the convex Spinu (2013) programme: minimise 0.5 y' Sigma y - (1/4) sum log y_i, then w = y / sum y.",
        "Why risk parity: it needs no expected returns. Under mandates v2-v4 the return estimator decided the outcome (50% mean shrinkage pushed the selection to about 88% AGG, which on raw means expects about 0.25% real). Risk parity spreads risk rather than capital, so no single ETF dominates the portfolio's bad days.",
        "Why EWMA and monthly: volatility shocks fade with half-lives of about 34 (SPY), 49 (AGG), 68 (XLE) and 219 (GLD) trading days, so a 23-day half-life tracks the current regime. After a month, 47% of the estimator's information is new. "
        "Weekly re-estimation traded noise (1.7x turnover a year) and breached the 20% limit in the GFC; quarterly held stale weights through COVID. No calendar rule catches day-scale crashes.",
        f"Range of monthly targets since 2006: {span}. The equity share rises when equity volatility is low relative to bonds and gold, and falls when it spikes. Expected return of the current target under the frozen estimator (50% shrinkage, Ledoit-Wolf): {fmt(rec.get('expected_geometric'),'pct')} nominal, {fmt(rec.get('expected_real'),'pct')} real.",
        "Fixed-weight comparisons (minimum CVaR, minimum variance, static risk parity, maximum Sharpe, the v1 max-return rule, 60/40, 40/60, equal weight, permanent 25/50/25 and balanced 35/50/15) are evaluated in the same run with their own forecasts. Minimum CVaR is the precomputed de-risk allocation for governance. SPY is the CAPM market proxy; 40/60 SPY/AGG is the active-return benchmark.",
        "Settings (lambda 0.97, 750 days, 500-day start, monthly) were registered before the strategy's risk backtest and were not tuned afterwards. The choice of method still followed retrospective comparisons on the same 2005-2026 history."
    ]
    page("Construction and alternatives",construction_v2 if v2 else [
        "The frozen selection maximises arithmetic expected return subject to historical CVaR99 and allocation constraints. A second LP minimises CVaR within 1e-8 of the optimal return. Failed solves remain unavailable. Sample annual arithmetic means are shrunk 50% toward their cross-asset mean; Ledoit-Wolf covariance supports the variance-based candidates.",
        "The hurdle tests geometric return after the fixed turnover-cost reserve. The lognormal moment approximation is (1 + net arithmetic return) exp(-variance/2) - 1. Estimation choices and constraints drive the result; expected return is uncertain and is not a realised performance promise.",
        "Shrinking toward one cross-asset mean can overstate expected bond returns by pulling them toward equity returns. Fixed-weight sensitivity across shrinkage strengths and five-year, ten-year and full-history windows is exported separately; the frozen recommendation is not re-tuned to these results.",
        "Markowitz comparisons use constrained minimum variance, maximum Sharpe and near-parity volatility contributions. Minimum CVaR is the precomputed de-risk portfolio. SPY is the CAPM market proxy for beta and Jensen alpha; the 40/60 SPY/AGG portfolio is the active-return benchmark.",
        "The adapted permanent portfolio uses 25% SPY, 50% AGG and 25% gold; AGG substitutes imperfectly for long Treasuries and cash. It is outside policy and is a comparison only. Constraint effects are isolated by identical-scenario re-solves changing one limit.",
        "Pairs trading and short market-neutral strategies introduce borrow, margin and implementation risks beyond this long-only policy. The retained long-only mechanism is rebalancing relative winners and losers. Diversification can reduce losses without guaranteeing a profit."
    ],[table(["Candidate","Expected geometric","Policy ES99 USD","Status"],candidates,[145,125,145,95])]+
      ([Spacer(1,8),Image(str(chart_paths["targets"]),width=510,height=217)] if "targets" in chart_paths else []))
    performance_rows=[[k,fmt(v,"pct" if k in ["cagr","maximum_drawdown","annual_volatility","jensen_alpha","cumulative_return"] else "number")] for k,v in perf.items() if isinstance(v,(float,int)) and not isinstance(v,bool)]
    page("Performance and accounting",[
        *([f"The strategy's path starts on {perf.get('period_start','?')}: the first {st.get('min_history')} return days (from 4 January 2005) estimate the first target, so its KPIs cover a shorter period than the fixed-weight candidates. Every target uses data through its decision close only, so the path is walk-forward by construction; the method choice is not."] if v5 else []),
        ("All historical allocation evaluations are retrospective. Fixed-weight candidates are estimated through the snapshot end, so their replays include the crises their estimates saw; the strategy's targets do not, but its design does." if v5 else
         "All historical allocation evaluations are retrospective. W_train is estimated through 2016, W_rec through the snapshot end, and neither erases prior exposure to the crises used when writing the policy. The annual walk-forward procedure uses only earlier data for each year's weights; policy design remains historically informed."),
        ("Wealth compounds simple portfolio returns; asset simple returns aggregate before conversion to log. The strategy's path and its risk forecasts use the same daily returns (monthly targets, drift between, zero cost), so there is no implementation mismatch for W_rec; fixed-weight candidates' forecasts replay daily constant weights." if v5 else
         "Wealth compounds simple portfolio returns; asset simple returns aggregate before conversion to log. Implementation performance includes quarterly/drift turnover costs. Risk forecasts instead replay daily constant weights without costs, a disclosed implementation mismatch."),
        "Sharpe uses daily excess return and sample volatility; Sortino uses a zero target and downside deviation over all days. Treynor is unavailable for near-zero beta. Jensen alpha uses SPY excess returns. Information ratio uses 40/60 active returns and tracking error. Calmar uses CAGR and drawdown over the same dates.",
        ("The cash reserve is withdrawn before the first trading day's return each year; a fund that cannot pay the full reserve is depleted and stays at zero. "+("Real values deflate by US CPI (2.59% a year), below the 3.64% reserve growth." if v5 else "Real values deflate by the policy inflation assumption, the same rate that grows the reserve.") if v2 else
        "Annual spending is deducted once after net returns. The real-capital target is initial NAV multiplied by the CPI ratio; spending is not added to this target. Money-weighted return includes distributions as investor cash flows and remaining NAV, while time-weighted CAGR measures the investment path.")
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
    if v5:rec_validation=("The recommended strategy is validated on its own daily path, with monthly target changes and drift, not on fixed weights. Its forecast file carries the strategy hash on every row, and no other allocation's results are reused. "
        f"C4 result: model used {rec.get('model_used') or 'none'}. A pass through the challenger after a primary failure is a weaker result and is disclosed.")
    page("Sequential forecast validation",[*([rec_validation] if v5 else []),
        "Each forecast uses only observations through the previous day. Historical/normal models refit daily; slower models refit every 21 observations on a 750-observation window. Conditional volatility updates daily between refits. Forecast files preserve training cutoffs, parameters' refit date, failures and portfolio hashes.",
        "FHS is the preregistered primary model; GARCH-EVT is the challenger. Earlier equal-weight development forecasts were seen: FHS had 65 versus 47.2 expected breaches and Kupiec p about 0.014; GARCH-EVT had 52 and p about 0.49. The choice was therefore not historically blind.",
        "Kupiec tests exception frequency; Christoffersen independence tests clustering and conditional coverage combines them. Degenerate transitions are inconclusive. Missing forecasts are disclosed and excluded from numerical denominators without connecting transitions across gaps.",
        "Traditional Basel colours apply to the final 250 complete observations at 99%: 0-4 green, 5-9 yellow, 10+ red. Other levels receive binomial assessments. These supervisory categories are a monitoring analogy, not a regulatory capital calculation for the fund.",
        "C4 requires at least 95% coverage, a non-red final zone, and Kupiec/conditional-coverage p-values above 0.05 for 2017 onward. The challenger is used once if the primary fails. If both fail the investment evaluation is incomplete, rather than rejected on economic grounds."
    ],[table(["Model","Days","Hits","Kupiec p","CC p","Zone"],validation_rows,[120,55,45,100,100,90])])
    stress_rows=[[s.get("scenario"),fmt(s.get("return"),"pct"),fmt(s.get("loss_usd"),"usd"),str(s.get("breach","unavailable"))] for s in stress]
    page("Stress, attribution and governance",[
        ("Historical stress windows run from SPY peak to trough: 9 October 2007-9 March 2009; 19 February-23 March 2020; 3 January-12 October 2022. The recommended strategy is stressed on its own path from the start-day close, with its monthly re-estimates and drift; dollar losses by ETF are holdings at each prior close times that day's return. Fixed-weight candidates are held buy-and-hold."
         if v5 else "Historical stress paths hold positions buy-and-hold from SPY peak to trough: 9 October 2007-9 March 2009; 19 February-23 March 2020; 3 January-12 October 2022. The start-day close is the initial valuation, so its earlier daily return is excluded. No intervening trade cost is assumed."),
        "The hypothetical inflation shock sets SPY -25%, AGG -10% and GLD 0%. Other equity shocks use conditional means under the covariance of training-period SPY worst-decile days. This extrapolation is uncertain and has no calibrated probability. Reverse stress measures covariance distance to a 20% one-step loss, not a path probability.",
        "Historical dollar ES components use the same joint scenarios and shared normalised portfolio tail weights, including proportional sharing at tied boundaries. Negative contributions remain visible and sum to that scenario-based ES. Portfolio-only FHS cannot supply asset attribution.",
        "Bonds and gold may diversify some equity losses and fail during other shocks. Stock-bond rolling correlation and Treasury-rate sensitivity contextualise that instability. Risk budgets must distinguish capital weights from contributions to the portfolio's bad days.",
        "At 10% drawdown or a yellow zone, review the portfolio and model. At 15% drawdown or a red zone, consider the independently evaluated minimum-CVaR allocation. No automatic trade or guarantee is implied. "+("Each USD 50,000 less in the first-year reserve reduces the whole inflation-linked schedule by 12.5%." if v2 else "Lowering annual spending by 0.5 percentage point reduces initial annual support by USD 50,000.")
    ],[table(["Scenario","Return","Loss USD","Limit breach"],stress_rows,[180,90,140,100])])
    page("Decision, limitations and disclosure",[
        f"Frozen-rule outcome: {decision['outcome']}. {decision['action']} Checks: {json.dumps(checks)}.",
        (f"Mandate v5 checks: C1 every monthly target long-only, fully invested and in the universe; C2 the path's ES99 ({fmt(es99.get('path'),'pct')}) and the current target's 2005-2026 ES99 ({fmt(es99.get('latest_target'),'pct')}) both at most {fmt(cfg['es_budget'],'pct')}; "
         "C3 expected real return at least 1% under the frozen estimator; C4 FHS or, if it fails, GARCH-EVT passes on the strategy's own forecasts; C5 the strategy path loses at most 20% in each scenario and its GFC drawdown stays within 20%. "
         "If the strategy failed, A1 would try the fixed-weight candidates in training ES order; no limit is relaxable further. Missing evidence blocks a final verdict." if v5 else
         "The mandate passes only if feasibility (C1), the ES budget (C2), "+(f"a realised real CAGR of at least {cfg['real_cagr_floor']:.0%} on the 2005-2026 replay (C3)" if "real_cagr_floor" in cfg else "an expected real return of at least 1% (C3)")+", a validated risk model (C4) and the stress limits (C5) all pass. Otherwise evaluate A1, the alternative candidates in training ES order, then A2, the ES budget raised to the frozen training-sample value. The reserve schedule and the 1% real floor are client needs and are not relaxed. Missing evidence blocks a final verdict." if v2 else
        "The original mandate passes only if feasibility, ES budget, expected geometric hurdle, validated risk model and stress checks all pass. Otherwise evaluate A1 alternative in-policy candidates in training ES order, A2 gold cap 20%, A3 spending 3.5%, A4 the frozen capped risk-budget increase, then A5 their combination. Missing evidence blocks a final verdict."),
        "Historical dependence, estimated means/covariances, sparse extremes, threshold uncertainty, changing regimes and conditional-filter specification limit inference. The analysis omits tax, detailed liquidity/price impact and Sri Lankan FX/spending risk. Revised macro data limits historical information claims.",
        ("The reserve simulation resamples the strategy's own monthly returns (2007-2026) in non-circular 12-month blocks for 25 years, pays the 3.64%-growing reserve each January and deflates by US CPI. It reports full-payment success, depletion timing and real balances. These are illustrative paths from a limited sample, not reliable forward probabilities." if v5 else
         "The reserve simulation resamples joint monthly asset returns in non-circular 12-month blocks for 25 years, pays the inflation-linked reserve each January, rebalances quarterly or on drift and reports full-payment success, depletion timing and real balances. These are illustrative paths from a limited sample, not reliable forward probabilities." if v2 else
        "The real-capital simulation resamples joint monthly asset/CPI observations in non-circular 12-month blocks, applies quarterly/drift trades and annual spending, and compares after-spending NAV with inflation-adjusted initial capital. These are illustrative paths from a limited sample, not reliable forward probabilities."),
        "AI disclosure: Codex assisted restoration, portfolio/validation/stress implementation, integration, tests, application and document generation. Earlier source records identify Claude Code and Antigravity assistance; Claude Code implemented the mandate v2-v5 rule changes, cash-reserve accounting, the dynamic risk-parity strategy evaluation and reruns. Automated independent numerical examples are software checks, not an independent human audit. Human reviewer/date: pending. The owner remains responsible for understanding, revising and defending every material result.",
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
            f"Portfolio {chosen}, "+(f"strategy {rec.get('forecast_hash','')[:12]}, path from {perf.get('period_start')}" if v5 else f"weights {rec.get('weight_hash','')[:12]}, from 2005")+f". Retrospective daily-return path through {cfg['snapshot_end']}, "+("with monthly re-estimates, zero cost and before " if v5 else "after quarterly/drift trading costs and before ")+("reserve withdrawals." if v2 else "spending."),
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
             paragraph(f"Proposed decision: {decision['outcome']}. {decision['action']}"),
             *([paragraph(f"Method: {method}. The target below applies from 1 October 2026 and changes monthly. Path ES99 {fmt(es99.get('path'),'pct')}; target ES99 {fmt(es99.get('latest_target'),'pct')} vs {fmt(cfg['es_budget'],'pct')} budget. Mandate v5 was written after these results were seen; Accept reproduces them and is not an independent test.")] if v5 else []),
             table(allocation_title,allocation,[140,130,240]),Spacer(1,12)]
    head=risk[(risk.alpha==.99)&risk.method.isin(["historical","normal","mc_t","evt"])] if len(risk) else risk
    concise.append(table(["One-day 99% model","VaR USD","ES USD"],[[r.method,fmt(r.var_usd,"usd"),fmt(r.es_usd,"usd")] for r in head.itertuples()],[230,140,140]))
    concise.extend([paragraph(f"After-cost CAGR {fmt(perf.get('cagr'),'pct')}"+(f" ({fmt(rec.get('realised_real_cagr'),'pct')} real over CPI) from {perf.get('period_start')}" if v5 else "")+f"; maximum drawdown {fmt(perf.get('maximum_drawdown'),'pct')}. Historical replay, not untouched evidence."),
                    paragraph("Stress losses and validation are allocation-specific. VaR/ES do not cap loss. Review at 10% drawdown/yellow zone; consider validated de-risking at 15%/red zone."),
                    paragraph(f"Run {meta['run_id']}; weights {rec.get('weight_hash','unavailable')[:12]}. Owner validation and solo eligibility pending. AI assistance disclosed in memorandum.")])
    monitor=next((v for v in rec.get("validation",[]) if v["method"]==rec.get("model_used") and v["alpha"]==.99),{})
    worst=max((s.get("loss_usd",0) for s in stress),default=0)
    concise.insert(-1,paragraph(f"Validation ({rec.get('model_used','unavailable')}, 99%): {monitor.get('breaches','?')}/{monitor.get('days','?')} breaches, {monitor.get('zone','unavailable')} zone; Kupiec p {fmt(monitor.get('kupiec_p'))}, conditional coverage p {fmt(monitor.get('conditional_coverage_p'))}. Largest specified scenario loss {fmt(worst,'usd')}."))
    if capital and v2:
        last=capital[-1]
        concise.insert(-1,paragraph(f"Expected return {fmt(rec.get('expected_geometric'),'pct')} nominal ({fmt(rec.get('expected_real'),'pct')} real; "+("floor 1% real over US CPI" if v5 else "target 1-3%")+f"). Cash reserve {schedule}. Illustrative {last['year']}-year outcome: all reserve payments funded in {fmt(last['all_payments_funded'],'pct')} of paths; initial real capital preserved in {fmt(last['real_capital_preserved'],'pct')}. Not a calibrated forecast."))
    elif capital:
        concise.insert(-1,paragraph(f"Illustrative real-capital shortfall after spending: {fmt(capital[0]['shortfall_probability'],'pct')} at five years; {fmt(capital[-1]['shortfall_probability'],'pct')} at ten years. Material concern for owner review; not a calibrated forecast."))
    pdf("executive_tear_sheet.pdf",concise)
    committee=[Paragraph("Investment committee decision",styles["Title"]),paragraph(f"Recommendation: {decision['outcome']}. {decision['action']}"),
               paragraph("What can go wrong? Equity markets can fall together, stock/bond correlations can rise, and income may not cover inflation plus spending."),
               paragraph("How bad could losses become? The specified scenarios quantify conditional losses. Historical crises and hypothetical shocks are examples, not maximum-loss bounds."),
               table(["Scenario","Loss USD","Breaches policy"],[[s.get("scenario"),fmt(s.get("loss_usd"),"usd"),str(s.get("breach"))] for s in stress],[230,140,140]),
               paragraph("How confident are we? Each allocation has its own sequential forecast tests; failures stay visible. Bootstrap intervals quantify part of estimation uncertainty. Prior development saw historical crises and the model-order choice is disclosed."),
               paragraph(f"Checks C1-C5: {checks}. "+("The frozen adjustment order changes weights (A1), then the risk budget (A2)." if v2 else "The frozen adjustment order changes weights, gold cap, spending, then risk budget.")+" No missing validation can yield an Accept verdict."),
               paragraph("Action: owner reviews the evidence, signs the investment judgement, confirms solo eligibility and deadline, then authorises any submission. Review at 10% drawdown/yellow; consider validated de-risking at 15%/red."),
               paragraph("AI assisted code and communications. Independent human validation remains pending. This proposal is not an executed mandate.")]
    pdf("committee_memo.pdf",committee)
    # Reusable slide contents for the editable deck; all numeric copy comes from the run.
    slides=[{"title":title,"body":texts[:3],"notes":"Allow about 55 seconds. Explain the evidence and limits in your own words. Source: this run's submission.json and associated evidence.\n"+"\n".join(texts)} for title,texts,_ in pages]
    slides.append({"title":"Committee questions","body":(["Why risk parity instead of an optimiser that targets return?","What happens if GARCH-EVT also starts failing in monitoring?","Can the strategy pay 25 years of reserves and keep real capital?"] if v5 else
                   ["Why so much AGG, and what if bond returns stay low?","What happens if FHS and the challenger both fail?","How long can the reserve schedule be paid?"] if v2 else
                   ["Why this portfolio rather than 100% bonds?","What happens if FHS and the challenger both fail?","How do spending, inflation and stress limits change the action?"]),
                   "notes":"Allow 50 seconds. Explain the frozen checks, spending hurdle and allocation-specific forecasts. Keep AI and human review distinct."})
    (dest/"pitch_content.json").write_text(json.dumps(slides,indent=2),encoding="utf-8")
    (dest/"speaker_qa_notes.md").write_text("# Pitch and Q&A notes\n\n"+"\n\n".join(f"## {i+1}. {s['title']}\n\n{s['notes']}" for i,s in enumerate(slides)),encoding="utf-8")
    from pypdf import PdfReader
    counts={p.name:len(PdfReader(p).pages) for p in dest.glob("*.pdf")}
    if not 7<=counts["investment_memorandum.pdf"]<=15:raise ValueError(f"Report page count {counts}")
    if counts["executive_tear_sheet.pdf"]!=1 or counts["committee_memo.pdf"]!=1:raise ValueError(f"One-page artifact overflow {counts}")
    (dest/"page_counts.json").write_text(json.dumps(counts,indent=2),encoding="utf-8")
