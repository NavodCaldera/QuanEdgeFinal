"""Technical report and investment memorandum for the final portfolio: monthly dynamic EWMA risk parity.

Written for the endowment's investment committee and the competition judges. The report reads the
same evidence and calculations as the committee dashboard (quanedge/final_portfolio.py, results/
dynamic-parity-r1, the frozen price snapshot and config/final.yaml), so its numbers match the
dashboard. It writes results/final-report-r1/: technical_report.pdf, technical_report.md (the same
text as Markdown), figures/, bootstrap.csv, numbers.json (the figures quoted) and manifest.json
(input and output hashes).

    python -m quanedge.final_report
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
from . import config
from . import final_portfolio as F
from .comparison import dynamic_parity_path
from .risk.models import LABEL
from .stress import SCENARIOS

OUT = config.RESULTS_DIR/"final-report-r1"
V5_RUN = "final-v5-20261031"            # the mandate v5 run: policy-limit verdicts for the fixed comparison mixes
V5_NAMES = {"permanent": "permanent 25/50/25", "balanced_35_50_15": "balanced 35/50/15", "near_parity": "static risk parity",
            "min_variance": "minimum variance", "max_sharpe": "maximum Sharpe", "min_cvar": "minimum CVaR", "40_60": "40/60",
            "60_40": "60/40", "equal_weight": "equal weight", "max_return": "the mandate v1 return-maximising rule"}
TITLE = "Monthly dynamic risk parity for the Serendib University Endowment Fund"
TITLE_V6 = "Monthly dynamic risk parity with a recession overlay for the Serendib University Endowment Fund"
OUT_V6 = config.RESULTS_DIR/"final-report-v6-r1"
OVERLAY_COLOR = "#eda100"
V6_REFERENCES = [
    "Estrella, A. and Mishkin, F. (1996). The yield curve as a predictor of U.S. recessions. Current Issues in Economics and "
    "Finance 2(7), Federal Reserve Bank of New York.",
    "Faber, M. (2007). A quantitative approach to tactical asset allocation. Journal of Wealth Management 9(4), 69-79."]
U = F.UNIVERSE
COLOR = {"SPY": "#2a78d6", "AGG": "#eb6834", "GLD": "#1baf7a", "XLE": "#eda100"}   # the dashboard's validated palette
ROLE = {"SPY": "US large-cap equity", "AGG": "US investment-grade bonds", "GLD": "Gold", "XLE": "US energy equity"}
INK, INK2, MUTED, RULE = "#0b0b0b", "#52514e", "#8a8984", "#d9d8d3"
ACCENT, LIGHT, NEUTRAL, CRITICAL, TINT = "#2a78d6", "#9ec3ef", "#c3c2b7", "#e34948", "#eef4fb"
METHODS = ["historical", "normal", "student_t", "mc_normal", "mc_t", "evt", "fhs", "garch_evt"]
FAMILY = {"historical": "Historical", "normal": "Parametric", "student_t": "Parametric", "mc_normal": "Monte Carlo",
          "mc_t": "Monte Carlo", "evt": "EVT", "fhs": "Conditional", "garch_evt": "Conditional"}


# ---------------------------------------------------------------- formatting (text uses ReportLab markup)
def minus(s):
    return s.replace("-", "−")


def usd(x, d=0):
    return "n/a" if x is None or not np.isfinite(x) else minus(f"USD {x:,.{d}f}")


def num(x, d=0):
    if x is None or not np.isfinite(x):
        return "n/a"
    x = 0. if abs(x) < .5*10**-d else x                 # no "−0"
    return minus(f"{x:,.{d}f}")


def usdm(x, d=2):
    return minus(f"USD {x/1e6:,.{d}f}m")


def pct(x, d=1):
    return "n/a" if x is None or not np.isfinite(x) else minus(f"{100*x:.{d}f}%")


def spct(x, d=1):
    return "n/a" if x is None or not np.isfinite(x) else minus(f"{100*x:+.{d}f}%")


def pval(p):
    return "n/a" if p is None or not np.isfinite(p) else ("&lt;0.001" if p < .001 else f"{p:.3f}")


def date(d):
    d = pd.Timestamp(d)
    return f"{d.day} {d:%b %Y}"


# ---------------------------------------------------------------- evidence
def data_facts(root):
    """Counts from the data pipeline's own logs and files (the cleaning evidence), nothing typed in."""
    clean = root/"data/clean"
    prices = pd.read_csv(clean/"prices_clean.csv", index_col=0, parse_dates=True)
    prov = json.loads((clean/"price_provenance.json").read_text(encoding="utf-8"))
    manifest = json.loads((clean/"data_manifest.json").read_text(encoding="utf-8"))
    cal = pd.read_csv(clean/"calendar_audit.csv")
    an = pd.read_csv(clean/"anomaly_log.csv", parse_dates=["date"])
    q = pd.read_csv(clean/"data_quality_log.csv")
    checks = pd.read_csv(clean/"data_quality_checks.csv").set_index("check").findings
    ff = pd.read_csv(clean/"macro_ffill_log.csv", parse_dates=["date"])
    macro = pd.read_csv(clean/"macro_clean.csv", index_col=0, parse_dates=True)
    st = pd.read_csv(clean/"stationarity_tests.csv")
    # CPI months missing at FRED, and how long the previous value is then carried (release = month + 1 month + 20 days)
    raw = pd.read_csv(root/"data/raw/fred_CPIAUCSL.csv", parse_dates=["observation_date"]).set_index("observation_date").CPIAUCSL.dropna()
    lag = pd.DateOffset(months=1, days=20); sessions = macro.index
    held = lambda a, b: sessions[(sessions >= a+lag) & (sessions < b+lag)]
    present = raw.index[(raw.index+lag >= sessions[0]) & (raw.index <= sessions[-1])]
    typical = float(np.median([len(held(a, b)) for a, b in zip(present[:-1], present[1:])]))
    gaps = []
    for m in pd.date_range(raw.index[0], raw.index[-1], freq="MS").difference(raw.index):
        carried = held(m-pd.DateOffset(months=1), m+pd.DateOffset(months=1))
        if len(carried):
            gaps.append({"month": f"{m:%B %Y}", "carried": f"{m-pd.DateOffset(months=1):%B %Y}", "sessions": len(carried),
                         "first": str(carried[0].date()), "last": str(carried[-1].date()), "typical": typical})
    review = an.disposition.str.contains("manual review recommended")
    rev = q[q.check == "SHARP_TWO_DAY_REVERSAL"]; shifts = q[q.check == "VOLATILITY_REGIME_SHIFT"].set_index("ticker")
    breaks = {}
    for t in U:
        m = re.search(r"break after (\d{4}-\d{2}-\d{2})", shifts.metric[t]); v = re.findall(r"([\d.]+)%", shifts.detail[t])
        breaks[t] = {"date": m.group(1), "before": float(v[0])/100, "after": float(v[1])/100}
    rf = macro.rf_daily_effective
    rows = st[st.asset.isin(U)]
    return {"dates": len(prices), "start": str(prices.index[0].date()), "end": str(prices.index[-1].date()),
            "weekdays": len(pd.bdate_range(prices.index[0], prices.index[-1])),
            "retrieved": prov["download_metadata"]["retrieved_at_utc"], "yfinance": prov["download_metadata"]["yfinance_version"],
            "auto_adjust": prov["download_metadata"]["auto_adjust"],
            "missing_price_rows": prov["snapshot"]["rows_with_missing_price"],
            "dropped_rows": prov["snapshot"]["rows_dropped_by_common_calendar_filter"],
            "calendar": cal.classification.value_counts().to_dict(),
            "closures": [[r.date, r.reason] for r in cal[cal.classification != "STANDARD_HOLIDAY"].itertuples()],
            "flags": len(an), "flags_by_ticker": {t: int((an.ticker == t).sum()) for t in U},
            "flags_2008": int((an.date.dt.year == 2008).sum()), "flags_2020": int((an.date.dt.year == 2020).sum()),
            "flags_corroborated": int((an.corroborating_assets >= 1).sum()), "flags_review": int(review.sum()),
            "flags_review_by_ticker": {t: int(n) for t, n in an[review].ticker.value_counts().items()},
            "flags_labelled": int((an.label_source != "none").sum()),
            "stale": int(checks["STALE_PRICE_STREAK"]), "reversals": int(checks["SHARP_TWO_DAY_REVERSAL"]),
            "reversals_by_ticker": {t: int((rev.ticker == t).sum()) for t in U}, "variance_breaks": breaks,
            "ffill_rows": len(ff), "ffill_by_series": ff.series.value_counts().to_dict(),
            "ffill_months": sorted(ff.date.dt.month.unique().tolist()),
            "cpi_gaps": gaps,
            "rf_annual": float((1+rf).prod()**(252/len(rf))-1), "dtb3_negative_days": int((macro.DTB3 < 0).sum()),
            "dtb3_min": float(macro.DTB3.min()/100),
            "stationarity": {f"{r.asset}|{r.series_type}": {k: (None if pd.isna(v) else v) for k, v in r._asdict().items()
                                                           if k not in ("Index",)} for r in rows.itertuples()},
            "manifest_files": len(manifest["files"]), "manifest_created": manifest["generated_at_utc"],
            "environment": manifest["environment"]}


def frequency_variants(path, returns, cfg):
    """The registered monthly rule beside the same rule re-estimated weekly and quarterly (evidence for
    the choice of frequency; all three were compared before monthly was chosen, so this is hindsight)."""
    s = cfg["strategy"]; rows = []
    for label, freq in (("Weekly", "W"), ("Monthly (chosen)", "M"), ("Quarterly", "Q")):
        p = path if freq == "M" else dynamic_parity_path(returns[U], freq, s["ewma_lambda"], s["window"], s["min_history"], cfg["cost"])
        r = p["return"]; wealth = (1+r).cumprod(); years = (r.index[-1]-r.index[0]).days/365.25
        rows.append({"rule": label, "cagr": float(wealth.iloc[-1]**(1/years)-1), "volatility": float(r.std()*np.sqrt(252)),
                     "max_drawdown": float(-(wealth/wealth.cummax()-1).min()),
                     "turnover": float(p.turnover.sum()/years), "rebalances": int(p.rebalanced.astype(bool).sum()),
                     **{k: F.window_return(wealth, a, b) for k, (a, b) in SCENARIOS.items()}})
    return pd.DataFrame(rows)


def overlay_evidence(ev, ev5, returns, rf, cpi, V, cfg):
    """v6 only: what the recession overlay did, beside the v5 core (the same rule without it), and where the
    final model's clustered 99% breaches fall relative to the months the overlay switched."""
    p6, p5 = ev["path"], ev5["path"]; s6, s5 = ev["summary"], ev5["summary"]
    on = p6["overlay_on"].astype(bool)
    month_on = on.groupby(on.index.to_period("M")).last()
    switches = month_on.index[month_on.ne(month_on.shift(fill_value=False))]
    near = set()
    for m in switches:                              # the switch month and the month after it
        near |= {m, m+1}
    _, frame = F.backtest(ev["forecasts"], ev["strategy_hash"], cfg["challenger"], .99, cfg["evaluation_start"], cfg["snapshot_end"])
    br = frame.index[frame.breach]
    months = s6["overlay_months_on"]
    runs = []
    for m in (pd.Period(x, "M") for x in months):
        if runs and m == runs[-1][1]+1:
            runs[-1][1] = m
        else:
            runs.append([m, m])
    w5 = F.wealth_usd(p5["return"], V)
    stress5 = {k: F.scenario_pnl(p5, returns, a, b, V) for k, (a, b) in SCENARIOS.items() if p5.index[0] < pd.Timestamp(a)}
    return {"months_on": len(months), "months": int(len(month_on))-1, "periods": [[str(a), str(b)] for a, b in runs],
            "on_now": bool(on.iloc[-1]), "average_cash": float(s6["average_cash"]), "switch_months": [str(m) for m in switches],
            "breaches": int(len(br)), "breaches_near_switch": int(sum(d.to_period("M") in near for d in br)),
            "days_near_switch_share": float(np.mean([d.to_period("M") in near for d in frame.index])),
            "breaches_near_switch_2020": int(sum(d.to_period("M") in near and pd.Timestamp("2020-02-01") <= d < pd.Timestamp("2020-04-01") for d in br)),
            "v5_performance": F.performance(p5, returns, rf, cpi), "v5_stress": stress5, "v5_wealth": w5,
            "v5_validation": {(v["method"], v["alpha"]): v for v in s5["validation"]},
            "v5_strategy_hash": ev5["strategy_hash"], "es99_path": s6["es99"]["path"], "es99_path_v5": s5.get("es99", {}).get("path"),
            "rule": ev["meta"]["overlay"]}


def gather(root=None, model="v6"):
    """Every number and series the report uses, from the dashboard's evidence and calculations."""
    from .risk import fit_evt
    from .risk.portfolio import loss_fraction, portfolio_log_returns
    root = root or config.ROOT
    ev = F.load_evidence(root, model=model); prices, returns, rf, cpi = F.load_market(root)
    cfg = F.policy(); V = float(cfg["value"]); path = ev["path"]; summary = ev["summary"]
    w = F.current_target(path)
    perf = F.performance(path, returns, rf, cpi)
    bench = F.benchmark_returns(returns).reindex(path["return"].index)
    kb = F.kpis(bench, rf, returns.SPY, bench); kb["real_cagr"] = F.policy_real(kb["cagr"])     # same basis as F.performance
    wealth = F.wealth_usd(path["return"], V); bwealth = F.wealth_usd(bench, V)
    models, table = F.risk_now(returns, w, V)
    windows = {"Full sample, 2005-2026": (None, None),
               "Last 750 days": (str(returns.index[-750].date()), None),
               "2017-2026": (config_eval(cfg), None)}
    sens = {}
    for label, (a, b) in windows.items():
        sens[label] = table if a is None else F.risk_now(returns, w, V, a, b)[1]
    evt = models["evt"]; losses = -portfolio_log_returns(np.log1p(returns[U]), w).to_numpy()
    thresholds = []
    for label, q in (("Chosen by the rule", None), ("90th percentile", .90), ("95th percentile", .95)):
        fit = evt if q is None else fit_evt(losses, threshold_q=q)
        thresholds.append({"threshold": label, "u": fit.params["u"], "q": fit.params["threshold_q"], "k": fit.params["n_exceed"],
                           "xi": fit.params["xi"], "xi_se": fit.params["xi_se"], "sigma": fit.params["sigma"],
                           "var99": V*loss_fraction(fit.var(.99)), "es99": V*fit.es_fraction(.99), "basis": fit.basis(.99)})
    contrib, tot = F.risk_contributions(returns, w, .99, V)
    stress, hyp, rev = F.stress_panel(path, prices, returns, w, V)
    validation = {(v["method"], v["alpha"]): v for v in summary["validation"]}
    res, frame = F.backtest(ev["forecasts"], ev["strategy_hash"], cfg["challenger"], .99, cfg["evaluation_start"], cfg["snapshot_end"])
    by_year = frame.groupby(frame.index.year).breach.agg(["sum", "count"])
    hist = F.target_history(path)
    data = data_facts(root)
    from .data.stationarity import _return_row        # the pipeline's own test settings, applied to the strategy's path
    strat_stationarity = _return_row("Strategy", "Daily Log Returns r_t", np.log1p(path["return"]))
    garch = models[cfg["challenger"]]
    vol_now, vol_avg = garch.params["sigma_next"]*np.sqrt(252), float(np.std(-losses, ddof=1)*np.sqrt(252))
    latest = {m: F.latest_forecast(ev["forecasts"], m, .99, V) for m in (cfg["challenger"], cfg["primary"])}
    comparison = F.comparison(path, returns, rf, cpi)
    fr, _, point = F.frontier(returns)
    points = {"Today's target": point(w), **{r.portfolio: point(r.weights) for r in comparison.itertuples() if r.weights}}
    liquidity = {r["scenario"]: {"day": r["path"]["worst_day"], **{t: float(returns.loc[r["path"]["worst_day"], t]) for t in U}}
                 for r in stress if r.get("path")}
    covid_agg = returns.loc[SCENARIOS["COVID"][0]:SCENARIOS["COVID"][1], "AGG"].nsmallest(2)
    v5_run = root/"results"/V5_RUN/"submission.json"          # policy-limit verdicts of the fixed mixes, as recorded
    v5_checks, v5_same = {}, {}
    if v5_run.exists():
        bundle = json.loads(v5_run.read_text(encoding="utf-8"))
        v5_checks = {k: p["checks"] for k, p in bundle["portfolios"].items() if p.get("checks")}
    if v5_run.exists() and model == "v5":
        sel = bundle["portfolios"]["selected"]; folder = root/"results"/V5_RUN/"selected"
        theirs = pd.read_csv(folder/"performance.csv", index_col=0, parse_dates=True)["return"]
        fc5 = pd.read_csv(folder/"forecasts.csv", index_col=0, parse_dates=True); fc = ev["forecasts"]
        cols = [c for c in fc.columns if c.startswith(("var_", "es_")) and c in fc5.columns]
        v5_same = {"strategy_hash": sel.get("forecast_hash"), "real_cagr": sel.get("realised_real_cagr"),
                   "path_max_diff": float((theirs-path["return"]).abs().max()),
                   "forecast_max_diff": float(max(np.nanmax(np.abs(fc5[c].to_numpy()-fc[c].to_numpy())) for c in cols))}
    D = {"path": path, "returns": returns, "wealth": wealth, "bench_wealth": bwealth, "table": table, "scan": evt.scan,
         "evt": evt.params, "losses": losses, "frame": frame, "by_year": by_year, "hist": hist, "contrib": contrib,
         "stress": stress, "hyp": hyp, "rev": rev, "comparison": comparison, "frontier": fr, "frontier_points": points,
         "mc_error": F.mc_error(returns, w, V),
         "frequency": frequency_variants(path if model == "v5" else F.load_evidence(root, model="v5")["path"], returns, cfg), "expected": F.expected_returns(returns, w),
         "bootstrap": F.bootstrap(returns, w, V), "sens": sens, "thresholds": pd.DataFrame(thresholds),
         "validation": validation, "corr": returns.corr(), "stationarity": strat_stationarity}
    overlay = None
    if model == "v6":
        overlay = overlay_evidence(ev, F.load_evidence(root, model="v5"), returns, rf, cpi, V, cfg)
        D["v5_wealth"] = overlay.pop("v5_wealth"); D["overlay_on"] = path["overlay_on"].astype(bool)
    settings = ev["meta"].get("settings") or dict(ev["meta"]["strategy"], universe=U,
                                                  risk_parity="Spinu convex form, equal volatility contributions")
    N = {"value": V, "fund": float(cfg["fund_value"]), "weights": w, "strategy_hash": ev["strategy_hash"], "data_hash": ev["data_hash"],
         "evidence_run": ev["run"], "prereg_tag": ev["meta"]["prereg_tag"], "settings": settings, "policy": cfg,
         "model": model, "overlay": overlay, "cash": 1-sum(w.values()),
         "start": str(path.index[0].date()), "end": str(path.index[-1].date()), "performance": perf, "benchmark": kb,
         "end_value": float(wealth.iloc[-1]), "bench_end_value": float(bwealth.iloc[-1]),
         "current_drawdown": float(F.drawdown(wealth).iloc[-1]), "targets": len(hist),
         "target_range": {t: [float(hist[t].min()), float(hist[t].max())] for t in U},
         "xle_at_maximum": bool(np.isclose(hist["XLE"].iloc[-1], hist["XLE"].max())),
         "contributions_total": tot, "reserve_test": F.reserve_test(path, cfg), "reserve_history": F.reserve_history(path, cpi, cfg),
         "adf": F.adf(path), "backtest_challenger_99": res, "data": data, "vol_next_day_annual": float(vol_now),
         "vol_average_annual": vol_avg, "latest_forecast_99": latest, "distribution_yield": F.distribution_yield(w, root),
         "liquidity_days": liquidity, "covid_agg_worst": {str(d.date()): float(x) for d, x in covid_agg.items()},
         "v5_run_checks": v5_checks, "v5_run_same_strategy": v5_same,
         "stationarity_strategy": strat_stationarity,
         "cpi_policy": cfg["inflation"], "nominal_floor": (1+cfg["inflation"])*(1+cfg["real_return_floor"])-1}
    return N, D


