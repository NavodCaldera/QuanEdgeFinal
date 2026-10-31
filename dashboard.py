"""Investment committee dashboard for the final portfolio (v6): monthly dynamic EWMA risk parity with a recession overlay.

Start: python -m streamlit run dashboard.py
Calculations live in quanedge/final_portfolio.py; this file only arranges and labels them.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from quanedge import final_portfolio as F
from quanedge import universe as U
from quanedge import recession_overlay as RO
from quanedge.risk.models import LABEL
from quanedge.stress import SCENARIOS

st.set_page_config(page_title="Endowment risk dashboard", layout="wide")

COLOR = {"SPY": "#2a78d6", "AGG": "#eb6834", "GLD": "#1baf7a", "XLE": "#eda100"}
NAME = {"SPY": "SPY · US equity", "AGG": "AGG · US bonds", "GLD": "GLD · gold", "XLE": "XLE · energy equity"}
INK, MUTED, GRID = "#52514e", "#8a8984", "rgba(128,128,128,.18)"
ACCENT, ALT = "#2a78d6", "#8a8984"
METHODS = ["historical", "normal", "student_t", "mc_normal", "mc_t", "evt", "fhs", "garch_evt"]
FAMILY_TEXT = {"historical": "Historical", "normal": "Parametric", "student_t": "Parametric",
               "mc_normal": "Monte Carlo", "mc_t": "Monte Carlo", "evt": "EVT", "fhs": "Conditional", "garch_evt": "Conditional"}
CRISIS_FILL = "rgba(128,128,128,.12)"


def usd(x, d=0):
    return "n/a" if x is None or not np.isfinite(x) else f"USD {x:,.{d}f}"


def money(x):
    """Compact USD for metric tiles: USD 9.60m, USD 155k."""
    if x is None or not np.isfinite(x):
        return "n/a"
    return f"USD {x/1e6:.2f}m" if abs(x) >= 1e6 else f"USD {x/1e3:,.0f}k"


def pct(x, d=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{100*x:.{d}f}%"


def p_text(p):
    return "n/a" if p is None else f"{p:.3f}"


def tick(ok):
    return "✅ pass" if ok else "❌ fail"


def style(fig, height=360, y=None, legend=True):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=INK),
                      showlegend=legend, legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=y)
    return fig


def shade_crises(fig, start=None, end=None):
    for name, (a, b) in SCENARIOS.items():
        if (start is None or pd.Timestamp(b) >= start) and (end is None or pd.Timestamp(a) <= end):
            fig.add_vrect(x0=a, x1=b, fillcolor=CRISIS_FILL, line_width=0, annotation_text=name,
                          annotation_position="top left", annotation_font_color=MUTED)


# ---------------------------------------------------------------- data (cached)
@st.cache_data(show_spinner="Loading the frozen evidence and prices")
def load(model):
    ev = F.load_evidence(model=model)
    prices, returns, rf, cpi = F.load_market()
    return ev, prices, returns, rf, cpi


@st.cache_resource(show_spinner="Fitting the risk models")
def risk(data_hash, start, end, weights_key):
    weights = dict(weights_key)
    return F.risk_now(RETURNS, weights, VALUE, start, end)


@st.cache_resource(show_spinner="Bootstrapping the risk estimates")
def intervals(data_hash, weights_key):
    return F.bootstrap(RETURNS, dict(weights_key), VALUE)


@st.cache_resource(show_spinner="Measuring what each ETF adds")
def universe(data_hash):
    return U.load_saved(data_hash) or U.evidence(*U.load())


@st.cache_resource(show_spinner="Simulating 25 years of cash reserves")
def reserve(strategy_hash):
    return F.reserve_test(PATH), F.reserve_history(PATH, CPI)


@st.cache_resource(show_spinner="Loading the recession-overlay evidence")
def overlay(data_hash):
    try:
        ev = RO.load_saved()
    except (RO.OverlayEvidenceError, FileNotFoundError, KeyError) as err:
        return {"error": str(err)}
    return {"ev": ev, "core": RO.core_path(), "signals": RO.signals(CFG["snapshot_end"])}


MODEL = st.sidebar.radio("Model", list(F.MODELS), format_func=F.MODELS.get,
                         help="v6 is the final model (owner decision, 31 Oct 2026). v5 is the same strategy without the overlay, for comparison.")
V6 = MODEL == "v6"
try:
    EV, PRICES, RETURNS, RF, CPI = load(MODEL)
except (F.EvidenceError, FileNotFoundError, KeyError) as err:
    st.title("Endowment risk dashboard")
    st.error(f"The saved evidence cannot be used: {err}")
    st.write("Rebuild it from the repository root, then reload:")
    st.code("python -m quanedge.data.run --check-only\npython -m quanedge.dynamic_parity_eval\npython -m quanedge.recession_overlay")
    st.stop()

CFG = F.policy()
VALUE = float(CFG["value"])                  # invested NAV after the 1 January cash reserve
PATH = EV["path"]; FC = EV["forecasts"]; SUMMARY = EV["summary"]; SH = EV["strategy_hash"]
W = F.current_target(PATH)
WKEY = tuple(sorted(W.items()))
FIRST_FC, LAST_FC = FC.index[0].date(), FC.index[-1].date()
ESTIMATION = {"Full sample, 2005-01-04 to 2026-09-30": (None, None),
              "Last 750 trading days (about 3 years)": (str(RETURNS.index[-750].date()), None),
              "2017-01-03 to 2026-09-30 (evaluation period)": ("2017-01-01", None)}


# ---------------------------------------------------------------- sidebar
def sidebar():
    st.sidebar.markdown("**Settings**")
    alpha = st.sidebar.selectbox("Confidence level", [.90, .95, .99], index=2, format_func=lambda a: f"{a:.0%}")
    method = st.sidebar.selectbox("VaR methodology", METHODS, index=METHODS.index("garch_evt"),
                                  format_func=lambda m: LABEL[m])
    dates = st.sidebar.date_input("Backtest date range", value=(pd.Timestamp(CFG["evaluation_start"]).date(), LAST_FC),
                                  min_value=FIRST_FC, max_value=LAST_FC)
    if not isinstance(dates, (tuple, list)) or len(dates) != 2:
        st.sidebar.warning("Choose a start and an end date.")
        dates = (pd.Timestamp(CFG["evaluation_start"]).date(), LAST_FC)
    st.sidebar.caption(f"Invested NAV {usd(VALUE)} (USD 10m fund less the USD 400,000 cash reserve). "
                       f"Risk horizon one trading day. Data to {CFG['snapshot_end']}.")
    st.sidebar.caption(f"Strategy hash {SH[:8]} · run {EV['run']}")
    return alpha, method, pd.Timestamp(dates[0]), pd.Timestamp(dates[1])


# ---------------------------------------------------------------- shared numbers
def headline(alpha):
    models, table = risk(EV["data_hash"], None, None, WKEY)
    row = lambda m: table[(table.method == m) & np.isclose(table.alpha, alpha)].iloc[0]
    return models, table, row


# ---------------------------------------------------------------- pages
def page_decision():
    alpha, method, start, end = SETTINGS
    st.title("Final portfolio: monthly dynamic risk parity" + (" with recession overlay" if V6 else " (v5 core, comparison)"))
    st.caption("Serendib University Endowment Fund · four ETFs (SPY, AGG, GLD, XLE) · retrospective portfolio evaluation")
    models, table, row = headline(.99)
    perf = F.performance(PATH, RETURNS, RF, CPI)
    stress, hyp, _ = F.stress_panel(PATH, PRICES, RETURNS, W, VALUE)
    worst = max((s["path"] for s in stress if "path" in s), key=lambda x: x["loss_usd"])
    c = st.columns(5)
    c[0].metric("Invested NAV", money(VALUE))
    c[1].metric("1-day 99% VaR", money(row("historical").var_usd), help=f"Historical simulation: {usd(row('historical').var_usd)}. Loss exceeded on about 1 day in 100.")
    c[2].metric("1-day 99% ES", money(row("historical").es_usd), help=f"Historical simulation: {usd(row('historical').es_usd)}. Average loss on the worst 1% of days.")
    c[3].metric("Worst crisis loss", money(worst["loss_usd"]), help=f"{usd(worst['loss_usd'])}: largest loss across GFC, COVID and 2022, as run.")
    c[4].metric("Maximum fall since 2006", pct(-perf["maximum_drawdown"]), help="Largest fall from a previous high, strategy as run.")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Allocation to hold now")
        contrib, _ = F.risk_contributions(RETURNS, W, .99, VALUE)
        frame = pd.DataFrame({"ETF": [NAME[t] for t in F.UNIVERSE], "Weight": [pct(W[t]) for t in F.UNIVERSE],
                              "USD": [f"{W[t]*VALUE:,.0f}" for t in F.UNIVERSE],
                              "Vol. share": [pct(contrib.vol_contribution[t]) for t in F.UNIVERSE],
                              "ES share": [pct(contrib.es_share[t]) for t in F.UNIVERSE]})
        st.dataframe(frame, hide_index=True, width="stretch")
        if V6:
            st.caption("Recession overlay at the last close: " + ("**ON**: half of SPY and XLE held as cash." if PATH.overlay_on.iloc[-1]
                       else "**off** (yield-curve warning on, but SPY is above its 12-month average). See the Recession overlay page."))
        st.caption(f"Target set at the {PATH.index[-1].date()} close from data up to that close; next review at the "
                   "next month-end close. Each ETF carries a quarter of the expected volatility, but XLE and SPY carry most "
                   "of the tail loss.")
    with right:
        st.subheader("Key evidence")
        ge = next(v for v in SUMMARY["validation"] if v["method"] == "garch_evt" and v["alpha"] == .99)
        fhs = next(v for v in SUMMARY["validation"] if v["method"] == "fhs" and v["alpha"] == .99)
        bench = F.kpis(F.benchmark_returns(RETURNS).loc[PATH.index[0]:], RF, RETURNS.SPY, F.benchmark_returns(RETURNS))
        ev = [("Return since " + SUMMARY["start"], f"{pct(perf['cagr'], 2)} a year; 40/60 SPY/AGG {pct(bench['cagr'], 2)}"),
              ("Real return (US CPI)", f"{pct(perf['real_cagr'], 2)} a year after {pct(perf['cpi_inflation'], 2)} CPI inflation"),
              ("Volatility", f"{pct(perf['annual_volatility'], 1)} a year; 40/60 {pct(bench['annual_volatility'], 1)}"),
              ("Largest fall", f"{pct(-perf['maximum_drawdown'])}; 40/60 {pct(-bench['maximum_drawdown'])}"),
              ("99% VaR backtest, GARCH-EVT", f"{ge['breaches']} breaches vs {ge['expected_breaches']:.1f} expected, "
               f"Kupiec p {ge['kupiec_p']:.2f}, cond. coverage p {ge['conditional_coverage_p']:.3f}, {ge['zone']}"),
              ("99% VaR backtest, FHS", f"{fhs['breaches']} breaches vs {fhs['expected_breaches']:.1f}, cond. coverage p "
               f"{fhs['conditional_coverage_p']:.3f}: breaches cluster"),
              ("Hypothetical equity-bond shock", f"{usd(hyp['loss_usd'])} ({pct(-hyp['return'])})")]
        test, _ = reserve(SH); r25 = test["results"][-1]
        ev.append((f"{r25['year']}-year cash-reserve test", f"every reserve paid in {pct(r25['all_payments_funded'])} of resampled paths; "
                   f"USD 10m kept in real terms in {pct(r25['real_capital_preserved'])}"))
        st.markdown("\n".join(f"- **{k}:** {v}" for k, v in ev))
        st.caption("Backtests 2017-01-03 to 2026-09-30 on the strategy's own forecasts; returns are a retrospective evaluation.")

    why_four(contrib.es_share)

    latest = F.latest_forecast(FC, CFG["challenger"], .99, VALUE)
    st.subheader("Recommendation to the committee")
    st.markdown(
        "**Hold this portfolio**, monitored as follows. This is the team's proposal for the owner's and committee's review.\n\n"
        f"1. **Hold** the current target and reset it at every month-end close by the rule on the Portfolio page"
        + (" and the recession overlay (half of SPY and XLE to cash while the yield curve has been inverted in the last 24 months "
           "and SPY is below its 12-month average).\n" if V6 else ".\n") +
        f"2. **Daily risk:** measure 99% one-day risk with GARCH-EVT refitted as in its backtest (latest forecast, for "
        f"{latest['date']}: VaR {usd(latest['var_usd'])}); "
        + ("its breach count matched the 99% level, but breaches clustered, mostly around overlay switches, so use the higher of "
           "the GARCH-EVT and FHS forecasts in any month the overlay switches.\n" if V6 else
           "its breaches matched the 99% level in testing. FHS stays as a second view because its breaches cluster.\n") +
        f"3. **Review triggers:** an extra committee review if the fall from the previous high passes 15% (the largest so far "
        f"was {pct(-perf['maximum_drawdown'])}) or if 99% VaR breaches exceed 9 in any 250 days (Basel red zone).\n"
        f"4. **Expectation setting:** the real return has been about {pct(perf['real_cagr'], 1)} a year after US CPI inflation. "
        "That is history, chosen after the fact; plan spending on a lower figure.")

    over = [(s["scenario"], -s["today_buy_hold"]["drawdown"]) for s in stress
            if s.get("today_buy_hold") and -s["today_buy_hold"]["drawdown"] > -perf["maximum_drawdown"]]
    if over:
        st.caption("**Main risk accepted:** a crash that arrives before the next month-end meets today's weights. Bought at the start of "
                   + " and ".join(f"{n} ({pct(x)})" for n, x in over) + " and left to drift, they would have fallen further than "
                   f"the strategy ever did as run ({pct(-perf['maximum_drawdown'])}). See the technical report, section 7.")

    st.subheader("The committee's three questions")
    q = st.columns(3)
    rates = next(s for s in stress if s["scenario"] == "Rates 2022")["path"]
    covid = next(s for s in stress if s["scenario"] == "COVID")["path"]
    with q[0]:
        st.markdown("**What can go wrong?**")
        st.markdown(f"- Stocks and bonds fall together, as in 2022: AGG lost {usd(-rates['pnl_usd']['AGG'])} while the path fell "
                    f"{pct(-rates['return'])}.\n- A sudden shock arrives between monthly reviews: in COVID the path lost "
                    f"{pct(-covid['return'])} in five weeks, worst day {covid['worst_day']} ({pct(covid['worst_day_return'])}).\n"
                    f"- Energy reverses: XLE is {pct(W['XLE'])} of the money but {pct(contrib.es_share['XLE'])} of the 99% ES.")
    with q[1]:
        st.markdown("**How bad can losses get?**")
        st.markdown(f"- A bad day (1 in 100): about {usd(row('historical').var_usd)}; the average of those days "
                    f"{usd(row('historical').es_usd)}.\n- Worst historical crisis, as run: {usd(worst['loss_usd'])}; "
                    f"largest fall {pct(-perf['maximum_drawdown'])}.\n- Hypothetical joint equity-bond shock: "
                    f"{usd(hyp['loss_usd'])} ({pct(-hyp['return'])}). None of these is a maximum.")
    with q[2]:
        st.markdown("**How confident are we?**")
        xi = models["evt"].params
        st.markdown(f"- GARCH-EVT 99% forecasts: {ge['breaches']} breaches vs {ge['expected_breaches']:.1f} expected, "
                    f"2017-2026 ({ge['zone']}). FHS: {fhs['breaches']}, clustered.\n- EVT tail shape ξ = {xi['xi']:.2f} "
                    f"± {1.96*xi['xi_se']:.2f}: a fat tail, estimated from {xi['n_exceed']} days.\n- All of this is history the "
                    "strategy was chosen after seeing; there is no untouched test period.")


def why_four(es_share):
    """Decision page section: why SPY, AGG, GLD and XLE, and not EFA, EEM or XLK."""
    u = universe(EV["data_hash"])
    corr, cr = u["correlation"], u["crises"].set_index("etf")
    rg = u["regimes"].set_index("regime"); bets = u["bets"].set_index("set")
    sp = u["spanning"].set_index("etf"); dyn = u["parity_dynamic"].set_index("universe")
    st_ = u["parity_static"].set_index("universe"); opt = u["optimisers"]
    shock, stress = rg.loc["Rate shock (10y yield +0.25 pt)"], rg.loc["Equity stress (VIX > 30 or SPY < -5%)"]
    hi = rg.loc["High inflation (CPI y/y >= 3%)"]
    four, seven = bets.loc["Four (SPY, AGG, GLD, XLE)"], bets.loc["All seven"]
    d4, d7 = dyn.loc["Four ETFs"], dyn.loc["All seven ETFs"]

    st.subheader("Why these four ETFs")
    st.markdown(
        f"Each of the four responds to a different economic condition, so together they cover the four conditions an endowment "
        f"must live through: growth, recession, inflation and a loss of confidence. EFA, EEM and XLK are a second, third and "
        f"fourth copy of the same equity risk as SPY. Adding all three raises the number of independent bets only from "
        f"**{four.effective_bets:.2f} to {seven.effective_bets:.2f}**, and in risk parity it would move the equity share "
        f"of risk from {pct(st_.loc['Four ETFs', 'equity_risk_share'], 0)} to {pct(st_.loc['All seven ETFs', 'equity_risk_share'], 0)}.")
    cards = {
        "SPY": ("Growth", f"Return engine: {pct(cr.loc['SPY', 'annual return 2005-2026'])} a year since 2005."),
        "AGG": ("Recession", f"Gained {pct(cr.loc['AGG', 'GFC return'])} in the GFC; {pct(stress['AGG'], 1)} a month in equity-stress "
                             f"months, when every equity ETF lost about {pct(-stress['SPY'], 0)}."),
        "GLD": ("Loss of confidence", f"Gained {pct(cr.loc['GLD', 'GFC return'])} in the GFC and {pct(stress['GLD'], 1)} a month in "
                                      "equity-stress months; correlation with SPY "
                                      f"{corr.loc['GLD', 'SPY']:.2f}."),
        "XLE": ("Inflation", f"The only ETF that gained in 2022 ({pct(cr.loc['XLE', 'Rates 2022 return'])}); "
                             f"{pct(shock['XLE'], 1)} a month when the 10-year yield jumped, AGG {pct(shock['AGG'], 1)}."),
    }
    for col, t in zip(st.columns(4), F.UNIVERSE):
        title, text = cards[t]
        with col.container(border=True):
            st.markdown(f"**{t}** · {title}")
            st.caption(text)

    tabs = st.tabs(["Economic roles", "Fundamentals", "Overlap (technical)", "Seven-ETF test", "What this does not prove"])
    with tabs[0]:
        st.markdown("Average **monthly** return of each ETF in four macro conditions, 2005-2026. Held ETFs first.")
        order = F.UNIVERSE + U.DROP
        show = rg[order].map(lambda x: f"{100*x:+.2f}%")
        show.insert(0, "Months", rg.months)
        st.dataframe(show, width="stretch")
        st.markdown(
            f"- **Rate shocks** ({int(shock.months)} months): bonds and gold lost ({pct(shock['AGG'], 1)}, {pct(shock['GLD'], 1)}); "
            f"XLE gained {pct(shock['XLE'], 1)}. It is the only eligible ETF whose profits rise with energy prices, a main "
            "driver of inflation shocks such as 2022.\n"
            f"- **Equity stress** ({int(stress.months)} months): all five equity ETFs lost {pct(-stress[U.EQUITY].max(), 1)} to "
            f"{pct(-stress[U.EQUITY].min(), 1)}; AGG and GLD were the only positive holdings. International and technology "
            "equity offered no shelter.\n"
            f"- **High inflation** ({int(hi.months)} months, CPI above 3%): SPY earned {pct(hi['SPY'], 1)} a month against "
            f"{pct(rg.loc['Low inflation (CPI y/y < 3%)', 'SPY'], 1)} in low inflation; XLE ({pct(hi['XLE'], 1)}) and GLD "
            f"({pct(hi['GLD'], 1)}) held up best of the four. XLK also did well ({pct(hi['XLK'], 1)}), so this row alone "
            "does not rule it out; the overlap tab does.")
        st.caption("Month-end classification with US CPI as published (revised data), FRED DGS10 and VIXCLS. Descriptive: the "
                   "regimes are identified after the fact and are not trading signals.")
    with tabs[1]:
        st.markdown("\n".join(f"- **{t} ({U.ROLE[t][0]}):** {U.ROLE[t][1]}" for t in F.UNIVERSE + U.DROP))
        st.markdown(
            "XLK and XLE are both sectors of the S&P 500, so both already sit inside SPY. The difference is behaviour: XLK moves with "
            f"SPY (correlation {corr.loc['XLK', 'SPY']:.2f}, beta {sp.loc['XLK', 'beta_spy']:.2f}), a leveraged bet on the same "
            f"growth stocks; XLE is the least SPY-like equity ETF ({corr.loc['XLE', 'SPY']:.2f}) because its profits follow "
            "commodity prices. EFA and EEM add currency exposure that a US-dollar fund paying US-dollar reserves does not need.")
    with tabs[2]:
        which = st.radio("Correlation of daily log returns", ["All days", f"SPY's worst 5% of days ({u['stress_days']} days)"],
                         horizontal=True, key="why_corr")
        m = corr if which == "All days" else u["stress_correlation"]
        order = F.UNIVERSE + U.DROP; m = m.loc[order, order]
        fig = go.Figure(go.Heatmap(z=m.values, x=order, y=order, zmin=-1, zmax=1, colorscale="RdBu_r",
                                   text=m.round(2).values, texttemplate="%{text}", hovertemplate="%{y}-%{x}: %{z:.2f}<extra></extra>"))
        st.plotly_chart(style(fig, 380, legend=False).update_yaxes(autorange="reversed"), width="stretch")
        b = u["bets"].copy()
        st.dataframe(pd.DataFrame({"ETF set": b.set, "ETFs": b.etfs, "Independent bets": b.effective_bets.round(2),
                                   "Bets per ETF": b.bets_per_etf.round(2), "First factor": b.first_factor_share.map(pct)}),
                     hide_index=True, width="stretch")
        st.caption("Independent bets: exp(entropy) of the correlation matrix's eigenvalue shares; 1 means one common factor, N means "
                   "N unrelated assets.")
        st.markdown("**What each excluded ETF adds once the four are held** (daily regression on SPY, AGG, GLD, XLE, HAC errors)")
        st.dataframe(pd.DataFrame({"ETF": sp.index, "Share explained by SPY": sp.r2_on_spy.map(pct),
                                   "Share explained by the four": sp.r2_on_four.map(pct),
                                   "Own volatility": sp.volatility.map(pct), "Volatility left over": sp.residual_volatility.map(pct),
                                   "Unexplained return a year": sp.alpha_annual.map(lambda x: f"{100*x:+.1f}%"),
                                   "t-statistic": sp.alpha_t.round(1)}), hide_index=True, width="stretch")
        st.markdown(f"EFA and EEM added risk and earned **less** than the mix of the four that tracks them best "
                    f"(t {sp.loc['EFA', 'alpha_t']:.1f} and "
                    f"{sp.loc['EEM', 'alpha_t']:.1f}). XLK's extra {pct(sp.loc['XLK', 'alpha_annual'])} a year is not "
                    f"statistically clear (t {sp.loc['XLK', 'alpha_t']:.1f}).")
    with tabs[3]:
        o = opt.loc[opt.allocation != "selected", ["run", "allocation", *U.TICKERS, "excluded_weight"]].copy()
        o["allocation"] = o.allocation.map({"min_cvar": "Minimum CVaR", "min_variance": "Minimum variance",
                                            "max_sharpe": "Maximum Sharpe"})
        o["run"] = o.run.str.split(" ").str[0].map({"v1": "Seven-ETF run 1", "v2": "Seven-ETF run 2"})
        for t in [*U.TICKERS, "excluded_weight"]:
            o[t] = o[t].map(lambda x: "·" if abs(x) < 5e-4 else pct(x))
        st.markdown("**In earlier runs the optimisers could use all seven ETFs.** What they chose:")
        st.dataframe(o.rename(columns={"excluded_weight": "EFA+EEM+XLK"}), hide_index=True, width="stretch")
        st.markdown("Neither risk-minimising optimiser bought EFA or EEM in either run; XLK appeared only in the "
                    "return-seeking one.")
        st.markdown("**The final rule (monthly EWMA risk parity) run on four versus seven ETFs**, same settings and dates:")
        st.dataframe(pd.DataFrame({
            "Universe": dyn.index, "CAGR": dyn.cagr.map(lambda x: pct(x, 2)), "Volatility": dyn.volatility.map(pct),
            "Largest fall": dyn.max_fall.map(pct), "Daily ES99": dyn.es99_daily.map(lambda x: pct(x, 2)),
            "GFC": dyn["GFC return"].map(pct), "COVID": dyn["COVID return"].map(pct), "2022": dyn["Rates 2022 return"].map(pct),
            "Average equity weight": dyn.average_equity_target.map(pct)}), hide_index=True, width="stretch")
        st.markdown(f"Seven ETFs earned {pct(d7.cagr - d4.cagr, 2)} a year more but fell {pct(d7.max_fall)} at worst, "
                    f"against {pct(d4.max_fall)}; in the GFC it lost {pct(-d7['GFC return'])} "
                    f"against {pct(-d4['GFC return'])}. For a fund whose first aim is avoiding large losses, the four-ETF version "
                    "is the better trade.")
        st.caption(f"Paths from {d4.start} (500-day warm-up), lambda 0.97, 750-day window, zero cost, no reserve withdrawals.")
    with tabs[4]:
        st.markdown(
            f"- **Chosen after seeing the data.** The four-ETF rule was written on 30 October 2026 with 2005-2026 correlations in "
            "view (PLAN.md 13c). Everything above is retrospective.\n"
            f"- **XLE is not a low-correlation asset.** Its correlation with SPY is {corr.loc['XLE', 'SPY']:.2f}, "
            f"{u['stress_correlation'].loc['XLE', 'SPY']:.2f} on SPY's worst days; it fell {pct(-cr.loc['XLE', 'COVID return'])} in "
            f"COVID and carries {pct(es_share['XLE'])} of today's 99% ES with {pct(W['XLE'])} of the money. It is held for "
            "inflation protection; risk parity sizes it by volatility, not by tail loss.\n"
            f"- **Excluding XLK gave up return.** XLK earned {pct(cr.loc['XLK', 'annual return 2005-2026'])} a year, the most of the "
            "seven; the seven-ETF rule had the higher CAGR. The case for leaving it out is concentration and drawdown, not return.\n"
            "- **Correlations move.** SPY-AGG was negative 2007-2019 and positive from 2020; bonds did not protect in 2022.\n"
            "- **Policy, not a brief rule.** The brief allows any combination of the seven ETFs; holding four is our choice.")


def page_portfolio():
    alpha, method, start, end = SETTINGS
    st.title("Portfolio")
    st.caption("Monthly dynamic EWMA risk parity · each month-end, weights are reset so each ETF contributes an equal share "
               "of expected volatility · zero trading cost · no cash-reserve withdrawals in the replay"
               + (" · recession overlay: half of SPY and XLE in cash in months it is on (target charts show the risk-parity "
                  "targets before the overlay; holdings and returns include it)" if V6 else ""))
    period = st.radio("Period", ["Full history (from 2006-12-28)", "Backtest date range from the sidebar"], horizontal=True)
    a, b = (None, None) if period.startswith("Full") else (start, end)
    path = PATH.loc[a:b]
    if len(path) < 2:
        st.warning("The chosen date range has fewer than two days of history."); return

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Target weights now")
        fig = go.Figure(go.Bar(x=[W[t] for t in F.UNIVERSE], y=[NAME[t] for t in F.UNIVERSE], orientation="h",
                               marker=dict(color=[COLOR[t] for t in F.UNIVERSE], cornerradius=4),
                               text=[pct(W[t]) for t in F.UNIVERSE], textposition="outside",
                               customdata=[W[t]*VALUE for t in F.UNIVERSE],
                               hovertemplate="%{y}: %{x:.1%} · %{customdata:$,.0f}<extra></extra>"))
        style(fig, 300, legend=False).update_xaxes(tickformat=".0%", range=[0, .8]); fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.subheader("How the targets changed")
        hist = F.target_history(path) if len(path) else F.target_history(PATH)
        fig = go.Figure()
        for t in F.UNIVERSE:
            fig.add_trace(go.Scatter(x=hist.index, y=hist[t], name=t, stackgroup="w", line=dict(width=.5, color=COLOR[t]),
                                     hovertemplate=f"{t} %{{y:.1%}}<extra></extra>"))
        st.plotly_chart(style(fig, 300, "Target weight").update_yaxes(tickformat=".0%", range=[0, 1]), width="stretch")

    r = path["return"]
    wealth = F.wealth_usd(r, VALUE)
    bench = F.benchmark_returns(RETURNS).reindex(r.index)
    bw = F.wealth_usd(bench, VALUE)
    st.subheader(f"Growth of {usd(VALUE)}")
    fig = go.Figure([go.Scatter(x=wealth.index, y=wealth, name="Final portfolio", line=dict(color=ACCENT, width=2)),
                     go.Scatter(x=bw.index, y=bw, name="40/60 SPY/AGG benchmark", line=dict(color=ALT, width=1.5, dash="dot"))])
    shade_crises(fig, wealth.index[0], wealth.index[-1])
    st.plotly_chart(style(fig, 360, "USD").update_yaxes(tickformat=",.0f"), width="stretch")

    st.subheader("Drawdown from the previous high")
    dd = F.drawdown(wealth)
    fig = go.Figure([go.Scatter(x=dd.index, y=dd, name="Final portfolio", fill="tozeroy", line=dict(color=ACCENT, width=1.5)),
                     go.Scatter(x=dd.index, y=F.drawdown(bw), name="40/60 benchmark", line=dict(color=ALT, width=1, dash="dot"))])
    shade_crises(fig, dd.index[0], dd.index[-1])
    st.plotly_chart(style(fig, 300, "Drawdown").update_yaxes(tickformat=".0%"), width="stretch")

    st.subheader("Performance KPIs")
    k = F.performance(PATH, RETURNS, RF, CPI, a, b)
    kb = F.kpis(bench.dropna(), RF, RETURNS.SPY, bench.dropna())
    rows = [("CAGR", pct(k["cagr"], 2), pct(kb["cagr"], 2), "Compound annual growth of the path"),
            ("Real CAGR", pct(k["real_cagr"], 2), pct(F.cpi_real(bench.dropna(), CPI)[2], 2),
             f"(1 + CAGR)/(1 + CPI inflation) − 1; US CPI rose {pct(k['cpi_inflation'], 2)} a year (FRED CPIAUCSL)"),
            ("Cumulative return", pct(k["cumulative_return"]), pct(kb["cumulative_return"]), "Whole period"),
            ("Volatility", pct(k["annual_volatility"], 2), pct(kb["annual_volatility"], 2), "Daily standard deviation × √252"),
            ("Sharpe ratio", f"{k['sharpe']:.2f}", f"{kb['sharpe']:.2f}", "Excess return over the 3-month T-bill (FRED DTB3) / its volatility"),
            ("Sortino ratio", f"{k['sortino']:.2f}", f"{kb['sortino']:.2f}", "Annual mean return / downside deviation below 0"),
            ("Beta to SPY", f"{k['beta']:.2f}", f"{kb['beta']:.2f}", "Excess-return regression on SPY"),
            ("Treynor ratio", pct(k["treynor"], 2) if k["treynor"] is not None else "n/a", "", "Annual excess return / beta"),
            ("Jensen's alpha", pct(k["jensen_alpha"], 2), "", "Annual excess return not explained by beta × SPY excess"),
            ("Information ratio", f"{k['information_ratio']:.2f}" if k["information_ratio"] is not None else "n/a", "",
             "Active return over 40/60 / tracking error"),
            ("Maximum drawdown", pct(-k["maximum_drawdown"]), pct(-kb["maximum_drawdown"]), "Largest fall from a previous high"),
            ("Calmar ratio", f"{k['calmar']:.2f}" if k["calmar"] is not None else "n/a", f"{kb['calmar']:.2f}" if kb["calmar"] else "", "CAGR / maximum drawdown"),
            ("Longest time under water", f"{k['max_underwater_days']} days", f"{kb['max_underwater_days']} days", "Trading days below a previous high"),
            ("Rebalances / turnover", f"{k['rebalances']} · {k['turnover_per_year']:.2f}× a year", "", "Month-end resets; sum of absolute weight changes")]
    st.dataframe(pd.DataFrame(rows, columns=["KPI", "Final portfolio", "40/60 benchmark", "Definition"]), hide_index=True, width="stretch")
    st.caption(f"Period {path.index[0].date()} to {path.index[-1].date()}. Daily simple returns compound the wealth path. "
               "Fixed-weight benchmark rebalanced quarterly or on a 5-point drift.")

    with st.expander("How the allocation rule works"):
        st.markdown(
            "At each month-end close:\n"
            "1. Take the last 750 trading days of daily returns for SPY, AGG, GLD and XLE.\n"
            "2. Weight each day by 0.97^k, where k is days ago (half-life about 23 trading days), and estimate the covariance Σ.\n"
            "3. Solve for long-only weights w with equal risk contributions, w_i(Σw)_i = σ_p²/4 for each ETF "
            "(Spinu's convex formulation).\n"
            "4. Trade to those weights at that close and hold them until the next month-end.\n\n"
            "Only data up to each decision close is used. The first target (2006-12-28) needed 500 days of history.")


def page_risk():
    alpha, method, start, end = SETTINGS
    st.title("Risk: VaR, Expected Shortfall and EVT")
    choice = st.radio("Estimation window", list(ESTIMATION), horizontal=False)
    a, b = ESTIMATION[choice]
    models, table = risk(EV["data_hash"], a, b, WKEY)
    t = table[np.isclose(table.alpha, alpha)].set_index("method").loc[METHODS]
    st.caption(f"Current target ({' · '.join(f'{k} {pct(v)}' for k, v in W.items())}) held fixed over the window · "
               f"{alpha:.0%} confidence · one trading day · NAV {usd(VALUE)} · losses in USD of simple loss")

    fig = go.Figure()
    labels = [LABEL[m] for m in METHODS]
    fig.add_trace(go.Bar(x=labels, y=t.var_usd, name=f"VaR {alpha:.0%}", marker=dict(color="#9ec3ef", cornerradius=4),
                         hovertemplate="%{x}<br>VaR %{y:$,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=t.es_usd, name=f"ES {alpha:.0%}", marker=dict(color=ACCENT, cornerradius=4),
                         hovertemplate="%{x}<br>ES %{y:$,.0f}<extra></extra>"))
    style(fig, 400, "USD loss, one day").update_layout(barmode="group", bargap=.25, bargroupgap=.08, hovermode="closest")
    fig.update_yaxes(tickformat="$,.0f")
    st.plotly_chart(fig, width="stretch")

    out = pd.DataFrame({"Model": labels, "Family": [FAMILY_TEXT[m] for m in METHODS],
                        "VaR %": t.var_pct.round(3).to_numpy(), "VaR USD": t.var_usd.round(0).to_numpy(),
                        "ES %": t.es_pct.round(3).to_numpy(), "ES USD": t.es_usd.round(0).to_numpy(),
                        "ES / VaR": (t.es_usd/t.var_usd).round(2).to_numpy(),
                        "Basis": [t.basis[m] or ("next day, current volatility" if m in ("fhs", "garch_evt") else "whole window")
                                  for m in METHODS],
                        "Status": t.status.to_numpy()})
    st.dataframe(out, hide_index=True, width="stretch")

    h, n, e, mc = (t.loc[m] for m in ("historical", "normal", "evt", "mc_normal"))
    st.subheader("Why the methods disagree")
    st.markdown(
        f"- **Normal versus history.** The normal model puts ES at {usd(n.es_usd)}; the observed worst days average "
        f"{usd(h.es_usd)} ({h.es_usd/n.es_usd:.2f}×). Daily returns have fatter tails than a bell curve, and the gap widens at "
        "higher confidence.\n"
        f"- **Monte Carlo (normal)** gives {usd(mc.es_usd)}. It simulates the four ETFs jointly and adds them up, so it differs "
        "slightly from the single-series normal fit, but it shares the thin-tail assumption.\n"
        f"- **EVT** fits only the largest losses (ξ = {models['evt'].params['xi']:.2f}) and gives {usd(e.es_usd)}, close to "
        "history because the tail is estimated from the same extremes. Unlike history, it can extrapolate past the worst day seen.\n"
        f"- **FHS and GARCH-EVT** scale risk to today's volatility, so they answer a different question: tomorrow's risk "
        f"given current conditions ({usd(t.loc['garch_evt'].es_usd)} ES), not the average over the window.")

    st.subheader("Sensitivity to the estimation window")
    rows = []
    for label, (x, y) in ESTIMATION.items():
        _, tb = risk(EV["data_hash"], x, y, WKEY)
        tb = tb[np.isclose(tb.alpha, alpha)].set_index("method")
        rows.append({"Window": label, **{f"{LABEL[m]} ES": usd(tb.es_usd[m]) for m in ("historical", "normal", "evt", "garch_evt")}})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.subheader("Bootstrap intervals")
    b = intervals(EV["data_hash"], WKEY)
    b = b[np.isclose(b.alpha, alpha)].set_index("method")
    st.dataframe(pd.DataFrame({"Model": [LABEL[m] for m in b.index],
                               f"VaR {alpha:.0%}, 95% interval": [f"{usd(r.var_usd_lo)} to {usd(r.var_usd_hi)}" for r in b.itertuples()],
                               f"ES {alpha:.0%}, 95% interval": [f"{usd(r.es_usd_lo)} to {usd(r.es_usd_hi)}" for r in b.itertuples()],
                               "Resamples": b.reps_ok.to_numpy()}), hide_index=True, width="stretch")
    st.caption(f"{CFG['bootstrap_reps']} resamples of {CFG['bootstrap_block']}-day blocks of whole daily rows (circular), current target, "
               "full sample. They cover estimation noise only: the EVT threshold percentile is held fixed (see the EVT page for "
               "threshold sensitivity), and the choice of model is not covered.")


def page_evt():
    alpha, method, start, end = SETTINGS
    st.title("EVT tail and threshold choice")
    models, table = risk(EV["data_hash"], None, None, WKEY)
    m = models["evt"]; scan = m.scan; p = m.params
    if scan is None or scan.empty:
        st.warning("No threshold scan is available for this fit."); return
    st.caption("Peaks over threshold: a generalised Pareto distribution is fitted to daily log losses above a threshold u. "
               "Full sample, current target held fixed.")
    c = st.columns(4)
    c[0].metric("Threshold u", pct(p["u"], 2), help=f"{p['threshold_q']:.1%} percentile of daily losses")
    c[1].metric("Exceedances", f"{p['n_exceed']}")
    c[2].metric("Shape ξ", f"{p['xi']:.3f}", help=f"Standard error {p['xi_se']:.3f}. ξ > 0 means a heavy, power-law tail.")
    c[3].metric("Scale σ", pct(p["sigma"], 3))
    st.info(f"**Rule:** {p['threshold_rule']}. A threshold is 'stable' when ξ lies within 1.96 standard errors of ξ at "
            "every higher candidate (at least three of them); candidates need at least 50 exceedances. This is a project "
            "heuristic, not an optimal or significance-calibrated procedure.")

    ok = scan[scan.fit_ok]
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Scatter(x=ok.u, y=ok.mean_excess, mode="lines+markers", line=dict(color=ACCENT, width=2),
                                   marker=dict(size=8), hovertemplate="u %{x:.2%}<br>mean excess %{y:.3%}<extra></extra>"))
        fig.add_vline(x=p["u"], line_dash="dash", line_color=MUTED, annotation_text="chosen u")
        st.markdown("**Mean excess over the threshold**")
        st.plotly_chart(style(fig, 300, "Mean excess", legend=False).update_xaxes(tickformat=".1%", title="threshold u")
                        .update_yaxes(tickformat=".2%"), width="stretch")
        st.caption("Roughly linear and rising above the chosen threshold, which is consistent with a GPD tail with ξ > 0.")
    with c2:
        fig = go.Figure([go.Scatter(x=ok.q, y=ok.xi+1.96*ok.xi_se, line=dict(width=0), showlegend=False, hoverinfo="skip"),
                         go.Scatter(x=ok.q, y=ok.xi-1.96*ok.xi_se, fill="tonexty", fillcolor="rgba(42,120,214,.15)",
                                    line=dict(width=0), name="95% band", hoverinfo="skip"),
                         go.Scatter(x=ok.q, y=ok.xi, name="ξ estimate", mode="lines+markers", line=dict(color=ACCENT, width=2),
                                    marker=dict(size=8, color=np.where(ok.stable, ACCENT, "#ffffff"), line=dict(color=ACCENT, width=2)),
                                    hovertemplate="q %{x:.3f}<br>ξ %{y:.3f}<extra></extra>")])
        fig.add_vline(x=p["threshold_q"], line_dash="dash", line_color=MUTED, annotation_text="chosen")
        st.markdown("**Shape ξ across thresholds** (filled = stable)")
        st.plotly_chart(style(fig, 300, "ξ").update_xaxes(tickformat=".0%", title="threshold percentile"), width="stretch")

    st.subheader("Does the choice matter?")
    from quanedge.risk import fit_evt
    from quanedge.risk.portfolio import loss_fraction, portfolio_log_returns
    r = portfolio_log_returns(np.log1p(RETURNS[F.UNIVERSE]), W); losses = -r.to_numpy()
    rows = []
    for label, q in (("Chosen by the rule", None), ("90th percentile", .90), ("95th percentile", .95)):
        fit = m if q is None else fit_evt(losses, threshold_q=q)
        rows.append({"Threshold": label, "u": pct(fit.params["u"], 2), "Exceedances": fit.params["n_exceed"],
                     "ξ": f"{fit.params['xi']:.3f} ± {1.96*fit.params['xi_se']:.3f}",
                     f"VaR {alpha:.0%}": usd(VALUE*loss_fraction(fit.var(alpha))), f"ES {alpha:.0%}": usd(VALUE*fit.es_fraction(alpha)),
                     "Basis": fit.basis(alpha)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.subheader("Tail fit against the data")
    srt = np.sort(losses)[::-1]; k = np.arange(1, len(srt)+1); emp = k/len(srt)
    grid = np.linspace(p["u"], srt[0]*1.3, 200)
    gpd = p["n_exceed"]/len(srt)*(1+p["xi"]*(grid-p["u"])/p["sigma"])**(-1/p["xi"])
    from scipy.stats import norm
    mu, sd = r.mean(), r.std()
    fig = go.Figure([go.Scatter(x=srt[:p["n_exceed"]], y=emp[:p["n_exceed"]], mode="markers", name="Observed losses",
                                marker=dict(size=6, color=MUTED)),
                     go.Scatter(x=grid, y=gpd, name="GPD tail", line=dict(color=ACCENT, width=2)),
                     go.Scatter(x=grid, y=norm.sf(grid, -mu, sd), name="Normal", line=dict(color="#eb6834", width=2, dash="dot"))])
    style(fig, 360, "Probability a day's loss is larger").update_yaxes(type="log", tickformat=".0e")
    fig.update_xaxes(tickformat=".1%", title="daily log loss"); fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption("The normal curve falls away far faster than the observed losses: it makes the worst days look nearly impossible. "
               "The GPD follows them. The tail shape alone is not a crash probability.")


def page_backtest():
    alpha, method, start, end = SETTINGS
    st.title("Backtesting the risk forecasts")
    st.caption("Sequential risk-forecast evaluation: each day's VaR uses only returns up to the day before, on the strategy's own "
               f"daily path (strategy hash {SH[:8]}). Forecasts exist from {FIRST_FC}. Breach = loss larger than VaR.")
    if method not in F.BACKTEST_METHODS:
        st.warning(f"**{LABEL[method]}** has no saved sequential forecasts for this strategy, so it cannot be backtested here. "
                   "It is not replaced by another model. Choose Historical, Parametric (normal), EVT, Filtered HS or GARCH-EVT "
                   "in the sidebar.")
    else:
        res, frame = F.backtest(FC, SH, method, alpha, start, end)
        if res.get("status") != "ok" or res.get("days", 0) < 2:
            st.warning(f"Not enough forecast days in this range ({res.get('days', 0)}).")
        else:
            c = st.columns(5)
            c[0].metric("Days tested", f"{res['days']:,}", help=f"Coverage {res['coverage']:.1%}; missing forecasts {res['missing_days']}")
            c[1].metric("Breaches", f"{res['breaches']}", f"{res['breaches']-res['expected_breaches']:+.1f} vs {res['expected_breaches']:.1f} expected",
                        delta_color="inverse")
            c[2].metric("Kupiec p-value", p_text(res["kupiec_p"]), help="Is the breach frequency consistent with the confidence level?")
            c[3].metric("Christoffersen independence p", p_text(res["independence_p"]), help="Do breaches cluster on consecutive days?")
            c[4].metric("Conditional coverage p", p_text(res["conditional_coverage_p"]), help="Frequency and independence together")
            zone = res["zone"]
            light = {"green": ("🟢", "Green zone"), "yellow": ("🟡", "Yellow zone"), "red": ("🔴", "Red zone")}
            if zone in light:
                st.markdown(f"### {light[zone][0]} Basel traffic light: {light[zone][1]}")
                st.caption("Basel calibration: 99% one-day VaR, last 250 days of the chosen range; green 0-4 breaches, yellow 5-9, red 10+.")
            else:
                st.markdown("### ⚪ Basel traffic light unavailable")
                st.caption(f"The Basel zones are calibrated for 99% VaR over 250 days. Binomial reading instead: "
                           f"{F.binomial_zone(res, alpha)} (p = {p_text(res['binomial_p'])}).")
            words = []
            words.append("too many breaches" if res["kupiec_p"] <= .05 and res["breaches"] > res["expected_breaches"] else
                         "too few breaches (conservative)" if res["kupiec_p"] <= .05 else "breach frequency acceptable")
            if res["independence_p"] is not None:
                words.append("breaches cluster" if res["independence_p"] <= .05 else "no evidence of clustering")
            clustered = res["independence_p"] is not None and res["independence_p"] <= .05
            verdict = ("acceptable, but watch the clustering" if res["passes_gate"] and clustered else "acceptable" if res["passes_gate"]
                       else "questionable" if res["kupiec_p"] > .05 or (res["conditional_coverage_p"] or 0) > .05 else "unreliable")
            st.markdown(f"**Reading:** {', '.join(words)} → model **{verdict}** for this range and level.")

            fig = go.Figure([go.Scatter(x=frame.index, y=frame.loss, name="Daily loss", line=dict(color=MUTED, width=1)),
                             go.Scatter(x=frame.index, y=frame["var"], name=f"{LABEL[method]} VaR {alpha:.0%}", line=dict(color=ACCENT, width=2)),
                             go.Scatter(x=frame.index[frame.breach], y=frame.loss[frame.breach], mode="markers", name="Breach",
                                        marker=dict(size=8, color="#e34948", line=dict(color="white", width=2)))])
            st.plotly_chart(style(fig, 380, "Log loss").update_yaxes(tickformat=".1%"), width="stretch")
            by_year = frame.groupby(frame.index.year).breach.agg(["sum", "count"])
            fig = go.Figure([go.Bar(x=by_year.index, y=by_year["sum"], name="Breaches", marker=dict(color=ACCENT, cornerradius=4)),
                             go.Scatter(x=by_year.index, y=by_year["count"]*(1-alpha), name="Expected", mode="markers",
                                        marker=dict(size=10, symbol="line-ew-open", color=INK, line=dict(width=2)))])
            st.markdown("**Breaches by year**")
            st.plotly_chart(style(fig, 260).update_layout(hovermode="closest"), width="stretch")

    st.subheader("Reference test, fixed whatever the sidebar says")
    rows = []
    for m, role in ((CFG["primary"], "Primary"), (CFG["challenger"], "Challenger")):
        v = next(x for x in SUMMARY["validation"] if x["method"] == m and x["alpha"] == .99)
        rows.append({"Role": role, "Model": LABEL[m], "Breaches": v["breaches"], "Expected": round(v["expected_breaches"], 1),
                     "Kupiec p": p_text(v["kupiec_p"]), "Cond. coverage p": p_text(v["conditional_coverage_p"]),
                     "Zone": v["zone"], "Passes": tick(F.model_pass(v))})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption(f"99% VaR, {CFG['evaluation_start']} to {CFG['snapshot_end']}, models named before these backtests were run. "
               "Pass = coverage ≥ 95%, green or yellow, and Kupiec and conditional-coverage p-values both above 0.05. "
               "GARCH-EVT passes; FHS fails because its breaches cluster.")

    with st.expander("All saved models and levels for the chosen dates"):
        rows = []
        for m in F.BACKTEST_METHODS:
            for a in (.90, .95, .99):
                v, _ = F.backtest(FC, SH, m, a, start, end)
                rows.append({"Model": LABEL[m], "Level": f"{a:.0%}", "Breaches": v.get("breaches"),
                             "Expected": round(v.get("expected_breaches", np.nan), 1), "Kupiec p": p_text(v.get("kupiec_p")),
                             "Independence p": p_text(v.get("independence_p")), "Zone": v.get("zone")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def page_stress():
    alpha, method, start, end = SETTINGS
    st.title("Stress tests")
    rows, hyp, rev = F.stress_panel(PATH, PRICES, RETURNS, W, VALUE)
    st.caption(f"Historical crisis paths at NAV {usd(VALUE)}. 'As run' is the strategy path, including its month-end rebalances, from "
               "the scenario start close. 'Today's target, held' applies the current target buy-and-hold to the same days.")
    table = []
    for s in rows:
        p, h = s.get("path"), s["today_buy_hold"]
        table.append({"Scenario": s["scenario"], "Dates": f"{s['start']} to {s['end']}",
                      "As run: return": pct(p["return"]) if p else "n/a", "As run: USD": usd(-p["loss_usd"]) if p else "n/a",
                      "As run: largest fall": pct(-p["max_fall"]) if p else "n/a",
                      "Worst day": f"{p['worst_day']} ({pct(p['worst_day_return'])})" if p else "n/a",
                      "Today's target, held": pct(h["return"]) if h and h.get("status") == "ok" else "n/a",
                      "Held: largest fall": pct(-h["drawdown"]) if h and h.get("status") == "ok" else "n/a"})
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
    over = [s for s in rows if s.get("path") and s["today_buy_hold"] and s["today_buy_hold"].get("status") == "ok"
            and -s["today_buy_hold"]["drawdown"] > s["path"]["max_fall"]]
    if over:
        st.warning("Bought at the start of " + " and ".join(f"{s['scenario']} ({pct(-s['today_buy_hold']['drawdown'])} fall)" for s in over)
                   + " and left to drift, today's target would have fallen further than the strategy did as run ("
                   + ", ".join(pct(s["path"]["max_fall"]) for s in over) + "). The monthly rule cut risk as volatility rose; "
                   "a crash that arrives before the next month-end meets today's weights.")

    st.subheader("Which ETFs did the damage (as run, USD)")
    fig = go.Figure()
    for t in F.UNIVERSE:
        fig.add_trace(go.Bar(x=[s["scenario"] for s in rows], y=[s["path"]["pnl_usd"][t] for s in rows], name=t,
                             marker=dict(color=COLOR[t], cornerradius=4), hovertemplate=f"{t} %{{y:$,.0f}}<extra></extra>"))
    style(fig, 360, "USD profit (+) or loss (−)").update_layout(barmode="group", hovermode="closest")
    st.plotly_chart(fig.update_yaxes(tickformat="$,.0f"), width="stretch")
    gfc, covid, rates = (next(s["path"] for s in rows if s["scenario"] == n) for n in ("GFC", "COVID", "Rates 2022"))
    st.markdown(
        f"- **GFC:** bonds and gold offset most of the equity loss (AGG {usd(gfc['pnl_usd']['AGG'])}, GLD {usd(gfc['pnl_usd']['GLD'])}).\n"
        f"- **COVID:** every ETF lost money in the liquidity weeks; nothing diversified (AGG {usd(covid['pnl_usd']['AGG'])}).\n"
        f"- **2022:** bonds were the largest loss ({usd(rates['pnl_usd']['AGG'])}) and only energy gained ({usd(rates['pnl_usd']['XLE'])}). "
        "Bonds and gold diversify some crises, not all.")

    st.subheader("Hypothetical scenario: joint equity-bond shock")
    if hyp.get("status") == "ok":
        shocks = pd.DataFrame({"ETF": F.UNIVERSE, "Shock": [pct(hyp["shocks"][t]) for t in F.UNIVERSE],
                               "Weight": [pct(W[t]) for t in F.UNIVERSE], "USD loss": [usd(hyp["contributions_usd"][t]) for t in F.UNIVERSE]})
        c1, c2 = st.columns([2, 1])
        c1.dataframe(shocks, hide_index=True, width="stretch")
        c2.metric("Portfolio loss", usd(hyp["loss_usd"]), pct(hyp["return"]), delta_color="off")
        st.caption("SPY −25% and AGG −10% at once, gold unchanged; XLE's shock is the conditional mean given those, from the "
                   "covariance of SPY's worst 10% of days in 2005-2016. Deterministic: it has no estimated probability.")
    else:
        st.warning(f"Hypothetical scenario unavailable: {hyp.get('status')}")

    st.subheader("Design your own shock")
    presets = {"Frozen hypothetical": {t: hyp["shocks"][t] for t in F.UNIVERSE} if hyp.get("status") == "ok" else {t: 0. for t in F.UNIVERSE},
               "Energy collapse (illustrative)": {"SPY": -.10, "AGG": .03, "GLD": 0., "XLE": -.45},
               "Rate shock, worse than 2022 (illustrative)": {"SPY": -.25, "AGG": -.20, "GLD": -.10, "XLE": .10}}
    preset = st.selectbox("Start from", list(presets))
    cols = st.columns(4)
    shocks = {t: cols[i].slider(f"{t} shock %", -60, 60, int(round(100*presets[preset][t])), key=f"{preset}-{t}")/100
              for i, t in enumerate(F.UNIVERSE)}
    res = F.custom_shock(W, shocks, VALUE)
    st.metric("Portfolio result", usd(-res["loss_usd"]), pct(res["return"]), delta_color="off")
    st.caption("Computed in the app for the current target; an illustration, not part of the frozen evidence.")

    st.subheader("Reverse stress test")
    if rev["status"] == "ok":
        st.markdown(f"The smallest one-step joint shock (in covariance distance) that costs {pct(rev['loss_fraction'], 0)} of NAV: "
                    + " · ".join(f"{t} {pct(rev['shocks'][t])}" for t in F.UNIVERSE) +
                    f". Squared distance {rev['distance_squared']:.0f}; this is not a probability.")
    else:
        st.warning("Reverse stress optimisation did not converge.")


def page_contributions():
    alpha, method, start, end = SETTINGS
    st.title("Risk contributions and position sizing")
    contrib, tot = F.risk_contributions(RETURNS, W, alpha, VALUE)
    st.caption(f"Source: historical attribution, joint daily rows of the four ETFs 2005-2026, current target, {alpha:.0%} ES, "
               f"NAV {usd(VALUE)}. Volatility shares use the EWMA covariance the allocation rule uses. Portfolio-only models "
               "(FHS, GARCH-EVT) cannot split risk by ETF: attribution unavailable for them.")
    fig = go.Figure()
    for col, label, color in (("weight", "Share of money", "#c3c2b7"), ("vol_contribution", "Share of volatility", "#9ec3ef"),
                              ("es_share", f"Share of {alpha:.0%} ES", ACCENT)):
        fig.add_trace(go.Bar(x=F.UNIVERSE, y=contrib[col], name=label, marker=dict(color=color, cornerradius=4),
                             hovertemplate="%{x} %{y:.1%}<extra>" + label + "</extra>"))
    style(fig, 360).update_layout(barmode="group", hovermode="closest")
    st.plotly_chart(fig.update_yaxes(tickformat=".0%"), width="stretch")
    st.dataframe(pd.DataFrame({"ETF": F.UNIVERSE, "Weight": [pct(contrib.weight[t]) for t in F.UNIVERSE],
                               "ES contribution": [usd(contrib.es_usd[t]) for t in F.UNIVERSE],
                               "Share of ES": [pct(contrib.es_share[t]) for t in F.UNIVERSE],
                               "Marginal ES per USD 1m more": [usd(1e6*contrib.marginal_es_per_usd[t]) for t in F.UNIVERSE]}),
                 hide_index=True, width="stretch")
    st.markdown(f"Portfolio ES {usd(tot['es_usd'])}; contributions add up to it (residual {usd(tot['residual_usd'], 2)}). "
                f"Holding the four ETFs separately would give ES {usd(tot['es_usd']+tot['diversification_benefit_usd'])}: the "
                f"diversification benefit is {usd(tot['diversification_benefit_usd'])}.")
    top = contrib.es_share.idxmax()
    st.info(f"**Reading.** Risk parity equalises *volatility* (each about 25%), not *tail loss*. On the worst days {top} carries "
            f"{pct(contrib.es_share[top])} of the ES with {pct(W[top])} of the money, because energy and equities crash together. "
            "Moving money from XLE or SPY to AGG lowers ES the most per dollar moved.")
    st.subheader("Position sizing")
    m = contrib.marginal_es_per_usd
    st.markdown(f"Moving USD 1m from {m.idxmax()} to {m.idxmin()} changes 99% ES by about "
                f"{usd(-1e6*(m.max()-m.min()))} (first-order estimate from the marginal ES column; the rule's monthly reset "
                "would undo a manual change unless the rule itself is altered).")


def page_limits():
    st.title("Assumptions & Limitations")
    st.caption("What this analysis does not capture, in plain language.")
    test, _ = reserve(SH); r25 = test["results"][-1]
    reserve_line = (f"In a {r25['year']}-year test that resamples the strategy's own monthly returns, every cash reserve was paid in "
                    f"{pct(r25['all_payments_funded'])} of paths, but the USD 10m was kept in real terms in only "
                    f"{pct(r25['real_capital_preserved'])}: the reserve grows {pct(CFG['reserve_growth'], 2)} a year, faster than US CPI. "
                    "These are illustrations from one history, not forecasts.")
    backtest_line = ("- The breach counts of both risk models matched the 99% level, but the breaches came in clusters (independence "
                     "tests failed), mostly around the months the overlay switches. Under the team's own pre-registered rule this "
                     "is recorded as evaluation incomplete; the owner adopted v6 knowing it (31 October 2026, PLAN.md 13h)."
                     if V6 else
                     "- The backtest passed with GARCH-EVT, the backup model. The first-choice model (FHS) had breaches that came in "
                     "clusters, which means risk rose faster than the model expected at the start of sudden shocks.")
    overlay_block = ("""
