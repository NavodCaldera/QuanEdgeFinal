"""Investment committee dashboard for the final portfolio (v6): monthly dynamic EWMA risk parity with a recession overlay.

Start: python -m streamlit run dashboard.py
Calculations live in quanedge/final_portfolio.py; this file only arranges and labels them.
"""
import json
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
    if x is None or not np.isfinite(x):
        return "n/a"
    return f"USD {(0. if round(x, d) == 0 else x):,.{d}f}"           # no "USD -0"


def money(x):
    """Compact USD for metric tiles: USD 9.60m, USD 155k."""
    if x is None or not np.isfinite(x):
        return "n/a"
    return f"USD {x/1e6:.2f}m" if abs(x) >= 1e6 else f"USD {x/1e3:,.0f}k"


def pct(x, d=1):
    return "n/a" if x is None or not np.isfinite(x) else f"{100*x:.{d}f}%"


def p_text(p):
    return "n/a" if p is None else f"{p:.3f}"


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
def load():
    ev = F.load_evidence()
    prices, returns, rf, cpi = F.load_market()
    return ev, prices, returns, rf, cpi


@st.cache_resource(show_spinner="Fitting the risk models")
def risk(data_hash, start, end, weights_key, settings_key):
    weights = dict(weights_key)
    return F.risk_now(RETURNS, weights, json.loads(settings_key)["value"], start, end)


@st.cache_resource(show_spinner="Bootstrapping the risk estimates")
def intervals(data_hash, weights_key, settings_key):
    return F.bootstrap(RETURNS, dict(weights_key), json.loads(settings_key)["value"], cfg=json.loads(settings_key))


@st.cache_resource(show_spinner="Measuring what each ETF adds")
def universe(data_hash):
    return U.load_saved(data_hash) or U.evidence(*U.load())


@st.cache_resource(show_spinner="Splitting risk by ETF")
def attribution_set(data_hash, strategy_hash, weights_key, alpha, settings_key):
    """Every number on the Risk contributions page, for one weight vector and confidence."""
    w, value, seed = dict(weights_key), json.loads(settings_key)["value"], json.loads(settings_key)["seed"]
    contrib, tot = F.risk_contributions(RETURNS, w, alpha, value)
    return {"contrib": contrib, "tot": tot, "cvar": F.component_var(RETURNS, w, alpha, value),
            "swaps": F.swap_table(RETURNS, w, alpha, value), "robust": F.share_robustness(RETURNS, w, value),
            "boot": F.share_bootstrap(RETURNS, w, alpha, value, seed=seed), "mc": F.mc_t_shares(RETURNS, w, alpha, value, seed=seed),
            "crisis": F.crisis_attribution(PATH, RETURNS, value), "history": F.share_history(PATH, RETURNS, alpha, value),
            "tilt": F.tilt_table(RETURNS, w, alpha, value)}


@st.cache_resource(show_spinner="Building the benchmarks")
def benchmark_set(data_hash, strategy_hash, policy_key):
    return F.benchmarks(PATH, RETURNS, json.loads(policy_key))


@st.cache_resource(show_spinner="Simulating 25 years of cash reserves")
def reserve(data_hash, policy_key):
    cfg = json.loads(policy_key)
    return F.reserve_test(PATH, cfg), F.reserve_history(PATH, CPI, cfg)


def target_losses(weights_key):
    from quanedge.risk.portfolio import portfolio_log_returns
    return -portfolio_log_returns(np.log1p(RETURNS[F.UNIVERSE]), dict(weights_key)).to_numpy()


@st.cache_resource(show_spinner="Scanning EVT thresholds")
def evt_scan(data_hash, weights_key, settings_key, alpha):
    return F.evt_scan(target_losses(weights_key), json.loads(settings_key)["value"], alpha)


@st.cache_resource(show_spinner="Building the refitted QQ envelope")
def evt_qq(data_hash, weights_key, settings_key):
    models, _ = risk(data_hash, None, None, weights_key, settings_key)
    return F.gpd_qq(models["evt"].fit, target_losses(weights_key), reps=200, seed=json.loads(settings_key)["seed"])


@st.cache_resource(show_spinner="Fitting EVT to the strategy path")
def evt_strategy(data_hash, strategy_hash):
    return F.strategy_evt(PATH)


@st.cache_resource(show_spinner="Loading the recession-overlay evidence")
def overlay(data_hash):
    try:
        ev = RO.load_saved()
    except (RO.OverlayEvidenceError, FileNotFoundError, KeyError) as err:
        return {"error": str(err)}
    return {"ev": ev, "core": RO.core_path(), "signals": RO.signals(CFG["snapshot_end"])}


try:
    EV, PRICES, RETURNS, RF, CPI = load()
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
DATA_START = PRICES.index[0]
DATA_SPAN = f"{DATA_START:%B %Y} to {pd.Timestamp(CFG['snapshot_end']):%B %Y}"
WKEY = tuple(sorted(W.items()))
RISK_KEY = json.dumps({k: CFG[k] for k in ("value", "n_sim", "seed", "bootstrap_reps", "bootstrap_block", "snapshot_end")}, sort_keys=True)
FIRST_FC, LAST_FC = FC.index[0].date(), FC.index[-1].date()
ESTIMATION = {f"Full sample, {RETURNS.index[0].date()} to {CFG['snapshot_end']}": (None, None),
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
def clustering(v):
    p = v.get("conditional_coverage_p")
    return "" if p is None else ", breaches cluster" if p <= .05 else ""


def monitoring_note(ge, fhs):
    """The two conditional models' 99% backtest statistics, 2017-2026, from the saved results."""
    def one(name, v):
        return (f"{name} {v['breaches']} breaches, Kupiec p {v['kupiec_p']:.2f}, conditional coverage p "
                f"{v['conditional_coverage_p']:.3f}, {v['zone']} zone{clustering(v)}")
    return f"2017-2026 backtests at 99%: {one('GARCH-EVT', ge)}; {one('FHS', fhs)}."


def headline(alpha):
    models, table = risk(EV["data_hash"], None, None, WKEY, RISK_KEY)
    row = lambda m: table[(table.method == m) & np.isclose(table.alpha, alpha)].iloc[0]
    return models, table, row


# ---------------------------------------------------------------- pages
def page_decision():
    alpha, method, start, end = SETTINGS
    st.title("Final portfolio: monthly dynamic risk parity with recession overlay")
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
    c[4].metric(f"Maximum fall since {PATH.index[0].year}", pct(-perf["maximum_drawdown"]), help="Largest fall from a previous high, strategy as run.")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Allocation to hold now")
        contrib, _ = F.risk_contributions(RETURNS, W, .99, VALUE)
        frame = pd.DataFrame({"ETF": [NAME[t] for t in F.UNIVERSE], "Weight": [pct(W[t]) for t in F.UNIVERSE],
                              "USD": [f"{W[t]*VALUE:,.0f}" for t in F.UNIVERSE],
                              "Vol. share": [pct(contrib.vol_contribution[t]) for t in F.UNIVERSE],
                              "ES share": [pct(contrib.es_share[t]) for t in F.UNIVERSE]})
        st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Recession overlay at the last close: " + ("**ON**: half of SPY and XLE held as cash." if PATH.overlay_on.iloc[-1]
                   else "**off** (no yield-curve warning confirmed by SPY below its 12-month average). See the Recession overlay page."))
        st.caption(f"Target set at the {PATH.index[-1].date()} close from data up to that close; next review at the "
                   "next month-end close. Each ETF carries a quarter of the expected volatility, but XLE and SPY carry most "
                   "of the tail loss.")
    with right:
        st.subheader("Key evidence")
        ge = next(v for v in SUMMARY["validation"] if v["method"] == "garch_evt" and v["alpha"] == .99)
        fhs = next(v for v in SUMMARY["validation"] if v["method"] == "fhs" and v["alpha"] == .99)
        ev = [("Return since " + SUMMARY["start"], f"{pct(perf['cagr'], 2)} a year"),
              ("Real return (US CPI)", f"{pct(perf['real_cagr'], 2)} a year after {pct(perf['cpi_inflation'], 2)} average CPI inflation "
               f"({DATA_START:%d %b %Y} to {CFG['snapshot_end']})"),
              ("Volatility", f"{pct(perf['annual_volatility'], 1)} a year"),
              ("Largest fall", f"{pct(-perf['maximum_drawdown'])}"),
              ("99% VaR backtest, GARCH-EVT", f"{ge['breaches']} breaches, "
               f"Kupiec p {ge['kupiec_p']:.2f}, cond. coverage p {ge['conditional_coverage_p']:.3f}, {ge['zone']}{clustering(ge)}"),
              ("99% VaR backtest, FHS", f"{fhs['breaches']} breaches, Kupiec p {fhs['kupiec_p']:.2f}, cond. coverage p "
               f"{fhs['conditional_coverage_p']:.3f}, {fhs['zone']}{clustering(fhs)}"),
              ("Hypothetical equity-bond shock", f"{usd(hyp['loss_usd'])} ({pct(-hyp['return'])})")]
        test, _ = reserve(EV["data_hash"], json.dumps(CFG, sort_keys=True)); r25 = test["results"][-1]
        ev.append((f"{r25['year']}-year cash-reserve test", f"every reserve paid in {pct(r25['all_payments_funded'])} of resampled paths; "
                   f"USD 10m kept in real terms in {pct(r25['real_capital_preserved'])}"))
        st.markdown("\n".join(f"- **{k}:** {v}" for k, v in ev))
        st.caption("Backtests 2017-01-03 to 2026-09-30 on the strategy's own forecasts; returns are a retrospective evaluation.")
        st.caption(f"Reserve test: USD {CFG['reserve_initial']:,.0f} paid at the beginning of year 1; "
                   f"payments and simulation inflation both grow at {pct(CFG['inflation'], 2)} a year, the average US CPI "
                   f"inflation from {DATA_START:%d %B %Y} to {CFG['snapshot_end']} (FRED CPIAUCSL). Over the strategy's own dates "
                   f"({PATH.index[0].date()} on) CPI rose {pct(perf['path_cpi_inflation'], 2)} a year.")

    why_four(contrib.es_share)

    latest = F.latest_forecast(FC, "garch_evt", .99, VALUE)
    st.subheader("Recommendation to the committee")
    st.markdown(
        "**Hold this portfolio**, monitored as follows. This is the team's proposal for the owner's and committee's review.\n\n"
        f"1. **Hold** the current target and reset it at every month-end close by the rule on the Portfolio page "
        "and the recession overlay (half of SPY and XLE to cash while the yield curve has been inverted in the last 24 months "
        "and SPY is below its 12-month average).\n"
        f"2. **Daily risk:** measure 99% one-day risk with GARCH-EVT refitted as in its backtest (latest forecast, for "
        f"{latest['date']}: VaR {usd(latest['var_usd'])}). {monitoring_note(ge, fhs)}\n"
        f"3. **Review triggers:** an extra committee review if the fall from the previous high exceeds 15% (the largest so far "
        f"was {pct(-perf['maximum_drawdown'])}) or if 99% VaR breaches exceed 9 in any 250 days (Basel red zone).\n"
        f"4. **Expectation setting:** the real return has been about {pct(perf['real_cagr'], 1)} a year after "
        f"{pct(CFG['inflation'], 2)} average US CPI inflation. "
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
        st.markdown(f"- GARCH-EVT 99% forecasts: {ge['breaches']} breaches, "
                    f"2017-2026 ({ge['zone']}{clustering(ge)}). FHS: {fhs['breaches']}{clustering(fhs)}.\n- EVT tail shape ξ = {xi['xi']:.2f} "
                    f"± {1.96*xi['xi_se']:.2f}: a fat tail, estimated from {xi['n_exceed']} days.\n- All of this is history the "
                    "strategy was chosen after seeing; there is no untouched test period.")


def energy_bond():
    """Fundamentals tab: XLE moves against AGG, one of the main reasons XLE is held."""
    u = universe(EV["data_hash"])
    s = u["energy_bond"].set_index("measure")["value"]; y = u["energy_bond_years"].set_index("year")
    recent = y.loc[2020:]
    st.markdown("#### Energy and bonds: why XLE sits beside AGG")
    st.markdown(
        "Bonds lose when interest rates and inflation rise. Energy companies earn more in exactly those conditions, because "
        "oil and gas prices are a main driver of inflation and higher prices raise their profits. So XLE tends to move against "
        f"AGG: its daily correlation with AGG is {s['Daily correlation with AGG: XLE']:+.2f}, the most negative of the six "
        f"eligible ETFs other than AGG, and it was negative in {int(s['Negative years with AGG since 2020: XLE'])} of the "
        f"{int(s['Years since 2020'])} years since 2020, against at most "
        f"{max(int(s[f'Negative years with AGG since 2020: {t}']) for t in ('SPY', 'EFA', 'EEM', 'XLK', 'GLD'))} for any other. "
        "That is one of the main reasons the portfolio holds it: AGG is about half of the money, and XLE is the holding most "
        "likely to gain when AGG falls.")
    c = st.columns(5)
    c[4].metric("Months below -0.5", f"{int(s['Months below -0.5'])}", help="Within-month correlation of daily log returns.")
    c[0].metric("Years XLE-AGG negative", f"{int(s['Years with negative correlation'])} of {int(s['Years'])}",
                help="Correlation of daily log returns within each calendar year.")
    c[1].metric("Months negative", f"{int(s['Months with negative correlation'])} of {int(s['Months'])}",
                help="Correlation of daily log returns within each calendar month.")
    c[2].metric("XLE, rate-shock months", pct(s["Mean monthly return in rate-shock months: XLE"], 1),
                f"AGG {pct(s['Mean monthly return in rate-shock months: AGG'], 1)}", delta_color="off",
                help=f"Average monthly return in the {int(s['Rate-shock months (10y yield +0.25 pt)'])} months when the 10-year "
                     "Treasury yield rose more than 0.25 points.")
    c[3].metric("XLE in 2022", pct(y.loc[2022, "XLE return"], 0), f"AGG {pct(y.loc[2022, 'AGG return'], 0)}", delta_color="off",
                help="Calendar-year buy-and-hold returns, adjusted closes.")
    fig = go.Figure([go.Bar(x=y.index, y=y["XLE-AGG"], name="XLE-AGG", marker=dict(color=COLOR["XLE"], cornerradius=3)),
                     go.Scatter(x=y.index, y=y["SPY-AGG"], name="SPY-AGG", mode="lines+markers",
                                line=dict(color=COLOR["SPY"], width=2), marker=dict(size=6))])
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
    st.plotly_chart(style(fig, 280, "Correlation with AGG").update_layout(hovermode="x unified")
                    .update_yaxes(tickformat=".1f"), width="stretch")

    mo = u["energy_bond_months"]; strong = mo[mo["XLE-AGG"] < -.5]
    opposite = int(((strong["XLE return"]*strong["AGG return"]) < 0).sum())
    st.markdown(
        f"**Months of strongly negative correlation.** In {int(s['Months below -0.5'])} months the within-month correlation "
        f"was below -0.5, and in {int(s['Months below -0.3'])} below -0.3. The strongest:")
    top = mo.head(10).assign(**{"XLE-AGG": lambda d: d["XLE-AGG"].map(lambda x: f"{x:.2f}"),
                                "XLE return": lambda d: d["XLE return"].map(lambda x: f"{100*x:+.1f}%"),
                                "AGG return": lambda d: d["AGG return"].map(lambda x: f"{100*x:+.1f}%")})
    st.dataframe(top.rename(columns={"month": "Month", "XLE-AGG": "Correlation"}), hide_index=True, width="stretch")
    def example(mask):
        x = strong[mask].head(2)
        return " and ".join(f"{pd.Period(m).strftime('%B %Y')} (XLE {100*a:+.1f}%, AGG {100*b:+.1f}%)"
                            for m, a, b in zip(x["month"], x["XLE return"], x["AGG return"]))
    st.caption(f"In those {len(strong)} months XLE and AGG ended the month with opposite signs {opposite} times. A negative "
               "correlation means their daily moves offset each other, either way round: XLE up while AGG fell, as in "
               f"{example((strong['XLE return'] > 0) & (strong['AGG return'] < 0))}, or XLE down while AGG rose, as in "
               f"{example((strong['XLE return'] < 0) & (strong['AGG return'] > 0))}. Both help a portfolio that holds the two. "
               "It does not mean XLE gains whenever bonds lose.")
    with st.expander(f"All {len(strong)} months below -0.5"):
        st.dataframe(strong.assign(**{"XLE-AGG": lambda d: d["XLE-AGG"].round(2),
                                      "XLE return": lambda d: (100*d["XLE return"]).round(1),
                                      "AGG return": lambda d: (100*d["AGG return"]).round(1)})
                     .rename(columns={"month": "Month", "XLE-AGG": "Correlation", "XLE return": "XLE return %",
                                      "AGG return": "AGG return %"}), hide_index=True, width="stretch")
    st.markdown(
        f"- **When bonds had their worst days** (AGG's worst 5%, {int(s['AGG worst 5% days'])} days): XLE averaged "
        f"{pct(s['Mean daily return on AGG worst 5% days: XLE'], 2)} a day, while GLD lost "
        f"{pct(-s['Mean daily return on AGG worst 5% days: GLD'], 2)} and SPY {pct(-s['Mean daily return on AGG worst 5% days: SPY'], 2)}.\n"
        f"- **Since 2020 SPY no longer does this job.** The stock-bond correlation turned positive (SPY-AGG "
        f"{recent['SPY-AGG'].mean():+.2f} on average over 2020-2026, {y.loc[y.index.max(), 'SPY-AGG']:+.2f} in {y.index.max()}), "
        f"while XLE-AGG stayed mostly negative ({recent['XLE-AGG'].mean():+.2f} on average, "
        f"{y.loc[y.index.max(), 'XLE-AGG']:+.2f} in {y.index.max()}). In 2022, the year stocks and bonds fell together, XLE was "
        "the only one of the four that gained.\n"
        f"- **The relationship is real but modest.** Over the full period the daily correlation is only "
        f"{s['Daily correlation, full sample']:+.2f}, and it was positive in some years (2020, 2022). XLE is an energy-equity "
        f"fund, not a bond hedge in a crash: it fell {pct(-u['crises'].set_index('etf').loc['XLE', 'GFC return'], 0)} in the GFC "
        f"and {pct(-u['crises'].set_index('etf').loc['XLE', 'COVID return'], 0)} in COVID, when AGG held up.")
    st.caption(f"Daily log returns, adjusted closes, {u['start']} to {u['end']}; {y.index.min()} has {int(y.loc[y.index.min(), 'days'])} days and "
               f"{y.index.max()} runs to {u['end']}. Rate shocks use FRED DGS10 month-end changes. Descriptive and retrospective: "
               "correlations change over time and are not a forecast.")


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
    eb = u["energy_bond"].set_index("measure")["value"]

    st.subheader("Why these four ETFs")
    st.markdown(
        f"Each of the four responds to a different economic condition, so together they cover the four conditions an endowment "
        f"must live through: growth, recession, inflation and a loss of confidence. EFA, EEM and XLK are a second, third and "
        f"fourth copy of the same equity risk as SPY. Adding all three raises the number of independent bets only from "
        f"**{four.effective_bets:.2f} to {seven.effective_bets:.2f}**, and in risk parity it would move the equity share "
        f"of risk from {pct(st_.loc['Four ETFs', 'equity_risk_share'], 0)} to {pct(st_.loc['All seven ETFs', 'equity_risk_share'], 0)}.")
    cards = {
        "SPY": ("Growth", f"Return engine: {pct(cr.loc['SPY', 'annual return, full period'])} a year since {DATA_START:%B %Y}."),
        "AGG": ("Recession", f"Gained {pct(cr.loc['AGG', 'GFC return'])} in the GFC; {pct(stress['AGG'], 1)} a month in equity-stress "
                             f"months, when every equity ETF lost about {pct(-stress['SPY'], 0)}."),
        "GLD": ("Loss of confidence", f"Gained {pct(cr.loc['GLD', 'GFC return'])} in the GFC and {pct(stress['GLD'], 1)} a month in "
                                      "equity-stress months; correlation with SPY "
                                      f"{corr.loc['GLD', 'SPY']:.2f}."),
        "XLE": ("Inflation, against bonds", f"The only ETF that gained in 2022 ({pct(cr.loc['XLE', 'Rates 2022 return'])}); "
                                            f"{pct(shock['XLE'], 1)} a month when the 10-year yield jumped, AGG {pct(shock['AGG'], 1)}; "
                                            f"moved against AGG in {int(eb['Years with negative correlation'])} of "
                                            f"{int(eb['Years'])} years."),
    }
    for col, t in zip(st.columns(4), F.UNIVERSE):
        title, text = cards[t]
        with col.container(border=True):
            st.markdown(f"**{t}** · {title}")
            st.caption(text)

    tabs = st.tabs(["Economic roles", "Fundamentals", "Overlap (technical)", "Seven-ETF test", "What this does not prove"])
    with tabs[0]:
        st.markdown(f"Average **monthly** return of each ETF in four macro conditions, {DATA_SPAN}. Held ETFs first.")
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
        energy_bond()
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
            f"- **Chosen after seeing the data.** The four-ETF rule was written on 30 October 2026 with {DATA_START.year}-2026 correlations in "
            "view (PLAN.md 13c). Everything above is retrospective.\n"
            f"- **XLE is not a low-correlation asset.** Its correlation with SPY is {corr.loc['XLE', 'SPY']:.2f}, "
            f"{u['stress_correlation'].loc['XLE', 'SPY']:.2f} on SPY's worst days; it fell {pct(-cr.loc['XLE', 'COVID return'])} in "
            f"COVID and carries {pct(es_share['XLE'])} of today's 99% ES with {pct(W['XLE'])} of the money. It is held for "
            "inflation protection; risk parity sizes it by volatility, not by tail loss.\n"
            f"- **Excluding XLK gave up return.** XLK earned {pct(cr.loc['XLK', 'annual return, full period'])} a year, the most of the "
            "seven; the seven-ETF rule had the higher CAGR. The case for leaving it out is concentration and drawdown, not return.\n"
            "- **Correlations move.** SPY-AGG was negative 2007-2019 and positive from 2020; bonds did not protect in 2022.\n"
            "- **Policy, not a brief rule.** The brief allows any combination of the seven ETFs; holding four is our choice.")