def config_eval(cfg):
    return str(pd.Timestamp(cfg["evaluation_start"]).date())


# ---------------------------------------------------------------- figures
def chart_style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.4, "axes.edgecolor": RULE, "axes.linewidth": .6,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 7,
                         "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.color": "#ecebe6", "grid.linewidth": .5, "axes.axisbelow": True, "legend.frameon": False,
                         "legend.fontsize": 7, "text.color": INK2, "axes.titlesize": 7.8, "axes.titleweight": "bold",
                         "axes.titlecolor": INK, "axes.titlelocation": "left", "savefig.dpi": 220, "xtick.major.size": 0,
                         "ytick.major.size": 0})


def shade(ax, label=False):
    for name, (a, b) in SCENARIOS.items():
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color="#8a8984", alpha=.10, linewidth=0)
        if label:
            ax.text(pd.Timestamp(a), 1.0, name, transform=ax.get_xaxis_transform(), fontsize=6.4, color=MUTED, va="bottom")


def save(fig, folder, name):
    p = folder/f"{name}.png"; fig.savefig(p, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return p


def fig_targets(D, folder):
    hist, path = D["hist"], D["path"]
    idx = list(hist.index)+[path.index[-1]]; vals = np.vstack([hist[U].to_numpy(), hist[U].to_numpy()[-1]])
    fig, ax = plt.subplots(figsize=(6.9, 2.1)); lower = np.zeros(len(idx))
    for t, col in zip(U, vals.T):
        upper = lower+col
        ax.fill_between(idx, lower, upper, step="post", color=COLOR[t], linewidth=0, label=t)
        ax.step(idx, upper, where="post", color="white", linewidth=.8)
        ax.text(path.index[-1]+pd.Timedelta(days=60), (lower[-1]+upper[-1])/2, f"{t} {100*col[-1]:.1f}%", fontsize=6.8,
                color=INK, va="center", clip_on=False)
        lower = upper
    ax.set_ylim(0, 1); ax.set_xlim(idx[0], idx[-1]); ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.grid(False)
    ax.set_ylabel("Target weight"); ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), handlelength=1.2)
    return save(fig, folder, "fig1_targets")


def fig_wealth(D, N, folder):
    w, b = D["wealth"]/1e6, D["bench_wealth"]/1e6
    fig, (a, d) = plt.subplots(2, 1, figsize=(6.9, 3.15), sharex=True, gridspec_kw={"height_ratios": [3, 2], "hspace": .1})
    for ax in (a, d):
        shade(ax, label=ax is a)
    if "overlay_on" in D:                       # v6: months the recession overlay held cash
        on = D["overlay_on"]; starts = on.index[on & ~on.shift(fill_value=False)]; ends = on.index[on & ~on.shift(-1, fill_value=False)]
        for ax in (a, d):
            for s0, e0 in zip(starts, ends):
                ax.axvspan(s0, e0, color=OVERLAY_COLOR, alpha=.22, linewidth=0,
                           label="Overlay on (cash)" if ax is a and s0 == starts[0] else None)
    if "v5_wealth" in D:
        a.plot(D["v5_wealth"].index, D["v5_wealth"]/1e6, color=NEUTRAL, lw=.9, label="v5 core (no overlay)")
        d.plot(D["v5_wealth"].index, F.drawdown(D["v5_wealth"]), color=NEUTRAL, lw=.7)
    a.plot(w.index, w, color=ACCENT, lw=1.5, label="Final portfolio"); a.plot(b.index, b, color=MUTED, lw=1.0, label="40/60 SPY/AGG")
    (n1, v1), (n2, v2) = sorted({"Final": w.iloc[-1], "40/60": b.iloc[-1]}.items(), key=lambda kv: kv[1])
    gap = .08*(max(w.max(), b.max())-min(w.min(), b.min()))
    y1, y2 = (v1, v2) if v2-v1 >= gap else ((v1+v2-gap)/2, (v1+v2+gap)/2)     # keep the two end labels apart
    for name, v, y in ((n1, v1, y1), (n2, v2, y2)):
        a.text(w.index[-1]+pd.Timedelta(days=40), y, f"{name} {v:.1f}m", color=INK, fontsize=6.6, va="center", clip_on=False)
    a.set_ylabel("USD million")
    a.legend(loc="upper left", ncol=4 if "v5_wealth" in D else 2, bbox_to_anchor=(0, .93), fontsize=6.4 if "v5_wealth" in D else 7)
    dw, db = F.drawdown(D["wealth"]), F.drawdown(D["bench_wealth"])
    d.fill_between(dw.index, dw, 0, color=LIGHT, linewidth=0, alpha=.7); d.plot(dw.index, dw, color=ACCENT, lw=.8)
    d.plot(db.index, db, color=MUTED, lw=.8)
    limit = -N["policy"]["drawdown_limit"]
    d.axhline(limit, color=CRITICAL, lw=.8, ls=(0, (4, 3)))
    d.text(dw.index[int(len(dw)*.45)], limit+.008, "20% decline limit", color=CRITICAL, fontsize=6.6, va="bottom")
    d.set_ylim(min(db.min(), limit)-.04, .01); d.yaxis.set_major_formatter(PercentFormatter(1, decimals=0)); d.set_ylabel("Fall from high")
    a.set_xlim(w.index[0], w.index[-1])
    return save(fig, folder, "fig2_wealth_drawdown")


SHORT = {"Final portfolio (monthly dynamic risk parity)": "Final portfolio", "Static risk parity": "Static RP",
         "Minimum variance": "Min variance", "Maximum Sharpe": "Max Sharpe", "40/60 SPY/AGG": "40/60", "60/40 SPY/AGG": "60/40",
         "Equal weight": "Equal weight", "Permanent 25/50/25": "Permanent", "Balanced 35/50/15": "Balanced", "Today's target": "Today's target"}


def fig_scatter(D, folder):
    c = D["comparison"]; fr = D["frontier"]; pts = D["frontier_points"]
    fig, (f, ax) = plt.subplots(1, 2, figsize=(6.9, 2.5), gridspec_kw={"wspace": .3, "width_ratios": [1, 1.25]})
    f.plot(fr.volatility, fr.expected, color=INK2, lw=1.1, label="Efficient frontier (long-only)")
    # a few points only, each with its own label position: the Markowitz pair, the benchmark, equal weight and today's target
    place = {"Today's target": (6, -5, "left"), "Minimum variance": (6, -5, "left"), "Maximum Sharpe": (6, 3, "left"),
             "40/60 SPY/AGG": (-6, 5, "right"), "Equal weight": (-6, 4, "right")}
    for name, (dx, dy, ha) in place.items():
        if name not in pts:
            continue
        vol, ret = pts[name]; mine = name == "Today's target"
        f.scatter(vol, ret, s=40 if mine else 18, color=ACCENT if mine else INK2, edgecolor="white", linewidth=1, zorder=3)
        f.annotate(SHORT.get(name, name), (vol, ret), xytext=(dx, dy), textcoords="offset points", fontsize=6.2, ha=ha, va="center",
                   color=INK if mine else INK2, fontweight="bold" if mine else "normal",
                   bbox=dict(boxstyle="square,pad=0.1", facecolor="white", edgecolor="none", alpha=.85))
    f.xaxis.set_major_formatter(PercentFormatter(1, decimals=0)); f.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    f.set_xlabel("Expected volatility"); f.set_ylabel("Expected annual return"); f.legend(loc="lower right", fontsize=6.2)
    f.set_title("(a) Markowitz view, frozen estimator")
    ax.axvline(.20, color=CRITICAL, lw=.8, ls=(0, (4, 3)), zorder=1)
    # label offsets (points): left of the point for portfolios inside the limit, right of it beyond; the final
    # portfolio and static risk parity sit almost on top of each other, so one goes above and one below
    place = {"Final portfolio (monthly dynamic risk parity)": (-6, 5, "right"), "Static risk parity": (5, -9, "left"),
             "Minimum variance": (-6, -2, "right"), "Maximum Sharpe": (-6, -2, "right"), "Permanent 25/50/25": (-6, 3, "right"),
             "Balanced 35/50/15": (6, 3, "left")}
    for i, r in c.iterrows():
        final = i == 0
        ax.scatter(r.max_drawdown, r.cagr, s=40 if final else 18, color=ACCENT if final else INK2, zorder=3,
                   edgecolor="white", linewidth=1.1)
        dx, dy, ha = place.get(r.portfolio, (6, -2, "left"))
        ax.annotate(SHORT.get(r.portfolio, r.portfolio), (r.max_drawdown, r.cagr), xytext=(dx, dy), textcoords="offset points",
                    fontsize=6.2, ha=ha, va="center", color=INK if final else INK2, fontweight="bold" if final else "normal", zorder=4,
                    bbox=dict(boxstyle="square,pad=0.1", facecolor="white", edgecolor="none"))
    ax.text(.202, c.cagr.min()-.002, "20% limit", color=CRITICAL, fontsize=6.2, va="bottom")
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0)); ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xlabel("Largest fall from a previous high"); ax.set_ylabel("Realised annual return (CAGR)")
    ax.set_xlim(.12, c.max_drawdown.max()+.05); ax.set_ylim(c.cagr.min()-.006, c.cagr.max()+.006)
    ax.set_title("(b) Realised, 2006-2026")
    return save(fig, folder, "fig3_return_vs_fall")


def fig_models(D, N, folder):
    t = D["table"][np.isclose(D["table"].alpha, .99)].set_index("method").loc[METHODS]
    fig, ax = plt.subplots(figsize=(6.9, 2.45)); y = np.arange(len(METHODS))[::-1]; h = .36
    ax.barh(y+h/2+.02, t.var_usd, height=h, color=LIGHT, label="VaR 99%")
    ax.barh(y-h/2-.02, t.es_usd, height=h, color=ACCENT, label="ES 99%")
    for yy, v in zip(y, t.es_usd):
        ax.text(v+2500, yy-h/2-.02, f"{v/1e3:,.0f}k", va="center", fontsize=6.5, color=INK)
    budget = N["policy"]["es_budget"]*N["value"]
    ax.axvline(budget, color=CRITICAL, lw=.8, ls=(0, (4, 3)))
    ax.text(budget+2500, y[0]+.55, f"ES budget USD {budget/1e3:,.0f}k", color=CRITICAL, fontsize=6.6, va="center")
    ax.set_yticks(y, [LABEL[m] for m in METHODS]); ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e3:,.0f}k")); ax.set_xlabel("One-day loss, USD (NAV USD 9.6m)")
    ax.set_xlim(0, max(t.es_usd.max(), budget)*1.12); ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    return save(fig, folder, "fig4_var_es_models")


def fig_evt(D, folder):
    scan = D["scan"]; ok = scan[scan.fit_ok]; p = D["evt"]
    fig, (m, a, b) = plt.subplots(1, 3, figsize=(6.9, 2.25), gridspec_kw={"wspace": .42})
    m.plot(ok.u, ok.mean_excess, color=ACCENT, lw=1.1, marker="o", ms=2.5)
    m.axvline(p["u"], color=INK2, lw=.8)
    m.xaxis.set_major_formatter(PercentFormatter(1, decimals=1)); m.yaxis.set_major_formatter(PercentFormatter(1, decimals=2))
    m.set_xlabel("Threshold u (daily loss)"); m.set_ylabel("Mean excess over u"); m.set_title("(a) Mean excess")
    a.fill_between(ok.q, ok.xi-1.96*ok.xi_se, ok.xi+1.96*ok.xi_se, color=LIGHT, alpha=.55, linewidth=0, label="95% band")
    a.plot(ok.q, ok.xi, color=ACCENT, lw=1.1)
    a.scatter(ok.q, ok.xi, s=10, color=np.where(ok.stable, ACCENT, "white"), edgecolor=ACCENT, linewidth=.8, zorder=3, label="ξ (filled = stable)")
    a.axvline(p["threshold_q"], color=INK2, lw=.8)
    a.xaxis.set_major_formatter(PercentFormatter(1, decimals=0)); a.set_xlabel("Threshold percentile"); a.set_ylabel("Shape ξ")
    a.set_title("(b) Shape by threshold"); a.legend(loc="upper left", fontsize=5.8)
    srt = np.sort(D["losses"])[::-1]; n = len(srt); k = p["n_exceed"]; emp = np.arange(1, n+1)/n
    grid = np.linspace(p["u"], srt[0]*1.25, 200)
    gpd = k/n*(1+p["xi"]*(grid-p["u"])/p["sigma"])**(-1/p["xi"])
    from scipy.stats import norm
    r = -D["losses"]; normal = norm.sf(grid, -r.mean(), r.std())
    b.scatter(srt[:k], emp[:k], s=6, color=MUTED, label="Observed losses", zorder=3)
    b.plot(grid, gpd, color=ACCENT, lw=1.4, label="GPD tail"); b.plot(grid, normal, color=INK2, lw=1.0, label="Normal")
    b.set_yscale("log"); b.set_ylim(1e-5, k/n*1.5); b.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    b.set_xlabel("Daily log loss"); b.set_ylabel("P(larger loss)"); b.set_title("(c) Tail fit")
    b.legend(loc="upper right", fontsize=5.8)
    return save(fig, folder, "fig5_evt")


def fig_backtest(D, folder):
    f, yr = D["frame"], D["by_year"]
    fig, (a, b) = plt.subplots(2, 1, figsize=(6.9, 3.1), gridspec_kw={"height_ratios": [3, 1.5], "hspace": .5})
    a.plot(f.index, f.loss, color=NEUTRAL, lw=.45, label="Daily loss")
    a.plot(f.index, f["var"], color=ACCENT, lw=1.0, label="GARCH-EVT VaR 99%")
    br = f[f.breach]; a.scatter(br.index, br.loss, s=14, color=CRITICAL, edgecolor="white", linewidth=.8, zorder=3, label=f"Breach ({len(br)})")
    a.yaxis.set_major_formatter(PercentFormatter(1, decimals=0)); a.set_ylabel("Log loss"); a.set_xlim(f.index[0], f.index[-1])
    a.set_ylim(-.035, max(.075, f.loss.max()*1.05)); a.legend(loc="upper left", ncol=3)
    a.set_title("(a) One-day 99% VaR forecast and realised loss, strategy path")
    x = yr.index.to_numpy(); expected = yr["count"].to_numpy()*.01
    b.bar(x, yr["sum"], color=ACCENT, width=.62, label="Breaches")
    b.scatter(x, expected, marker="_", s=120, color=INK, linewidth=1.6, zorder=3, label="Expected (1% of days)")
    for xx, v, e in zip(x, yr["sum"], expected):
        b.text(xx+.36, max(v, e)+.2, f"{int(v)}", ha="left", fontsize=6.4, color=INK)
    b.set_xticks(x, [str(v) for v in x]); b.grid(axis="x", visible=False); b.set_ylim(0, max(yr["sum"].max()+2, 6))
    b.set_title("(b) Breaches by year", pad=14); b.legend(loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2, fontsize=6.3)
    return save(fig, folder, "fig6_backtest")


def fig_stress(D, folder):
    rows = D["stress"]; names = [r["scenario"] for r in rows]
    fig, ax = plt.subplots(figsize=(6.9, 1.95)); x = np.arange(len(rows)); width = .19
    for i, t in enumerate(U):
        vals = [r["path"]["pnl_usd"][t] for r in rows]
        ax.bar(x+(i-1.5)*width, vals, width=width*.92, color=COLOR[t], label=t)
    ax.axhline(0, color=INK2, lw=.6)
    labels = [f"{n}\nportfolio {100*r['path']['return']:+.1f}%".replace("-", "−") for n, r in zip(names, rows)]
    ax.set_xticks(x, labels); ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: minus(f"{v/1e3:,.0f}k"))); ax.set_ylabel("Profit (+) or loss (−), USD")
    ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0))
    return save(fig, folder, "fig7_stress_pnl")


def fig_contrib(D, folder):
    c = D["contrib"]; x = np.arange(len(U)); width = .26
    fig, ax = plt.subplots(figsize=(6.9, 1.7))
    for i, (col, label, color) in enumerate((("weight", "Share of money", NEUTRAL), ("vol_contribution", "Share of volatility", LIGHT),
                                             ("es_share", "Share of 99% ES", ACCENT))):
        ax.bar(x+(i-1)*width, c[col], width=width*.92, color=color, label=label)
        if col == "es_share":
            for xx, v in zip(x, c[col]):
                ax.text(xx+width, v+.012, f"{100*v:.1f}%", ha="center", fontsize=6.5, color=INK)
    ax.set_xticks(x, U); ax.grid(axis="x", visible=False); ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_ylim(0, max(.6, c.es_share.max()+.08)); ax.legend(ncol=3, loc="upper left")
    return save(fig, folder, "fig8_contributions")