**About the recession overlay**
- It uses the yield curve (inverted at some point in the last 24 months) confirmed by SPY below its 12-month average. The curve
  preceded every US recession since 1969 but also gave false alarms (1966, 2022); the price check filters most of them.
- Only two recessions (2008 and 2020) fall inside the 2005-2026 data, so the overlay's benefit rests mostly on economic reasoning
  and the 60-year signal record, not on many tested episodes.
- It holds cash (0%) while on. Cash is outside the brief's seven-ETF list; this is a disclosed policy choice.
- It does not help in an inflation shock without a recession, such as 2022.
- The rules were written in a session that had seen these crises; every number has a stated economic or published reason.
""" if V6 else "")
    st.markdown("""
**About the choice of portfolio**
- This strategy was chosen after many alternatives had been tried on the same 2005-2026 data. Every number here is hindsight:
  there is no untouched test period. Good past results may partly reflect that search.
- RESERVE_LINE

**About the risk numbers**
- VaR is not the most we can lose. It is a loss level that is exceeded about once in 100 days at 99%. Bigger losses happen.
- Expected Shortfall is the average of the bad days, not a cap. A worse day than any in the data is possible.
- All models learn from 2005-2026. A crisis unlike any in that period (for example, a long inflation decade) may not be captured.
- The extreme-value (EVT) estimate rests on a few hundred bad days and a threshold rule we chose. A different threshold gives a
  somewhat different answer (see the EVT page).