def page_portfolio():
    _, _, start, end = SETTINGS
    st.title("Portfolio")
    st.caption("Monthly dynamic EWMA risk parity; month-end targets, holdings drift between resets. "
               "Recession overlay: half of SPY and XLE in cash in months it is on (target charts show the risk-parity targets "
               "before the overlay; holdings and returns include it). "
               "Investment performance is before university payments and uses zero trading cost unless stated.")
    period = st.radio("Period", [f"Full history (from {PATH.index[0].date()})", "Backtest date range from the sidebar"], horizontal=True)
    a, b = (None, None) if period.startswith("Full") else (start, end)
    path = PATH.loc[a:b]
    if len(path) < 2:
        st.warning("The chosen date range has fewer than two days of history."); return
    r = path["return"]
    annual_ok = len(r) >= 63
    ratio = lambda v: "n/a" if v is None or not np.isfinite(v) else f"{round(v, 2)+0.:.2f}"
    annual = lambda v, fmt=pct: fmt(v) if annual_ok else "n/a (under 3 months)"
    catalog = benchmark_set(EV["data_hash"], SH, json.dumps(CFG, sort_keys=True))
    available = {n: item for n, item in catalog.items() if item[0] is not None}
    for n, (w, why) in catalog.items():
        if w is None:
            st.warning(f"{n}: {why}")
    chosen = st.multiselect("Benchmarks to compare", list(available), default=list(available))
    # All comparisons continue their original full-history holdings and trade dates.
    full_frames = {n: F.benchmark_frame(w, RETURNS, PATH.index[0], PATH.index[-1])
                   for n, (w, _) in available.items()}
    frames = {n: F.benchmark_window(full_frames[n], a, b) for n in chosen}
    bench = {n: f["return"] for n, f in frames.items()}
    k = F.page_kpis(r, RF, RETURNS.SPY, CPI, CFG)
    if k.get("status"):
        st.warning(k["status"]); return
    years = (r.index[-1]-r.index[0]).days/365.25
    k["rebalances"] = int(path.rebalanced.astype(bool).sum())
    k["turnover_per_year"] = float(path.turnover.sum()/years)
    kb = {n: F.page_kpis(x, RF, RETURNS.SPY, CPI, CFG) for n, x in bench.items()}
    rel = {n: F.relative(r, x) for n, x in bench.items()}
    cols = st.columns(4)
    cols[0].metric("Annualised return (CAGR)", annual(k["cagr"], lambda x: pct(x, 2)))
    cols[1].metric("Annualised volatility", pct(k["annual_volatility"], 2))
    cols[2].metric("Maximum drawdown", pct(-k["maximum_drawdown"]))
    cols[3].metric("Longest time under water", f"{k['max_underwater_days']:,} trading days")
    if len(r) < 252:
        st.caption(f"Only {len(r)} trading observations are shown. Annualised figures are unstable over short periods; "
                   "return ratios and annualised returns are hidden below 63 observations (approximately three months).")
    if chosen:
        if annual_ok:
            reference = chosen[0]
            highest = max(chosen, key=lambda n: kb[n]["cagr"])
            st.info(f"**Observed comparison, {r.index[0].date()} to {r.index[-1].date()}.** "
                    f"Against {reference}: CAGR {100*rel[reference]['cagr_diff']:+.2f} pp, volatility "
                    f"{100*(k['annual_volatility']-kb[reference]['annual_volatility']):+.2f} pp; maximum drawdown "
                    f"{pct(-k['maximum_drawdown'])} vs {pct(-kb[reference]['maximum_drawdown'])}. "
                    f"Highest CAGR among the displayed benchmarks: {highest} ({pct(kb[highest]['cagr'], 2)}); "
                    f"final portfolio {pct(k['cagr'], 2)}.")
        else:
            st.info(f"**Observed comparison, {r.index[0].date()} to {r.index[-1].date()}.** "
                    f"Portfolio cumulative return {pct(k['cumulative_return'])}; maximum drawdown "
                    f"{pct(-k['maximum_drawdown'])}. Annualised return comparisons are hidden for this short period.")
    else:
        st.info("Only the final portfolio is shown. Select benchmarks above to compare their results.")
    st.caption("These are descriptive historical comparisons. Small measured gaps do not establish superiority; "
               "no statistical-significance claim is made. Full-sample fitted comparisons benefited from hindsight.")

    colors = dict(zip(catalog, ("#8a8984", "#1baf7a", "#eb6834", "#9b59b6")))
    dashes = dict(zip(catalog, ("solid", "dash", "dot", "dashdot")))
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader(f"Latest target, set {PATH.index[-1].date()} close")
        fig = go.Figure(go.Bar(x=[W[t] for t in F.UNIVERSE], y=[NAME[t] for t in F.UNIVERSE], orientation="h",
                               marker=dict(color=[COLOR[t] for t in F.UNIVERSE], cornerradius=4),
                               text=[pct(W[t]) for t in F.UNIVERSE], textposition="outside",
                               customdata=[W[t]*VALUE for t in F.UNIVERSE],
                               hovertemplate="%{y}: %{x:.1%} · %{customdata:$,.0f}<extra></extra>"))
        style(fig, 300, legend=False).update_xaxes(tickformat=".0%", range=[0, min(1., max(W.values())*1.25)])
        fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        st.caption("This latest target is independent of the historical date filter. Positions are held between resets, "
                   "so their weights drift with prices.")
        if a is not None:
            pos = PATH.index.get_loc(path.index[0])
            opening = (PATH.iloc[pos-1][F.UNIVERSE].to_dict() if pos > 0 else SUMMARY["initial_target"])
            st.caption(f"Opening holdings before the {path.index[0].date()} return: "
                       + ", ".join(f"{t} {pct(opening[t])}" for t in F.UNIVERSE) + ".")
    with c2:
        st.subheader("Allocation history")
        allocation_view = st.radio("Allocation series", ["Target weights", "Actual holdings after each close"], horizontal=True)
        if allocation_view == "Target weights":
            hist = F.target_history(path)
            if hist.index[-1] != path.index[-1]:
                hist.loc[path.index[-1]] = [path[f"target_{t}"].iloc[-1] for t in F.UNIVERSE]
            hist = hist.sort_index(); shape = "hv"
        else:
            hist = path[F.UNIVERSE]; shape = "linear"
        fig = go.Figure()
        for t in F.UNIVERSE:
            fig.add_trace(go.Scatter(x=hist.index, y=hist[t], name=t, stackgroup="w",
                                     line=dict(width=.5, color=COLOR[t], shape=shape),
                                     hovertemplate=f"{t} %{{y:.1%}}<extra></extra>"))
        st.plotly_chart(style(fig, 300, "Allocation weight").update_yaxes(tickformat=".0%", range=[0, 1]), width="stretch")
        st.caption("Targets step at decision closes. Actual end-of-day holdings also reflect price moves between resets; "
                   "targets decided at a close apply to subsequent returns.")

    st.subheader(f"Investment growth of {usd(VALUE)} before university withdrawals")
    wealth = F.wealth_usd(r, VALUE)
    fig = go.Figure([go.Scatter(x=wealth.index, y=wealth, name="Final portfolio", line=dict(color=ACCENT, width=2.5))])
    for n in chosen:
        bw = F.wealth_usd(bench[n], VALUE)
        fig.add_trace(go.Scatter(x=bw.index, y=bw, name=n, line=dict(color=colors[n], width=1.5, dash=dashes[n])))
    shade_crises(fig, wealth.index[0], wealth.index[-1])
    st.plotly_chart(style(fig, 380, "USD before withdrawals").update_yaxes(tickformat=",.0f"), width="stretch")
    st.caption("Both portfolio and benchmarks continue their full-history allocations; only their displayed investment "
               "growth is rebased to the same starting amount. Date filtering creates no new benchmark trades.")

    st.subheader("Fund balance after university payments")
    all_ledgers = {"Final portfolio": F.reserve_ledger(PATH["return"], CFG),
                   **{n: F.reserve_ledger(full_frames[n]["return"], CFG) for n in chosen}}
    views = {n: F.reserve_window(ledger, r.index[0], r.index[-1]) for n, ledger in all_ledgers.items()}
    payment_dates = all_ledgers["Final portfolio"].index[all_ledgers["Final portfolio"].required_payment > 0]
    if views["Final portfolio"].empty or not len(payment_dates) or r.index[-1] < payment_dates[0]:
        st.info("The spending replay begins in the strategy's first full calendar year. This selected period ends before it starts.")
    else:
        fig = go.Figure()
        for n, view in views.items():
            if not view.empty:
                fig.add_trace(go.Scatter(x=view.index, y=view.balance, name=n,
                    line=dict(color=ACCENT if n == "Final portfolio" else colors[n],
                              width=2.5 if n == "Final portfolio" else 1.5,
                              dash="solid" if n == "Final portfolio" else dashes[n])))
        st.plotly_chart(style(fig, 380, "USD remaining after payments").update_yaxes(tickformat=",.0f"), width="stretch")
        ledger = all_ledgers["Final portfolio"].loc[:r.index[-1]]
        inception = ledger.index[ledger.required_payment > 0][0]
        st.caption(f"The fund starts with {usd(CFG['fund_value'])} in the first full calendar year ({inception.date()}). "
                   f"The first {usd(CFG['reserve_initial'])} payment is deducted before that day's return; later payments "
                   f"grow {pct(CFG['reserve_growth'], 2)} each year and are paid before the first trading day's return. "
                   "Date filtering zooms this existing fund history: balances and payment years do not restart or rebase. "
                   "Payments are cash leaving the fund, not investment losses.")
        st.caption(f"After paying the reserves, final portfolio balance at {r.index[-1].date()}: "
                   f"{usd(views['Final portfolio'].balance.iloc[-1])}. Investment drawdown and KPIs below exclude withdrawals.")
        problems = []
        for n, ledger in all_ledgers.items():
            for date, row in ledger.loc[:r.index[-1]].query("shortfall > 0.000001").iterrows():
                problems.append({"Portfolio": n, "Payment date": date.date(), "Required USD": row.required_payment,
                                 "Paid USD": row.paid_payment, "Shortfall USD": row.shortfall})
        if problems:
            st.warning("At least one scheduled university payment could not be funded in full. Depleted balances remain zero.")
            st.dataframe(pd.DataFrame(problems), hide_index=True, width="stretch")

    st.subheader("Investment drawdown from the previous high")
    dd = F.drawdown(wealth)
    fig = go.Figure([go.Scatter(x=dd.index, y=dd, name="Final portfolio", fill="tozeroy", line=dict(color=ACCENT, width=1.5))])
    for n in chosen:
        fig.add_trace(go.Scatter(x=dd.index, y=F.drawdown(F.wealth_usd(bench[n], VALUE)).reindex(dd.index), name=n,
                                 line=dict(color=colors[n], width=1, dash=dashes[n])))
    shade_crises(fig, dd.index[0], dd.index[-1])
    st.plotly_chart(style(fig, 300, "Drawdown before withdrawals").update_yaxes(tickformat=".0%"), width="stretch")
    st.caption("Drawdown is measured from the high within the selected view, including its opening value; it excludes university payments.")

    st.subheader("Performance KPIs")
    turnover = {"Final portfolio": path.turnover, **{n: f.turnover for n, f in frames.items()}}
    series = {"Final portfolio": r, **bench}
    costed = lambda n, c: annual(F.cagr(F.with_cost(series[n], turnover[n], c)), lambda x: pct(x, 2))
    spec = [
        ("CAGR", lambda q, n: annual(q["cagr"], lambda x: pct(x, 2)), "Compound annual growth, zero cost"),
        ("CAGR at 5 bp cost", lambda q, n: costed(n, .0005), "5 bp per dollar traded on recorded rebalances; entry/exit costs excluded"),
        ("CAGR at 10 bp cost", lambda q, n: costed(n, .001), "10 bp per dollar traded on recorded rebalances; entry/exit costs excluded"),
        ("Real CAGR (actual CPI)", lambda q, n: annual(q["real_cagr_cpi"], lambda x: pct(x, 2)),
         f"CPI index-ratio adjustment over the selected dates; CPI rose {pct(k['cpi_inflation'], 2)} a year"),
        (f"Real CAGR at the {pct(CFG['inflation'], 2)} planning rate", lambda q, n: annual(q["real_cagr_policy"], lambda x: pct(x, 2)),
         "Fixed planning inflation assumption, not actual inflation over the selected period"),
        ("Cumulative return", lambda q, n: pct(q["cumulative_return"]), "Investment growth over the selected period"),
        ("Volatility", lambda q, n: pct(q["annual_volatility"], 2), "Daily sample standard deviation × √252"),
        ("Sharpe ratio", lambda q, n: annual(q["sharpe"], ratio),
         "Annualised mean daily excess return over DTB3 / annualised standard deviation of those excess returns"),
        ("Sortino ratio", lambda q, n: annual(q["sortino_excess"], ratio),
         "Annualised mean excess return over DTB3 / downside deviation of excess returns below zero"),
        ("Beta to SPY", lambda q, n: ratio(q["beta"]), "Excess-return regression on SPY; descriptive on short periods"),
        ("Maximum drawdown", lambda q, n: pct(-q["maximum_drawdown"]), "Largest investment fall from a previous high within the view"),
        ("Calmar ratio", lambda q, n: annual(q["calmar"], ratio), "CAGR / absolute maximum drawdown"),
        ("Longest time under water", lambda q, n: f"{q['max_underwater_days']} trading days (approx. {q['max_underwater_days']/252:.1f} years)",
         "Consecutive trading observations below a prior high; approximate years use 252 sessions")]
    st.dataframe(pd.DataFrame([{"KPI": name, "Final portfolio": f(k, "Final portfolio"),
                               **{n: f(kb[n], n) for n in chosen}, "Definition": definition}
                              for name, f, definition in spec]), hide_index=True, width="stretch")
    st.caption(f"Period {r.index[0].date()} to {r.index[-1].date()}. Final portfolio: {k['rebalances']} recorded resets "
               f"and {k['turnover_per_year']:.2f}× NAV traded per year. Benchmarks rebalance quarterly or after "
               "five-percentage-point drift. Actual CPI and planning-rate returns are separate; no withdrawals enter these KPIs.")
    with st.expander("SPY-only risk-adjusted measures"):
        st.caption("A one-factor equity model does not establish manager skill for a portfolio holding bonds, gold and energy. "
                   "Treynor is unstable for low beta and unavailable near zero beta.")
        st.dataframe(pd.DataFrame([
            {"KPI": "Treynor ratio (vs SPY)", "Final portfolio": annual(k["treynor"], lambda x: pct(x, 2)),
             **{n: annual(kb[n]["treynor"], lambda x: pct(x, 2)) for n in chosen}},
            {"KPI": "Alpha vs SPY only (Jensen)", "Final portfolio": annual(k["jensen_alpha"], lambda x: pct(x, 2)),
             **{n: annual(kb[n]["jensen_alpha"], lambda x: pct(x, 2)) for n in chosen}}]), hide_index=True, width="stretch")

    st.markdown("**The final portfolio against the selected benchmarks**")
    if chosen:
        st.dataframe(pd.DataFrame([{"Benchmark": n, "CAGR difference (pp)": annual(x["cagr_diff"], lambda v: f"{100*v:+.2f}"),
            "Annual mean return difference (pp)": annual(x["mean_diff"], lambda v: f"{100*v:+.2f}"),
            "Volatility difference (pp)": f"{100*(k['annual_volatility']-kb[n]['annual_volatility']):+.2f}",
            "Maximum drawdown, final vs benchmark": f"{pct(-k['maximum_drawdown'])} vs {pct(-kb[n]['maximum_drawdown'])}",
            "Tracking error": pct(x["tracking_error"], 2), "Information ratio": annual(x["information_ratio"], ratio)}
            for n, x in rel.items()]), hide_index=True, width="stretch")
    st.caption("CAGR difference is geometric; annual mean return difference is arithmetic and supplies the information-ratio "
               "numerator. Their signs can differ. Tracking error is annualised volatility of daily active returns. "
               "The information ratio is descriptive; no t-test or claim that a gap is statistically significant is made.")
    with st.expander("Benchmark definitions and matching period"):
        rows = []
        for n, (w, why) in catalog.items():
            rows.append({"Benchmark": n, "Weights": "Unavailable" if w is None else " / ".join(f"{t} {pct(x, 0)}" for t, x in w.items() if x > 0),
                         "Volatility over selected dates": "n/a" if w is None else pct(full_frames[n].loc[a:b, "return"].std()*np.sqrt(252), 2),
                         "Definition": why})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("The volatility match is approximate, uses a one-point weight grid, and refers to the full strategy history. "
                   "It need not hold in a shorter view. Equal volatility does not imply equal tail risk. Static parity changes "
                   "both the covariance estimator and trading convention, so it does not isolate monthly adaptation.")
    with st.expander("How the allocation rule works"):
        st.markdown(
            "1. Collect 500 daily ETF returns before estimating the first target.\n"
            "2. Expand the window until 750 observations are available, then retain the latest 750.\n"
            "3. At each month-end close, estimate EWMA covariance using weights proportional to 0.97^k "
            "(half-life about 23 trading days).\n"
            "4. Solve for long-only weights with equal volatility risk contributions across the four ETFs.\n"
            "5. Trade to the target at that close; hold positions and allow weights to drift until the next reset.\n\n"
            f"The first performance date is {PATH.index[0].date()}, after the initial estimation history "
            f"beginning with prices on {DATA_START.date()}. Decisions use data through their close only; the "
            "strategy was selected after this history had been seen.")