def figures(N, D, folder):
    folder.mkdir(parents=True, exist_ok=True); chart_style()
    return {"targets": fig_targets(D, folder), "wealth": fig_wealth(D, N, folder), "scatter": fig_scatter(D, folder),
            "models": fig_models(D, N, folder), "evt": fig_evt(D, folder), "backtest": fig_backtest(D, folder),
            "stress": fig_stress(D, folder), "contrib": fig_contrib(D, folder)}


# ---------------------------------------------------------------- document model: one list of blocks, rendered to PDF and Markdown
class Doc:
    """Blocks of ReportLab-markup text. Cross-references are written @T:label@ or @F:label@ and
    resolved to table and figure numbers when rendered, so text may refer forward."""
    def __init__(self):
        self.blocks = []; self.figures = 0; self.tables = 0; self.labels = {}

    def add(self, kind, *args, **kw):
        self.blocks.append((kind, args, kw))

    def resolve(self, x):
        if isinstance(x, str):
            return re.sub(r"@([TF]):(\w+)@", lambda m: str(self.labels[(m.group(1), m.group(2))]), x)
        if isinstance(x, (list, tuple)):
            return type(x)(self.resolve(v) for v in x)
        return x

    def resolved(self):
        return [(kind, self.resolve(args), kw) for kind, args, kw in self.blocks]

    def h1(self, t): self.add("h1", t)
    def h2(self, t): self.add("h2", t)
    def p(self, t): self.add("p", t)
    def note(self, t): self.add("note", t)
    def bullets(self, items): self.add("bullets", list(items))
    def numbered(self, items): self.add("numbered", list(items))
    def box(self, *paras): self.add("box", list(paras))
    def pagebreak(self): self.add("pagebreak")

    def table(self, header, rows, widths, align=None, caption=None, bold_first=False, label=None):
        self.tables += 1
        if label:
            self.labels[("T", label)] = self.tables
        self.add("table", header, rows, widths, align or ["l"]+["r"]*(len(header)-1),
                 f"<b>Table {self.tables}.</b> {caption}" if caption else None, bold_first)

    def figure(self, path, caption, width=1.0, label=None):
        self.figures += 1
        if label:
            self.labels[("F", label)] = self.figures
        self.add("figure", path, f"<b>Figure {self.figures}.</b> {caption}", width)


def markdown_text(t):
    t = re.sub(r"<b>(.*?)</b>", r"**\1**", t, flags=re.S); t = re.sub(r"<i>(.*?)</i>", r"*\1*", t, flags=re.S)
    t = re.sub(r"<sub>(.*?)</sub>", r"_\1", t); t = re.sub(r"<super>(.*?)</super>", r"^\1", t)
    t = re.sub(r"<br/>", " ", t); t = re.sub(r"<[^>]+>", "", t)
    return t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def to_markdown(doc, path, figure_dir):
    lines = []
    for kind, args, kw in doc.resolved():
        if kind == "title":
            lines += [f"# {markdown_text(args[0])}", "", *(markdown_text(x)+"  " for x in args[1]), ""]
        elif kind == "h1":
            lines += [f"## {markdown_text(args[0])}", ""]
        elif kind == "h2":
            lines += [f"### {markdown_text(args[0])}", ""]
        elif kind in ("p", "note"):
            lines += [markdown_text(args[0]), ""]
        elif kind == "bullets":
            lines += [f"- {markdown_text(x)}" for x in args[0]]+[""]
        elif kind == "numbered":
            lines += [f"{i}. {markdown_text(x)}" for i, x in enumerate(args[0], 1)]+[""]
        elif kind == "box":
            lines += [f"> {markdown_text(x)}" for x in args[0]]+[""]
        elif kind == "table":
            header, rows, _, _, caption, _ = args
            if caption:
                lines += [markdown_text(caption), ""]
            cell = lambda x: markdown_text(str(x)).replace("|", "/")
            lines += ["| "+" | ".join(cell(h) for h in header)+" |", "|"+"---|"*len(header)]
            lines += ["| "+" | ".join(cell(x) for x in r)+" |" for r in rows]+[""]
        elif kind == "figure":
            p, caption, _ = args
            lines += [f"![{markdown_text(caption)}]({figure_dir}/{Path(p).name})", "", markdown_text(caption), ""]
        elif kind == "refs":
            lines += [f"- {markdown_text(x)}" for x in args[0]]+[""]
    path.write_text("\n".join(lines), encoding="utf-8")