- The risk numbers assume today's weights are held for a day. Over weeks, losses compound and monthly rebalancing changes the
  weights; multi-day risk is not the one-day figure times a square root.
BACKTEST_LINE

OVERLAY_BLOCK
**About the portfolio**
- Risk parity balances everyday volatility. It does not balance crash losses: energy and US stocks carry most of the tail risk.
- Bonds did not protect in 2022, when stocks and bonds fell together. Gold helped in 2008 but not in March 2020.
- The weights change once a month. A shock that happens within a month (COVID took five weeks) is met with last month's weights.
- The covariance is estimated from recent data and can be wrong when relationships change suddenly.

**About implementation**
- Trading costs are assumed to be zero. Real costs, bid-ask spreads and market impact in a stressed month would
  lower returns a little (turnover is about 0.95× NAV a year).
- Adjusted closing prices from Yahoo Finance are used: dividends are reinvested, and fund fees are already in the prices.
- No taxes, currency effects, cash yield on the reserve or new contributions are modelled. The reserve itself is assumed paid out.
- Real returns use US CPI (FRED CPIAUCSL). That is US consumer inflation; a university's own costs (salaries, research,
  construction) can rise faster. CPI is a revised series with an approximate publication lag, not what was known at the time.

**About the data**
- Only seven ETFs are eligible and this portfolio uses four. Each ETF's history starts in 2005 in the frozen snapshot; earlier
  crises such as the 2000-2002 dot-com crash cannot be replayed with bonds and gold.