def page_risk():
    alpha, method, start, end = SETTINGS
    st.title("Risk: VaR, Expected Shortfall and EVT")
    choice = st.radio("Estimation window", list(ESTIMATION), horizontal=False)
    a, b = ESTIMATION[choice]
    scope = F.risk_scope(RETURNS, a, b, price_start=DATA_START, strategy_start=PATH.index[0])
    c = st.columns(3)
    c[0].metric("Data as of", CFG["snapshot_end"])
    c[1].metric("Estimation observations", f"{scope['n']:,}")
    c[2].metric("Invested NAV", usd(VALUE))
    st.caption(f"Price history from {DATA_START.date()}; return estimation window {scope['first'].date()} to "
               f"{scope['last'].date()}; strategy path starts {PATH.index[0].date()}. "
               f"Confidence {alpha:.0%}; horizon one trading day.")
    st.write("VaR is a loss threshold; ES is the average loss in the worst (1 - confidence) of days. Neither is a maximum possible loss.")
    models, table = risk(EV["data_hash"], a, b, WKEY, RISK_KEY)
    t = table[np.isclose(table.alpha, alpha)].set_index("method").reindex(METHODS)
    st.subheader("Two portfolios, one measure")
    sr = F.strategy_risk(PATH, VALUE, (alpha,), a, b).iloc[0]
    st.dataframe(pd.DataFrame([
        {"Portfolio": "Strategy as run: monthly targets, holdings drift", "VaR USD": sr.var_usd,
         "ES USD": sr.es_usd, "Observations": sr.n, "First return": sr['first'].date(), "Last return": sr['last'].date()},
        {"Portfolio": "Latest target replay: daily rebalancing", "VaR USD": t.loc['historical', 'var_usd'],
         "ES USD": t.loc['historical', 'es_usd'], "Observations": scope['n'],
         "First return": scope['first'].date(), "Last return": scope['last'].date()}]), hide_index=True, width="stretch")
    st.caption("Latest target: " + " / ".join(f"{k} {pct(v)}" for k, v in W.items()))
    st.markdown("The latest target is the most XLE-heavy since 2006; historical monthly holdings differ from this fixed replay. "
                "See [Risk contributions](contributions).")
    panels = [("Unconditional: whole estimation window", METHODS[:6]),
              ("Conditional: next day, volatility estimated as of 30 September 2026", METHODS[6:])]
    for col, (title, methods) in zip(st.columns(2), panels):
        with col:
            st.subheader(title)
            good = [m for m in methods if str(t.loc[m, 'status']).lower().startswith(('ok', 'warning'))
                    and np.isfinite(t.loc[m, 'var_usd']) and np.isfinite(t.loc[m, 'es_usd'])]
            fig = go.Figure()
            for field, label, color in [('var_usd', 'VaR', '#9ec3ef'), ('es_usd', 'ES', ACCENT)]:
                fig.add_trace(go.Bar(x=[LABEL[m] for m in good], y=t.loc[good, field], name=f"{label} {alpha:.0%}",
                    marker=dict(color=color, line=dict(color=[ACCENT if m == method else 'rgba(0,0,0,0)' for m in good],
                                                      width=[3 if m == method else 0 for m in good])),
                    hovertemplate="%{x}<br>%{y:$,.0f}<extra></extra>"))
            style(fig, 400, "USD simple loss, one day").update_layout(barmode="group", hovermode="closest")
            fig.update_yaxes(tickformat="$,.0f")
            st.plotly_chart(fig, width="stretch")
            for m in methods:
                if m not in good:
                    st.caption(f"Unavailable: {LABEL[m]}: {t.loc[m, 'status']}")
            q = t.loc[methods]
            st.dataframe(pd.DataFrame({"Model": [LABEL[m] for m in methods], "Family": [FAMILY_TEXT[m] for m in methods],
                "VaR %": q.var_pct.to_numpy(), "VaR USD": q.var_usd.to_numpy(),
                "ES %": q.es_pct.to_numpy(), "ES USD": q.es_usd.to_numpy(),
                "ES / VaR": (q.es_usd/q.var_usd.where(q.var_usd > 0)).to_numpy(),
                "Basis": [q.loc[m, 'basis'] or ("next day, volatility as of 30 Sep 2026" if m in METHODS[6:] else "whole window") for m in methods],
                "Status": q.status.to_numpy()}), hide_index=True, width="stretch")
    st.caption(f"Outlined bars highlight the sidebar methodology: {LABEL[method]}.")
    st.subheader("Why the methods disagree")
    for note in F.disagreement_notes(table, models, alpha):
        st.markdown(f"- {note}")
    st.subheader("Reliability")
    st.markdown("These are fitted estimates, not validated forecasts. The strategy's own sequential backtest "
                "(breaches, Kupiec, conditional coverage, zone and clustering for both conditional models) is on "
                "[Backtesting](backtest). The fixed-target replay has no backtest of its own and inherits no verdict.")
    st.subheader("Sensitivity to the estimation window")
    rows = []
    for label, (x, y) in ESTIMATION.items():
        _, tb = risk(EV["data_hash"], x, y, WKEY, RISK_KEY)
        tb = tb[np.isclose(tb.alpha, alpha)].set_index("method")
        rows.append({"Window": label, **{f"{LABEL[m]} ES": usd(tb.es_usd[m]) for m in ("historical", "normal", "evt", "garch_evt")}})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if a is None and b is None:
        st.subheader("Full-sample bootstrap intervals")
        boot = intervals(EV["data_hash"], WKEY, RISK_KEY)
        boot = boot[np.isclose(boot.alpha, alpha)].set_index("method")
        st.dataframe(pd.DataFrame({"Model": [LABEL[m] for m in boot.index],
            f"VaR {alpha:.0%}, 95% interval": [f"{usd(r.var_usd_lo)} to {usd(r.var_usd_hi)}" for r in boot.itertuples()],
            f"ES {alpha:.0%}, 95% interval": [f"{usd(r.es_usd_lo)} to {usd(r.es_usd_hi)}" for r in boot.itertuples()],
            "Successful resamples": boot.reps_ok.to_numpy(), "Failed resamples": CFG['bootstrap_reps']-boot.reps_ok.to_numpy()}),
            hide_index=True, width="stretch")
        st.caption("Circular blocks of whole daily rows preserve cross-asset dependence. Intervals cover estimation noise; "
                   "the EVT threshold percentile is fixed, and model choice is not covered.")
    else:
        st.info("Bootstrap intervals exist for the full sample only. They are hidden here because they do not match this window; "
                "refitting the block bootstrap for each window is computationally expensive.")
    with st.expander("Technical details"):
        st.dataframe(pd.DataFrame([{"Model": LABEL[m], "Estimation n": scope['n'],
            "Effective tail count": (CFG['n_sim'] if m in ('mc_normal', 'mc_t') else scope['n'])*(1-alpha),
            "MC seed": CFG['seed'] if m in ('mc_normal', 'mc_t') else None,
            "MC scenarios": CFG['n_sim'] if m in ('mc_normal', 'mc_t') else None} for m in METHODS]), hide_index=True)
        for m in METHODS:
            st.write(LABEL[m], models[m].params)
        evt = models['evt']
        if str(evt.status).lower().startswith(('ok', 'warning')):
            st.write("EVT body/tail basis", {f"{v:.0%}": evt.basis(v) for v in (.90, .95, .99)})
        st.caption(f"Bootstrap: {CFG['bootstrap_reps']} repetitions, {CFG['bootstrap_block']}-day blocks, seed {CFG['seed']}. "
                   f"Strategy hash {SH}; run {EV['run']}; data hash {EV['data_hash'][:12]}.")
        st.markdown("[EVT threshold diagnostics](evt)")
        st.caption("Sidebar backtest dates affect only the Backtesting page.")


