"""One-page executive tear sheet for the final model (v6): monthly dynamic EWMA risk parity with a recession overlay.

Written for the investment committee. Every number comes from the committee dashboard's own evidence and
functions (quanedge/final_portfolio.py with model "v6", results/recession-overlay-r1, the frozen price
snapshot and config/final.yaml), so the page matches the dashboard. The v5 core (results/dynamic-parity-r1)
and 40/60 SPY/AGG are shown for comparison. Writes results/tear-sheet-v6-r1/: executive_tear_sheet.pdf,
wealth_drawdown.png, numbers.json (the figures quoted) and manifest.json (input and output hashes).

    python -m quanedge.tear_sheet
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from . import config
from . import final_portfolio as F
from .final_report import (ACCENT, COLOR, CRITICAL, INK, INK2, MUTED, NEUTRAL, RULE, ROLE, TINT, git_rev, jsonable, num, pct,
                           pval, sha, usd, usdm)

OUT = config.RESULTS_DIR/"tear-sheet-v6-r1"
REPORT = config.RESULTS_DIR/"final-report-r1"       # v5 report: its bootstrap is reused only for identical weights
U = F.UNIVERSE
PREPARED = "31 Oct 2026"
OVERLAY = "#eda100"


def date(d):
    d = pd.Timestamp(d)
    return f"{d.day} {d:%b %Y}"


def periods(months):
    """Consecutive 'YYYY-MM' months as [first, last] runs."""
    runs = []
    for p in (pd.Period(m, "M") for m in months):
        if runs and p == runs[-1][1]+1:
            runs[-1][1] = p
        else:
            runs.append([p, p])
    return runs


# ---------------------------------------------------------------- evidence
def bootstrap_es99(returns, w, V):
    """95% bootstrap interval of historical ES99 for the current target. The v5 report computed it with the
    same call and inputs; reuse it when the weights are identical and the file matches the report's
    manifest, otherwise recompute."""
    try:
        man = json.loads((REPORT/"manifest.json").read_text(encoding="utf-8"))
        same = json.loads((REPORT/"numbers.json").read_text(encoding="utf-8"))["weights"] == w
        if same and man["outputs"]["tables/bootstrap.csv"] == sha(REPORT/"tables/bootstrap.csv"):
            b = pd.read_csv(REPORT/"tables/bootstrap.csv")
            r = b[(b.method == "historical") & np.isclose(b.alpha, .99)].iloc[0]
            return [float(r.es_usd_lo), float(r.es_usd_hi)], "final-report-r1 (identical weights and inputs)"
    except (OSError, KeyError, ValueError, IndexError):
        pass
    b = F.bootstrap(returns, w, V)
    r = b[(b.method == "historical") & np.isclose(b.alpha, .99)].iloc[0]
    return [float(r.es_usd_lo), float(r.es_usd_hi)], "recomputed"


def gather(root=None):
    """The figures the tear sheet quotes and the series it draws, for v6 with the v5 core and 40/60 beside it."""
    root = root or config.ROOT
    e6, e5 = F.load_evidence(root, model="v6"), F.load_evidence(root, model="v5")
    prices, returns, rf, cpi = F.load_market(root)
    cfg = F.policy(); V = float(cfg["value"]); p6, p5 = e6["path"], e5["path"]
    w = F.current_target(p6)
    perf6, perf5 = F.performance(p6, returns, rf, cpi), F.performance(p5, returns, rf, cpi)
    bench = F.benchmark_returns(returns).reindex(p6.index)
    kb = F.kpis(bench, rf, returns.SPY, bench); kb["real_cagr"] = F.cpi_real(bench, cpi)[2]
    wealth = {"v6": F.wealth_usd(p6["return"], V), "v5": F.wealth_usd(p5["return"], V), "40/60": F.wealth_usd(bench, V)}
    _, table = F.risk_now(returns, w, V)
    t99 = table[np.isclose(table.alpha, .99)].set_index("label")
    contrib, tot = F.risk_contributions(returns, w, .99, V)
    s6, hyp, _ = F.stress_panel(p6, prices, returns, w, V)
    s5 = {s["scenario"]: s["path"] for s in F.stress_panel(p5, prices, returns, w, V)[0] if s.get("path")}
    bt = {m: F.backtest(e6["forecasts"], e6["strategy_hash"], m, .99, cfg["evaluation_start"], cfg["snapshot_end"])[0]
          for m in (cfg["challenger"], cfg["primary"])}
    bt5 = F.backtest(e5["forecasts"], e5["strategy_hash"], cfg["challenger"], .99, cfg["evaluation_start"], cfg["snapshot_end"])[0]
    latest = {m: F.latest_forecast(e6["forecasts"], m, .99, V) for m in (cfg["challenger"], cfg["primary"])}
    res25 = next(r for r in F.reserve_test(p6, cfg)["results"] if r["year"] == 25)
    interval, interval_source = bootstrap_es99(returns, w, V)
    stress = {}
    for s in s6:
        if not s.get("path"):
            continue
        a, b = s["start"], s["end"]
        stress[s["scenario"]] = {"start": a, "end": b, "return": s["path"]["return"], "loss_usd": s["path"]["loss_usd"],
                                 "max_fall": s["path"]["max_fall"], "v5_return": s5[s["scenario"]]["return"],
                                 "bench_return": F.window_return(wealth["40/60"], a, b),
                                 "held_max_fall": -s["today_buy_hold"]["drawdown"], "pnl_usd": s["path"]["pnl_usd"]}
    months = e6["summary"]["overlay_months_on"]
    Q = {"model": "v6", "value": V, "fund": float(cfg["fund_value"]), "start": str(p6.index[0].date()), "end": str(p6.index[-1].date()),
         "weights": w, "cash": 1-sum(w.values()), "usd": {t: V*w[t] for t in U},
         "vol_share": contrib.vol_contribution.to_dict(), "es_share": contrib.es_share.to_dict(),
         "diversification_benefit_usd": tot["diversification_benefit_usd"],
         "overlay_on_now": bool(p6["overlay_on"].iloc[-1]), "overlay_months": len(months),
         "months": int(len((1+p6["return"]).resample("ME").prod()))-1,     # the first month is partial
         "overlay_periods": [[str(a), str(b)] for a, b in periods(months)],
         "performance": {"v6": perf6, "v5": perf5, "40/60": kb},
         "models_99": {k: {"var_usd": float(r.var_usd), "es_usd": float(r.es_usd)} for k, r in t99.iterrows()},
         "es99_interval": interval, "es99_interval_source": interval_source,
         "latest_99": latest, "backtest": bt, "backtest_v5_challenger": bt5, "stress": stress,
         "hypothetical": {"shocks": {t: hyp["shocks"][t] for t in U}, "return": hyp["return"], "loss_usd": hyp["loss_usd"]},
         "reserve_25y": {"all_paid": res25["all_payments_funded"], "real_kept": res25["real_capital_preserved"],
                         "median_real_usd": res25["median_real_balance_usd"]},
         "reserve_growth": cfg["reserve_growth"],
         "strategy_hash": e6["strategy_hash"], "strategy_hash_v5": e5["strategy_hash"], "data_hash": e6["data_hash"],
         "prereg_tag": e6["meta"]["prereg_tag"], "evidence_run": e6["run"], "evidence_run_v5": e5["run"]}
    return Q, {"wealth": wealth, "overlay_on": p6["overlay_on"].astype(bool)}


# ---------------------------------------------------------------- chart
def chart(series, path):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.edgecolor": RULE, "axes.labelcolor": INK2,
                         "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})
    fig, (a, b) = plt.subplots(2, 1, figsize=(7.4, 2.1), sharex=True, gridspec_kw={"height_ratios": [2.1, 1], "hspace": .08})
    style = {"v6": (ACCENT, 1.4, "v6 final (with overlay)"), "v5": (MUTED, .9, "v5 core (no overlay)"),
             "40/60": (NEUTRAL, .9, "40/60 SPY/AGG")}
    on = series["overlay_on"]
    starts = on.index[on & ~on.shift(fill_value=False)]; ends = on.index[on & ~on.shift(-1, fill_value=False)]
    for ax in (a, b):
        for s, e in zip(starts, ends):
            ax.axvspan(s, e, color=OVERLAY, alpha=.18, lw=0)
    for k in ("40/60", "v5", "v6"):
        c, lw, label = style[k]; w = series["wealth"][k]
        a.plot(w.index, w/1e6, color=c, lw=lw, label=label, zorder=3 if k == "v6" else 2)
        b.plot(w.index, w/w.cummax()-1, color=c, lw=lw, zorder=3 if k == "v6" else 2)
    a.fill_between([], [], color=OVERLAY, alpha=.18, label="overlay on (cash held)")
    a.set_ylabel("USD million"); b.set_ylabel("Fall from high")
    b.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{100*x:.0f}%".replace("-", "−")))
    a.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, ncol=4, fontsize=6.6, borderaxespad=0)
    for ax in (a, b):
        ax.grid(axis="y", color=RULE, lw=.4)
    fig.savefig(path, dpi=220, bbox_inches="tight"); plt.close(fig)


# ---------------------------------------------------------------- page
def compose(Q, figure, path, footer):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import BaseDocTemplate, Frame, Image, PageTemplate, Paragraph, Spacer, Table, TableStyle
    base = Path(matplotlib.get_data_path())/"fonts"/"ttf"
    for name, file in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
                       ("DV-BI", "DejaVuSans-BoldOblique.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(base/file)))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")
    c = colors.HexColor
    body = ParagraphStyle("body", fontName="DV", fontSize=7.2, leading=9.2, textColor=c(INK), spaceAfter=0)
    small = ParagraphStyle("small", parent=body, fontSize=6.1, leading=7.7, textColor=c(INK2))
    cell = ParagraphStyle("cell", parent=body, fontSize=6.6, leading=8.0)
    cellr = ParagraphStyle("cellr", parent=cell, alignment=TA_RIGHT)
    head = ParagraphStyle("head", parent=cell, fontName="DV-B", textColor=c(INK2))
    headr = ParagraphStyle("headr", parent=head, alignment=TA_RIGHT)
    h2 = ParagraphStyle("h2", fontName="DV-B", fontSize=8.1, leading=10.2, textColor=c(ACCENT), spaceAfter=2.2)
    title = ParagraphStyle("title", fontName="DV-B", fontSize=14.2, leading=17, textColor=c(INK))
    sub = ParagraphStyle("sub", parent=body, fontSize=7.2, leading=9.3, textColor=c(INK2))
    left, right, top, bottom = 34, 34, 26, 38
    width = A4[0]-left-right; gap = 14; half = (width-gap)/2
    w, V = Q["weights"], Q["value"]
    p6, p5, pb = (Q["performance"][k] for k in ("v6", "v5", "40/60"))
    ge, fhs, ge5 = Q["backtest"]["garch_evt"], Q["backtest"]["fhs"], Q["backtest_v5_challenger"]

    def grid(header, rows, widths, align, total=False, highlight=None):
        hs = [Paragraph(h, headr if a == "r" else head) for h, a in zip(header, align)]
        data = [hs]+[[Paragraph(str(x), cellr if a == "r" else cell) for x, a in zip(r, align)] for r in rows]
        tb = Table(data, colWidths=widths, hAlign="LEFT")
        st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), .6, c(INK2)),
              ("LINEBELOW", (0, 1), (-1, -1), .25, c(RULE)), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
              ("RIGHTPADDING", (0, 0), (-1, -1), 2.5)]
        if total:
            st.append(("LINEABOVE", (0, len(rows)), (-1, len(rows)), .6, c(INK2)))
        if highlight is not None:
            st.append(("BACKGROUND", (0, highlight+1), (-1, highlight+1), c(TINT)))
        tb.setStyle(TableStyle(st))
        return tb

    def section(heading, *flow):
        return [Paragraph(heading, h2), *flow]

    def two(a, b):
        tb = Table([[a, b]], colWidths=[half+gap/2, half+gap/2])
        tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (0, -1), gap/2), ("RIGHTPADDING", (1, 0), (1, -1), 0),
                                ("LEFTPADDING", (1, 0), (1, -1), gap/2), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        return tb

    def box(paras):
        tb = Table([[paras]], colWidths=[width])
        tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c(TINT)), ("LINEBEFORE", (0, 0), (0, -1), 2.2, c(ACCENT)),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5)]))
        return tb

    swatch = lambda t: f'<font color="{COLOR[t]}">■</font> <b>{t}</b>'
    S = Q["stress"]; worst = max(S, key=lambda k: S[k]["loss_usd"]); hyp = Q["hypothetical"]; r25 = Q["reserve_25y"]
    held_over = [k for k in ("GFC", "COVID") if S[k]["held_max_fall"] > -p6["maximum_drawdown"]]
    lg, lf = Q["latest_99"]["garch_evt"], Q["latest_99"]["fhs"]
    story = [Paragraph("Executive tear sheet · Serendib University Endowment Fund", title), Spacer(1, 2),
             Paragraph(f"Final model v6: monthly dynamic risk parity across SPY, AGG, GLD and XLE with a recession overlay · "
                       f"{usdm(V, 1)} invested of the {usdm(Q['fund'], 0)} fund after the first-year cash reserve · data "
                       f"{date('2005-01-03')} to {date(Q['end'])} · prepared {PREPARED} · Team Ghosted (solo entry) · Quant Edge 1.0 final",
                       sub), Spacer(1, 5)]

    rec = [Paragraph("<b>Recommendation: hold this portfolio (v6, the owner's final model).</b> From 1 October 2026 hold "
                     + ", ".join(f"{t} {pct(w[t])}" for t in U)
                     + ". At every month-end close reset to equal-risk weights (EWMA covariance, λ 0.97, 750 days), and while the yield "
                     "curve (10-year minus 3-month) has been inverted in the last 24 months <i>and</i> SPY closes below its 12-month "
                     "average, hold half of SPY and XLE in cash; the overlay is "
                     + ("<b>on</b>" if Q["overlay_on_now"] else "<b>off</b>") + f" at the {date(Q['end'])} close. "
                     f"Monitor one-day 99% VaR daily with GARCH-EVT (latest {usd(lg['var_usd'])}; FHS {usd(lf['var_usd'])}), using the "
                     "higher of the two in any month the overlay switches. Call an extra committee review if the fall from the previous "
                     "high passes 15% or 99% VaR breaches exceed 9 in any 250 days.",
                     ParagraphStyle("r", parent=body, fontSize=7.4, leading=9.6)),
           Spacer(1, 2.5),
           Paragraph(f"<b>Disclosed:</b> under the team's pre-registered rule v6 is <i>evaluation incomplete</i>: its VaR breach counts "
                     f"match the 99% level but breaches cluster (conditional coverage p {pval(ge['conditional_coverage_p'])} GARCH-EVT, "
                     f"{pval(fhs['conditional_coverage_p'])} FHS). The owner adopted it for its smaller falls; the v5 core passes with "
                     f"GARCH-EVT (p {pval(ge5['conditional_coverage_p'])}). <b>Main risk accepted:</b> a crash before the next month-end "
                     f"meets today's weights; held through the {' and '.join(held_over)} they would have fallen "
                     f"{' and '.join(pct(S[k]['held_max_fall']) for k in held_over)}. Team proposal; independent human review pending.",
                     ParagraphStyle("r2", parent=body, fontSize=6.8, leading=8.8, textColor=c(INK2)))]
    story += [box(rec), Spacer(1, 6)]

    alloc_rows = [[swatch(t), ROLE[t], pct(w[t]), num(Q["usd"][t]), pct(Q["vol_share"][t]), pct(Q["es_share"][t])] for t in U]
    alloc_rows.append(["<b>Total</b>", "cash " + pct(Q["cash"]), pct(sum(w.values())), num(V*sum(w.values())), "100.0%", "100.0%"])
    mon = lambda p: pd.Period(p, "M").strftime("%b %Y")
    periods_txt = "; ".join(mon(a) + ("" if a == b else f"–{mon(b)}") for a, b in Q["overlay_periods"])
    alloc = section("Allocation to hold now", grid(["ETF", "Exposure", "Weight", "USD", "Vol. share", "ES99 share"], alloc_rows,
                    [.14*half, .29*half, .14*half, .17*half, .13*half, .13*half], "llrrrr", total=True),
                    Spacer(1, 2.5),
                    Paragraph(f"XLE is {pct(w['XLE'])} of the money but {pct(Q['es_share']['XLE'])} of 99% ES: equal volatility shares "
                              f"are not equal tail shares. The overlay held cash in {Q['overlay_months']} of {Q['months']} months: "
                              f"{periods_txt}.", small))
    kp = [["CAGR (real)", *(f"{pct(p['cagr'], 2)} ({pct(p['real_cagr'], 2)})" for p in (p6, p5, pb))],
          ["Volatility", *(pct(p["annual_volatility"]) for p in (p6, p5, pb))],
          ["Maximum drawdown", *(pct(-p["maximum_drawdown"]) for p in (p6, p5, pb))],
          ["Sharpe; Sortino", *(f"{p['sharpe']:.2f}; {p['sortino']:.2f}" for p in (p6, p5, pb))],
          ["Calmar; beta to SPY", *(f"{p['calmar']:.2f}; {p['beta']:.2f}" for p in (p6, p5, pb))],
          ["Jensen's alpha", *(pct(p["jensen_alpha"], 2) for p in (p6, p5, pb))],
          ["Longest under water", *(f"{p['max_underwater_days']} days" for p in (p6, p5, pb))]]
    kpis = section(f"Performance, {date(Q['start'])} to {date(Q['end'])}",
                   grid(["KPI", "v6 final", "v5 core", "40/60"], kp, [.29*half, .24*half, .24*half, .23*half], "lrrr"),
                   Spacer(1, 2.5),
                   Paragraph("Daily simple returns, zero trading cost, before the cash reserve; overlay cash earns 0%. Real deflates by "
                             f"US CPI ({pct(p6['cpi_inflation'], 2)} a year). Sharpe over the 3-month T-bill.", small))
    story += [two(alloc, kpis), Spacer(1, 5)]

    from PIL import Image as PILImage
    with PILImage.open(figure) as im:
        wpx, hpx = im.size
    img_w = .70*width
    story += [Image(str(figure), width=img_w, height=img_w*hpx/wpx),
              Paragraph(f"Growth of {usdm(V, 1)} and fall from the previous high: v6, v5 core and 40/60 SPY/AGG, daily, zero cost, before "
                        "the cash reserve. Orange: months the overlay held cash.", small), Spacer(1, 5)]

    m = Q["models_99"]
    order = ["Historical simulation", "Parametric (normal)", "Monte Carlo (Student-t)", "EVT (POT-GPD)", "GARCH-EVT"]
    rk = [[k if k != "GARCH-EVT" else "GARCH-EVT (current volatility)", num(m[k]["var_usd"]), num(m[k]["es_usd"])] for k in order]
    risk = section(f"Risk: one day, NAV {usdm(V, 1)}, today's weights",
                   grid(["Model, 99%", "VaR (USD)", "ES (USD)"], rk, [.52*half, .24*half, .24*half], "lrr", highlight=0),
                   Spacer(1, 2.5),
                   Paragraph(f"ES 95% bootstrap interval {usd(Q['es99_interval'][0])} to {usd(Q['es99_interval'][1])}. "
                             f"Historical ES is {m['Historical simulation']['es_usd']/m['Parametric (normal)']['es_usd']:.2f}× the normal "
                             "model's: fat tails. Fitted on 2005-2026 with today's weights.",
                             small))
    bk = [[lbl, f"{r['breaches']} / {r['expected_breaches']:.1f}", pval(r["kupiec_p"]), pval(r["independence_p"]),
           pval(r["conditional_coverage_p"]), r["zone"]] for lbl, r in (("v6 GARCH-EVT", ge), ("v6 FHS", fhs), ("v5 core GARCH-EVT", ge5))]
    valid = section(f"Validation: 99% VaR backtest, 2017 to {pd.Timestamp(Q['end']):%b %Y}",
                    grid(["Model", "Breaches / exp.", "Kupiec p", "Indep. p", "Cond. cov. p", "Last 250"], bk,
                         [.27*half, .19*half, .13*half, .13*half, .15*half, .13*half], "lrrrrl", highlight=0),
                    Spacer(1, 2.5),
                    Paragraph(f"{ge['days']:,} sequential forecasts, each from data to the day before, on each path's own returns (v6 hash "
                              f"{Q['strategy_hash'][:8]}). v6 breach counts are right but "
                              f'<font color="{CRITICAL}">cluster</font> around overlay switches, hence the higher-of-two rule. '
                              "Basel zone: green 0-4, yellow 5-9, red 10+ breaches in 250 days.", small))
    story += [two(risk, valid), Spacer(1, 5)]

    st_rows = [[k, f"{date(r['start'])} – {date(r['end'])}", pct(r["return"]), num(r["loss_usd"]), pct(r["max_fall"]),
                pct(r["v5_return"]), pct(r["bench_return"]), pct(r["held_max_fall"])] for k, r in S.items()]
    sh = hyp["shocks"]
    st_rows.append(["Hypothetical", f"SPY {pct(sh['SPY'], 0)}, AGG {pct(sh['AGG'], 0)}, GLD {pct(sh['GLD'], 0)}, XLE {pct(sh['XLE'])}",
                    pct(hyp["return"]), num(hyp["loss_usd"]), "one step", "", "", ""])
    story += section(f"Stress tests on {usdm(V, 1)}",
                     grid(["Scenario", "Dates or shock", "v6 return", "v6 loss (USD)", "v6 max fall", "v5 core", "40/60",
                           "Target held: max fall"], st_rows,
                          [.10*width, .31*width, .09*width, .11*width, .09*width, .08*width, .08*width, .14*width], "llrrrrrr"),
                     Spacer(1, 2.5),
                     Paragraph("Paths as run, month-end resets and overlay included, from the start close to the end close; a negative "
                               "loss is a gain. 'Target held' buys today's weights at the start and lets them drift. The hypothetical shock "
                               "is deterministic (XLE from its conditional mean in SPY's worst 10% of days, 2005-2016) and carries no "
                               "probability.", small))
    story += [Spacer(1, 5)]

    rates, covid, gfc = S["Rates 2022"], S["COVID"], S["GFC"]
    hs = m["Historical simulation"]
    qs = [f"<b>What can go wrong?</b> Stocks and bonds fall together, as in 2022 ({pct(rates['return'])}, the worst crisis as run; "
          f"the overlay was off); a shock lands between month-ends (COVID: {pct(covid['return'])} in five weeks); energy reverses (XLE "
          f"carries {pct(Q['es_share']['XLE'])} of ES); the overlay gives false alarms or reacts late to fast crashes.",
          f"<b>How bad can losses get?</b> About 1 day in 100 loses more than {usd(hs['var_usd'])}; those days average "
          f"{usd(hs['es_usd'])}. Worst crisis as run {usd(S[worst]['loss_usd'])}; hypothetical shock {usd(hyp['loss_usd'])}. "
          "None of these is a maximum.",
          f"<b>How confident are we?</b> Less than for v5: v6's risk forecasts have the right breach count but clustered breaches, and the "
          "strategy and overlay were chosen after many rules were compared on the same 2005-2026 data, so there is no untouched test "
          f"period. The overlay's GFC gain ({pct(gfc['return'])} against {pct(gfc['v5_return'])} for v5) rests on one deep recession.",
          f"<b>Spending, 25 years:</b> resampled v6 history pays every reserve in {pct(r25['all_paid'])} of paths but keeps "
          f"{usdm(Q['fund'], 0)} in real terms in only {pct(r25['real_kept'])} (median {usdm(r25['median_real_usd'])}): the reserve rising "
          f"{pct(Q['reserve_growth'], 2)} a year slowly draws down real capital. Plan spending below the {pct(p6['real_cagr'])} real "
          "earned historically."]
    story += section("The committee's three questions", *[Paragraph(q, ParagraphStyle("q", parent=body, spaceAfter=2)) for q in qs])
    story += [Spacer(1, 3.5),
              Paragraph("Evaluation labels: performance, comparisons and stress tests are a <b>retrospective portfolio evaluation</b>; "
                        "VaR backtests are a <b>sequential risk-forecast evaluation</b>; no result is an untouched out-of-sample test. Data: "
                        "Yahoo Finance adjusted closes, FRED DGS10, DTB3 and CPIAUCSL. Cash is outside the brief's seven ETFs: a disclosed "
                        "policy choice. AI use: Codex and Claude Code wrote the code and documents; automated checks are not human "
                        "validation. Human reviewer and date: pending.", small)]

    def decorate(canvas, d):
        canvas.saveState(); canvas.setFont("DV", 6.1); canvas.setFillColor(c(INK2))
        canvas.drawString(left, 24, footer)
        canvas.setStrokeColor(c(RULE)); canvas.setLineWidth(.4); canvas.line(left, 32, A4[0]-right, 32); canvas.restoreState()
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
                          title="Executive tear sheet: final model v6", author="Team Ghosted",
                          subject="Serendib University Endowment Fund, one-page executive tear sheet")
    doc.addPageTemplates([PageTemplate(id="page", frames=[Frame(left, bottom, width, A4[1]-top-bottom, leftPadding=0,
                                                                rightPadding=0, topPadding=0, bottomPadding=0)],
                                       onPage=decorate)])
    doc.build(story)


# ---------------------------------------------------------------- build
def build(out=None, root=None):
    out = Path(out or OUT); root = root or config.ROOT
    out.mkdir(parents=True, exist_ok=True)
    Q, series = gather(root)
    Q["code_rev"] = git_rev()
    chart(series, out/"wealth_drawdown.png")
    pdf = out/"executive_tear_sheet.pdf"
    footer = (f"Tear sheet v6 r1 · evidence {Q['evidence_run']} · data {Q['data_hash'][:12]} · strategy {Q['strategy_hash'][:12]} · "
              f"policy {Q['prereg_tag']} · code {Q['code_rev']}")
    compose(Q, out/"wealth_drawdown.png", pdf, footer)
    from pypdf import PdfReader
    pages = len(PdfReader(pdf).pages)
    (out/"numbers.json").write_text(json.dumps(jsonable(Q), indent=2), encoding="utf-8")
    norm = lambda p: hashlib.sha256((config.ROOT/p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    ins = ["data/clean/prices_clean.csv", "data/clean/macro_clean.csv", "config/final.yaml",
           *(f"results/{F.RUN_V6}/{f}" for f in ("path.csv", "forecasts.csv", "summary.json", "metadata.json"))]
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "code_rev": Q["code_rev"], "pages": pages,
                "model": "v6", "inputs": {p: sha(root/p) for p in ins},
                "sources_lf_normalised": {p: norm(p) for p in ["quanedge/tear_sheet.py", "quanedge/final_portfolio.py"]},
                "outputs": {p.name: sha(p) for p in (pdf, out/"wealth_drawdown.png", out/"numbers.json")},
                "evaluation_label": "retrospective portfolio evaluation; backtests are sequential risk-forecast evaluation",
                "human_review": "pending"}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if pages != 1:
        raise ValueError(f"tear sheet has {pages} pages; the brief requires one")
    return out, pages


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    out, pages = build()
    print(f"{out/'executive_tear_sheet.pdf'}: {pages} page")


if __name__ == "__main__":
    main()