def to_pdf(doc, path, footer):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                    Paragraph, Spacer, Table, TableStyle)
    base = Path(matplotlib.get_data_path())/"fonts"/"ttf"
    for name, file in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
                       ("DV-BI", "DejaVuSans-BoldOblique.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(base/file)))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")
    c = colors.HexColor
    body = ParagraphStyle("body", fontName="DV", fontSize=8.5, leading=11.9, textColor=c(INK), spaceAfter=4.5)
    note = ParagraphStyle("note", parent=body, fontSize=7.4, leading=10, textColor=c(INK2), spaceAfter=6)
    cap = ParagraphStyle("cap", parent=note, spaceBefore=3, spaceAfter=9)
    cell = ParagraphStyle("cell", parent=body, fontSize=7.3, leading=9.4, spaceAfter=0)
    cellr = ParagraphStyle("cellr", parent=cell, alignment=TA_RIGHT)
    head = ParagraphStyle("head", parent=cell, fontName="DV-B", textColor=c(INK2))
    headr = ParagraphStyle("headr", parent=head, alignment=TA_RIGHT)
    h1 = ParagraphStyle("h1", fontName="DV-B", fontSize=12.4, leading=16, spaceBefore=9, spaceAfter=5, textColor=c(INK), keepWithNext=1)
    h2 = ParagraphStyle("h2", fontName="DV-B", fontSize=9.4, leading=12.4, spaceBefore=6, spaceAfter=3, textColor=c(INK), keepWithNext=1)
    title = ParagraphStyle("title", fontName="DV-B", fontSize=16.5, leading=20.5, textColor=c(INK), spaceAfter=5)
    sub = ParagraphStyle("sub", parent=body, fontSize=8.2, leading=11.2, textColor=c(INK2), spaceAfter=1)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=11, bulletIndent=1, spaceAfter=2.5)
    left, right, top, bottom = 48, 48, 44, 46
    width = A4[0]-left-right
    ref = ParagraphStyle("ref", parent=note, leftIndent=10, firstLineIndent=-10, spaceAfter=1.5)
    story = []
    for kind, args, kw in doc.resolved():
        if kind == "refs":
            story += [Paragraph(x, ref) for x in args[0]]
        elif kind == "title":
            story += [Paragraph(args[0], title)]+[Paragraph(x, sub) for x in args[1]]+[Spacer(1, 7)]
        elif kind == "h1":
            story.append(Paragraph(args[0], h1))
        elif kind == "h2":
            story.append(Paragraph(args[0], h2))
        elif kind == "p":
            story.append(Paragraph(args[0], body))
        elif kind == "note":
            story.append(Paragraph(args[0], note))
        elif kind == "bullets":
            story += [Paragraph(x, bullet, bulletText="•") for x in args[0]]+[Spacer(1, 3)]
        elif kind == "numbered":
            story += [Paragraph(x, bullet, bulletText=f"{i}.") for i, x in enumerate(args[0], 1)]+[Spacer(1, 3)]
        elif kind == "box":
            inner = [Paragraph(x, ParagraphStyle("boxp", parent=body, spaceAfter=3)) for x in args[0]]
            t = Table([[inner]], colWidths=[width])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c(TINT)), ("LINEBEFORE", (0, 0), (0, -1), 2.2, c(ACCENT)),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                                   ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story += [t, Spacer(1, 8)]
        elif kind == "table":
            header, rows, widths, align, caption, bold_first = args
            hs = [Paragraph(h, headr if a == "r" else head) for h, a in zip(header, align)]
            data = [hs]+[[Paragraph(str(x), cellr if a == "r" else cell) for x, a in zip(r, align)] for r in rows]
            t = Table(data, colWidths=[f*width for f in widths], repeatRows=1, hAlign="LEFT")
            style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), .7, c(INK2)),
                     ("LINEBELOW", (0, 1), (-1, -1), .3, c(RULE)), ("TOPPADDING", (0, 0), (-1, -1), 2.6),
                     ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
            if bold_first:
                style.append(("BACKGROUND", (0, 1), (-1, 1), c(TINT)))
            t.setStyle(TableStyle(style))
            block = ([Paragraph(caption, ParagraphStyle("tcap", parent=note, spaceAfter=3))] if caption else [])+[t]
            if len(rows) <= 4:
                story += [KeepTogether(block), Spacer(1, 8)]
            else:                                    # long tables may split; never strand a caption at a page foot
                story += [CondPageBreak(110), *block, Spacer(1, 8)]
        elif kind == "figure":
            p, caption, frac = args
            from PIL import Image as PILImage
            with PILImage.open(p) as im:
                wpx, hpx = im.size
            iw = width*frac
            story.append(KeepTogether([Image(str(p), width=iw, height=iw*hpx/wpx), Paragraph(caption, cap)]))
        elif kind == "pagebreak":
            story.append(PageBreak())

    def decorate(canvas, d):
        canvas.saveState(); canvas.setFont("DV", 6.8); canvas.setFillColor(c(INK2))
        canvas.drawString(left, 26, footer); canvas.drawRightString(A4[0]-right, 26, f"Page {d.page}")
        canvas.setStrokeColor(c(RULE)); canvas.setLineWidth(.4); canvas.line(left, 35, A4[0]-right, 35); canvas.restoreState()
    template = BaseDocTemplate(str(path), pagesize=A4, leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
                               title=TITLE, author="Team Ghosted", subject="Technical report and investment memorandum")
    template.addPageTemplates([PageTemplate(id="page", frames=[Frame(left, bottom, width, A4[1]-top-bottom, id="f",
                                                                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
                                            onPage=decorate)])
    template.build(story)


# ---------------------------------------------------------------- the report text
def compose(N, D, figs):
    cfg = N["policy"]; V = N["value"]; w = N["weights"]; perf = N["performance"]; kb = N["benchmark"]
    tab = D["table"]; t99 = tab[np.isclose(tab.alpha, .99)].set_index("method"); t95 = tab[np.isclose(tab.alpha, .95)].set_index("method")
    c = D["contrib"]; tot = N["contributions_total"]; s = N["settings"]; val = D["validation"]
    stress = {r["scenario"]: r for r in D["stress"]}; gfc, covid, rates = (stress[k] for k in ("GFC", "COVID", "Rates 2022"))
    worst = max((r["path"] for r in D["stress"]), key=lambda x: x["loss_usd"])
    worst_name = next(r["scenario"] for r in D["stress"] if r["path"] is worst)
    hyp, rev = D["hyp"], D["rev"]; evt = D["evt"]
    ge99, fh99 = val[(cfg["challenger"], .99)], val[(cfg["primary"], .99)]
    ge95, fh95 = val[(cfg["challenger"], .95)], val[(cfg["primary"], .95)]
    boot = D["bootstrap"].set_index(["method", "alpha"]); bh = boot.loc[("historical", .99)]
    rt = {r["year"]: r for r in N["reserve_test"]["results"]}; r10, r25 = rt[10], rt[cfg["survival_years"]]
    rh = N["reserve_history"]; budget = cfg["es_budget"]*V; limit = cfg["drawdown_limit"]
    cmp = D["comparison"]; perm = cmp.set_index("portfolio").loc["Permanent 25/50/25"]
    ew = cmp.set_index("portfolio").loc["Equal weight"]; mv = cmp.set_index("portfolio").loc["Minimum variance"]
    ms = cmp.set_index("portfolio").loc["Maximum Sharpe"]; srp = cmp.set_index("portfolio").loc["Static risk parity"]
    b4060 = cmp.set_index("portfolio").loc["40/60 SPY/AGG"]
    exp = D["expected"]; frq = D["frequency"].set_index("rule"); corr = D["corr"]; data = N["data"]
    held = {k: v["today_buy_hold"] for k, v in stress.items()}
    breaching = [k for k, h in held.items() if h and -h["drawdown"] > limit]
    xi_lo, xi_hi = evt["xi"]-1.96*evt["xi_se"], evt["xi"]+1.96*evt["xi_se"]
    stable = D["scan"][D["scan"].stable]; ok_scan = D["scan"][D["scan"].fit_ok]
    thr = D["thresholds"]
    span = "; ".join(f"{t} {100*lo:.0f}-{100*hi:.0f}%" for t, (lo, hi) in N["target_range"].items())
    alloc = ", ".join(f"{t} {pct(w[t])}" for t in U)
    lf, lf_fhs = N["latest_forecast_99"][cfg["challenger"]], N["latest_forecast_99"][cfg["primary"]]
    same = N["v5_run_same_strategy"]
    liq = N["liquidity_days"]["GFC"]
    # real return needed to keep USD 10m in real terms while paying the schedule: draw w_t (real, share of the initial fund)
    # at the start of year t, so (1 - w_t)(1 + r) = 1, i.e. r = w_t/(1 - w_t)
    real_draw = lambda t: cfg["reserve_initial"]/cfg["fund_value"]*((1+cfg["reserve_growth"])/(1+cfg["inflation"]))**(t-1)
    need1, need25 = (real_draw(t)/(1-real_draw(t)) for t in (1, cfg["survival_years"]))
    V6 = N["model"] == "v6"; ov = N["overlay"] or {}
    if V6:
        v5p, v5s, v5v = ov["v5_performance"], ov["v5_stress"], ov["v5_validation"]
        ge5 = v5v[(cfg["challenger"], .99)]
        mon = lambda x: pd.Period(x, "M").strftime("%b %Y")
        ov_periods = "; ".join(mon(a)+("" if a == b else f"–{mon(b)}") for a, b in ov["periods"])
        overlay_rule = ("while the yield curve (10-year Treasury minus 3-month bill) has been inverted in any of the last 24 months "
                        "<i>and</i> SPY closes the month below the mean of its last 12 month-end closes, half of the SPY and XLE targets "
                        "are held as cash at 0%, until SPY closes a month above that mean")
    worst_fall = max(stress, key=lambda k: stress[k]["path"]["max_fall"])
    doc = Doc()

    # ---------------------------------------------------------------- front page
    doc.add("title", TITLE_V6 if V6 else TITLE, ["Technical report and investment memorandum · Team Ghosted (solo entry) · Quant Edge 1.0 final",
                             f"Data 3 Jan 2005 to {date(N['end'])} · prepared 31 Oct 2026 · committee dashboard: "
                             "<font face='DV-I'>python -m streamlit run dashboard.py</font>"])
    rec = (f"<b>Recommendation: hold this portfolio (mandate v6, the owner's final model).</b> Invest the USD {V/1e6:.1f} million by "
           f"monthly dynamic risk parity across SPY, AGG, GLD and XLE with a recession overlay. From 1 October 2026 hold {alloc}; reset "
           f"the weights at every month-end close with the rule in section 3, and {overlay_rule} (section 3.4; the overlay is "
           f"{'on' if ov['on_now'] else 'off'} at the {date(N['end'])} close). Measure one-day 99% risk daily with GARCH-EVT refitted as "
           f"in its backtest (latest forecast, for {date(lf['date'])}: VaR {usd(lf['var_usd'])}; FHS {usd(lf_fhs['var_usd'])}), using "
           "the higher of the two in any month the overlay switches. Call an extra committee review if the fall from the previous high "
           "passes 15% or if 99% VaR breaches exceed 9 in any 250 days." if V6 else
           f"<b>Recommendation: accept the mandate with this portfolio.</b> Invest the USD {V/1e6:.1f} million by monthly dynamic "
           f"risk parity across SPY, AGG, GLD and XLE. From 1 October 2026 hold {alloc}, and reset the weights at every month-end "
           f"close with the rule in section 3. Measure one-day 99% risk daily with GARCH-EVT, refitted as in its backtest (latest "
           f"forecast, for {date(lf['date'])}: VaR {usd(lf['var_usd'])}). Call an extra committee review if the fall from the previous "
           f"high passes 15%, if 99% VaR breaches exceed 9 in any 250 days, or if a month-end target's historical ES exceeds "
           f"{usd(budget)}.")
    doc.box(rec+f" Plan spending on a real return below the {pct(perf['real_cagr'])} a year the strategy earned after US "
            "inflation, because that figure is history chosen after the fact."
            +(f" <b>Main risk accepted:</b> a crash that arrives before the next month-end meets today's weights, which, held through "
              f"{' and '.join(breaching)}, would have fallen {' and '.join(pct(-held[k]['drawdown']) for k in breaching)}, beyond the "
              "20% limit (section 7)." if breaching else ""),
            *([f"<b>Disclosed:</b> under the team's pre-registered rule the overlay's evaluation is incomplete: its 99% VaR breach counts "
               f"match the expected rate, but the breaches cluster (conditional coverage p {pval(ge99['conditional_coverage_p'])} for "
               f"GARCH-EVT and {pval(fh99['conditional_coverage_p'])} for FHS, both below 0.05). The owner adopted v6 for its smaller "
               f"falls (largest {pct(-perf['maximum_drawdown'])} against {pct(-v5p['maximum_drawdown'])} for the v5 core, which passes "
               f"with GARCH-EVT, p {pval(ge5['conditional_coverage_p'])}). Section 5.6 and PLAN.md 13h record the decision."] if V6 else []),
            "This is the team's proposal for the owner's and the committee's review. Independent human review of the calculations "
            "and of the investment judgement is pending.")
    doc.table(["ETF", "Exposure", "Weight", "USD", "Share of volatility", "Share of 99% ES"],
              [[t, ROLE[t], pct(w[t]), num(w[t]*V), pct(c.vol_contribution[t]), pct(c.es_share[t])] for t in U]
              + [["Total", f"cash {pct(N['cash'])}" if V6 else "", pct(1-N["cash"]), num(V*(1-N["cash"])), "100.0%", "100.0%"]],
              [.08, .3, .12, .16, .17, .17], align=["l", "l", "r", "r", "r", "r"],
              caption=f"Allocation to hold now: target set at the {date(N['end'])} close from data up to that close. Volatility "
                      "shares use the rule's EWMA covariance; ES shares use 2005-2026 daily history (section 5.8).")
    doc.table(["Measure", "Final portfolio", "Context"], [
        [f"Return, {date(N['start'])} to {date(N['end'])}", f"{pct(perf['cagr'], 2)} a year; {pct(perf['real_cagr'], 2)} real",
         f"40/60 SPY/AGG {pct(kb['cagr'], 2)} ({pct(kb['real_cagr'], 2)} real); US CPI {pct(perf['cpi_inflation'], 2)} a year"],
        ["Volatility; largest fall from a high", f"{pct(perf['annual_volatility'])}; {pct(-perf['maximum_drawdown'])}",
         f"40/60: {pct(kb['annual_volatility'])}; {pct(-kb['maximum_drawdown'])}. Policy limit {pct(limit, 0)}"],
        ["One-day 99% VaR; ES (historical, today's weights)", f"{usd(t99.var_usd['historical'])}; {usd(t99.es_usd['historical'])}",
         f"ES budget {usd(budget)} ({pct(cfg['es_budget'], 0)} of NAV); 95% bootstrap interval for ES {usd(bh.es_usd_lo)} to {usd(bh.es_usd_hi)}"],
        ["Worst historical crisis, as run", f"{worst_name}: {pct(worst['return'])} (loss {usd(worst['loss_usd'])})",
         f"GFC {pct(gfc['path']['return'])}, COVID {pct(covid['path']['return'])}; largest fall inside a crisis {pct(gfc['path']['max_fall'])} (GFC)"],
        ["Today's weights held through the GFC; COVID", f"Largest fall {pct(-held['GFC']['drawdown'])}; {pct(-held['COVID']['drawdown'])}",
         (f"{' and '.join(breaching)} beyond the 20% limit: a crash before the next month-end meets today's weights" if breaching
          else "Within the 20% limit")],
        ["Hypothetical joint equity-bond shock", f"{pct(hyp['return'])} (loss {usd(hyp['loss_usd'])})",
         f"SPY −25%, AGG −10%, GLD 0%, XLE {pct(hyp['shocks']['XLE'])}"],
        *([["Recession overlay", f"Cash held in {ov['months_on']} of {ov['months']} months",
             f"{ov_periods}. v5 core without it: largest fall {pct(-v5p['maximum_drawdown'])}, GFC {pct(v5s['GFC']['return'])}"]] if V6 else []),
        [f"99% VaR backtest, {date(ge99_first(D))} to {date(N['end'])}",
         f"GARCH-EVT {ge99['breaches']} breaches vs {ge99['expected_breaches']:.1f} expected; "+("breaches cluster" if V6 else "passes"),
         f"Kupiec p {pval(ge99['kupiec_p'])}, conditional coverage p {pval(ge99['conditional_coverage_p'])}, {ge99['zone']}. "
         f"FHS (named first) {fh99['breaches']} breaches; fails on clustering (p {pval(fh99['conditional_coverage_p'])})"
         +(". Evaluation incomplete; v5 core GARCH-EVT passes (p "+pval(ge5['conditional_coverage_p'])+")" if V6 else "")],
        [f"{cfg['survival_years']}-year cash-reserve test (resampled history)", f"All reserves paid in {pct(r25['all_payments_funded'])} of paths",
         f"USD 10m kept in real terms in {pct(r25['real_capital_preserved'])}; median real balance {usdm(r25['median_real_balance_usd'])}"],
        ["Income: trailing 12-month distribution yield", pct(N["distribution_yield"]["portfolio"], 2),
         "Cash distributions of today's target over the year to 30 Sep 2026; reinvested in every return figure"]],
        [.31, .27, .42], align=["l", "l", "l"],
        caption="Key evidence. NAV USD 9.6 million; one-day risk horizon; returns before the cash reserve. Historical VaR and ES "
                "average today's weights over 2005-2026; the GARCH-EVT figures in the recommendation are tomorrow's risk at current "
                "volatility, so they differ.")
    doc.p("<b>What can go wrong?</b> Stocks and bonds can fall together, as in 2022, when AGG lost "
          f"{usd(-rates['path']['pnl_usd']['AGG'])} and the strategy {pct(-rates['path']['return'])}. A shock can arrive between monthly "
          f"reviews: in COVID the strategy lost {pct(-covid['path']['return'])} in five weeks. Energy can reverse: XLE is {pct(w['XLE'])} of "
          f"the money but {pct(c.es_share['XLE'])} of the 99% ES"
          +(", and today's XLE weight is the highest the rule has set since 2006. " if N["xle_at_maximum"] else ". ")+
          f"In liquidity panics bond and gold ETFs can fall with equities: on the strategy's worst GFC day ({date(liq['day'])}) AGG fell "
          f"{pct(-liq['AGG'])} and GLD {pct(-liq['GLD'])}, and in March 2020 AGG fell "
          + " and ".join(f"{pct(-x)} on {date(d)}" for d, x in sorted(N["covid_agg_worst"].items())) + ". "
          f"<b>How bad can losses get?</b> On about 1 day in 100 the loss exceeds {usd(t99.var_usd['historical'])}, and those days average "
          f"{usd(t99.es_usd['historical'])}. The worst crisis as run cost {usd(worst['loss_usd'])}; the hypothetical shock costs "
          f"{usd(hyp['loss_usd'])}. None of these is a maximum. <b>How confident are we?</b> "
          +("Less than for the v5 core. v6's risk forecasts have about the right number of breaches over "
            f"{ge99['days']:,} days but they cluster, so neither named model passes the pre-registered test; the overlay's benefit rests "
            "mainly on one deep recession (2008); and the strategy and the overlay were chosen after many alternatives were tried on the "
            "same 2005-2026 data, so there is no untouched test period." if V6 else
            f"GARCH-EVT forecasts passed a {ge99['days']:,}-day backtest, but the first-named model (FHS) did not, and the strategy was "
            "chosen after many alternatives were tried on the same 2005-2026 data, so there is no untouched test period."))
    doc.note("Evaluation labels: performance, comparisons and stress tests are a <b>retrospective portfolio evaluation</b>; VaR backtests are "
             "a <b>sequential risk-forecast evaluation</b> (each day's forecast uses data up to the day before). No result is an untouched "
             "out-of-sample test.")

    # ---------------------------------------------------------------- 1 policy
    doc.h1("1. Client, objective and investment policy")
    doc.p("The Serendib University Endowment Fund is a conservative, perpetual USD 10 million pool that pays for scholarships, research, "
          "faculty development and capital projects. Its committee ranks avoiding large losses above maximising return, and wants "
          "real growth over the long run. Each 1 January a cash reserve is set aside for that year's spending: "
          f"{usd(cfg['reserve_initial'])} in the first year, rising {pct(cfg['reserve_growth'], 2)} a year. The first reserve is set aside "
          f"at inception, so {usd(V)} is invested, and every dollar risk figure in this report is on that amount. The return objective "
          f"below is a floor, not what the reserve needs: keeping the USD 10 million in real terms while paying the schedule would need "
          f"a real return of about {pct(need1)} in the first year, rising to {pct(need25)} by year {cfg['survival_years']} as the reserve "
          "outgrows US CPI. The strategy's history falls short of that (section 5.9).")
    doc.table(["Item", "Policy", "Why"], [
        ["Horizon", "Perpetual; strategic review every five years; spending tested over 25 years; risk measured over one trading day",
         "An endowment serves future generations; 25 years = USD 10m ÷ USD 400k (section 5.9)"],
        ["Return objective", f"Expected real return at least {pct(cfg['real_return_floor'], 0)} a year over US CPI; with CPI at "
         f"{pct(cfg['inflation'], 2)} a year (2005-2026) the nominal floor is {pct(N['nominal_floor'], 2)}",
         "Grow purchasing power after inflation; realised returns are reported, not targeted"],
        ["Spending", f"1 January cash reserve: {usd(cfg['reserve_initial'])} in year 1, then +{pct(cfg['reserve_growth'], 2)} a year; paid out, earns nothing",
         "Owner's schedule; it rises faster than US CPI, a conservative assumption"],
        ["Acceptable loss", f"Largest fall from a previous high at most {pct(limit, 0)} (USD {limit*V/1e6:.2f}m), judged on historical crisis paths",
         "The client's first priority: avoid large losses"],
        ["Daily risk budget", f"Historical one-day 99% ES of the current weights at most {pct(cfg['es_budget'], 0)} of NAV ({usd(budget)})",
         "ES measures how large tail losses are, not only how often they occur"],
        *([["Recession overlay", upper_first(overlay_rule)+".", "The curve's slope predicts recessions (Estrella and Mishkin 1996); "
             "the 12-month trend confirms the warning and screens false alarms (section 3.4)"]] if V6 else []),
        ["Universe and concentration", "SPY, AGG, GLD, XLE; long-only, fully invested"
         +(", except cash at 0% while the overlay is on" if V6 else "")+"; no per-ETF caps. Equal risk contributions "
         f"spread volatility, not tail loss (XLE carries {pct(c.es_share['XLE'])} of ES)", f"EFA, EEM and XLK move with SPY (daily "
         f"correlation {corr.loc['SPY', 'EFA']:.2f}, {corr.loc['SPY', 'EEM']:.2f}, {corr.loc['SPY', 'XLK']:.2f}) and add little diversification"],
        ["Rebalancing", "Re-estimate and trade at each month-end close; holdings drift in between; trading cost assumed zero",
         "Monthly matches how fast volatility changes (section 3)"],
        ["Monitoring", "One-day 99% VaR from GARCH-EVT refitted as in its backtest, daily; FHS as a second view"
         +("; the higher of the two in months the overlay switches; review at a 15% fall or a Basel red zone" if V6 else
           "; review at a 15% fall, a Basel red zone or a month-end target above the ES budget"),
         "On v6 both models' breaches cluster (section 5.6), hence the higher-of-two safeguard" if V6 else
         "GARCH-EVT is the model whose forecasts passed the backtest (section 5.6); chosen after that backtest"],
        ["Benchmarks", "40/60 SPY/AGG (active return); SPY (beta, Treynor, Jensen's alpha); 3-month T-bill (Sharpe)",
         "A passive balanced mix the endowment could hold instead"]],
        [.16, .48, .36], align=["l", "l", "l"],
        caption=("Investment policy (mandate v6, tag prereg-v6: the v5 policy values, tag prereg-v5, plus the recession overlay). "
                 if V6 else "Investment policy (mandate v5, tag prereg-v5). ")+"These are the team's choices, not competition rules; the brief "
                "leaves the horizon, objective and limits to the manager.")
    doc.note("The policy was written in October 2026 with the 2005-2026 history in view. In particular the ES budget was raised from 2.5% "
             f"to 3% of NAV after the current target's ES ({pct(t99.es_pct['historical']/100, 2)}) was seen to exceed 2.5% (section 6).")

    # ---------------------------------------------------------------- 2 data
    doc.h1("2. Data sources and cleaning")
    data_section(doc, N, D)

    # ---------------------------------------------------------------- 3 construction
    doc.h1("3. Portfolio construction")
    doc.h2("3.1 Why risk parity rather than a return-maximising optimiser")
    doc.p("Markowitz mean-variance optimisation chooses weights from expected returns and a covariance matrix. The weights are very "
          "sensitive to the expected returns, the least reliable input. Earlier versions of this mandate show the problem: a "
          "return-maximising optimiser chose 45% equity (SPY 35 / AGG 40 / GLD 15 / XLK 10) and broke the 20% loss limit in the GFC "
          "replay, and the minimum-CVaR optimiser used after it put 70-88% in AGG; with shrunk historical means as inputs, the choice "
          "of return estimator decided the result. Risk parity needs only the covariance matrix: it sets weights so that each ETF "
          "contributes the same share of portfolio volatility, which spreads risk rather than capital (Maillard, Roncalli and "
          "Teïletche 2010). Markowitz and CAPM tools remain in use for evaluation: minimum-variance and maximum-Sharpe portfolios are "
          "comparisons in section 5.2, and beta, the Treynor ratio and Jensen's alpha against SPY are in section 5.1.")
    doc.h2("3.2 The rule")
    doc.numbered([
        f"At each month-end close t, take the last {s['window']} daily simple returns of SPY, AGG, GLD and XLE.",
        f"Weight the return k days back by λ<super>k</super> with λ = {s['ewma_lambda']}, normalise the weights to sum to one, and "
        "estimate the covariance Σ<sub>t</sub> around the weighted mean.",
        "Find long-only weights with equal risk contributions, w<sub>i</sub>(Σ<sub>t</sub>w)<sub>i</sub> = w′Σ<sub>t</sub>w / 4 for each "
        "ETF, by solving the convex problem min ½y′Σ<sub>t</sub>y − ¼Σ<sub>i</sub> ln y<sub>i</sub> over y &gt; 0 and setting "
        "w = y / Σ<sub>i</sub>y<sub>i</sub> (Spinu 2013). Its first-order condition (Σ<sub>t</sub>y)<sub>i</sub> = 1/(4y<sub>i</sub>) "
        "makes every contribution equal.",
        "Trade to w at that close and hold the shares until the next month-end; the weights drift with prices in between."])
    doc.p(f"Only data up to each decision close is used, so every target could have been computed on its date. The first target needed "
          f"{s['min_history']} days of returns; the strategy's returns start on {date(N['start'])}, and {N['targets']-1} month-end "
          f"re-estimations follow to {date(N['end'])}. Targets ranged over {span}; the equity share rises when equity volatility is low "
          "relative to bonds and gold and falls when it spikes (Figure @F:targets@)."
          +(" Today's XLE weight is the highest the rule has set." if N["xle_at_maximum"] else ""))
    doc.figure(figs["targets"], f"Target weights at each month-end, {date(N['start'])} to {date(N['end'])}; labels show the target "
               "from 1 October 2026. Weights sum to 100%.", label="targets")
    doc.h2("3.3 Settings")
    half = np.log(.5)/np.log(s["ewma_lambda"]); eff = (1+s["ewma_lambda"])/(1-s["ewma_lambda"]); fresh = 1-s["ewma_lambda"]**21
    doc.p(f"λ = {s['ewma_lambda']} gives a half-life of {half:.0f} trading days and an effective sample of about {eff:.0f} days; "
          "RiskMetrics (1996) uses 0.94 for daily and 0.97 for monthly forecasts. After a month, "
          f"{pct(fresh, 0)} of the estimator's information is new, which suits monthly decisions. The {s['window']}-day window caps "
          "the memory at about three years. The settings were registered before the strategy's risk backtest and were not tuned "
          "afterwards, but they were fixed after the strategy's return path had been seen, and the monthly frequency was chosen after "
          "the weekly and quarterly versions in Table @T:frequency@ had been compared.")
    doc.table(["Re-estimation", "CAGR", "Volatility", "Largest fall", "Turnover a year", "Resets", "GFC", "COVID", "2022"],
              [[k, pct(r.cagr, 2), pct(r.volatility), pct(r.max_drawdown), f"{r.turnover:.2f}×", f"{int(r.rebalances):,}",
                pct(r.GFC), pct(r.COVID), pct(r["Rates 2022"])] for k, r in frq.iterrows()],
              [.19, .09, .1, .11, .12, .1, .09, .09, .11], label="frequency",
              caption=("The core rule (no overlay)" if V6 else "The same rule")+f" re-estimated weekly, monthly and quarterly, {date(N['start'])} to {date(N['end'])}. Crisis "
                      "columns: return from the scenario start close to its end close. Zero trading cost. Retrospective.")
    wk, qt, mo = frq.loc["Weekly"], frq.loc["Quarterly"], frq.loc["Monthly (chosen)"]
    doc.p(f"Weekly re-estimation traded {wk.turnover:.2f}× NAV a year against {mo.turnover:.2f}× and its largest fall was "
          f"{pct(wk.max_drawdown)} ({'beyond' if wk.max_drawdown > limit else 'within'} the 20% limit); quarterly re-estimation "
          f"{'lost more' if qt.COVID < mo.COVID else 'lost less'} in COVID ({pct(qt.COVID)} against {pct(mo.COVID)}) because its weights "
          "were set before volatility rose. Monthly sits between noise and staleness; no calendar rule catches a crash that unfolds "
          "within days."+(" All three rows are the core rule without the overlay (the monthly row is the v5 core)." if V6 else ""))
    if V6:
        doc.h2("3.4 The recession overlay")
        doc.p("The core rule reacts to volatility, so it cuts risk only after markets have become turbulent. The overlay adds a slower, "
              "economic signal aimed at long downturns such as 2008. At each month-end close: (1) <b>warning</b>: the 10-year Treasury "
              "yield minus the 3-month bill yield (FRED DGS10 and DTB3, bond-equivalent, monthly mean) was negative in any of the last "
              "24 months; the curve's slope predicts US recessions (Estrella and Mishkin 1996), the team's 1962-2025 check found an "
              "inversion before each of the eight recessions since 1969, and 24 months is the upper end of the published 6-24 month lead. (2) <b>Confirmation</b>: SPY's month-end close is below the mean of its last 12 "
              "month-end closes, a trend filter of the kind Faber (2007) tests (he uses 10 months; 12 matches annual earnings), which "
              "screens the curve's false alarms. (3) <b>Action</b>: while both "
              "hold, half of the SPY and XLE targets are held as cash at 0%; XLE is cut because energy demand and earnings fall in "
              "recessions, and cash rather than AGG because AGG also fell in the October 2008 liquidity crunch. (4) <b>Exit</b>: the first "
              "month-end with SPY above its 12-month mean. Sahm-rule and credit-spread signals were tested and left out: in 2005-2026 the "
              "first was late and the second often on outside recessions (PLAN.md 13h).")
        rows = [["CAGR", pct(perf["cagr"], 2), pct(v5p["cagr"], 2)], ["Real CAGR (US CPI)", pct(perf["real_cagr"], 2), pct(v5p["real_cagr"], 2)],
                ["Volatility", pct(perf["annual_volatility"]), pct(v5p["annual_volatility"])],
                ["Largest fall from a high", pct(-perf["maximum_drawdown"]), pct(-v5p["maximum_drawdown"])],
                *[[("2022 rates" if k == "Rates 2022" else k)+" (start to end close)", pct(stress[k]["path"]["return"]),
                   pct(v5s[k]["return"])] for k in SCENARIOS],
                ["Historical ES99 of the daily path", pct(ov["es99_path"], 2), pct(ov["es99_path_v5"], 2) if ov["es99_path_v5"] else "n/a"],
                ["Months in cash (average cash); turnover a year", f"{ov['months_on']} ({pct(ov['average_cash'], 1)}); "
                 f"{perf['turnover_per_year']:.2f}×", f"none; {v5p['turnover_per_year']:.2f}×"]]
        doc.table(["Measure", "v6 (with overlay)", "v5 core (no overlay)"], rows, [.46, .27, .27], label="overlay",
                  caption=f"What the overlay changed, {date(N['start'])} to {date(N['end'])}, daily, zero cost, before the cash reserve. "
                          "Retrospective.")
        doc.p(f"The overlay held cash in {ov_periods}. It mattered most in the GFC, where it was on from December 2007 to June 2009: the "
              f"strategy ended the scenario {pct(stress['GFC']['path']['return'])} against {pct(v5s['GFC']['return'])} for the core, and "
              f"its largest fall over the whole period dropped from {pct(-v5p['maximum_drawdown'])} to {pct(-perf['maximum_drawdown'])}. "
              "In 2022 it switched on only in November, after the rate-rise drawdown, so that scenario is unchanged; apart from the GFC, "
              f"each spell lasted at most {max(pd.Period(b, 'M').ordinal-pd.Period(a, 'M').ordinal+1 for a, b in ov['periods'][1:])} "
              "months. Today's target is unaffected while the overlay is off. "
              f"<b>Disclosure:</b> the overlay was designed in the session that had seen the 2005-2026 data and a scratch backtest of it, "
              f"including an 18-month warning window seen to miss part of 2008 before 24 months was chosen; it was registered at tag "
              f"{N['prereg_tag']} before its risk forecasts were computed, and a disclosed post-tag timing fix was rerun.")

    # ---------------------------------------------------------------- 4 risk methods
    doc.h1("4. Risk measurement and validation methods")
    doc.h2("4.1 Units and definitions")
    doc.p("The daily portfolio simple return is R<sub>p</sub> = Σ<sub>i</sub>w<sub>i</sub>R<sub>i</sub> with weights at the previous "
          "close, and the log loss is L = −ln(1 + R<sub>p</sub>), positive for a loss. Log returns are used for statistics; simple "
          "returns compound wealth and add across ETFs. VaR<sub>α</sub> is the α-quantile of L; ES<sub>α</sub> is the average loss "
          "beyond it, the mean of the worst (1 − α) share of days (Artzner et al. 1999; Acerbi and Tasche 2002). Dollar VaR is "
          f"V(1 − e<super>−VaR</super>) with V = {usd(V)}; dollar ES averages the dollar tail losses rather than converting log ES. "
          "The horizon is one trading day; multi-day risk is not obtained by multiplying by √h.")
    doc.h2("4.2 Models")
    doc.table(["Model", "How it works", "Main assumption"], [
        ["Historical simulation", f"Today's weights applied to all {len(D['losses']):,} daily returns since 2005; VaR by linear interpolation; ES "
         "averages the worst 1% with fractional weight at the boundary", "The past contains the relevant losses; cannot go beyond the worst day seen"],
        ["Parametric normal; Student-t", "Normal or Student-t distribution fitted to daily portfolio log returns; closed-form VaR and ES",
         "Normal: thin tails. Student-t: fatter, symmetric tails"],
        ["Monte Carlo normal; Student-t", f"{cfg['n_sim']:,} joint scenarios of the four ETFs (multivariate normal, or t with a shared "
         "scale shock), combined through simple returns; fixed seed", "Joint distribution and dependence correctly specified"],
        ["EVT (peaks over threshold)", "Generalised Pareto distribution fitted to losses above a threshold u (section 5.5); empirical below u",
         "Losses beyond u follow a GPD (Balkema and de Haan 1974; Pickands 1975)"],
        ["Filtered historical simulation (FHS)", "GJR-GARCH(1,1) volatility (Glosten, Jagannathan and Runkle 1993); past standardised "
         "residuals rescaled by tomorrow's volatility (Barone-Adesi et al. 1999)", "Volatility clustering captured; residuals independent"],
        ["GARCH-EVT", "The same GARCH filter with a GPD fitted to the worst 10% of standardised residuals (McNeil and Frey 2000)",
         "As FHS, plus a GPD residual tail"]],
        [.2, .5, .3], align=["l", "l", "l"], caption="Risk models. The first six describe the whole sample; FHS and GARCH-EVT give "
                                                     "tomorrow's risk at current volatility.")
    doc.h2("4.3 Backtesting, stress testing and attribution")
    doc.p(f"For every day from {date(ge99_first(D))} to {date(N['end'])} ({ge99['days']:,} days) each model is refitted on the previous "
          f"{cfg['window']} days of the strategy's own returns (slow models every {cfg['refit']} days, volatility daily) and forecasts the "
          "next day's VaR; a breach is a loss larger than the VaR. Kupiec's (1995) test asks whether the breach rate equals 1 − α; "
          "Christoffersen's (1998) independence test asks whether breaches follow breaches; conditional coverage combines both. The "
          "Basel (1996) traffic light classifies the last 250 days of 99% VaR: green 0-4 breaches, yellow 5-9, red 10 or more; the "
          "share of all rolling 250-day windows in the red is also reported. A model passes at 99% if forecasts exist for at least 95% "
          "of days, the last 250 days are green or yellow, and the Kupiec and conditional-coverage p-values both exceed 0.05. "
          f"{LABEL[cfg['primary']]} was named the primary model and {LABEL[cfg['challenger']]} the challenger before these backtests "
          "were run; the forecast file carries the strategy hash on every row and is refused for any other weights.")
    doc.p("Historical scenarios replay the strategy's actual path, month-end resets included, from the close on each start date to the "
          "end date (SPY peak to trough): GFC 9 Oct 2007-9 Mar 2009, COVID 19 Feb-23 Mar 2020, rate rises 3 Jan-12 Oct 2022. Today's "
          "target is also bought at each start close and left to drift with prices, to show a crisis that arrives before the rule "
          "reacts. The hypothetical "
          "scenario shocks SPY −25% and AGG −10% at once with gold unchanged; XLE's shock is its conditional mean given those, from the "
          "covariance of SPY's worst 10% of days in 2005-2016. The reverse stress test finds the smallest joint shock, in covariance "
          "distance, that costs 20% of NAV. Dollar ES contributions use the joint daily returns of the four ETFs: the worst 1% of "
          "portfolio days, with fractional weight at the boundary, define one set of tail weights, applied to every ETF's dollar loss, "
          "so the contributions add up exactly to the portfolio ES.")
    doc.p(f"Uncertainty: {cfg['bootstrap_reps']} bootstrap resamples of {cfg['bootstrap_block']}-day blocks of whole daily rows "
          "(circular, so cross-ETF dependence and short volatility clusters survive) refit the historical, normal and EVT models; "
          "the report gives 95% percentile intervals. The EVT threshold percentile is held fixed in the bootstrap, so threshold "
          "uncertainty is shown separately in section 5.5.")

    # ---------------------------------------------------------------- 5 results
    doc.h1("5. Results")
    doc.h2("5.1 Performance")
    doc.p(f"From {date(N['start'])} to {date(N['end'])} the strategy grew {usd(V)} to {usdm(N['end_value'])} ({pct(perf['cagr'], 2)} a year), "
          f"a little less than the 40/60 benchmark ({pct(kb['cagr'], 2)}, {usdm(N['bench_end_value'])}), with lower volatility "
          f"({pct(perf['annual_volatility'])} against {pct(kb['annual_volatility'])}) and a smaller largest fall ({pct(-perf['maximum_drawdown'])} "
          f"against {pct(-kb['maximum_drawdown'])}). After US CPI inflation of {pct(perf['cpi_inflation'], 2)} a year it earned "
          f"{pct(perf['real_cagr'], 2)} real. Its beta to SPY is {perf['beta']:.2f}; Jensen's alpha of {pct(perf['jensen_alpha'], 2)} a year "
          "is return not explained by that exposure, and the information ratio of "
          f"{minus(format(perf['information_ratio'], '.2f'))} reflects the small shortfall against 40/60. On {date(N['end'])} the strategy stood "
          f"{pct(-N['current_drawdown'])} below its previous high.")
    doc.figure(figs["wealth"], f"Growth of {usd(V)} and fall from the previous high, final portfolio against 40/60 SPY/AGG (quarterly "
               "or 5-point drift rebalancing)"+(" and the v5 core without the overlay" if V6 else "")+", daily, zero cost, before the cash "
               "reserve. Grey: the three crisis scenarios"+("; orange: months the overlay held cash." if V6 else "."))
    k = perf
    doc.table(["KPI", "Final portfolio", "40/60 SPY/AGG", "Definition"], [
        ["CAGR", pct(k["cagr"], 2), pct(kb["cagr"], 2), "Compound annual growth of the daily path"],
        ["Real CAGR", pct(k["real_cagr"], 2), pct(kb["real_cagr"], 2), f"(1 + CAGR)/(1 + {pct(cfg['inflation'], 2)}) − 1: the policy CPI rate, "
         "US CPI 2005-2026 (FRED CPIAUCSL)"],
        ["Cumulative return", pct(k["cumulative_return"]), pct(kb["cumulative_return"]), "Whole period"],
        ["Volatility", pct(k["annual_volatility"], 2), pct(kb["annual_volatility"], 2), "Daily standard deviation × √252"],
        ["Sharpe ratio", f"{k['sharpe']:.2f}", f"{kb['sharpe']:.2f}", "Annual excess return over the 3-month T-bill (FRED DTB3) / its volatility"],
        ["Sortino ratio", f"{k['sortino']:.2f}", f"{kb['sortino']:.2f}", "Annual mean return / downside deviation below 0"],
        ["Beta to SPY", f"{k['beta']:.2f}", f"{kb['beta']:.2f}", "Excess-return regression on SPY excess returns"],
        ["Treynor ratio", pct(k["treynor"], 1), pct(kb["treynor"], 1), "Annual excess return / beta"],
        ["Jensen's alpha", pct(k["jensen_alpha"], 2), pct(kb["jensen_alpha"], 2), "Annual excess return not explained by beta × SPY excess return"],
        ["Information ratio", minus(f"{k['information_ratio']:.2f}"), "n/a", "Annual active return over 40/60 / tracking error"],
        ["Maximum drawdown", pct(-k["maximum_drawdown"]), pct(-kb["maximum_drawdown"]), "Largest fall from a previous high"],
        ["Calmar ratio", f"{k['calmar']:.2f}", f"{kb['calmar']:.2f}", "CAGR / maximum drawdown"],
        ["Longest time under water", f"{k['max_underwater_days']} days", f"{kb['max_underwater_days']} days", "Trading days below a previous high"],
        ["Rebalancing", f"{k['rebalances']} resets; {k['turnover_per_year']:.2f}× a year", "Quarterly or 5-pt drift", "Month-end resets; sum of absolute weight changes"]],
        [.18, .19, .17, .46], align=["l", "r", "r", "l"],
        caption=f"Performance, {date(N['start'])} to {date(N['end'])}, daily simple returns, zero cost, before the cash reserve. "
                f"Real returns deflate by the policy rate {pct(cfg['inflation'], 2)} a year (US CPI 2005-2026); CPI over these dates "
                f"was {pct(k.get('path_cpi_inflation', k['cpi_inflation']), 2)} a year.")
    doc.h2("5.2 Comparison with alternatives")
    weights_text = lambda r: "dynamic" if r.weights is None else "/".join(f"{100*r.weights[t]:.0f}" for t in U)
    doc.table(["Portfolio", "Weights % SPY / AGG / GLD / XLE", "CAGR", "Real", "Vol.", "Max fall", "Sharpe", "ES99 1-day", "GFC", "COVID", "2022"],
              [[r.portfolio.replace(" (monthly dynamic risk parity)", ""), weights_text(r), pct(r.cagr, 2), pct(r.real_cagr, 2),
                pct(r.volatility), pct(r.max_drawdown), f"{r.sharpe:.2f}", pct(r.es99_daily, 2), pct(r.GFC), pct(r.COVID),
                pct(r["Rates 2022"])] for _, r in cmp.iterrows()],
              [.165, .15, .07, .068, .06, .07, .075, .075, .075, .08, .08], bold_first=True, label="comparison",
              caption=f"Final portfolio against fixed-weight alternatives, {date(N['start'])} to {date(N['end'])}. Fixed weights rebalance "
                      "quarterly or on a 5-point drift; zero cost. Minimum variance, maximum Sharpe and static risk parity are estimated "
                      "on the whole 2005-2026 sample, so they use hindsight the final portfolio did not have. ES99 1-day: historical ES of "
                      f"each path's own daily returns (for the final portfolio its realised path; today's target alone: "
                      f"{pct(t99.es_pct['historical']/100, 2)}). Retrospective.")
    doc.figure(figs["scatter"], "(a) Ex-ante Markowitz view: long-only efficient frontier of the four ETFs, with the Markowitz "
               "portfolios, the 40/60 benchmark, equal weight and today's target, under the frozen estimator (means shrunk 50% toward "
               "the seven-ETF average, Ledoit-Wolf covariance, 2005-2026). (b) Realised annual return against largest fall for the "
               "portfolios in Table @T:comparison@.",
               label="scatter")
    final = cmp.iloc[0]; peers = cmp[cmp.cagr >= final.cagr-.005]          # alternatives earning about as much or more
    best_fall = final.max_drawdown <= peers.max_drawdown.min()+1e-12
    crisis_best = [k for k in SCENARIOS if final[k] >= peers[k].max()-1e-12]
    crisis_beaten = {k: peers.loc[peers[k].idxmax()] for k in SCENARIOS if k not in crisis_best}
    beaten = "; ".join(f"in {('2022' if k == 'Rates 2022' else k)} {r.portfolio.lower()} lost less ({pct(r[k])})" for k, r in crisis_beaten.items())
    doc.p(f"Among the portfolios that earned at least about as much ({pct(final.cagr-.005, 1)} a year or more), the final portfolio had "
          f"{'the smallest' if best_fall else 'not the smallest'} largest fall ({pct(final.max_drawdown)}) and the smallest losses in "
          f"{' and '.join('2022' if k == 'Rates 2022' else k for k in crisis_best) or 'none of the crises'}"
          +(f"; {beaten}." if beaten else ".")+
          f" It is not best on every measure. The permanent-portfolio mix (SPY 25 / AGG 50 / GLD 25) earned {pct(perm.cagr, 2)} a year "
          f"with a similar largest fall ({pct(perm.max_drawdown)}) and a Sharpe ratio of {perm.sharpe:.2f} against {final.sharpe:.2f}, but "
          f"lost {pct(-perm['Rates 2022'])} in 2022; equal weight earned {pct(ew.cagr, 2)} but fell {pct(ew.max_drawdown)}. The Markowitz "
          f"minimum-variance and maximum-Sharpe portfolios, built with hindsight, did best in the GFC ({pct(mv.GFC)} and {pct(ms.GFC)}) but "
          f"earned only {pct(mv.cagr, 2)} and {pct(ms.cagr, 2)} a year and lost {pct(-mv['Rates 2022'])} and {pct(-ms['Rates 2022'])} in "
          f"2022, when bonds fell. Static risk parity, the same idea with fixed weights, earned {pct(srp.cagr, 2)} with a larger fall "
          f"({pct(srp.max_drawdown)}) and a larger COVID loss ({pct(-srp.COVID)}).")
    bal = cmp.set_index("portfolio").loc["Balanced 35/50/15"]
    # the fixed mixes of Table 9, classified by their recorded mandate v5 checks (C2 ES budget, C4 backtest, C5 crisis loss)
    shown = ["near_parity", "min_variance", "max_sharpe", "40_60", "60_40", "equal_weight", "permanent", "balanced_35_50_15"]
    v5 = {k: N["v5_run_checks"][k] for k in shown if k in N["v5_run_checks"]}
    passed = [k for k, ch in v5.items() if all(ch.values())]
    other_failed = [k for k, ch in v5.items() if not (ch.get("C2") and ch.get("C5"))]
    c4_failed = [k for k, ch in v5.items() if ch.get("C4") is False and k not in other_failed]
    join = lambda ks: ", ".join(V5_NAMES[k] for k in ks[:-1])+(" and " if len(ks) > 1 else "")+(V5_NAMES[ks[-1]] if ks else "none")
    doc.p("The Markowitz portfolios use the same frozen estimator as Figure @F:scatter@(a): minimum variance minimises w′Σw; maximum "
          "Sharpe maximises (w′μ − 2%)/√(w′Σw) with a fixed 2% risk-free rate; both are long-only and fully invested. Under those "
          f"inputs today's target lies below the frontier, because risk parity ignores expected returns by design. "
          +(f"In the mandate v5 run (results/{V5_RUN}), which judges each fixed mix with its own risk forecasts and buy-and-hold crisis "
            f"replays, {({0: 'no', 1: 'one', 2: 'two', 3: 'three'}).get(len(passed), len(passed))} fixed "
            f"mix{'' if len(passed) == 1 else 'es'} also met every policy limit: {join(passed)}"
            +(f" (balanced's quarterly-rebalanced path here fell {pct(bal.max_drawdown)})" if "balanced_35_50_15" in passed else "")
            +f". {upper_first(join(c4_failed))} failed the risk-forecast backtest, and {join(other_failed)} broke the crisis-loss or ES "
            "limits. " if v5 else "")+
          "The team prefers the dynamic rule to the permanent mix because it "
          f"lost less in all three crises ({pct(final.GFC)}, {pct(final.COVID)}, {pct(final['Rates 2022'])} against {pct(perm.GFC)}, "
          f"{pct(perm.COVID)}, {pct(perm['Rates 2022'])}) with lower volatility ({pct(final.volatility)} against {pct(perm.volatility)}), at "
          f"a cost of {100*(perm.cagr-final.cagr):.2f} points of return a year. For a fund that ranks avoiding large losses first that is "
          "the right trade on this evidence, but it is a judgement on one 20-year history.")
    doc.h2("5.3 Expected return and the return objective")
    rows = []
    for window in ("Full sample", "Last 10 years", "Last 5 years"):
        e = exp[exp.window == window]
        raw, shr = e.iloc[0], e.iloc[1]
        rows.append([f"{window} (from {date(raw.start)})", pct(raw.geometric, 2), pct(raw.real, 2), pct(shr.geometric, 2), pct(shr.real, 2)])
    doc.table(["Estimation window", "Raw means: nominal", "Raw: real", "50% shrinkage: nominal", "Shrinkage: real"], rows,
              [.3, .18, .14, .22, .16], label="expected",
              caption=f"Expected geometric annual return of today's target, (1 + w′μ)e<super>−w′Σw/2</super> − 1 with Ledoit-Wolf covariance; "
                      f"real at US CPI {pct(cfg['inflation'], 2)} a year. The frozen estimator shrinks each ETF's mean halfway to the "
                      "seven-ETF average. History projected forward, not a forecast.")
    doc.p(f"The objective is forward-looking: at least {pct(cfg['real_return_floor'], 0)} a year above inflation, a nominal "
          f"{pct(N['nominal_floor'], 2)}. Today's target expects {pct(exp.geometric.min(), 1)} to {pct(exp.geometric.max(), 1)} nominal "
          f"({pct(exp.real.min(), 1)} to {pct(exp.real.max(), 1)} real) across the six estimates, so the objective is met under each. "
          f"Shrinkage adds {100*(exp.geometric[exp.estimator != 'Raw historical means'].mean()-exp.geometric[exp.estimator == 'Raw historical means'].mean()):.1f} "
          "points on average because it lifts AGG's mean toward the equity average; the raw-mean figures are the more conservative guide. "
          f"The realised real return was {pct(perf['real_cagr'], 2)} a year (section 5.9 tests whether that pays the reserve).")
    doc.h2("5.4 VaR and Expected Shortfall")
    doc.table(["Model", "Family", "VaR 95%", "ES 95%", "VaR 99%", "ES 99%", "ES/VaR 99%"],
              [[LABEL[m], FAMILY[m], num(t95.var_usd[m]), num(t95.es_usd[m]), num(t99.var_usd[m]), num(t99.es_usd[m]),
                f"{t99.es_usd[m]/t99.var_usd[m]:.2f}"] for m in METHODS],
              [.25, .14, .12, .12, .12, .12, .13], label="models",
              caption="One-day VaR and ES of today's target held fixed, USD on NAV USD 9.6 million, estimated on 3 Jan 2005-30 Sep 2026; "
                      "FHS and GARCH-EVT are conditional on current volatility. "
                      +("All fits succeeded." if (tab.status == "ok").all() else "Failed fits are shown as unavailable."))
    doc.figure(figs["models"], "One-day 99% VaR and ES by model, today's target, USD (Table @T:models@). Dashed line: the policy ES "
               "budget, which applies to historical ES.", label="models")
    h, n, e, mcn, mct, st = (t99.loc[m] for m in ("historical", "normal", "evt", "mc_normal", "mc_t", "student_t"))
    mce = D["mc_error"].set_index("method")
    mc_spread = "; ".join(f"{LABEL[m]} {usd(mce.es_min[m])} to {usd(mce.es_max[m])}" for m in mce.index)
    doc.p(f"At 99% VaR ranges from {usd(t99.var_usd.min())} ({LABEL[t99.var_usd.idxmin()]}) to {usd(t99.var_usd.max())} "
          f"({LABEL[t99.var_usd.idxmax()]}) and ES from {usd(t99.es_usd.min())} to {usd(t99.es_usd.max())}. The normal model puts ES at "
          f"{usd(n.es_usd)}, while the observed worst 1% of days average {usd(h.es_usd)} ({h.es_usd/n.es_usd:.2f}×): daily returns have "
          f"fatter tails than a bell curve, and the gap widens with confidence (historical over normal ES "
          f"{t95.es_usd['historical']/t95.es_usd['normal']:.2f}× at 95% and {h.es_usd/n.es_usd:.2f}× at 99%). At 95% the normal VaR "
          f"({usd(t95.var_usd['normal'])}) is even above the historical one ({usd(t95.var_usd['historical'])}) while its ES is below: "
          "daily returns are peaked in the middle and heavy in the tails, so a bell curve fitted to them overstates moderate losses "
          f"and understates extreme ones. Student-t and its Monte Carlo version ({usd(st.es_usd)}, {usd(mct.es_usd)}) capture most of the "
          f"fat tail; Monte Carlo normal ({usd(mcn.es_usd)}) simulates the four ETFs jointly but keeps the thin tail. "
          f"Monte Carlo simulation error: across five seeds (100,000 scenarios each) the 99% ES ranged {mc_spread}. EVT ({usd(e.es_usd)}) "
          "agrees with history because both are driven by the same extremes, but unlike history it can extrapolate past the worst day. "
          f"FHS and GARCH-EVT ({usd(t99.es_usd['fhs'])}, {usd(t99.es_usd['garch_evt'])}) answer a different question: tomorrow's risk at "
          f"today's volatility, which GARCH puts at {pct(N['vol_next_day_annual'])} a year against a 2005-2026 average of "
          f"{pct(N['vol_average_annual'])} for these weights.")
    sens = D["sens"]; srows = []
    for label, tb in sens.items():
        tb = tb[np.isclose(tb.alpha, .99)].set_index("method")
        srows.append([label]+[num(tb.es_usd[m]) for m in ("historical", "normal", "evt", "garch_evt")])
    brows = [[LABEL[m], f"{num(boot.loc[(m, .99)].var_usd_lo)} to {num(boot.loc[(m, .99)].var_usd_hi)}",
              f"{num(boot.loc[(m, .99)].es_usd_lo)} to {num(boot.loc[(m, .99)].es_usd_hi)}", f"{int(boot.loc[(m, .99)].reps_ok)}"]
             for m in ("historical", "normal", "evt")]
    doc.table(["Estimation window", "Historical ES 99%", "Normal ES 99%", "EVT ES 99%", "GARCH-EVT ES 99%"], srows,
              [.28, .18, .18, .18, .18], caption="Sensitivity of one-day 99% ES (USD) to the estimation window, today's target.")
    doc.table(["Model", "VaR 99%, 95% interval (USD)", "ES 99%, 95% interval (USD)", "Resamples"], brows, [.25, .3, .3, .15],
              caption=f"Bootstrap intervals: {cfg['bootstrap_reps']} circular block resamples of {cfg['bootstrap_block']} days, today's "
                      "target, 2005-2026. They cover estimation noise, not the choice of model.")
    doc.p(f"Historical ES of {usd(h.es_usd)} is inside the {usd(budget)} budget, but its 95% interval runs from {usd(bh.es_usd_lo)} to "
          f"{usd(bh.es_usd_hi)}: the budget is met by the point estimate, not with statistical confidence. Over the last 750 days, a "
          f"calmer period, historical ES is {usd(sens['Last 750 days'].set_index(['method', 'alpha']).loc[('historical', .99)].es_usd)}.")
    doc.h2("5.5 Extreme value theory: threshold and tail")
    doc.p("The threshold rule scans u from the 80th to the 98.5th percentile of daily losses in steps of 0.5 points, keeping candidates "
          "with at least 50 exceedances. A threshold is stable when its shape estimate ξ lies within the 95% confidence interval of ξ at "
          "every higher candidate (at least three of them). Among stable thresholds the rule picks the fit with the smallest "
          "Kolmogorov-Smirnov distance to the exceedances. This is a project heuristic, not an optimal or significance-calibrated "
          f"procedure. It chose u = {pct(evt['u'], 2)} daily loss (the {100*evt['threshold_q']:.1f}th percentile) with {evt['n_exceed']} "
          f"exceedances, ξ = {evt['xi']:.3f} (95% interval {xi_lo:.2f} to {xi_hi:.2f}) and scale σ = {pct(evt['sigma'], 3)}. Stable "
          f"thresholds run from the {100*stable.q.min():.1f}th to the {100*stable.q.max():.1f}th percentile. ξ &gt; 0 means a heavy, "
          "power-law tail; ξ &lt; 1 means ES is finite. The mean excess rises roughly in a straight line above u (Figure @F:evt@(a)), "
          f"as a GPD with ξ &gt; 0 implies. ξ is not flat, though: it drifts up from {ok_scan.xi.iloc[0]:.2f} at the "
          f"{100*ok_scan.q.iloc[0]:.0f}th percentile to {stable.xi.min():.2f}-{stable.xi.max():.2f} inside the stable band, and the "
          "stability test passes partly because standard errors widen at high thresholds. Figure @F:evt@(c) shows the normal curve "
          "dropping far faster than the observed losses, while the GPD follows them.")
    doc.figure(figs["evt"], "EVT diagnostics for today's target, 2005-2026 daily log losses. (a) Mean excess over each candidate "
               "threshold. (b) ξ with 95% bands across candidate thresholds; filled points are stable. (c) Probability that a day's loss "
               "exceeds x: observed exceedances, the fitted GPD and a normal fit (log scale). Vertical lines: the chosen threshold.",
               label="evt")
    doc.table(["Threshold", "u (daily loss)", "Exceedances", "ξ ± 1.96 s.e.", "VaR 99% (USD)", "ES 99% (USD)"],
              [[r.threshold, pct(r.u, 2), f"{r.k}", f"{r.xi:.3f} ± {1.96*r.xi_se:.3f}", num(r.var99), num(r.es99)] for r in thr.itertuples()],
              [.24, .14, .13, .19, .15, .15], caption="Does the threshold matter? Refits at fixed 90th and 95th percentiles.")
    doc.p(f"Fixed thresholds at the 90th and 95th percentiles give 99% ES of {usd(thr.es99[1])} and {usd(thr.es99[2])} against "
          f"{usd(thr.es99[0])} for the chosen threshold, so the choice moves ES by at most "
          f"{pct((thr.es99.max()-thr.es99.min())/thr.es99[0], 1)}: the 99% figures sit close to the thresholds and barely move, while ξ "
          f"({thr.xi.min():.2f} to {thr.xi.max():.2f} across these three) does, so tail shape far beyond 99% is much less certain.")
    doc.h2("5.6 Backtests of the risk forecasts")
    brows = []
    for m in F.BACKTEST_METHODS:
        for a in (.95, .99):
            v = val[(m, a)]
            at99 = a == .99
            brows.append([LABEL[m], f"{a:.0%}", f"{v['breaches']}", f"{v['expected_breaches']:.1f}", pval(v["kupiec_p"]),
                          pval(v["independence_p"]), pval(v["conditional_coverage_p"]), v["zone"] if at99 else "n/a",
                          pct(v.get("red_window_share"), 0) if at99 else "n/a",
                          ("pass" if F.model_pass(v) else "fail") if at99 else "n/a"])
    doc.table(["Model", "Level", "Breaches", "Expected", "Kupiec p", "Indep. p", "Cond. cov. p", "Last 250 days", "Red windows",
               "Gate"], brows, [.21, .06, .09, .09, .09, .09, .1, .1, .1, .07],
              caption=f"Sequential one-day VaR forecasts on the strategy's own path, {date(ge99_first(D))} to {date(N['end'])}, "
                      f"strategy hash {N['strategy_hash'][:8]}; coverage 100% for every model. Basel zones and the pass gate apply "
                      "to 99% only; red windows: share of all rolling 250-day windows with 10 or more breaches.")
    doc.figure(figs["backtest"], f"GARCH-EVT one-day 99% VaR against realised log loss of the strategy, {date(ge99_first(D))} to "
               f"{date(N['end'])} (a), and breaches by year against the expected 1% (b).")
    hs99, ev99, nm99 = val[("historical", .99)], val[("evt", .99)], val[("normal", .99)]
    if V6:
        doc.p(f"At 99% GARCH-EVT had {ge99['breaches']} breaches in {ge99['days']:,} days against {ge99['expected_breaches']:.1f} expected "
              f"(Kupiec p {pval(ge99['kupiec_p'])}) and FHS {fh99['breaches']} (Kupiec p {pval(fh99['kupiec_p'])}): the number of breaches "
              f"is acceptable for both. The breaches cluster, though (independence p {pval(ge99['independence_p'])} and "
              f"{pval(fh99['independence_p'])}; conditional coverage p {pval(ge99['conditional_coverage_p'])} and "
              f"{pval(fh99['conditional_coverage_p'])}), so neither model passes the pre-registered gate and the formal outcome is "
              f"<b>evaluation incomplete</b>. {ov['breaches_near_switch']} of GARCH-EVT's {ov['breaches']} breaches fell in a month the "
              f"overlay switched or the month after, which make up {pct(ov['days_near_switch_share'], 0)} of the days; "
              f"{ov['breaches_near_switch_2020']} of them are the February-March 2020 crash, when the overlay switched because markets were falling, so "
              "the test cannot separate the overlay's effect from the crash itself. The same rule without the overlay (v5 core) passes with GARCH-EVT "
              f"({ge5['breaches']} breaches, conditional coverage p {pval(ge5['conditional_coverage_p'])}). GARCH-EVT breaches were most "
              "frequent in "+", ".join(f"{y} ({int(n)})" for y, n in D["by_year"]["sum"].sort_values(ascending=False).head(3).items())+". "
              f"Historical simulation and unconditional EVT ({hs99['breaches']} and {ev99['breaches']} breaches) cluster more strongly, and "
              f"the normal model has too many ({nm99['breaches']}). At 95%, GARCH-EVT and FHS had {ge95['breaches']} and "
              f"{fh95['breaches']} breaches against {ge95['expected_breaches']:.1f} expected (independence p {pval(ge95['independence_p'])} "
              f"and {pval(fh95['independence_p'])}).")
        doc.p("The owner adopted v6 despite this result, for its smaller falls; the decision and its reason are logged in PLAN.md 13h. As "
              "a safeguard, daily risk limits use the higher of the GARCH-EVT and FHS forecasts in any month the overlay switches. The "
              f"validated specification is the rolling one in this table (750-day window, refit every 21 days, on the strategy's own "
              f"returns); its latest forecasts, for {date(lf['date'])} with data to {date(lf['data_through'])}, are VaR "
              f"{usd(lf['var_usd'])} (GARCH-EVT) and {usd(lf_fhs['var_usd'])} (FHS). Table @T:models@'s GARCH-EVT figure "
              f"({usd(t99.var_usd['garch_evt'])}) comes from one fit on 2005-2026 with today's weights and is shown for comparison.")
    else:
      doc.p(f"At 99% GARCH-EVT had {ge99['breaches']} breaches in {ge99['days']:,} days against {ge99['expected_breaches']:.1f} expected "
          f"(Kupiec p {pval(ge99['kupiec_p'])}) and passes conditional coverage (p {pval(ge99['conditional_coverage_p'])}); its last 250 "
          f"days are {ge99['zone']}. Its independence test on its own (p {pval(ge99['independence_p'])}) still points to some clustering. "
          f"FHS, the model named first, had {fh99['breaches']} breaches (Kupiec p {pval(fh99['kupiec_p'])}) that cluster (independence "
          f"p {pval(fh99['independence_p'])}, conditional coverage p {pval(fh99['conditional_coverage_p'])}), so it fails: the forecasts are "
          "validated only through the challenger, a weaker result than a primary pass. GARCH-EVT breaches were most frequent in "
          + ", ".join(f"{y} ({int(n)})" for y, n in D["by_year"]["sum"].sort_values(ascending=False).head(3).items())
          + ", years with sudden shocks that arrived before the volatility filter caught up. "
          f"Historical simulation and unconditional EVT have about the right number of breaches "
          f"({hs99['breaches']} and {ev99['breaches']}) but strongly clustered ones, because they ignore changing volatility; the normal "
          f"model has far too many ({nm99['breaches']}). The last-250-day zone is green for every model, which hides this: across all "
          f"rolling 250-day windows the normal model was red {pct(nm99.get('red_window_share'), 0)} of the time and historical simulation "
          f"{pct(hs99.get('red_window_share'), 0)}, while GARCH-EVT and FHS never were. At 95%, FHS and GARCH-EVT both had "
          f"{ge95['breaches']} breaches against {ge95['expected_breaches']:.1f} expected with no sign of clustering (independence p "
          f"{pval(ge95['independence_p'])}).")
      doc.p(f"Using GARCH-EVT for daily monitoring is a choice made after this backtest, because the model named first (FHS) failed; FHS "
          "had also failed on clustering for the static risk-parity and overlay candidates studied before this strategy's "
          "settings were registered. The validated specification is the rolling one in this table (750-day window, refit every 21 days, "
          f"on the strategy's own returns); its latest forecast, for {date(lf['date'])} with data to {date(lf['data_through'])}, is VaR "
          f"{usd(lf['var_usd'])} (FHS {usd(lf_fhs['var_usd'])}). Table @T:models@'s GARCH-EVT figure ({usd(t99.var_usd['garch_evt'])}) "
          "comes from one fit on 2005-2026 with today's weights and is shown for comparison with the other models.")
    doc.h2("5.7 Stress tests")
    srows = []
    for name, r in stress.items():
        p, kept = r["path"], r["today_buy_hold"]
        srows.append([name, f"{date(r['start'])} to {date(r['end'])}", pct(p["return"]), num(-p["loss_usd"]), pct(p["max_fall"]),
                      f"{date(p['worst_day'])} ({pct(p['worst_day_return'])})", pct(kept["return"]), pct(-kept["drawdown"])])
    doc.table(["Scenario", "Dates", "As run", "As run, P&amp;L USD", "Max fall, as run", "Worst day, as run", "Target held", "Max fall, held"],
              # v6: 'as run' includes the overlay state
              srows, [.1, .215, .075, .12, .1, .17, .1, .1], align=["l", "l", "r", "r", "r", "l", "r", "r"],
              caption="Historical crisis paths on NAV USD 9.6 million. 'As run' is the strategy path, month-end resets"
                      +(" and overlay" if V6 else "")+" included, from "
                      "the start close; 'target held' buys the 1 October 2026 weights at the start close and lets them drift.")
    doc.figure(figs["stress"], "Dollar profit or loss by ETF in each crisis, strategy as run (holdings at each prior close × that day's "
               "return); the parts add up to the portfolio result.")
    doc.p(f"As run, the worst scenario was {worst_name} ({pct(worst['return'])}, a loss of {usd(worst['loss_usd'])}) and the largest fall inside "
          f"any scenario was {pct(stress[worst_fall]['path']['max_fall'])} in {'the GFC' if worst_fall == 'GFC' else worst_fall}, "
          f"{'within' if stress[worst_fall]['path']['max_fall'] <= limit else 'beyond'} the 20% limit. "
          +(f"With the overlay holding cash, the strategy gained {pct(gfc['path']['return'])} over the GFC scenario (v5 core "
            f"{pct(v5s['GFC']['return'])}). " if V6 else "")+
          f"Bonds and gold {'more than offset' if gfc['path']['return'] > 0 else 'offset most of'} the GFC equity loss (AGG {usd(gfc['path']['pnl_usd']['AGG'])}, GLD {usd(gfc['path']['pnl_usd']['GLD'])}); in COVID every ETF lost "
          f"money; in 2022 AGG lost most ({usd(-rates['path']['pnl_usd']['AGG'])}) and only XLE gained "
          f"({usd(rates['path']['pnl_usd']['XLE'])}). Bonds and gold diversify some crises, not all. Bought at the start close and left "
          f"to drift, today's target would have fallen {pct(-held['GFC']['drawdown'])} in the GFC and {pct(-held['COVID']['drawdown'])} in COVID"
          +(f" ({' and '.join(breaching)} beyond the limit)" if breaching else "")+
          ": the monthly rule did better by cutting equity and energy as their volatility rose"
          +(", and the overlay by moving half of them to cash" if V6 else "")+", so a crash that arrives before the next "
          "month-end meets today's weights"+(", which hold more energy than at any earlier month-end." if N["xle_at_maximum"] else "."))
    doc.table(["", *U, "Portfolio"],
              [["Shock", *(pct(hyp["shocks"][t]) for t in U), pct(hyp["return"])],
               ["Loss, USD", *(num(hyp["contributions_usd"][t]) for t in U), num(hyp["loss_usd"])],
               ["Reverse-stress shock (20% loss)", *(pct(rev["shocks"][t]) for t in U), pct(-rev["loss_fraction"])]],
              [.28, .13, .13, .13, .13, .2],
              caption="Hypothetical joint equity-bond shock and reverse stress test, today's target. Deterministic; no probability is "
                      "attached. The reverse-stress shock is the smallest one-step move that costs 20%; under the 2005-2016 daily "
                      f"covariance it lies {np.sqrt(rev['distance_squared']):.0f} standard deviations out (squared Mahalanobis distance "
                      f"{rev['distance_squared']:,.0f}), so a 20% loss needs a multi-day crisis, not one bad day.")
    doc.h2("5.8 Risk contributions")
    doc.table(["ETF", "Weight", "Share of volatility", "ES contribution (USD)", "Share of ES", "Marginal ES per USD 1m more"],
              [[t, pct(c.weight[t]), pct(c.vol_contribution[t]), num(c.es_usd[t]), pct(c.es_share[t]),
                num(1e6*c.marginal_es_per_usd[t])] for t in U]+[["Total", "100.0%", "100.0%", num(tot["es_usd"]), "100.0%", ""]],
              [.1, .12, .17, .21, .14, .26],
              caption="Historical attribution: joint daily rows 2005-2026, today's target, one-day 99% ES on NAV USD 9.6 million. "
                      "Portfolio-only models (FHS, GARCH-EVT) cannot split risk by ETF.")
    doc.figure(figs["contrib"], "Shares of money, of volatility (rule's EWMA covariance) and of 99% ES (2005-2026 history) by ETF.")
    m = c.marginal_es_per_usd
    doc.p(f"The rule equalises volatility contributions ({pct(c.vol_contribution.min())} to {pct(c.vol_contribution.max())}) but not tail "
          f"losses: on the worst 1% of days XLE carries {pct(c.es_share['XLE'])} of the ES with {pct(w['XLE'])} of the money, and SPY "
          f"{pct(c.es_share['SPY'])} with {pct(w['SPY'])}, because equities and energy crash together while AGG and gold usually do not. "
          f"The contributions add up to the portfolio ES (residual {usd(abs(tot['residual_usd']), 2)}); holding the four ETFs as separate "
          f"portfolios would give {usd(tot['es_usd']+tot['diversification_benefit_usd'])}, so diversification removes "
          f"{usd(tot['diversification_benefit_usd'])}. Moving USD 1 million from {m.idxmax()} to {m.idxmin()} would lower 99% ES by about "
          f"{usd(1e6*(m.max()-m.min()))} (first-order estimate); the monthly reset would undo a manual change unless the rule changed.")
    doc.h2("5.9 Spending sustainability: the 25-year test")
    doc.p(f"USD 10 million divided by USD 400,000 is 25 payments. If the fund earned exactly the reserve's growth rate "
          f"({pct(cfg['reserve_growth'], 2)} a year), its value deflated at that same rate would fall by USD 400,000 a year and the 25th "
          "payment would exhaust it. To leave capital the strategy must beat that. Three outcomes are kept apart: every payment made, "
          "capital left afterwards, and the USD 10 million kept in real terms (deflated by US CPI).")
    doc.p(f"<b>Actual history.</b> From {date(rh['start'])} the strategy paid {rh['payments']} reserves totalling {usdm(rh['paid_usd'])} "
          f"({usd(rh['first_payment_usd'])} rising to {usd(rh['last_payment_usd'])}) and was still worth {usdm(rh['end_usd'])} on "
          f"{date(rh['end'])}, or {usdm(rh['end_real_usd'])} in 2007 dollars after US CPI rose {pct(rh['cpi_ratio']-1, 0)}.")
    doc.table(["Horizon", "All reserves paid", "USD 10m kept in real terms", "Median real balance", "10th percentile",
               "Median depletion year, failing paths"],
              [[f"{r['year']} years", pct(r["all_payments_funded"]), pct(r["real_capital_preserved"]), usdm(r["median_real_balance_usd"]),
                usdm(r["p10_real_balance_usd"]), "none" if r["median_depletion_year"] is None else f"{r['median_depletion_year']:.0f}"]
               for r in (r10, r25)], [.12, .16, .22, .18, .16, .16],
              caption=f"Resampled history: {N['reserve_test']['paths']:,} paths built from random 12-month blocks of the strategy's own "
                      f"monthly returns ({N['reserve_test']['sample']}); reserve paid each 1 January; real values at "
                      f"{pct(cfg['inflation'], 2)} a year. Illustrations, not forecasts.")
    doc.p(f"The strategy paid every reserve for {cfg['survival_years']} years in {pct(r25['all_payments_funded'])} of resampled paths, so "
          f"on this evidence the spending schedule looks affordable. Real capital is a different matter: it was kept in only "
          f"{pct(r25['real_capital_preserved'])} of "
          f"paths, because the reserve grows {pct(cfg['reserve_growth'], 2)} a year against US CPI of {pct(cfg['inflation'], 2)}: keeping "
          f"real capital would need {pct(need1)} real in the first year rising to {pct(need25)} by year {cfg['survival_years']}, more than "
          f"the strategy's historical {pct(perf['real_cagr'])}. The committee should treat the schedule as drawing down real capital slowly.")

    # ---------------------------------------------------------------- 6 assumptions and limitations
    doc.h1("6. Assumptions and limitations")
    doc.h2("6.1 Assumptions")
    doc.table(["Assumption", "Where it matters", "If it is wrong"], [
        ["2005-2026 contains the kind of risks the next years will bring", "All risk models, stress tests, comparisons",
         "A crisis unlike any since 2005 (for example a long inflation decade) is understated"],
        ["A 750-day EWMA covariance (λ 0.97) is a good guide to the coming month", "Monthly target weights",
         "Sudden correlation changes, as stocks and bonds in 2022, mis-size the risk until the next reset"],
        ["Trades at the month-end close at observed prices, zero cost", "Performance, turnover",
         f"Turnover is {perf['turnover_per_year']:.2f}× NAV a year: at 5-10 bp one-way, return falls about "
         f"{perf['turnover_per_year']*.0005*100:.2f}-{perf['turnover_per_year']*.001*100:.2f} points a year"],
        ["Adjusted closes are total returns with dividends reinvested; fund fees are already in prices", "All returns",
         "No fee is deducted twice; taxes and withholding are ignored"],
        [f"US CPI ({pct(cfg['inflation'], 2)} a year) measures the fund's inflation", "Real returns, return objective, reserve test",
         "University costs (salaries, research, construction) can rise faster"],
        ["The reserve is a fixed schedule, +3.64% a year, paid out, earning nothing", "Spending test",
         "A different spending rule changes the survival results"],
        ["Risk is measured over one day with weights held for the day", "VaR, ES, backtests", "Multi-day losses compound and weights drift"],
        ["Each model's distribution: normal and t symmetric; GPD above u; GARCH residuals independent", "VaR, ES",
         "Section 5.4 shows how far the models disagree"],
        ["The EVT threshold rule is a reasonable heuristic", "EVT estimates", f"ES moves by about {pct((thr.es99.max()-thr.es99.min())/thr.es99[0], 0)} across thresholds"],
        ["The hypothetical shock and reverse stress are deterministic", "Stress tests", "They carry no probability"]],
        [.38, .24, .38], align=["l", "l", "l"], caption="Main assumptions and what changes if they fail.")
    doc.h2("6.2 Limitations")
    doc.bullets([
        "<b>Hindsight and multiple testing.</b> The strategy was chosen in October 2026 after about twenty allocation rules had been "
        "compared on the same 2005-2026 data, and the policy limits were set with that history in view. Every number is history the "
        "choice has seen; there is no untouched test period, and good past results partly reflect the search.",
        f"<b>Policy limits were adjusted after the results were seen.</b> The ES budget was raised from 2.5% to 3% of NAV after the current "
        f"target's ES ({pct(t99.es_pct['historical']/100, 2)} of NAV) exceeded 2.5%, and the inflation basis was moved from an unverified "
        "3.64% to US CPI. The budget is met by the point estimate only (bootstrap upper bound "
        f"{usd(bh.es_usd_hi)}).",
        (f"<b>Risk-model validation is incomplete.</b> On the v6 path both named models' breaches cluster (conditional coverage p "
         f"{pval(ge99['conditional_coverage_p'])} and {pval(fh99['conditional_coverage_p'])}), so the pre-registered rule records "
         "evaluation incomplete; v6 was adopted by the owner's decision, with the higher-of-two forecast safeguard in switch months. "
         f"The v5 core passes with GARCH-EVT (p {pval(ge5['conditional_coverage_p'])})." if V6 else
         f"<b>Risk-model validation is partial.</b> The backtest passes only with the second-named model (GARCH-EVT); FHS fails on "
         f"clustering, as it had for earlier candidates, and GARCH-EVT's own independence p-value ({pval(ge99['independence_p'])}) also "
         "shows some clustering at the onset of shocks. Making GARCH-EVT the monitoring model was decided after the backtest."),
        *(["<b>The overlay rests on little evidence.</b> Its benefit comes mainly from one deep recession (2008); it can switch on for "
           "short spells that cost return if markets recover, react a month late, or miss a crash with no curve inversion. It was designed "
           "after the 2005-2026 data had been seen. Cash is outside the brief's seven-ETF list: a disclosed policy choice."] if V6 else []),
        "<b>Today's weights carry more crash risk than the strategy's history suggests.</b> "
        +(f"XLE is at its highest weight since 2006 ({pct(w['XLE'])}). " if N["xle_at_maximum"] else "")+
        f"Bought at the start of the GFC or COVID and left to drift without the monthly resets, today's target would have fallen "
        f"{pct(-held['GFC']['drawdown'])} and {pct(-held['COVID']['drawdown'])}"
        +(f", {' and '.join(breaching)} beyond the 20% limit." if breaching else "."),
        "<b>VaR and ES are not caps.</b> VaR is exceeded on about 1 day in 100 at 99%; ES is the average of bad days, and a worse day than "
        f"any since 2005 is possible. The EVT tail rests on {evt['n_exceed']} exceedances and only a handful of true crashes.",
        "<b>Uncertainty is only partly measured.</b> Bootstrap intervals cover estimation noise for three models with the threshold held "
        "fixed; they do not cover the choice of model, the choice of window or future regime change.",
        "<b>Diversification is unreliable.</b> Risk parity equalises everyday volatility, not crash losses. Bonds did not protect in "
        "2022, gold did not in March 2020, and the weights change only monthly (COVID took five weeks).",
        "<b>Data.</b> The frozen snapshot starts in 2005, so earlier crises (2000-2002) cannot be replayed with AGG and gold. CPI and other "
        "FRED macro series are revised data with approximate publication lags, not the figures known at the time, and no macroeconomic "
        "conditioning (interest-rate or inflation regimes) enters the model. Flagged price anomalies were kept, not deleted; the "
        f"{N['data']['flags_review']} asset-specific flags still await manual review, and event labels are analyst-compiled.",
        "<b>Implementation.</b> No trading costs, bid-ask spreads, market impact in stressed months, taxes, currency effects (the "
        "university's own currency) or interest on the cash reserve are modelled.",
        "<b>Attribution.</b> Conditional models fitted to portfolio returns cannot split risk by ETF; the contributions are historical.",
        "<b>Human review.</b> AI tools helped write the code and this document (section 8). Independent human review of the "
        "calculations and the investment judgement is pending, and the organisers have not yet confirmed that a solo entry is eligible."])

    # ---------------------------------------------------------------- 7 recommendation
    doc.h1("7. Recommendation and monitoring")
    doc.p(("<b>Hold this portfolio (mandate v6, the owner's final model)</b>, subject to the committee's review. Under the "
           "pre-registered rule the outcome is evaluation incomplete, because the risk-forecast backtest does not pass; the owner "
           "adopted v6 for its smaller falls. " if V6 else
           "<b>Accept the mandate with this portfolio</b>, subject to the owner's and the committee's review. ")
          +"Table @T:limits@ sets the evidence against each policy limit.")
    shrunk = exp[exp.estimator != "Raw historical means"].set_index("window").loc["Full sample"]
    doc.table(["Policy limit", "Requirement", "Evidence", "Met?"], [
        ["Daily risk budget", f"Historical one-day 99% ES at most {usd(budget)} ({pct(cfg['es_budget'], 0)} of NAV)",
         f"Today's target {usd(t99.es_usd['historical'])}; strategy path {pct(cmp.es99_daily[0], 2)} of NAV; bootstrap upper bound "
         f"{usd(bh.es_usd_hi)}",
         "Yes, on the point estimate"],
        ["Return objective", f"Expected real return at least {pct(cfg['real_return_floor'], 0)} a year over US CPI",
         f"{pct(shrunk.real, 2)} under the frozen estimator; {pct(exp.real.min(), 2)} to {pct(exp.real.max(), 2)} across six "
         "estimates (Table @T:expected@)", "Yes"],
        ["Acceptable loss", f"Largest fall at most {pct(limit, 0)} in the historical crises",
         f"As run: {pct(gfc['path']['max_fall'])} at worst (GFC). Today's target bought at the start and left to drift: "
         f"{pct(-held['GFC']['drawdown'])} (GFC), {pct(-held['COVID']['drawdown'])} (COVID)",
         "As run yes; today's weights held no" if breaching else "Yes"],
        ["Validated risk model", "The named model, or if it fails the challenger, passes the 99% backtest",
         f"GARCH-EVT {'clusters' if V6 else 'passes'} (Kupiec p {pval(ge99['kupiec_p'])}, conditional coverage p "
         f"{pval(ge99['conditional_coverage_p'])}); FHS fails (p {pval(fh99['conditional_coverage_p'])})",
         "No: evaluation incomplete; owner's decision" if V6 else "Yes, through the challenger"],
        ["Universe and positions", "SPY, AGG, GLD, XLE only; long-only; fully invested"+(", except cash at 0% while the overlay is on" if V6 else ""),
         f"All {N['targets']} month-end targets"+(f"; cash in {ov['months_on']} months" if V6 else ""), "Yes"]],
        [.15, .27, .42, .16], align=["l", "l", "l", "l"], label="limits",
        caption=f"Policy limits (mandate {'v6' if V6 else 'v5'}) against the evidence for the recommended strategy. The fixed mixes' results against the "
                "same limits are summarised in section 5.2.")
    doc.p("Monitoring:")
    doc.numbered([
        f"<b>Hold</b> {alloc} from 1 October 2026 and reset the weights at every month-end close by the rule in section 3.2"
        +(f"; apply the recession overlay (section 3.4) at the same close." if V6 else "."),
        f"<b>Daily limit:</b> measure one-day 99% risk with GARCH-EVT refitted as in its backtest (latest forecast, for "
        f"{date(lf['date'])}: VaR {usd(lf['var_usd'])}); "
        +("as a precaution, use the higher of GARCH-EVT and FHS in any month the overlay switches, because v6's breaches cluster." if V6 else
          "FHS stays as a second view because its breaches cluster."),
        f"<b>Review triggers:</b> an extra committee review if the fall from the previous high passes 15% (the largest so far was "
        f"{pct(-perf['maximum_drawdown'])})"+(" or" if V6 else ",")+" if 99% VaR breaches exceed 9 in any 250 days (Basel red zone)"
        +("." if V6 else f", or if a month-end target's historical ES exceeds the {usd(budget)} budget."),
        f"<b>Expectation setting:</b> plan spending on a real return below the {pct(perf['real_cagr'])} earned historically, and treat "
        "the reserve schedule as a slow draw on real capital (section 5.9)."])
    if breaching:
        doc.p(f"<b>The risk this recommendation accepts.</b> The {pct(limit, 0)} loss limit held for the strategy as run, but not for "
              f"today's weights held through {' or '.join(breaching)} ({' and '.join(pct(-held[k]['drawdown']) for k in breaching)}) "
              "if such a crash came before the rule reacted. We accept that risk because the rule cut equity and energy within weeks in "
              "every past crisis, the 15% review trigger gives the committee a decision point before 20%, and the weights are reset again "
              "at the end of October. "
              +("The overlay reacts monthly, so it does not remove this risk. " if V6 else "")+
              "If the committee wants the limit protected mechanically, two options exist, neither backtested here: "
              "re-estimate the target mid-month when the daily GARCH-EVT VaR or the fall from the high crosses a preset level, or cap any "
              f"one ETF's share of 99% ES (XLE now carries {pct(c.es_share['XLE'])}). Either would be a logged change to the strategy "
              "and would need its own backtest before use.")
    doc.p("<b>What would change this recommendation:</b> "
          +("breaches continuing to cluster on new data after the safeguard, the overlay failing to act in a recession or acting "
            "repeatedly without one, " if V6 else "GARCH-EVT failing its own coverage tests on new data, ")+
          "a month-end target whose ES persistently exceeds the budget, or a sustained rise in the joint fall of stocks and bonds, the "
          "2022 pattern that neither AGG nor gold offset.")

    # ---------------------------------------------------------------- 8 reproducibility and AI
    doc.h1("8. Reproducibility, provenance and AI use")
    doc.p("Every figure in this report is produced by <font face='DV-I'>python -m quanedge.final_report</font> from the repository, "
          "using the same evidence and functions as the committee dashboard (<font face='DV-I'>quanedge/final_portfolio.py</font>). "
          "Setup: <font face='DV-I'>python -m pip install -r requirements.lock.txt</font>; "
          "<font face='DV-I'>python -m quanedge.data.run --check-only</font> verifies the frozen data; "
          +("<font face='DV-I'>python -m quanedge.recession_overlay</font> rebuilds the v6 evidence and "
            "<font face='DV-I'>python -m quanedge.dynamic_parity_eval</font> the v5 core. " if V6 else
            "<font face='DV-I'>python -m quanedge.dynamic_parity_eval</font> rebuilds the strategy evidence. ")+
          f"Identities: price file SHA-256 {N['data_hash'][:16]}…; strategy hash {N['strategy_hash'][:16]}… on every forecast row; "
          f"evidence run results/{N['evidence_run']} (settings registered at tag {N['prereg_tag']}); policy config at tag "
          f"{cfg['prereg_tag']}; report code revision {N.get('code_rev', 'recorded in manifest.json')}. numbers.json and the CSV files in "
          "tables/ beside this PDF hold the figures quoted; manifest.json hashes the inputs and outputs."
          +(f" The same strategy was also evaluated in the mandate v5 run (results/{V5_RUN}, strategy hash "
            f"{same['strategy_hash'][:8]}…): its daily returns agree with this evidence to {same['path_max_diff']:.0e} and its risk "
            f"forecasts to {same['forecast_max_diff']:.0e}, with the same breach counts. The hashes differ because the two runs describe "
            f"the same settings differently, and its real CAGR ({pct(same['real_cagr'], 2)}) deflates by the flat {pct(cfg['inflation'], 2)} "
            f"policy rate, where this report uses CPI over the strategy's own dates ({pct(perf['real_cagr'], 2)})." if same else ""))
    doc.p("<b>AI use.</b> Codex (OpenAI) restored and extended the data and risk modules and wrote the first portfolio, validation, "
          "stress, pipeline, application and document code (26-29 October 2026). Claude Code (Anthropic) implemented mandates v2-v5 and "
          "their runs, the exploratory studies, the dynamic risk-parity evaluation, "+("the recession overlay (v6), the tear sheet, " if V6 else "")
          +"the committee dashboard and this report and its generator (29-31 October 2026); earlier risk-engine work also used Claude Code, and earlier data work Antigravity and Claude "
          "Code. AI output was checked by automated tests and reconciliations (dollar ES contributions add up to portfolio ES; crisis "
          "P&amp;L by ETF adds up to the path loss; the bootstrap reproduces an independent run exactly; forecast files are refused for "
          "other weights). These are software checks, not human validation. Human reviewer and date: pending. The owner must be able "
          "to explain and defend every result.")
    doc.h2("References")
    doc.add("refs", sorted(REFERENCES+V6_REFERENCES) if V6 else REFERENCES)
    return doc


def upper_first(s):
    return s[:1].upper()+s[1:]


def ge99_first(D):
    return D["frame"].index[0]


REFERENCES = [
    "Acerbi, C. and Tasche, D. (2002). On the coherence of expected shortfall. Journal of Banking and Finance 26(7), 1487-1503.",
    "Artzner, P., Delbaen, F., Eber, J.-M. and Heath, D. (1999). Coherent measures of risk. Mathematical Finance 9(3), 203-228.",
    "Balkema, A. and de Haan, L. (1974). Residual life time at great age. Annals of Probability 2(5), 792-804.",
    "Barone-Adesi, G., Giannopoulos, K. and Vosper, L. (1999). VaR without correlations for portfolios of derivative securities. "
    "Journal of Futures Markets 19(5), 583-602.",
    "Basel Committee on Banking Supervision (1996). Supervisory framework for the use of backtesting in conjunction with the "
    "internal models approach to market risk capital requirements.",
    "Christoffersen, P. (1998). Evaluating interval forecasts. International Economic Review 39(4), 841-862.",
    "Glosten, L., Jagannathan, R. and Runkle, D. (1993). On the relation between the expected value and the volatility of the "
    "nominal excess return on stocks. Journal of Finance 48(5), 1779-1801.",
    "Inclán, C. and Tiao, G. (1994). Use of cumulative sums of squares for retrospective detection of changes of variance. "
    "Journal of the American Statistical Association 89(427), 913-923.",
    "J.P. Morgan/Reuters (1996). RiskMetrics: Technical Document, 4th edition.",
    "Kupiec, P. (1995). Techniques for verifying the accuracy of risk measurement models. Journal of Derivatives 3(2), 73-84.",
    "Ledoit, O. and Wolf, M. (2004). A well-conditioned estimator for large-dimensional covariance matrices. Journal of "
    "Multivariate Analysis 88(2), 365-411.",
    "Maillard, S., Roncalli, T. and Teïletche, J. (2010). The properties of equally weighted risk contribution portfolios. "
    "Journal of Portfolio Management 36(4), 60-70.",
    "Markowitz, H. (1952). Portfolio selection. Journal of Finance 7(1), 77-91.",
    "McNeil, A. and Frey, R. (2000). Estimation of tail-related risk measures for heteroscedastic financial time series: an "
    "extreme value approach. Journal of Empirical Finance 7(3-4), 271-300.",
    "Pickands, J. (1975). Statistical inference using extreme order statistics. Annals of Statistics 3(1), 119-131.",
    "Sharpe, W. (1964). Capital asset prices: a theory of market equilibrium under conditions of risk. Journal of Finance 19(3), 425-442.",
    "Spinu, F. (2013). An algorithm for computing risk parity weights. SSRN working paper 2297383.",
]


def data_section(doc, N, D):
    """Section 2, every count read from the data pipeline's logs (data_facts)."""
    d = N["data"]; cfg = N["policy"]; corr = D["corr"]
    doc.p("Only approved open sources are used: Yahoo Finance for ETF prices and FRED for interest rates and inflation. The raw "
          "downloads are frozen in the repository with their hashes, and the clean files are rebuilt from them offline, so every "
          "result can be reproduced without new downloads.")
    retrieved = pd.Timestamp(d["retrieved"])
    doc.table(["Data", "Source", "Coverage", "Used for"], [
        ["ETF prices", f"Yahoo Finance via yfinance {d['yfinance']}, auto-adjusted close (dividends reinvested, splits adjusted, fund "
         f"expenses already deducted by the provider); retrieved {date(retrieved)} {retrieved:%H:%M} UTC",
         f"7 eligible ETFs; {date(d['start'])} to {date(d['end'])}; {d['dates']:,} trading days", "All returns, risk models, stress tests"],
        ["Risk-free rate", "FRED DTB3: 3-month Treasury bill, discount basis", "Daily", "Sharpe, Treynor, Jensen's alpha"],
        ["Inflation", "FRED CPIAUCSL: US CPI, all urban consumers (index)", "Monthly, lagged to release", "Real returns, return objective"],
        ["Other macro", "FRED DGS10, FEDFUNDS, VIXCLS; World Bank US GDP growth and CPI inflation", "Daily, monthly, annual",
         "Collected for context; not used in this report"]],
        [.13, .45, .23, .19], align=["l", "l", "l", "l"], caption="Data sources.")
    doc.h2("2.1 Cleaning steps")
    named = {}
    for x, r in d["closures"]:                        # group consecutive closures with the same cause
        cause = re.sub(r"^National Day of Mourning for President (.*)$", r"mourning for President \1", r.split(":")[0])
        named.setdefault(cause, []).append(pd.Timestamp(x))
    closures = "; ".join(f"{cause} ({date(ds[0]) if len(ds) == 1 else f'{ds[0].day}-{date(ds[-1])}'})" for cause, ds in named.items())
    flags4 = sum(d["flags_by_ticker"].values()); review = d["flags_review_by_ticker"]
    breaks = d["variance_breaks"]
    gap_text = " ".join(f"FRED has no CPI for {g['month']}, so the {g['carried']} value is used for {g['sessions']} sessions "
                        f"({date(g['first'])} to {date(g['last'])}) instead of the usual {g['typical']:.0f}; that longer carry is not "
                        "in the log." for g in d["cpi_gaps"])
    doc.numbered([
        f"<b>Freeze the snapshot.</b> One download covers the whole period; its SHA-256 ({N['data_hash'][:12]}…), size, rows and "
        f"dates are recorded with those of the other {d['manifest_files']-1} data files and the software versions, and "
        "<font face='DV-I'>python -m quanedge.data.run --check-only</font> re-verifies them. A later download would not match, "
        "because the provider rescales adjusted prices after each dividend, so the committed snapshot is the reference.",
        f"<b>Align the calendar.</b> A date is kept only if all seven ETFs traded: {d['missing_price_rows']} incomplete rows were found and "
        f"{d['dropped_rows']} dropped, and no price is forward-filled or interpolated. The period has {d['weekdays']:,} weekdays and "
        f"{d['dates']:,} trading days; all {d['weekdays']-d['dates']} missing weekdays are explained: "
        f"{d['calendar'].get('STANDARD_HOLIDAY', 0)} standard NYSE holidays and {d['calendar'].get('NON_STANDARD_CLOSURE', 0)} special "
        f"closure days: {closures}.",
        "<b>Validate.</b> Prices must be positive and finite, dates unique and increasing, tickers limited to the seven eligible ETFs "
        "in a fixed order, and log returns must equal ln(1 + simple return) to within 10<super>−12</super>. Data dated after "
        f"{date(cfg['snapshot_end'])} are refused.",
        f"<b>Flag anomalies, do not delete them.</b> Return outliers (|z| ≥ 4 on full-sample moments, or |log return| ≥ 8%): "
        f"{d['flags']} flags, {flags4} of them in SPY, AGG, GLD and XLE, with {d['flags_2008']} in 2008 and {d['flags_2020']} in 2020. "
        f"{d['flags_corroborated']} were confirmed by another ETF moving the same way that day; the other "
        f"{d['flags_review']} are asset-specific moves ({', '.join(f'{t} {n}' for t, n in review.items())}) left for manual review. "
        f"Stale prices (three or more unchanged days): {d['stale']}. Sharp two-day reversals (|return| ≥ 6% on consecutive days with "
        f"opposite signs): {d['reversals']}, of which SPY {d['reversals_by_ticker']['SPY']} and XLE {d['reversals_by_ticker']['XLE']}. "
        "Variance-break tests (ICSS; Inclán and Tiao 1994) find a volatility shift in every ETF, for example XLE from "
        f"{pct(breaks['XLE']['before'])} to {pct(breaks['XLE']['after'])} a year after {date(breaks['XLE']['date'])}; they are "
        "informational, which is why conditional models are used.",
        "<b>Keep genuine extremes.</b> Every flagged observation was kept: none was corrected or deleted, and the clean price file is "
        "byte-identical to the snapshot. Crash days are real data that VaR, ES and EVT need.",
        f"<b>Align macro data without look-ahead.</b> Each FRED series is carried forward onto trading days from its last published "
        "value and never back-filled; a month's CPI is treated as available on the 21st of the following month (one month and "
        f"20 days after its reference date). The {d['ffill_rows']} daily carries are logged "
        f"({', '.join(f'{k} {v}' for k, v in d['ffill_by_series'].items())}, on Columbus and Veterans Days, when the bond market is "
        f"shut). {gap_text}",
        "<b>Compute returns.</b> Simple returns R<sub>t</sub> = P<sub>t</sub>/P<sub>t−1</sub> − 1 are added across ETFs and compound "
        "wealth; log returns r<sub>t</sub> = ln(P<sub>t</sub>/P<sub>t−1</sub>) are used for statistics and risk models.",
        "<b>Convert the risk-free rate.</b> The DTB3 discount yield d (360-day basis) becomes a bond-equivalent yield "
        "y = 365d/(360 − 91d) and a daily rate (1 + y)<super>1/252</super> − 1. It averaged "
        f"{pct(d['rf_annual'], 2)} a year; {d['dtb3_negative_days']} days were slightly negative (lowest {pct(d['dtb3_min'], 2)}) and kept."])
    doc.h2("2.2 Statistical properties")
    stn = d["stationarity"]; strat = D["stationarity"]
    def tiny(p, floor):
        return f"&lt;10<super>−{floor}</super>" if p < 10.**-floor else minus(f"{p:.1e}")
    def row(name, r, price):
        return [name, minus(f"{r['adf_stat']:.2f}")+f" ({int(r['adf_lags'])})", tiny(r["adf_p_value"], 20),
                minus(f"{r['adf_stat_lag5']:.2f}"), f"{r['kpss_stat']:.3f}" + (" (p ≥ 0.10)" if r["kpss_p_capped"] else f" (p {r['kpss_p_value']:.2f})"),
                tiny(r["arch_lm_p_value"], 20), "n/a" if price is None else f"{price['adf_p_value']:.2f}"]
    rows = [row(t, stn[f"{t}|Daily Log Returns r_t"], stn.get(f"{t}|Log Price Levels ln(P_t)")) for t in U]
    rows.append(row("Strategy path", strat, None))
    doc.table(["Daily log returns", "ADF statistic (lags)", "ADF p", "ADF, 5 lags", "KPSS (p)", "ARCH-LM p", "ADF p, log price"], rows,
              [.16, .16, .12, .11, .17, .13, .15],
              caption="Stationarity tests, 2005-2026 (strategy from 28 Dec 2006): ADF with a constant and AIC lag choice (5% critical "
                      "value −2.86), KPSS for level stationarity, ARCH-LM with 10 lags.")
    doc.p("ADF rejects a unit root in every return series, including the strategy's own path, while the price levels themselves are "
          "non-stationary; KPSS does not reject level stationarity. ARCH-LM finds strong volatility clustering in every series, which "
          "is why the conditional models (FHS, GARCH-EVT) are used. Stationary in mean is not the same as a constant distribution: the "
          "variance breaks above show volatility changing over time. Daily correlations over 2005-2026 support the four-ETF universe: "
          f"SPY with AGG {corr.loc['SPY', 'AGG']:.2f}, with GLD {corr.loc['SPY', 'GLD']:.2f} and with XLE {corr.loc['SPY', 'XLE']:.2f}; "
          f"AGG with GLD {corr.loc['AGG', 'GLD']:.2f}. XLE is the only one of the three that moves closely with SPY, which matters for "
          "tail risk (section 5.8).")


# ---------------------------------------------------------------- build
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_rev():
    try:
        rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=config.ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--", "quanedge", "config", "dashboard.py"],
                                        cwd=config.ROOT, text=True).strip()
        return rev[:12]+("+uncommitted changes" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return float(x) if np.isfinite(x) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp,)):
        return str(x)
    return x