def page_evt():
    from quanedge.risk import fit_evt
    from quanedge.risk import settings as S
    from quanedge.risk.portfolio import loss_fraction
    from quanedge.risk.validation import ModelFitError
    from scipy.stats import norm

    alpha, method, start, end = SETTINGS
    st.title("EVT tail and threshold choice")
    st.info(f"Today's target ({' / '.join(f'{k} {pct(v)}' for k, v in W.items())}), rebalanced daily with no costs over "
            f"the full sample, {RETURNS.index[0].date()} to {RETURNS.index[-1].date()}. Charts use daily log losses; tables "
            f"use USD simple losses on the {usd(VALUE)} invested NAV. This is not the strategy's changing holdings and not "
            "GARCH-EVT. Sequential forecast evidence is below and on [Backtesting](backtest).")
    models, table = risk(EV["data_hash"], None, None, WKEY, RISK_KEY)
    m = models["evt"]
    if not hasattr(m, "fit"):
        st.warning(f"EVT result unavailable: {m.status}"); return
    p = m.params
    losses = target_losses(WKEY); r = -losses
    scan = evt_scan(EV["data_hash"], WKEY, RISK_KEY, alpha)
    if scan.empty:
        st.warning("No threshold scan is available for this fit."); return
    qq = evt_qq(EV["data_hash"], WKEY, RISK_KEY)
    alts = {}
    for label, q in (("90th percentile", .90), ("95th percentile", .95)):
        try:
            alts[label] = fit_evt(losses, threshold_q=q)
        except (ModelFitError, ValueError) as err:
            alts[label] = {"status": str(err)}
    boot = intervals(EV["data_hash"], WKEY, RISK_KEY)
    boot = boot[(boot.method == "evt") & np.isclose(boot.alpha, alpha)]
    notes = F.evt_notes(m, scan, alpha, VALUE, alts, boot.iloc[0] if len(boot) else None, qq)
    st.subheader("Conclusion")
    st.write(notes["conclusion"])
    seq = next((x for x in SUMMARY["validation"] if x["method"] == "evt" and x["alpha"] == .99), None)
    if seq and seq.get("status") == "ok":
        st.markdown(f"**Sequential evidence (a different fit):** EVT refitted on a rolling {CFG['window']}-day window of the "
                    f"strategy's own path, refit every {CFG['refit']} days, 99% VaR, {CFG['evaluation_start']} to "
                    f"{CFG['snapshot_end']}: {seq['breaches']} breaches in {seq['days']:,} days, Kupiec p {p_text(seq['kupiec_p'])}, "
                    f"independence p {p_text(seq['independence_p'])}, conditional coverage p {p_text(seq['conditional_coverage_p'])}, "
                    f"{seq['zone']} zone{'; breaches came in clusters' if seq.get('independence_p') is not None and seq['independence_p'] <= .05 else ''}. "
                    "It tests the rolling EVT forecasts, not this full-sample fit.")
    else:
        st.markdown("**Sequential evidence:** no saved rolling EVT backtest is available for this run.")
    chosen = scan.iloc[(scan.u-p["u"]).abs().argmin()]
    c = st.columns(5)
    c[0].metric("Threshold u (log loss)", pct(p["u"], 3), help=f"{p['threshold_q']:.1%} percentile")
    c[1].metric("Exceedances / rate", f"{p['n_exceed']} / {m.zeta:.1%}")
    c[2].metric("Shape ξ", f"{p['xi']:.3f}", help=f"Approximate 95% interval {p['xi']-1.96*p['xi_se']:.3f} to {p['xi']+1.96*p['xi_se']:.3f}")
    c[3].metric("Scale σ (log loss)", pct(p["sigma"], 3))
    c[4].metric("KS distance", f"{chosen.ks:.4f}")
    st.caption(f"Approximate 95% shape interval: {p['xi']-1.96*p['xi_se']:.3f} to {p['xi']+1.96*p['xi_se']:.3f}. " + notes["shape"])

    st.subheader("Threshold choice")
    st.info(f"**Rule:** {p['threshold_rule']}. A threshold meets the stability heuristic when ξ lies within 1.96 standard errors of ξ at "
            "every higher candidate (at least three of them); candidates need at least 50 exceedances. This is a project "
            "heuristic, not an optimal or significance-calibrated procedure.")
    st.write(f"The selected threshold includes the worst {m.zeta:.1%} of days. A lower u brings more non-tail days into the fit "
             "and can bias it; a higher u leaves fewer points and increases uncertainty. The diagnostics below assess that trade-off.")
    ok = scan[scan.fit_ok]
    for pair in ((('mean_excess', 'Mean excess', True), ('xi', 'Shape ξ', False)),
                 (('sigma_star', 'Modified scale σ* = σ − ξu', True), ('ks', 'KS distance', False))):
        for col, (field, title, percent) in zip(st.columns(2), pair):
            with col:
                fig = go.Figure()
                if field == 'xi':
                    fig.add_trace(go.Scatter(x=ok.q, y=ok.xi+1.96*ok.xi_se, line=dict(width=0), showlegend=False))
                    fig.add_trace(go.Scatter(x=ok.q, y=ok.xi-1.96*ok.xi_se, fill='tonexty', fillcolor='rgba(42,120,214,.15)', line=dict(width=0), name='Approximate 95% band'))
                x = ok.u if field == 'mean_excess' else ok.q
                fig.add_trace(go.Scatter(x=x, y=ok[field], mode='lines+markers', name=title,
                              line=dict(color=ACCENT), marker=dict(size=7, color=np.where(ok.stable, ACCENT, '#ffffff'), line=dict(color=ACCENT, width=1)),
                              customdata=ok.n_exceed, hovertemplate='%{x:.3%}<br>%{y:.5f}<br>exceedances %{customdata}<extra></extra>'))
                fig.add_vline(x=p['u'] if field == 'mean_excess' else p['threshold_q'], line_dash='dash', line_color=MUTED)
                st.markdown(f"**{title}**")
                style(fig, 300, title, legend=field == 'xi').update_xaxes(tickformat='.1%', title='threshold u' if field == 'mean_excess' else 'threshold percentile')
                if percent:
                    fig.update_yaxes(tickformat='.2%')
                st.plotly_chart(fig, width='stretch')
    st.caption("Filled markers meet the stability heuristic. Bands are approximate, pointwise and computed on nested samples. "
               "They are not simultaneous bands or a calibrated test.")
    st.caption(notes['diagnostics'])

    st.subheader("Does the choice matter?")
    fig = go.Figure()
    body = (ok.q > alpha + 1e-12).to_numpy()            # above q = alpha the model answers from the empirical body
    for field, label, color in (('es_usd', 'ES', ACCENT), ('var_usd', 'VaR', MUTED)):
        fig.add_trace(go.Scatter(x=ok.q, y=ok[field], mode='lines+markers', name=f'{alpha:.0%} {label}', line=dict(color=color),
                                marker=dict(size=7, color=np.where(body, '#ffffff', color), line=dict(color=color, width=1)),
                                customdata=np.column_stack([ok.n_exceed, np.where(body, 'empirical body', 'GPD tail')]),
                                hovertemplate='q %{x:.1%}<br>USD %{y:,.0f}<br>exceedances %{customdata[0]}<br>%{customdata[1]}<extra></extra>'))
    for q, label in ((p['threshold_q'], 'chosen'), (.90, '90th'), (.95, '95th')):
        fig.add_vline(x=q, line_dash='dash', annotation_text=label)
    st.plotly_chart(style(fig, 340, 'USD simple loss').update_xaxes(tickformat='.0%', title='threshold percentile'), width='stretch')
    if body.any():
        st.caption(f"Hollow markers: thresholds above the {alpha:.0%} level, where the {alpha:.0%} VaR and ES come from the "
                   "empirical losses below u, not the GPD tail. They are excluded from the stable-region range above.")
    rows = []
    fits = {"Chosen by the rule (today's target)": m, **alts,
            'Strategy path (rule chosen)': evt_strategy(EV['data_hash'], SH)}
    for label, fit in fits.items():
        if not hasattr(fit, 'fit'):
            rows.append({'Threshold / portfolio': label, 'Status': f"unavailable: {fit.get('status', 'failed fit')}"}); continue
        rows.append({'Threshold / portfolio': label, 'u (log loss)': pct(fit.fit.u, 3), 'Exceedances': fit.fit.n_exceed,
                     'ξ (approx. 95% interval)': f"{fit.fit.xi:.3f} [{fit.fit.xi-1.96*fit.fit.se[0]:.3f}, {fit.fit.xi+1.96*fit.fit.se[0]:.3f}]",
                     f'VaR {alpha:.0%}': usd(VALUE*loss_fraction(fit.var(alpha))), f'ES {alpha:.0%}': usd(VALUE*fit.es_fraction(alpha)),
                     'Basis': fit.basis(alpha), 'Status': fit.status})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')

    st.subheader("Fit diagnostics (in-sample)")
    tail = np.sort(losses[losses > p['u']]); maximum = tail[-1]
    fig = go.Figure(go.Scatter(x=tail, y=(len(tail)-np.arange(len(tail)))/len(losses), mode='markers', name='Observed losses', marker=dict(color=MUTED, size=5)))
    for grid, dash, name in ((np.linspace(p['u'], maximum, 200), 'solid', 'GPD: observed range'),
                             (np.linspace(maximum, maximum*1.3, 80), 'dash', 'GPD: extrapolation')):
        fig.add_trace(go.Scatter(x=grid, y=F.gpd_tail_prob(grid, m.fit, m.zeta), name=name, line=dict(color=ACCENT, dash=dash)))
    grid = np.linspace(p['u'], maximum*1.3, 280)
    fig.add_trace(go.Scatter(x=grid, y=norm.sf(grid, -r.mean(), r.std(ddof=1)), name='Normal', line=dict(color='#eb6834', dash='dot')))
    fig.add_vrect(x0=maximum, x1=maximum*1.3, fillcolor=GRID, line_width=0, annotation_text='Extrapolation')
    style(fig, 360, 'Probability of loss at least this large').update_yaxes(type='log', tickformat='.0e')
    fig.update_xaxes(tickformat='.1%', title='daily log loss')
    st.plotly_chart(fig, width='stretch'); st.caption(notes['survival'])
    if qq['status'] == 'ok':
        fig = go.Figure()
        for field in ('hi', 'lo'):
            fig.add_trace(go.Scatter(x=qq['theoretical'], y=qq[field], line=dict(width=0),
                                    fill='tonexty' if field == 'lo' else None, fillcolor='rgba(42,120,214,.15)',
                                    name='95% pointwise envelope', showlegend=field == 'lo'))
        fig.add_trace(go.Scatter(x=qq['theoretical'], y=qq['theoretical'], name='Reference', line=dict(color=MUTED, dash='dash')))
        fig.add_trace(go.Scatter(x=qq['theoretical'], y=qq['observed'], mode='markers', name='Observed excesses', marker=dict(color=ACCENT, size=5)))
        st.plotly_chart(style(fig, 360, 'Observed excess (log loss)').update_xaxes(title='Fitted GPD excess quantile', tickformat='.1%').update_yaxes(tickformat='.1%'), width='stretch')
    st.caption(notes['qq'])
    st.caption('Parametric-bootstrap envelope: 200 simulated tail samples, refitted individually; refit-standardised order statistics mapped back to fitted GPD units. Threshold held fixed.')

    with st.expander('All candidates'):
        audit = scan[['q', 'u', 'n_exceed', 'fit_ok', 'note', 'xi', 'xi_se', 'sigma_star', 'ks', 'stable', 'var_usd', 'es_usd']].copy()
        dropped = []
        for q in S.EVT_THRESHOLD_GRID:
            u = np.quantile(losses, q, method=S.QUANTILE_METHOD); n = int((losses > u).sum())
            if n < S.EVT_MIN_EXCEED:
                dropped.append(dict(q=q, u=u, n_exceed=n, fit_ok=False, note=f'fewer than {S.EVT_MIN_EXCEED} exceedances', stable=False))
        audit = pd.concat([audit, pd.DataFrame(dropped)], ignore_index=True).sort_values('q')
        st.caption(f'{len(dropped)} grid points dropped for fewer than {S.EVT_MIN_EXCEED} exceedances; {int((~scan.fit_ok).sum())} failed fits retained with reasons.')
        st.dataframe(audit, hide_index=True, width='stretch')
        if qq['failures']:
            st.write('QQ refit failures:', qq['failures'])
    st.subheader('Limits')
    clustered = bool(seq and seq.get('independence_p') is not None and seq['independence_p'] <= .05)
    st.write('Volatility clustering breaks the i.i.d. assumption behind POT' + (
             ', and the rolling EVT backtest above shows its breaches cluster. ' if clustered else '. ') + 'Threshold-selection uncertainty is outside the bootstrap. Neither the rolling EVT backtest nor GARCH-EVT '
             '(fixed 90th-percentile residual threshold) validates this full-sample fit.')