- Suspected data errors were flagged and kept, not deleted. Genuine crash days remain in the data.

**About human review**
- AI tools (Claude Code, Codex, Antigravity) helped write the code and documents. Independent human review of the calculations and the
  investment judgement is still pending, and solo entry eligibility has not been confirmed by the organisers.
""".replace("RESERVE_LINE", reserve_line).replace("BACKTEST_LINE", backtest_line).replace("OVERLAY_BLOCK", overlay_block))


def page_data():
    st.title("Data & provenance")
    meta = EV["meta"]; ST = meta.get("settings") or meta["strategy"]
    OV = ("\n- **Recession overlay (v6):** 10-year minus 3-month T-bill spread from FRED DGS10 and DTB3 (in the frozen raw data); "
          "SPY 12-month average from the frozen prices. Unemployment (UNRATE) and the Baa credit spread (BAA10Y) were supplied by "
          "the owner from FRED and are kept with SHA-256 hashes in `context/fred/` (tested, not used by the rule)." if V6 else "")
    st.markdown(f"""
- **Prices:** Yahoo Finance adjusted closes via yfinance, frozen snapshot to {CFG['snapshot_end']} (`data/clean/prices_clean.csv`,
  SHA-256 `{EV['data_hash'][:16]}…`). Trading calendars aligned; anomalies flagged, not deleted.