def export_tables(D, folder):
    """Every table the report quotes, as CSV (scalars are in numbers.json)."""
    folder.mkdir(parents=True, exist_ok=True)
    stress = []
    for r in D["stress"]:
        p, h = r.get("path") or {}, r.get("today_buy_hold") or {}
        stress.append({"scenario": r["scenario"], "start": r["start"], "end": r["end"], "as_run_return": p.get("return"),
                       "as_run_loss_usd": p.get("loss_usd"), "as_run_max_fall": p.get("max_fall"), "worst_day": p.get("worst_day"),
                       "worst_day_return": p.get("worst_day_return"), **{f"pnl_usd_{t}": p.get("pnl_usd", {}).get(t) for t in U},
                       "held_return": h.get("return"), "held_max_fall": -h["drawdown"] if "drawdown" in h else None})
    frames = {"risk_models": D["table"], "evt_scan": D["scan"], "evt_thresholds": D["thresholds"],
              "window_sensitivity": pd.concat(D["sens"], names=["window"]).reset_index(level=0),
              "backtests": pd.DataFrame(D["validation"].values()), "breaches_by_year": D["by_year"].reset_index(),
              "stress": pd.DataFrame(stress), "risk_contributions": D["contrib"].reset_index(names="etf"),
              "comparison": D["comparison"].assign(weights=D["comparison"].weights.map(json.dumps)),
              "rebalancing_frequency": D["frequency"], "expected_returns": D["expected"], "bootstrap": D["bootstrap"],
              "mc_error": D["mc_error"], "frontier": D["frontier"], "target_history": D["hist"].reset_index(names="date"),
              "correlations": D["corr"].reset_index(names="etf")}
    for name, frame in frames.items():
        frame.to_csv(folder/f"{name}.csv", index=False)