def page_backtest():
    alpha, method, start, end = SETTINGS
    st.title("Backtesting the risk forecasts")
    st.caption("Sequential risk-forecast evaluation: each day's VaR uses only returns up to the day before, on the strategy's own "
               f"daily path (strategy hash {SH[:8]}). Forecasts exist from {FIRST_FC}. Breach = loss larger than VaR.")
    fixed = (start == pd.Timestamp(CFG["evaluation_start"]) or start.date() == FIRST_FC) and end.date() == LAST_FC
    ref = {m: next(x for x in SUMMARY["validation"] if x["method"] == m and x["alpha"] == .99) for m in ("garch_evt", "fhs")}

    with st.expander("What this backtest does and does not show", expanded=False):
        st.markdown(
            f"- **Does:** each forecast is made from the previous {CFG['window']} trading days only (slow models refitted every "
            f"{CFG['refit']} days, volatility updated daily), then compared with the next day's loss. Breach counts and their timing "
            "are tested with Kupiec (frequency) and Christoffersen (do breaches follow breaches).\n"
            f"- **Does not give an untouched test.** The strategy, the recession overlay and the risk models were chosen after the "
            f"{DATA_SPAN} history had been seen. Sequential forecasting avoids look-ahead inside each forecast, but the choices "
            "around it were informed by the same history.\n"
            "- **Tests the strategy's own return path.** That path mixes changing monthly weights and overlay switches. It is "
            "not a direct test of tomorrow's risk for today's exact holdings.\n"
            "- **Validates VaR only.** Breach tests say nothing about how large losses are beyond VaR; Expected Shortfall is not "
            "validated here (the size of breaches is shown below as a description).\n"
            "- **A high p-value means \"not rejected\", not \"correct\".** With about 25 expected breaches at 99% the tests have "
            "limited power, especially over short ranges.")

    if method not in F.BACKTEST_METHODS:
        st.warning(f"**{LABEL[method]}** has no saved sequential forecasts for this strategy, so it cannot be backtested here. "
                   "It is not replaced by another model. Choose Historical, Parametric (normal), EVT, Filtered HS or GARCH-EVT "
                   "in the sidebar.")
    else:
        res, frame = F.backtest(FC, SH, method, alpha, start, end)
        if res.get("days", 0) < 2:
            st.warning(f"Not enough forecast days in this range ({res.get('days', 0)}). Choose a range of at least two "
                       f"trading days between {FIRST_FC} and {LAST_FC}.")
        else:
            label = "Fixed evaluation period" if fixed else "Exploratory range (sidebar)"
            st.markdown(f"**{label}: {LABEL[method]}, {alpha:.0%} VaR, {start.date()} to {end.date()}**")
            sentence, rejected = F.finding_text(res, alpha)
            (st.warning if rejected else st.info)(sentence)
            if res["independence_p"] is None:
                why = ("there were no breaches" if res["breaches"] == 0 else
                       "every day was a breach" if res["breaches"] == res["days"] else "there are too few transitions")
                st.caption(f"The Christoffersen tests need breaches and non-breaches to follow each other; in this range {why}, "
                           "so they cannot be computed. The Kupiec test still applies.")
            if res["days"] < 250:
                st.caption(f"Short range: {res['days']} forecast days, so about {res['expected_breaches']:.1f} breaches are expected "
                           f"at {alpha:.0%}. The tests have little power here; a range of a year or more (250+ days) is more informative.")

            c = st.columns(5)
            c[0].metric("Days tested", f"{res['days']:,}")
            c[1].metric("Breaches", f"{res['breaches']}", f"expected {res['expected_breaches']:.1f}", delta_color="off",
                        help="Observed breaches are whole days; the expected number is days × (1 − confidence level), so it can be fractional.")
            c[2].metric("Breach rate", f"{res['breaches']/res['days']:.2%}", f"target {1-alpha:.2%}", delta_color="off")
            c[3].metric("Kupiec p", p_text(res["kupiec_p"]),
                        help="Tests whether the breach frequency is consistent with the confidence level. At or below 0.05: rejected.")
            c[4].metric("Independence p", p_text(res["independence_p"]),
                        help="Christoffersen test: is a breach more likely the day after a breach? At or below 0.05: breaches cluster.")
            st.caption(f"Conditional coverage p (frequency and independence together): {p_text(res['conditional_coverage_p'])}. "
                       f"Forecast coverage {res['coverage']:.1%}, missing forecast days {res['missing_days']} (missing days are "
                       "left out of the counts, not treated as safe days).")

            cl = F.clustering_summary(res, frame)
            zone = res["zone"]
            dot = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(zone, "⚪")
            if zone in ("green", "yellow", "red"):
                st.markdown(f"{dot} **Basel zone, last 250 days only ({cl['window_start']} to {cl['window_end']}): {zone}, "
                            f"{cl['window_breaches']} breaches.**")
                st.caption("Basel calibration for 99% one-day VaR over 250 days: green 0-4, yellow 5-9, red 10+. It describes only "
                           "the most recent year of the range, a different window from the tests above"
                           + (f"; {res['red_window_share']:.0%} of all rolling 250-day windows in the range were red."
                              if res.get("red_window_share") is not None else "."))
            else:
                st.markdown(f"{dot} **Basel zone unavailable** for {alpha:.0%} VaR or ranges shorter than 250 days.")
                st.caption(f"Binomial reading instead: {F.binomial_zone(res, alpha)} (p = {p_text(res['binomial_p'])}).")

            if cl["after_breach"] is not None and cl["after_calm"] is not None:
                st.markdown("**What clustering means here**")
                yr = (f" {cl['worst_year_breaches']} of the {cl['breaches']} breaches fell in {cl['worst_year']}."
                      if cl["worst_year"] else "")
                st.markdown(
                    f"The day after a breach, another breach followed {cl['after_breach']:.1%} of the time "
                    f"({cl['back_to_back']} back-to-back pairs); after a normal day, only {cl['after_calm']:.1%}.{yr} "
                    + ("So the total count can look right while misses bunch together in sudden shocks, which is when "
                       "protection matters most: the model reacts a few days late when volatility jumps."
                       if res["independence_p"] is not None and res["independence_p"] <= .05 else
                       "In this range that difference is not statistically significant."))

            sev = F.breach_severity(frame, VALUE)
            st.markdown("**How large the breaches were**")
            s = st.columns(3)
            s[0].metric("Largest daily loss", pct(sev["largest_loss"], 2) if sev["largest_loss"] is not None else "n/a",
                        str(sev["largest_loss_date"] or ""), delta_color="off", help="Log loss; close to the percentage loss for small moves.")
            if "largest_excess" in sev:
                s[1].metric("Largest excess over VaR", money(sev["largest_excess_usd"]), str(sev["largest_excess_date"]),
                            delta_color="off", help=f"{usd(sev['largest_excess_usd'])} beyond the forecast VaR at NAV {usd(VALUE)}.")
                s[2].metric("Average excess over VaR", money(sev["mean_excess_usd"]),
                            help=f"Mean of loss minus VaR over the breach days, in USD at NAV {usd(VALUE)}; descriptive, not an ES test.")

            fig = go.Figure([go.Scatter(x=frame.index, y=frame.loss, name="Daily loss", line=dict(color=MUTED, width=1)),
                             go.Scatter(x=frame.index, y=frame["var"], name=f"{LABEL[method]} VaR {alpha:.0%}", line=dict(color=ACCENT, width=2)),
                             go.Scatter(x=frame.index[frame.breach], y=frame.loss[frame.breach], mode="markers", name="Breach",
                                        marker=dict(size=8, color="#e34948", line=dict(color="white", width=2)))])
            st.plotly_chart(style(fig, 380, "Log loss").update_yaxes(tickformat=".1%"), width="stretch")
            st.caption("Log loss = −log(1 + return); for daily moves it is close to the percentage loss "
                       "(a 5% log loss is a 4.9% fall). Positive values are losses.")
            if len(sev["table"]):
                with st.expander(f"Breach dates ({len(sev['table'])})"):
                    t = sev["table"]
                    shown = pd.DataFrame({"Date": t.index.date, "Loss": t.loss.map(lambda x: pct(x, 2)),
                                          "VaR": t["var"].map(lambda x: pct(x, 2)), "Excess": t.excess.map(lambda x: pct(x, 2)),
                                          "Loss USD": t.loss_usd.map(usd), "Excess USD": t.excess_usd.map(usd)})
                    st.dataframe(shown, hide_index=True, width="stretch")
                    st.download_button("Download breaches (CSV)", t.to_csv().encode(), f"breaches_{method}_{alpha:.0%}.csv", "text/csv")
            by_year = frame.groupby(frame.index.year).breach.agg(["sum", "count"])
            fig = go.Figure([go.Bar(x=by_year.index, y=by_year["sum"], name="Breaches", marker=dict(color=ACCENT, cornerradius=4)),
                             go.Scatter(x=by_year.index, y=by_year["count"]*(1-alpha), name="Expected", mode="markers",
                                        marker=dict(size=10, symbol="line-ew-open", color=INK, line=dict(width=2)))])
            st.markdown("**Breaches by year**")
            st.plotly_chart(style(fig, 260).update_layout(hovermode="closest"), width="stretch")

    st.subheader(f"Fixed evaluation period, whatever the sidebar says: 99% VaR, {CFG['evaluation_start']} to {CFG['snapshot_end']}")
    rows = []
    for m, v in ref.items():
        n00, n01, n10, n11 = v.get("transitions") or (0, 0, 0, 0)
        rows.append({"Model": LABEL[m], "Breaches": v["breaches"], "Expected": f"{v['expected_breaches']:.1f}",
                     "Kupiec p": p_text(v["kupiec_p"]), "Independence p": p_text(v["independence_p"]),
                     "Cond. coverage p": p_text(v["conditional_coverage_p"]), "Back-to-back": n11,
                     "Coverage": f"{v.get('coverage', 1):.1%}", "Basel zone (last 250 days)": v["zone"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Both conditional models, on the strategy's own sequential forecasts. Kupiec tests the breach frequency, "
               "Christoffersen independence tests whether breaches follow breaches, conditional coverage tests both; a p-value "
               "at or below 0.05 rejects that hypothesis. " + monitoring_note(ref["garch_evt"], ref["fhs"]))
    if not fixed:
        st.caption("The sidebar range above is exploratory; this table is the fixed reference period.")

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
    st.caption(f"Historical crisis paths at NAV {usd(VALUE)}. 'As run' is the strategy path (v6, with its month-end rebalances and "
               "the recession overlay) from the scenario start close. 'Today's target, held' applies the current target "
               "buy-and-hold to the same days. Profit is positive and loss negative throughout this page.")
    rows, hyp, _ = F.stress_panel(PATH, PRICES, RETURNS, W, VALUE)
    o = overlay(EV["data_hash"]); core = None if "error" in o else o["core"]
    _, tot = F.risk_contributions(RETURNS, W, .99, VALUE); es99 = tot["es_usd"]

    table = []
    for s in rows:
        p, h = s.get("path"), s["today_buy_hold"]
        c = F.scenario_pnl(core, RETURNS, s["start"], s["end"], VALUE) if core is not None and p else None
        rec = s.get("recovery") or {}
        table.append({"Scenario": s["scenario"], "Dates": f"{s['start']} to {s['end']}", "Trading days": s.get("days"),
                      "As run (v6): return": pct(p["return"]) if p else "n/a", "As run: USD P&L": usd(-p["loss_usd"]) if p else "n/a",
                      "As run: largest fall": pct(-p["max_fall"]) if p else "n/a",
                      "Largest fall in days of 99% ES": f"{p['max_fall']*VALUE/es99:.1f}" if p else "n/a",
                      "Without overlay (v5 core): return": pct(c["return"]) if c else "n/a",
                      "v5 core: largest fall": pct(-c["max_fall"]) if c else "n/a",
                      "Back to the pre-crisis peak": ("above it at the end" if rec.get("days") == 0 else f"{rec['days']} trading days after the end ({rec['date']})" if rec.get("days") is not None
                                                      else "not yet" if rec else "n/a"),
                      "Worst day": f"{p['worst_day']} ({pct(p['worst_day_return'])})" if p else "n/a",
                      "Today's target, held": pct(h["return"]) if h and h.get("status") == "ok" else "n/a",
                      "Held: largest fall": pct(-h["drawdown"]) if h and h.get("status") == "ok" else "n/a"})
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
    st.caption(f"'Days of 99% ES' divides the largest fall in USD by today's 1-day historical 99% ES ({usd(es99)}): how many "
               "average bad days the crisis was worth. 'Back to the pre-crisis peak' counts from the scenario end.")
    over = [s for s in rows if s.get("path") and s["today_buy_hold"] and s["today_buy_hold"].get("status") == "ok"
            and -s["today_buy_hold"]["drawdown"] > s["path"]["max_fall"]]
    if over:
        st.warning("Bought at the start of " + " and ".join(f"{s['scenario']} ({pct(-s['today_buy_hold']['drawdown'])} fall)" for s in over)
                   + " and left to drift, today's target would have fallen further than the strategy did as run ("
                   + ", ".join(pct(s["path"]["max_fall"]) for s in over) + "). The monthly rule cut risk as volatility rose; "
                   "a crash that arrives before the next month-end meets today's weights.")

    st.subheader("Which ETFs did the damage (as run, USD)")
    ran = [s for s in rows if s.get("path")]
    labels = [f"{s['scenario']}<br>{s['start']} to {s['end']} ({s['days']} days)" for s in ran]
    fig = go.Figure()
    for t in F.UNIVERSE:
        fig.add_trace(go.Bar(x=labels, y=[s["path"]["pnl_usd"][t] for s in ran], name=t,
                             marker=dict(color=COLOR[t], cornerradius=4), hovertemplate=f"{t} %{{y:$,.0f}}<extra></extra>"))
    fig.add_trace(go.Scatter(x=labels, y=[-s["path"]["loss_usd"] for s in ran], name="Portfolio (net)", mode="markers+text",
                             marker=dict(symbol="diamond", size=14, color=INK, line=dict(color="white", width=1)),
                             text=[usd(-s["path"]["loss_usd"]) for s in ran], textposition="top center",
                             hovertemplate="Portfolio %{y:$,.0f}<extra></extra>"))
    style(fig, 400, "USD profit (+) or loss (−)").update_layout(barmode="group", hovermode="closest")
    st.plotly_chart(fig.update_yaxes(tickformat="$,.0f"), width="stretch")
    st.markdown("\n".join("- " + line for line in F.stress_findings(rows)))
    st.caption("Generated from the numbers above. The windows differ in length (5 weeks to 17 months), so compare returns, "
               "not dollar sizes alone.")

    with st.expander("Other historical episodes since 2005 (as run)"):
        ep = F.episodes(PATH, RETURNS, VALUE)
        st.dataframe(pd.DataFrame([{"Episode": e["scenario"], "Dates": f"{e['start']} to {e['end']}", "Return": pct(e["return"]),
                                    "USD P&L": usd(e["pnl_usd"]), "Largest fall": pct(-e["max_fall"]),
                                    "Largest loss": f"{e['worst']} {usd(e['worst_usd'])}", "Largest gain": f"{e['best']} {usd(e['best_usd'])}",
                                    "Back to the pre-crisis peak": ("above it at the end" if e["recovery"]["days"] == 0 else f"{e['recovery']['days']} days" if e["recovery"]["days"] is not None else "not yet")}
                                   for e in ep]), hide_index=True, width="stretch")
        st.caption("Windows from the deepest ETF drawdowns since 2005 (results/crisis-methods-r1). They hit gold and energy, the "
                   "portfolio's most specific risks, which the three required crises do not.")

    st.subheader("Hypothetical scenario: joint equity-bond shock")
    if hyp.get("status") == "ok":
        pnl = {t: -hyp["contributions_usd"][t] for t in F.UNIVERSE}
        shocks = pd.DataFrame({"ETF": F.UNIVERSE, "Shock": [pct(hyp["shocks"][t]) for t in F.UNIVERSE],
                               "Weight": [pct(W[t]) for t in F.UNIVERSE], "USD P&L": [usd(pnl[t]) for t in F.UNIVERSE]})
        c1, c2 = st.columns([2, 1])
        c1.dataframe(shocks, hide_index=True, width="stretch")
        c2.metric("Portfolio P&L", usd(-hyp["loss_usd"]), pct(hyp["return"]), delta_color="off")
        c2.caption(f"{hyp['loss_usd']/es99:.1f} days of today's 99% ES.")
        st.caption("SPY −25% and AGG −10% at once, gold unchanged; XLE's shock is the conditional mean given those, from the "
                   "covariance of SPY's worst 10% of days from the data start to 2016. Deterministic: it has no estimated probability. "
                   f"Note: that covariance makes XLE fall with stocks ({pct(hyp['shocks']['XLE'])}), so this is an equity-led "
                   "crash, not an energy-led inflation shock; the stagflation preset below covers that case.")
    else:
        st.warning(f"Hypothetical scenario unavailable: {hyp.get('status')}")

    st.subheader("Design your own shock")
    presets = {"Frozen hypothetical": {t: hyp["shocks"][t] for t in F.UNIVERSE} if hyp.get("status") == "ok" else {t: 0. for t in F.UNIVERSE},
               "Stagflation, worse than 2022 (illustrative)": {"SPY": -.20, "AGG": -.12, "GLD": .05, "XLE": .15},
               "Energy collapse (illustrative)": {"SPY": -.10, "AGG": .03, "GLD": 0., "XLE": -.45},
               "Rate shock, worse than 2022 (illustrative)": {"SPY": -.25, "AGG": -.20, "GLD": -.10, "XLE": .10}}
    notes = {"Stagflation, worse than 2022 (illustrative)": "Inflation with slowing growth: stocks and bonds fall together "
             "(2022: SPY −18%, AGG −13% over the year), energy earns from the supply shock (XLE +49% in 2022), gold holds value.",
             "Energy collapse (illustrative)": "Oil demand or price-war shock (XLE fell 71% from 2014 to 2020); bonds rally on lower inflation.",
             "Rate shock, worse than 2022 (illustrative)": "A faster tightening than 2022; gold falls as real yields rise."}

    def reset():
        for t in F.UNIVERSE:
            st.session_state[f"shock-{t}"] = int(round(100*presets[st.session_state["shock-preset"]][t]))
    preset = st.selectbox("Start from", list(presets), key="shock-preset", on_change=reset)
    if notes.get(preset):
        st.caption(notes[preset])
    for t in F.UNIVERSE:
        st.session_state.setdefault(f"shock-{t}", int(round(100*presets[preset][t])))
    cols = st.columns(4)
    shocks = {t: cols[i].slider(f"{t} shock %", -60, 60, key=f"shock-{t}")/100 for i, t in enumerate(F.UNIVERSE)}
    res = F.custom_shock(W, shocks, VALUE)
    c1, c2 = st.columns([2, 1])
    f = go.Figure(go.Bar(x=F.UNIVERSE, y=[res["pnl_usd"][t] for t in F.UNIVERSE],
                         marker=dict(color=[COLOR[t] for t in F.UNIVERSE], cornerradius=4),
                         hovertemplate="%{x} %{y:$,.0f}<extra></extra>"))
    c1.plotly_chart(style(f, 260, "USD profit (+) or loss (−)").update_yaxes(tickformat="$,.0f"), width="stretch")
    c2.metric("Portfolio P&L", usd(-res["loss_usd"]), pct(res["return"]), delta_color="off")
    c2.caption(f"{max(res['loss_usd'], 0)/es99:.1f} days of today's 99% ES. Computed in the app for the current target; "
               "an illustration, not part of the frozen evidence.")

    st.subheader("Reverse stress test")
    target = st.slider("Loss to explain (% of NAV, in one step)", 5, 30, 20) / 100
    _, _, rev = F.stress_panel(PATH, PRICES, RETURNS, W, VALUE, reverse_loss=target)
    if rev["status"] == "ok":
        d = np.sqrt(rev["distance_squared"])
        month = (1 + RETURNS[F.UNIVERSE]).rolling(21).apply(np.prod, raw=True) - 1
        st.markdown(f"The most plausible joint move that costs {pct(rev['loss_fraction'], 0)} of NAV ({usd(rev['loss_fraction']*VALUE)}) "
                    f"is about **{d:.1f} standard deviations** from a normal day, counting all ETFs together "
                    "(Mahalanobis distance on the 2005-2016 daily covariance). It is not a probability.")
        st.dataframe(pd.DataFrame({"ETF": F.UNIVERSE, "Required move": [pct(rev["shocks"][t]) for t in F.UNIVERSE],
                                   "Worst 1-day move since 2005": [pct(RETURNS[t].min()) for t in F.UNIVERSE],
                                   "Worst 1-month move since 2005": [pct(month[t].min()) for t in F.UNIVERSE]}),
                     hide_index=True, width="stretch")
        st.caption("If the required moves exceed anything seen in a month, the loss needs a crash beyond the data; "
                   "if not, history has already produced such moves.")
    else:
        st.warning("Reverse stress optimisation did not converge.")


def page_contributions():
    alpha, method, start, end = SETTINGS
    st.title("Risk contributions and position sizing")
    A = attribution_set(EV["data_hash"], SH, WKEY, alpha, RISK_KEY)
    contrib, tot, cvar = A["contrib"], A["tot"], A["cvar"]
    lvl = f"{alpha:.0%}"
    st.caption(f"Today's target (from the {PATH.index[-1]:%d %b %Y} close), NAV {usd(VALUE)}, one-day {lvl} loss, "
               f"joint daily rows of the four ETFs {DATA_SPAN} ({len(RETURNS):,} days).")
    note = (f" The sidebar model, {LABEL[method]}, is fitted to the portfolio's returns only, so it cannot split risk by ETF;"
            " the split below is not that model's decomposition." if method in ("fhs", "garch_evt") else "")
    st.info(f"**Source of this split: historical attribution.** Every ETF's share comes from the same worst portfolio days "
            f"(shared tail weights), so the parts add up exactly to the portfolio's historical ES.{note}")
    top = contrib.es_share.idxmax()
    c = st.columns(4)
    c[0].metric(f"Historical {lvl} VaR", money(cvar["var_usd"]))
    c[1].metric(f"Historical {lvl} ES", money(tot["es_usd"]))
    c[2].metric("Diversification benefit", money(tot["diversification_benefit_usd"]),
                help="Sum of each ETF's stand-alone ES minus the portfolio ES.")
    c[3].metric("Largest ES share", f"{top} {pct(contrib.es_share[top])}", help=f"with {pct(W[top])} of the capital")

    st.subheader("Capital, everyday risk and tail risk")
    fig = go.Figure()
    for col, label, color in (("weight", "Capital weight", "#c3c2b7"),
                              ("vol_contribution", "Volatility share (EWMA, last 750 days)", "#9ec3ef"),
                              ("es_share", f"{lvl} ES share (full sample)", ACCENT)):
        fig.add_trace(go.Bar(x=F.UNIVERSE, y=contrib[col], name=label, marker=dict(color=color, cornerradius=4),
                             hovertemplate="%{x} %{y:.1%}<extra>" + label + "</extra>"))
    fig.add_hline(y=.25, line=dict(color=MUTED, dash="dot"), annotation_text="equal share 25%", annotation_position="top left")
    style(fig, 360, y="Share of total").update_layout(barmode="group", hovermode="closest")
    st.plotly_chart(fig.update_yaxes(tickformat=".0%"), width="stretch")
    st.caption("The volatility shares are about 25% each by construction: that is what risk parity sets. They use the "
               "recent EWMA covariance the rule uses; the ES shares use the whole history. The window effect is shown below.")

    table = pd.DataFrame({"ETF": F.UNIVERSE, "Weight": [pct(W[t]) for t in F.UNIVERSE],
                          f"Component VaR {lvl}": [usd(cvar["components"][t]) for t in F.UNIVERSE],
                          f"Component ES {lvl}": [usd(contrib.es_usd[t]) for t in F.UNIVERSE],
                          "Share of ES": [pct(contrib.es_share[t]) for t in F.UNIVERSE],
                          "95% interval of share": [f"{pct(A['boot'].lo[t])} to {pct(A['boot'].hi[t])}" for t in F.UNIVERSE],
                          "Marginal ES per extra USD 1m": [usd(1e6*contrib.marginal_es_per_usd[t]) for t in F.UNIVERSE]})
    st.dataframe(table, hide_index=True, width="stretch")
    raw = pd.DataFrame({"weight": contrib.weight, "component_var_usd": pd.Series(cvar["components"]),
                        "component_es_usd": contrib.es_usd, "es_share": contrib.es_share,
                        "es_share_lo": A["boot"].lo, "es_share_hi": A["boot"].hi,
                        "marginal_es_per_usd": contrib.marginal_es_per_usd, "vol_share": contrib.vol_contribution})
    st.download_button("Download contributions (CSV)", raw.to_csv().encode(), f"risk_contributions_{alpha:.2f}.csv", "text/csv")
    st.caption(f"Component ES adds up to portfolio ES exactly (residual {usd(tot['residual_usd'], 2)}). Component VaR averages "
               f"each ETF's loss on the {cvar['scenarios']} days ranked around the VaR day, an estimate: its parts differ from "
               f"VaR by {usd(cvar['residual_usd'])}. Share intervals: 500 circular 20-day block resamples of whole rows. "
               "Marginal ES adds USD 1m to one ETF without selling another, so the fund grows; see position sizing for funded moves. "
               "A negative contribution would mean the ETF gained on the portfolio's worst days; none is clipped.")

    st.subheader("Position sizing: moving USD 1m between ETFs")
    sw = A["swaps"]
    grid = sw.pivot(index="from", columns="to", values="exact_usd").reindex(index=F.UNIVERSE, columns=F.UNIVERSE)
    for _, r in sw[~sw.feasible].iterrows():
        grid.loc[r["from"], r["to"]] = np.nan
    st.dataframe(grid.map(lambda v: "" if pd.isna(v) else usd(v)).rename_axis("Sell (row), buy (column)"), width="stretch")
    best = sw[sw.feasible].sort_values("exact_usd").iloc[0]
    gap = (sw.exact_usd - sw.first_order_usd).abs()[sw.feasible].max()
    st.caption(f"Exact change in historical {lvl} ES, recomputed after each move with the NAV unchanged. Blank: the ETF "
               f"holds less than USD 1m, or the same ETF. The best single move is {best['from']} to {best['to']} "
               f"({usd(best['exact_usd'])}). The marginal-ES shortcut differs from the exact figure by at most {usd(gap)}, "
               "because the worst days change as the weights change.")

    st.subheader(f"Risk budget: XLE's tail share and what reducing it would cost")
    tilt = A["tilt"]
    fig = go.Figure(go.Scatter(x=tilt.mean_annual, y=tilt.es_usd, mode="lines+markers+text",
                               text=[f"{m:.0%}" for m in tilt.moved], textposition="top right", marker=dict(color=ACCENT),
                               customdata=tilt.share, hovertemplate="moved %{text}<br>mean return %{x:.2%}<br>ES USD %{y:,.0f}"
                               "<br>XLE share %{customdata:.1%}<extra></extra>"))
    style(fig, 300, y=f"Historical {lvl} ES (USD)", legend=False).update_xaxes(title="Historical mean annual return", tickformat=".1%")
    st.plotly_chart(fig, width="stretch")
    st.caption("What-if, not part of the strategy: XLE weight moved to AGG in 2-point steps (labels), today's target, full "
               "history. Mean return is the arithmetic historical average of these fixed weights, hindsight. The monthly rule "
               "would reset any manual change unless the rule itself were changed.")
    st.dataframe(pd.DataFrame({"XLE moved to AGG": [pct(m, 0) for m in tilt.moved], f"ES {lvl}": [usd(v) for v in tilt.es_usd],
                               "XLE share of ES": [pct(v) for v in tilt.share],
                               "Mean annual return": [pct(v, 2) for v in tilt.mean_annual]}), hide_index=True, width="stretch")

    st.subheader("How stable are the shares?")
    mc_share, mc_es = A["mc"]
    rob = A["robust"].copy()
    rob.loc[f"Multivariate-t Monte Carlo, {lvl}"] = mc_share
    st.dataframe(rob.map(pct), width="stretch")
    st.caption(f"Each row splits ES by ETF for today's target. Last 750 days: the same window as the volatility shares. "
               f"Monte Carlo check: 200,000 joint draws of daily log returns from a multivariate t with 5 degrees of freedom "
               f"(fixed, not fitted) and the sample covariance; its portfolio ES is {usd(mc_es)}. A symmetric t cannot copy "
               "the joint energy-equity crashes, so its shares are flatter than history's.")

    hist = A["history"]
    st.subheader(f"{lvl} ES share of each month's target since {hist.index[0]:%Y}")
    fig = go.Figure()
    for t, color in zip(F.UNIVERSE, ("#2a78d6", "#9ec3ef", "#c9a227", "#c0504d")):
        fig.add_trace(go.Scatter(x=hist.index, y=hist[t], name=t, line=dict(color=color, width=2),
                                 hovertemplate="%{y:.1%}<extra>" + t + "</extra>"))
    style(fig, 320, y="Share of ES").update_yaxes(tickformat=".0%")
    shade_crises(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption("Each point: the target set at that month-end (half of SPY and XLE in cash when the overlay was on), with ES "
               "measured on data up to that date only.")

    st.subheader("Who did the damage in the required crises")
    cr = A["crisis"]
    if cr.empty:
        st.write("The strategy path starts after these crises.")
    else:
        fig = go.Figure()
        for t, color in zip(F.UNIVERSE, ("#2a78d6", "#9ec3ef", "#c9a227", "#c0504d")):
            s = cr[cr.etf == t]
            fig.add_trace(go.Bar(x=s.scenario, y=s.pnl_usd, name=t, marker=dict(color=color, cornerradius=3),
                                 customdata=np.c_[s.etf_return, s.weight_at_start],
                                 hovertemplate="%{x}: USD %{y:,.0f}<br>ETF return %{customdata[0]:.1%}, weight at start "
                                 "%{customdata[1]:.1%}<extra>" + t + "</extra>"))
        style(fig, 320, y="P&L (USD)").update_layout(barmode="group", hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        lines = []
        for name, g in cr.groupby("scenario", sort=False):
            worst_ret = g.loc[g.etf_return.idxmin()]; worst_pnl = g.loc[g.pnl_usd.idxmin()]
            lines.append(f"- **{name}:** largest fall {worst_ret.etf} ({pct(worst_ret.etf_return)}); largest dollar loss "
                         f"{worst_pnl.etf} ({usd(worst_pnl.pnl_usd)}).")
        st.markdown("\n".join(lines))
        st.caption("Strategy path as run, with monthly rebalancing and the overlay. The biggest faller and the biggest dollar "
                   "loss differ when the weights differ.")

    cut = tilt[tilt.share <= .25 + 1e-9]
    st.info(f"**Reading.** Risk parity spreads everyday volatility evenly, not crash losses. On the worst {100*(1-alpha):.0f}% of "
            f"days {top} carries {pct(contrib.es_share[top])} of ES with {pct(W[top])} of the capital (95% interval "
            f"{pct(A['boot'].lo[top])} to {pct(A['boot'].hi[top])}), because energy and US equities crash together. "
            f"Moving USD 1m from {best['from']} to {best['to']} cuts ES by {usd(-best['exact_usd'])}. "
            + (f"Bringing XLE to a 25% share would need about {pct(cut.moved.iloc[0], 0)} of NAV moved to AGG, "
               f"at {pct(tilt.mean_annual.iloc[0]-cut.mean_annual.iloc[0], 2)} a year of historical return. "
               if len(cut) else "")
            + "Monitoring: report the XLE share of ES each month, beside its weight.")


def page_limits():
    st.title("Assumptions & Limitations")
    st.caption("What this analysis does not capture, in plain language.")
    test, _ = reserve(EV["data_hash"], json.dumps(CFG, sort_keys=True)); r25 = test["results"][-1]
    reserve_line = (f"In a {r25['year']}-year test that resamples the strategy's own monthly returns, every cash reserve was paid in "
                    f"{pct(r25['all_payments_funded'])} of paths, but the USD 10m was kept in real terms in only "
                    f"{pct(r25['real_capital_preserved'])}: the reserve grows {pct(CFG['reserve_growth'], 2)} a year, matching the fixed CPI assumption used for this simulation. "
                    "These are illustrations from one history, not forecasts.")
    ge, fhs = (next(v for v in SUMMARY["validation"] if v["method"] == m and v["alpha"] == .99) for m in ("garch_evt", "fhs"))
    backtest_line = (monitoring_note(ge, fhs) + " Breaches cluster mostly around the months the overlay switches. Under the "
                     "team's own pre-registered rule this is recorded as evaluation incomplete; the owner adopted v6 knowing it "
                     "(31 October 2026).")
    inflation_line = (f"{pct(CFG['inflation'], 2)} a year: the average US CPI inflation (FRED CPIAUCSL index ratio) from "
                      f"{DATA_START:%d %B %Y} to {CFG['snapshot_end']}.")
    st.markdown("""
**About the choice of portfolio**
- This strategy was chosen after many alternatives had been tried on the same DATA_SPAN data. Every number here is hindsight:
  there is no untouched test period. Good past results may partly reflect that search.
- RESERVE_LINE

**About the risk numbers**
- VaR is not the most we can lose. It is a loss level that is exceeded about once in 100 days at 99%. Bigger losses happen.
- Expected Shortfall is the average of the bad days, not a cap. A worse day than any in the data is possible.
- All models learn from DATA_SPAN. A crisis unlike any in that period (for example, a long inflation decade) may not be captured.
- The extreme-value (EVT) estimate rests on a few hundred bad days and a threshold rule we chose. A different threshold gives a
  somewhat different answer (see the EVT page).
- The risk numbers assume today's weights are held for a day. Over weeks, losses compound and monthly rebalancing changes the
  weights; multi-day risk is not the one-day figure times a square root.
- BACKTEST_LINE

**About the recession overlay**
- It uses the yield curve (inverted at some point in the last 24 months) confirmed by SPY below its 12-month average. The curve
  preceded every US recession since 1969 but also gave false alarms (1966, 2022); the price check filters most of them.
- Only two recessions (2008 and 2020) fall inside the data, so the overlay's benefit rests mostly on economic reasoning
  and the 60-year signal record, not on many tested episodes.
- It holds cash (0%) while on. Cash is outside the brief's seven-ETF list; this is a disclosed policy choice.
- It does not help in an inflation shock without a recession, such as 2022.
- The rules were written in a session that had seen these crises; every number has a stated economic or published reason.

**About the portfolio**
- Risk parity balances everyday volatility. It does not balance crash losses: energy and US stocks carry most of the tail risk.
- Bonds did not protect in 2022, when stocks and bonds fell together. Gold helped in 2008 but not in March 2020.
- The weights change once a month. A shock that happens within a month (COVID took five weeks) is met with last month's weights.
- The covariance is estimated from recent data and can be wrong when relationships change suddenly.

**About implementation**
- Trading costs are assumed to be zero. Real costs, bid-ask spreads and market impact in a stressed month would
  lower returns a little (turnover is about TURNOVER× NAV a year on this model's own path).
- Adjusted closing prices from Yahoo Finance are used: dividends are reinvested, and fund fees are already in the prices.
- No taxes, currency effects, cash yield on the reserve or new contributions are modelled. The reserve itself is assumed paid out.
- Real returns use one inflation rate, INFLATION_LINE That is US consumer inflation; a university's own
  costs (salaries, research, construction) can rise faster. CPI is a revised series with an approximate publication lag, not
  what was known at the time, and a single average hides high-inflation years such as 2022.

**About the data**
- Only seven ETFs are eligible and this portfolio uses four. The common history used here starts on DATA_FIRST
  (GLD first traded on 18 November 2004); earlier crises such as the 2000-2002 dot-com crash cannot be replayed with bonds and gold.
- Suspected data errors were flagged and kept, not deleted. Genuine crash days remain in the data.

**About human review**
- AI tools (Claude Code, Codex, Antigravity) helped write the code and documents. Independent human review of the calculations and the
  investment judgement is still pending, and solo entry eligibility has not been confirmed by the organisers.
""".replace("TURNOVER", f"{PATH.turnover.sum()/((PATH.index[-1] - PATH.index[0]).days/365.25):.2f}").replace("RESERVE_LINE", reserve_line).replace("DATA_FIRST", f"{DATA_START:%d %B %Y}").replace("DATA_SPAN", DATA_SPAN).replace("BACKTEST_LINE", backtest_line)
       .replace("INFLATION_LINE", inflation_line))


def page_data():
    st.title("Data & provenance")
    meta = EV["meta"]; ST = meta.get("settings") or meta["strategy"]
    OV = ("\n- **Recession overlay (v6):** 10-year minus 3-month T-bill spread from FRED DGS10 and DTB3 (in the frozen raw data); "
          "SPY 12-month average from the frozen prices. Unemployment (UNRATE) and the Baa credit spread (BAA10Y) were supplied by "
          "the owner from FRED and are kept with SHA-256 hashes in `context/fred/` (tested, not used by the rule).")
    st.markdown(f"""
- **Prices:** Yahoo Finance adjusted closes via yfinance, frozen snapshot to {CFG['snapshot_end']} (`data/clean/prices_clean.csv`,
  SHA-256 `{EV['data_hash'][:16]}…`). Trading calendars aligned; anomalies flagged, not deleted.
- **Risk-free rate:** FRED DTB3, converted from a discount basis to a bond-equivalent daily rate.
- **Inflation:** FRED CPIAUCSL (US CPI, all urban consumers), index ratios as available on each date; never the level as a rate.
  Policy rate {pct(CFG['inflation'], 2)} a year = average from {DATA_START:%d %B %Y} to {CFG['snapshot_end']} (mandate {CFG['mandate']}).
- **Strategy evidence:** `results/{EV['run']}/` (strategy pre-registered at tag `{meta['prereg_tag']}`, policy tag
  `{meta.get('policy_tag', meta['prereg_tag'])}`, created {meta['created']}).
  Strategy hash `{SH}` on every forecast row; the dashboard refuses forecasts with another hash or a changed price file.
- **Settings:** EWMA λ = {ST['ewma_lambda']}, window {ST['window']} days, first target after
  {ST['min_history']} days, month-end decisions, universe SPY, AGG, GLD, XLE.{OV}
- **Settings read from** `config/final.yaml`: NAV, seed, Monte Carlo size, rolling window and refit interval.
- **Model shown:** v6, monthly dynamic EWMA risk parity with the recession overlay (final). The v5 core is the same strategy without the overlay.
- **Technical report (v5 wording, not yet regenerated for v6):** `results/final-report-r1/technical_report.pdf`, built by `python -m quanedge.final_report` from the same
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
            "python -m quanedge.universe              # rebuilds results/universe-r3 (why these four ETFs)\n"
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


TRIED = [
    # (group, model, what it is, mathematical result, economic reason, decision)
    ("Fixed weights", "Maximum-return CVaR LP (original v1 selection)",
     "Highest expected return with a historical CVaR99 budget, fixed weights.",
     "GFC path drawdown 23.4%; expected return rests on estimated means, which are noisy.",
     "Return-chasing tilts towards equities, which all fall together in a crisis; a conservative endowment cannot absorb that.",
     "Removed"),
    ("Fixed weights", "Minimum CVaR (SPY 15 / AGG 70 / GLD 15; later SPY 6 / AGG 88 / GLD 6)",
     "Lowest historical 99% tail loss.",
     "Smallest crisis losses, but realised real CAGR about 0.3% (2005-2026); its own FHS forecasts breached 41 vs 24.5 expected (Kupiec p 0.002). "
     "Expected return clears inflation only under 50% mean shrinkage.",
     "Almost all bonds: protects in equity crashes but lost 11-16% in the 2020-22 bond bear and does not grow real capital for scholarships.",
     "Removed (previous recommendation)"),
    ("Fixed weights", "Minimum variance", "Lowest volatility from the covariance matrix.",
     "Same bond concentration as minimum CVaR; real CAGR about 0.1%; risk forecasts failed coverage.",
     "Variance treats bonds as riskless; 2022 showed rates risk is real.", "Removed"),
    ("Fixed weights", "Maximum Sharpe (Markowitz tangency)", "Best return per unit of volatility on estimated means.",
     "Very sensitive to small changes in expected returns; forecasts failed coverage.",
     "Estimated means are the least reliable input; the optimiser maximises estimation error.", "Removed"),
    ("Fixed weights", "Inverse variance / inverse volatility",
     "Weights proportional to 1/variance or 1/volatility; ignores correlation.",
     "Inverse variance ~83% AGG, real CAGR 0.7%; inverse volatility GFC drawdown 19.2% and clustered breaches (conditional coverage p 0.011).",
     "Ignores that SPY and XLE move together, so equity risk is double-counted less than it should be.", "Removed"),
    ("Fixed weights", "Static risk parity (equal risk contribution, full sample)",
     "Each ETF contributes 25% of volatility, weights fixed.",
     "CAGR 6.5%, but GFC drawdown 18-19% and buy-and-hold drift to 43% equity (GFC fall 21.4%); breaches clustered.",
     "Right idea (balance risk, not dollars), but a fixed covariance does not react when volatility regimes change.",
     "Replaced by the dynamic version"),
    ("Fixed weights", "Benchmarks: 60/40, 40/60, permanent 25/50/25, balanced 35/50/15, equal weight",
     "Simple policy mixes for comparison.",
     "60/40 max fall 35%; equal weight high return but large crisis losses; permanent and balanced reasonable but not risk-based.",
     "Fixed dollar mixes do not adjust to which asset is risky now.", "Kept as comparisons only"),
    ("Fixed weights", "Minimum CVaR with a 4% real return target (SPY 28 / AGG 42 / GLD 30)",
     "Lowest tail loss subject to earning the 4% real needed to fund the reserve.",
     "Only allocation that earned it historically (4.2% real vs 4.17% break-even), but GFC fall 19.9%; under shrunk means the same "
     "target picks SPY 12 / AGG 77 / GLD 11, which earned 1.2% real. No backtest of its own forecasts.",
     "A 4% real return and a conservative loss limit barely coexist with these assets; the answer depends on unreliable mean estimates.",
     "Not adopted"),
    ("Fixed weights", "Return-maximising CVaR LP with stress-loss caps (15% / 12%)",
     "Original selection rule plus a cap on buy-and-hold loss in each named crisis.",
     "12% cap: max decline 18.8%, CAGR 6.86%.",
     "The caps are fitted to crises already observed; the next crisis will differ.", "Removed"),
    ("Fixed weights", "Rebalancing rules: daily, monthly, quarterly, annual, 5/10-point bands, never",
     "Same weights, different trading schedule.",
     "Any rule trading at least yearly or on a band keeps ES99 near target; never rebalancing lifts risk-parity ES99 from USD 165k to "
     "209k and its GFC fall to 21.4%. Daily is not safer.",
     "Without rebalancing the winners (equities) grow into a larger risk share; too frequent trading only adds cost.",
     "Quarterly + 5-point band kept for fixed mixes"),
    ("Hedges", "XLE 5% / 10% funded from SPY",
     "Energy as a long-only inflation hedge.",
     "On the min-CVaR mix: 2022 path -15.3% to -8.8%, worst year -11.9% to -4.8%; but COVID -6.5% to -8.8%, ES99 1.43% to 1.53%.",
     "Energy earns in supply-driven inflation (2022) and falls in demand crashes (2008, 2020). Kept as an idea: risk parity holds XLE anyway.",
     "Absorbed into the final model"),
    ("Hedges", "Pairs trading and market-neutral investing",
     "Long one ETF, short another.",
     "Not tested: no stable cointegrated pair among the seven ETFs.",
     "Shorting adds borrowing cost, margin and unlimited loss; market-neutral earns roughly cash, below the spending need.",
     "Rejected before testing"),
    ("Hedges", "Cash sleeve and expected-shortfall caps",
     "Hold part of the fund in cash, or cut weights whenever ES99 exceeds a cap.",
     "Scratch tests in the v6 session (not saved): cash permanently lowers return; ES caps act only after volatility has risen.",
     "Permanent cash fails the growth objective; the recession overlay uses cash only when an economic signal says so.",
     "Removed (overlay kept instead)"),
    ("Universe", "All seven ETFs (with EFA, EEM, XLK)", "Risk parity or optimisers over the full list.",
     "EFA/EEM/XLK correlate 0.82-0.91 with SPY; they add only 0.18 independent bets; seven-ETF risk parity puts 71% of risk in equities "
     "and breaches a 22% fall.",
     "Foreign and tech equity are the same global equity factor in a crisis; more tickers is not more diversification.",
     "Reduced to SPY, AGG, GLD, XLE"),
    ("Timing rules", "Drawdown bands and CPPI risk budgets",
     "Cut risk as the portfolio falls from its peak.",
     "Max decline 27.0% to 21-23% on the risky mix; almost no effect on the defensive mix; lower CAGR, more turnover.",
     "Sells after losses and buys back late; in October 2008 even bonds fell, so de-risking could not avoid the drop.", "Removed"),
    ("Timing rules", "EWMA volatility overlay on the original selection (PORT-005)",
     "Scale equity to its long-run volatility each week; freed weight to AGG then GLD.",
     "GFC drawdown 23.4% to 19.4% (0.6 pt inside the limit), Kupiec p 0.068; walk-forward 2017-2026 CAGR 9.0% vs 10.5% static. "
     "Turnover 0.67x vs 0.16x.",
     "Most of the benefit came from 2008, which the design had already seen; thin margins.", "Removed"),
    ("Timing rules", "EWMA volatility-target overlay (v4c with risk parity)",
     "Scale equity down when short-run volatility is high.",
     "Lower drawdown but breaches strongly clustered (conditional coverage p 0.0005); CAGR 6.3% vs 6.9%.",
     "Volatility reacts after a shock starts; it was idle in slow crises (2018, oil, 2022 bond bear).", "Removed"),
    ("Timing rules", "Winner-to-loser rebalancing (sell after +10%, buy the faller)",
     "Contrarian switching between ETFs.",
     "No reversal signal; best variant broke concentration (52% gold).",
     "Asset momentum persists over months; selling winners fights it.", "Rejected"),
    ("Timing rules", "Correlation triggers (SPY-AGG > +0.3, < -0.25, any pair < -0.5)",
     "Shift SPY to GLD or rebalance when correlation crosses a threshold.",
     "2022 signal fired only in Sep 2022, after the losses; gains within +/-0.3 pt CAGR across settings; thresholds chosen with hindsight.",
     "Correlation measures co-movement, not the size of moves; risk parity's covariance already reacts to it.", "Removed"),
    ("Timing rules", "Relative bands and capped dip-buying ladder",
     "Buy SPY/GLD/XLE after 30-45% falls from the 3-year high.",
     "+0.2 pt CAGR but ES99 +0.28 pt and deeper GFC/COVID losses; XLE re-triggered repeatedly while falling.",
     "Buying falling assets catches crashes early (XLE fell 71% 2014-2020); unsuitable for a conservative client.", "Removed"),
    ("Timing rules", "Trend filters, GARCH panic rule, momentum for XLE, Markov regimes",
     "Exit risky assets on trend breaks or volatility spikes.",
     "XLE momentum not significant (t = -0.22); trend filters cut drawdown but lowered CAGR with high turnover.",
     "Price-only signals are noisy and whipsaw; no economic reason for them to work in advance.", "Removed"),
    ("Recession signals", "Sahm rule (unemployment) and credit spread",
     "Macro signals for recessions.",
     "Sahm confirmed 6 of 8 recessions 2-9 months late; credit spread above its 12-month mean on in 143 non-recession months.",
     "Unemployment is a lagging indicator; spreads react to many non-recession shocks.", "Not used in the rule"),
    ("Dynamic optimisers", "Dynamic minimum variance and minimum CVaR (monthly)",
     "Re-optimised each month-end on data to date.",
     "CAGR 3.8% and 4.3% (2007-2026); stay 55-100% AGG.",
     "Updating the inputs does not change the optimiser's preference for bonds.", "Removed"),
    ("Dynamic optimisers", "Walk-forward yearly re-selection",
     "Re-run the selection rule each January on prior data only.",
     "Used to check the procedure, not as a portfolio: 2017-2026 CAGR 10.5% static, max decline 19.6%.",
     "Shows how a rule would have behaved without seeing the future; it is a validation, not a strategy.",
     "Validation only"),
    ("Dynamic risk parity", "Risk parity on 1-year, 3-year and full-history covariance",
     "Same equal-risk rule, different look-back window.",
     "Shorter windows hold more equity (ES99 1.72% full history to 2.04% one year); no window predicted next year's risk shares well "
     "(16-18 point miss). 1-year version: CAGR 6.06%, max decline 18.1%.",
     "Short windows chase calm periods; the EWMA keeps the long window but weights recent data more.", "Replaced by EWMA"),
    ("Dynamic risk parity", "Weekly and quarterly EWMA risk parity",
     "Same as final model, different rebalancing frequency.",
     "Weekly: GFC drawdown 20.7%, turnover 1.7x; quarterly: COVID -12.9%, too slow.",
     "Volatility half-lives are 1-2 months (SPY 34 days); weekly chases noise, quarterly misses shocks.", "Removed"),
    ("Final", "Monthly EWMA risk parity (v5 core)",
     "Equal risk contributions from an EWMA covariance (lambda 0.97), re-estimated each month-end.",
     "CAGR 6.16% since 2006, max decline 18.5%, GARCH-EVT backtest 26 vs 24.5 breaches (Kupiec p 0.76).",
     "Balances risk across equity, bonds, gold and energy and updates at the pace macro data arrives.", "Kept as the core"),
    ("Final", "Same strategy on data from 18 Nov 2004 with 2.62% CPI (v7)",
     "v5 core with two more months of data and a matching inflation figure.",
     "The dashboard was built on it (branch backup/local-v7-20261031); no full run of it is recorded.",
     "Same economics as v5; the change was the data start, not the model.", "Not carried forward (main reset to v6)"),
    ("Final", "v5 core + yield-curve recession overlay (v6)",
     "Half of SPY and XLE to cash when the curve inverted in the last 24 months and SPY is below its 12-month average.",
     "CAGR 6.30%, max decline 13.9%; breach count matched but breaches clustered (disclosed).",
     "Yield-curve inversion preceded all 8 US recessions since 1969; the price check filters false alarms.", "Final model"),
]


def page_tried():
    st.title("Models we tried")
    st.caption("Every portfolio approach tested before the final model, and why it was kept or removed. All results are "
               "retrospective on the same 2005-2026 data (hindsight; no untouched test period). Figures are from the "
               "project's recorded studies; see AGENTS.md section 17 and PLAN.md sections 13 and 19.")
    df = pd.DataFrame(TRIED, columns=["Group", "Model", "What it does", "Mathematical evidence", "Economic reason", "Decision"])
    group = st.multiselect("Show groups", list(dict.fromkeys(df.Group)), default=list(dict.fromkeys(df.Group)))
    df = df[df.Group.isin(group)]
    st.dataframe(df[["Group", "Model", "Decision"]].set_index("Model"), use_container_width=True)
    for _, r in df.iterrows():
        with st.expander(f"{r.Model} — {r.Decision}"):
            st.markdown(f"**What it does.** {r['What it does']}\n\n**Mathematical evidence.** {r['Mathematical evidence']}"
                        f"\n\n**Economic reason.** {r['Economic reason']}")
    st.subheader("What the search taught us")
    st.markdown("- Optimisers that rely on expected returns are unstable; risk-based weights are more robust.\n"
                "- The seven ETFs hold one big equity factor; real diversifiers are bonds, gold and, partly, energy.\n"
                "- Price-based timing rules react after losses; only an economic leading signal (the yield curve) acted in advance.\n"
                "- Monthly updating matches how fast volatility decays and how often macro data arrives.")


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
         st.Page(page_data, title="Data & provenance", url_path="data"),
         st.Page(page_tried, title="Models we tried", url_path="tried")]
nav = st.navigation(pages)
SETTINGS = sidebar()
nav.run()