- **Risk-free rate:** FRED DTB3, converted from a discount basis to a bond-equivalent daily rate.
- **Inflation:** FRED CPIAUCSL (US CPI, all urban consumers), index ratios as available on each date; never the level as a rate.
- **Strategy evidence:** `results/{EV['run']}/` (pre-registered at tag `{meta['prereg_tag']}`, created {meta['created']}).
  Strategy hash `{SH}` on every forecast row; the dashboard refuses forecasts with another hash or a changed price file.
- **Settings:** EWMA λ = {ST['ewma_lambda']}, window {ST['window']} days, first target after
  {ST['min_history']} days, month-end decisions, universe SPY, AGG, GLD, XLE.{OV}
- **Settings read from** `config/final.yaml`: NAV, seed, Monte Carlo size, rolling window and refit interval.
- **Technical report:** `results/final-report-r1/technical_report.pdf`, built by `python -m quanedge.final_report` from the same
  evidence and calculations as this dashboard.
""")
    a = F.adf(PATH)
    st.subheader("Stationarity of the returns used for modelling")
    st.write(f"Augmented Dickey-Fuller on the strategy's daily log returns: statistic {a['statistic']:.2f}, p-value {a['p_value']:.1e}, "
             f"{a['lags']} lags, {a['observations']:,} observations. A unit root is rejected. That does not prove the distribution is "
             "constant over time; volatility clearly changes.")
    st.subheader("Reproduce")
    st.code("python -m pip install -r requirements.lock.txt\npython -m quanedge.data.run --check-only\n"
            "python -m quanedge.dynamic_parity_eval   # rebuilds results/dynamic-parity-r1 (v5 core)\n"
            "python -m quanedge.recession_overlay     # rebuilds results/recession-overlay-r1 (v6 final)\n"
            "python -m quanedge.universe              # rebuilds results/universe-r1 (why these four ETFs)\n"
            "python -m streamlit run dashboard.py")
    st.download_button("Download the daily strategy path (CSV)", PATH.to_csv().encode(), "final_portfolio_path.csv", "text/csv")
    st.download_button("Download the risk forecasts (CSV)", FC.to_csv().encode(), "final_portfolio_forecasts.csv", "text/csv")


def page_overlay():
    st.title("Recession overlay (part of the final model, v6)")
    o = overlay(EV["data_hash"])
    if "error" in o:
        st.error(f"The saved overlay evidence cannot be used: {o['error']}")
        st.code("python -m quanedge.recession_overlay")
        return
    ev, core, sig = o["ev"], o["core"], o["signals"]; path = ev["path"]; sm = ev["summary"]
    st.markdown("**Rule.** At each month-end, if the 10-year Treasury yield was below the 3-month T-bill yield in any of "
                "the last 24 months **and** SPY closes below its 12-month average, half of SPY and XLE is held as cash. "
                "It returns at the first month-end with SPY back above that average. Everything else is the monthly "
                "risk-parity strategy unchanged.")
    last = sig.iloc[-1]
    inv = sig.index[sig.spread < 0]
    c = st.columns(4)
    c[0].metric("Overlay at 30 Sep 2026", "ON" if path.overlay_on.iloc[-1] else "OFF")
    c[1].metric("Yield-curve warning", "ON" if last.warning else "OFF",
                help=f"Last inverted month: {inv[-1]:%b %Y}" if len(inv) else None)
    c[2].metric("SPY vs 12-month average", pct(last.spy/last.spy_12m_mean - 1), help="Below zero confirms the warning")
    c[3].metric("Sahm rule (backup)", f"{last.sahm_gap:+.2f} pt", help="Signals a recession at +0.50 points; not part of the rule")
    st.info("Status: adopted by the owner as part of the final model (v6, 31 October 2026). It reduced drawdowns; its risk "
            "forecasts matched the 99% breach count but the breaches clustered (below), which is disclosed.")

    st.subheader("Strategy with and without the overlay (from 2006-12-28)")
    g = (1 + path["return"]).cumprod()*VALUE; gc = (1 + core["return"]).cumprod()*VALUE
    fig = go.Figure()
    fig.add_scatter(x=gc.index, y=gc, name="Without overlay (v5 core)", line=dict(color=ALT))
    fig.add_scatter(x=g.index, y=g, name="With recession overlay", line=dict(color=ACCENT))
    on = path.overlay_on.astype(int).diff().fillna(path.overlay_on.iloc[0]).astype(int)
    for a, b in zip(path.index[on == 1], list(path.index[on == -1]) + [path.index[-1]]):
        fig.add_vrect(x0=a, x1=b, fillcolor="rgba(235,104,52,.15)", line_width=0)
    st.plotly_chart(style(fig, 380, "USD"), use_container_width=True)
    st.caption("Orange bands: months the overlay held cash. No costs; no reserve withdrawals; data to 30 Sep 2026.")

    def row(name, r, p):
        w = (1 + r).cumprod(); dd = w/w.cummax() - 1; yrs = (r.index[-1] - r.index[0]).days/365.25
        out = {"Strategy": name, "CAGR": pct(w.iloc[-1]**(1/yrs) - 1, 2), "Volatility": pct(r.std()*np.sqrt(252)),
               "Maximum decline": pct(-dd.min()), "Average cash": pct(p.cash.mean() if "cash" in p else 0)}
        for n, (a, b) in SCENARIOS.items():
            x = w.loc[a:b]; out[f"{n} (from peak)"] = pct((x/x.cummax() - 1).min())
        return out
    st.dataframe(pd.DataFrame([row("Without overlay (v5 core)", core["return"], core),
                               row("With recession overlay (v6, final)", path["return"], path)]).set_index("Strategy"), use_container_width=True)

    st.subheader("Risk-model backtest of the overlay path (99%, 2017-2026)")
    rows = []
    for v in sm["validation"]:
        if v["alpha"] == .99 and v["method"] in ("fhs", "garch_evt"):
            rows.append({"Model": LABEL[v["method"]], "Days": v["days"], "Breaches": v["breaches"],
                         "Expected": round(v["expected_breaches"], 1), "Kupiec p": p_text(v["kupiec_p"]),
                         "Independence p": p_text(v["independence_p"]), "Conditional coverage p": p_text(v["conditional_coverage_p"]),
                         "Zone": v["zone"]})
    st.dataframe(pd.DataFrame(rows).set_index("Model"), use_container_width=True)
    st.caption("Breach counts are close to expected, but breaches cluster (independence p below 0.05), mostly when the "
               "overlay switches. Forecast rows carry strategy hash " + ev["meta"]["strategy_hash"][:8] + ".")

    st.subheader("Signals")
    t1, t2, t3 = st.tabs(["Yield curve", "SPY trend", "Unemployment and credit (tested, not used)"])
    with t1:
        f = go.Figure(); f.add_scatter(x=sig.index, y=sig.spread, name="10y minus 3m", line=dict(color=ACCENT))
        f.add_hline(y=0, line_color=MUTED, line_dash="dot")
        st.plotly_chart(style(f, 300, "percentage points"), use_container_width=True)
        st.caption("Monthly mean of DGS10 minus the bond-equivalent DTB3 yield (FRED). Below zero: inverted. "
                   "Inversion preceded all 8 US recessions since 1969 (probit z = -3.7, 1962-2025).")
    with t2:
        f = go.Figure(); f.add_scatter(x=sig.index, y=sig.spy, name="SPY month-end", line=dict(color=COLOR["SPY"]))
        f.add_scatter(x=sig.index, y=sig.spy_12m_mean, name="12-month average", line=dict(color=MUTED, dash="dot"))
        st.plotly_chart(style(f, 300, "price"), use_container_width=True)
    with t3:
        f = go.Figure(); f.add_scatter(x=sig.index, y=sig.unemployment, name="Unemployment rate", line=dict(color=COLOR["AGG"]))
        f.add_scatter(x=sig.index, y=sig.credit_spread, name="Baa minus 10y", line=dict(color=COLOR["GLD"]))
        st.plotly_chart(style(f, 300, "percent"), use_container_width=True)
        st.caption("Sahm rule confirmed 6 of 8 recessions 2-9 months after they began and added nothing in 2005-2026. "
                   "Unemployment levelling off came after the stock bottom (or falsely, in 2008), so it is not used to re-enter. "
                   "The credit spread above its 12-month average was on in 143 non-recession months. "
                   "Files supplied by the owner from FRED (context/fred, hashed).")


SETTINGS = None
pages = [st.Page(page_decision, title="Decision", default=True, url_path="decision"),
         st.Page(page_portfolio, title="Portfolio", url_path="portfolio"),
         st.Page(page_risk, title="Risk: VaR, ES, EVT", url_path="risk"),
         st.Page(page_evt, title="EVT tail", url_path="evt"),
         st.Page(page_backtest, title="Backtesting", url_path="backtest"),
         st.Page(page_stress, title="Stress tests", url_path="stress"),
         st.Page(page_contributions, title="Risk contributions", url_path="contributions"),
         st.Page(page_overlay, title="Recession overlay", url_path="overlay"),
         st.Page(page_limits, title="Assumptions & Limitations", url_path="limitations"),
         st.Page(page_data, title="Data & provenance", url_path="data")]
nav = st.navigation(pages)
SETTINGS = sidebar()
nav.run()