def build(out=None, root=None, model="v6"):
    out = Path(out or (OUT_V6 if model == "v6" else OUT)); out.mkdir(parents=True, exist_ok=True)
    N, D = gather(root, model)
    N["code_rev"] = git_rev()
    figs = figures(N, D, out/"figures")
    doc = compose(N, D, figs)
    footer = (f"Technical report v6 r1 · Serendib University Endowment Fund · risk parity with recession overlay · data to {N['end']}"
              if model == "v6" else
              f"Serendib University Endowment Fund · monthly dynamic risk parity · technical report r1 · data to {N['end']}")
    to_pdf(doc, out/"technical_report.pdf", footer)
    to_markdown(doc, out/"technical_report.md", "figures")
    export_tables(D, out/"tables")
    from pypdf import PdfReader
    pages = len(PdfReader(out/"technical_report.pdf").pages)
    N["pages"] = pages
    (out/"numbers.json").write_text(json.dumps(jsonable(N), indent=2), encoding="utf-8")
    ev = config.ROOT/"results"/F.RUN
    inputs = {p: sha(config.ROOT/p) for p in ["data/clean/prices_clean.csv", "data/clean/macro_clean.csv", "config/final.yaml",
                                              *(f"results/{F.RUN}/{f.name}" for f in sorted(ev.glob("v4d_monthly_*.csv"))),
                                              f"results/{F.RUN}/summary.json", f"results/{F.RUN}/metadata.json",
                                              *((f"results/{F.RUN_V6}/{f}" for f in ("path.csv", "forecasts.csv", "summary.json",
                                                                                      "metadata.json")) if model == "v6" else ())]}
    norm = lambda p: hashlib.sha256((config.ROOT/p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    sources = {p: norm(p) for p in ["quanedge/final_portfolio.py", "quanedge/final_report.py", "dashboard.py",
                                    *(["quanedge/recession_overlay.py"] if model == "v6" else [])]}
    outputs = {p.relative_to(out).as_posix(): sha(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "code_rev": N["code_rev"], "pages": pages,
                "model": model,
                "evaluation_label": "retrospective portfolio evaluation; backtests are sequential risk-forecast evaluation",
                "inputs": inputs, "sources_lf_normalised": sources, "outputs": outputs,
                "human_review": "pending"}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not 7 <= pages <= 15:
        raise ValueError(f"report has {pages} pages; the brief requires 7-15")
    return out, pages


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", choices=["v6", "v5"], default="v6", help="v6 final model (default) or the v5 report final-report-r1")
    out, pages = build(model=ap.parse_args().model)
    print(f"{out/'technical_report.pdf'}: {pages} pages")


if __name__ == "__main__":
    main()
