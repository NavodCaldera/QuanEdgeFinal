"""
The risk workstream in one command:

    python -m quanedge.risk.run              # full run  -> results/risk/
    python -m quanedge.risk.run --quick      # fast look -> results/risk_quick/ (never touches the full run)
    python -m quanedge.risk.run --returns returns.csv --weights weights.json --out results/risk_final

--returns takes daily asset log returns (dates in the first column, one
column per permitted ticker) and --weights a JSON object {ticker: weight}:
the adapters for Person 1's approved dataset and Person 2's weights.  Without
them the run uses the TEMPORARY development cache and placeholder equal
weights, and every output says so.

A run is built in a hidden sibling folder and replaces the output folder only
once every file has been written, so a failed run never mixes old and new
evidence.  manifest.json records the inputs (with SHA-256 hashes), code
version, settings, seeds, units and each model's fit status.  Every sentence
in summary.md is computed from the run's own tables.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from ..config import CONF_LEVELS, PORTFOLIO_VALUE, RESULTS_DIR, ROOT
from . import dev_data, diagnostics, evt, plots, rolling, settings as S
from .models import LABEL, UNCONDITIONAL, Unavailable, fit_models, risk_table
from .portfolio import loss_fraction, portfolio_log_returns
from .uncertainty import bootstrap_intervals, with_intervals
from .validation import check_dated_history
from .var_es import batch_se, mc_convergence

SCHEMA_VERSION = 1
UNITS = {
    "alpha": "confidence level as a probability (0.99, not 99)",
    "var, es": "one-day loss in log-return units (0.01 = a log loss of 0.01); positive = loss",
    "*_pct": "percentage points of portfolio value lost (simple loss)",
    "*_usd": "US dollars lost on the portfolio value",
    "es_pct, es_usd and their bounds": "exact: each tail loss averaged in dollars, not the dollar value of log ES",
    "rolling_forecasts return, var_*, es_*": "log-return units; a breach is a day with -return > var",
}
CONVENTIONS = {
    "horizon": "1 trading day",
    "portfolio_value_usd": PORTFOLIO_VALUE,
    "confidence_levels": list(CONF_LEVELS),
    "aggregation": "asset log returns -> simple returns -> weighted sum -> portfolio log return",
    "rebalancing": "weights held fixed every day (daily rebalanced, no costs): today's portfolio replayed",
    "var_quantile": f"numpy '{S.QUANTILE_METHOD}' interpolation (Hyndman-Fan type 7)",
    "es": "exact average of the worst (1 - alpha) probability mass",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(*args) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20,
                              check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _json_default(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)                                   # dates, timestamps, paths


def _ok(model) -> bool:
    return model is not None and not isinstance(model, Unavailable)


def _k(usd: float) -> str:
    return f"${usd / 1e3:,.0f}k" if np.isfinite(usd) else "n/a"


def _pct(log_loss: float) -> str:
    return f"{100 * loss_fraction(log_loss):.2f}%" if np.isfinite(log_loss) else "n/a"


def _levels(alphas) -> str:
    return ", ".join(f"{a:.0%}" for a in alphas) or "no level"


def _versus(a: float, b: float) -> str:
    """'21% below' / '8% above': a relative to b."""
    d = 100 * (1 - a / b)
    return f"{abs(d):.0f}% {'below' if d > 0 else 'above'}"


def _md_table(df: pd.DataFrame) -> list[str]:
    rows = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * df.shape[1]]
    return rows + ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]


def load_inputs(returns_path=None, weights_path=None, refresh: bool = False):
    """Asset log returns, weights, and a record of where both came from."""
    if returns_path:
        source = Path(returns_path)
        x = pd.read_csv(source, index_col=0, parse_dates=True)
        data_mode = f"provided returns file {source.name}"
    else:
        x = dev_data.load_log_returns(refresh)
        source, data_mode = dev_data.PRICE_FILE, "temporary development cache from yfinance, standing in for Person 1's dataset"
    check_dated_history(x)
    if weights_path:
        raw = json.loads(Path(weights_path).read_text(encoding="utf-8"))
        weights, weights_mode = {str(k): float(v) for k, v in raw.items()}, f"provided weights file {Path(weights_path).name}"
    else:
        weights, weights_mode = dict(S.DEV_WEIGHTS), "placeholder equal weights, not a recommendation"
    info = {"data_mode": data_mode, "source_file": str(source), "source_sha256": _sha256(source),
            "first_date": x.index[0].date(), "last_date": x.index[-1].date(), "n_days": len(x),
            "assets": list(map(str, x.columns)), "weights_mode": weights_mode, "weights": weights,
            "weights_sha256": hashlib.sha256(json.dumps(weights, sort_keys=True).encode()).hexdigest(),
            "development": not (returns_path and weights_path)}
    return x, weights, info


def publish(tmp: Path, out: Path) -> None:
    """Swap a finished run into place; the previous output is deleted only after the swap succeeded."""
    old = out.with_name(f".{out.name}.replaced")
    if old.exists():
        shutil.rmtree(old)
    if out.exists():
        out.rename(old)
    try:
        tmp.rename(out)
    except OSError:
        if old.exists() and not out.exists():
            old.rename(out)                         # put the previous results back
        raise
    shutil.rmtree(old, ignore_errors=True)


def summary(info, mode, run_id, r, models, table, scan, chosen, checks, inside, mc_conv, bs, fc, reps) -> str:
    d = diagnostics.describe(r)
    t = table.set_index(["method", "alpha"])
    last = pd.Timestamp(info["last_date"])
    L = ["# Risk measurement summary (Person 3)", "",
         f"Run `{run_id}` ({mode} mode). Every number is read from this run's `tables/`; `manifest.json` "
         "records the inputs, settings and code version.", ""]
    if info["development"]:
        L += [f"> **Development inputs.** Data: {info['data_mode']}. Weights: {info['weights_mode']}. Every "
              "number here will change when Person 1's approved data and Person 2's weights are used.", ""]
    L += ["## Data", "",
          f"- {d['n_days']:,} trading days, {d['start']:%d %b %Y} to {d['end']:%d %b %Y}; the as-of date of "
          f"every estimate is {last:%d %b %Y}. Data: {info['data_mode']}.",
          f"- Weights ({info['weights_mode']}): " + ", ".join(f"{k} {v:.1%}" for k, v in info["weights"].items()) + ".",
          f"- Daily volatility {100 * d['vol_daily']:.2f}% ({100 * d['vol_annual']:.1f}% annualised); skewness "
          f"{d['skewness']:.2f}; excess kurtosis {d['excess_kurtosis']:.1f} (normal: 0).",
          f"- Worst day {d['worst_day_date']:%d %b %Y}: {_pct(-d['worst_day'])} of portfolio value "
          f"(${PORTFOLIO_VALUE * loss_fraction(-d['worst_day']):,.0f}).", "",
          f"## One-day VaR and ES on USD {PORTFOLIO_VALUE / 1e6:.0f}m", "",
          "ES is the exact average dollar loss over the worst days, not the dollar value of log ES. Brackets: "
          f"95% moving-block bootstrap interval ({reps} resamples), covering estimation and simulation noise but "
          "not EVT threshold re-selection or model risk. No bracket means not estimated (conditional models), "
          "not zero uncertainty. The 90% level is in `risk_table.csv`.", "",
          "| Model | 95% VaR | 95% ES | 99% VaR | 99% ES |", "|---|---|---|---|---|"]
    for m in models:
        cells = []
        for a in (0.95, 0.99):
            row = t.loc[(m, a)]
            for q in ("var", "es"):
                c = _k(row[f"{q}_usd"])
                if pd.notna(row[f"{q}_lo_usd"]):
                    c += f" [{_k(row[f'{q}_lo_usd'])}–{_k(row[f'{q}_hi_usd'])}]"
                cells.append(c)
        L.append(f"| {LABEL[m]} | " + " | ".join(cells) + " |")

    flagged = {m: mod.status for m, mod in models.items() if mod.status != "ok"}
    failed = table.groupby("method")["reps_failed"].max().dropna()
    L += ["", "## Model status", ""]
    L += [f"- {LABEL[m]}: {s}" for m, s in flagged.items()] or [f"- All {len(models)} models fitted without warnings."]
    L += [f"- {LABEL[m]}: {int(k)} of {reps} bootstrap resamples could not be fitted." for m, k in failed.items() if k > 0]

    L += ["", "## Where the models disagree (99%, one day)", ""]
    u99 = table[(table["alpha"] == 0.99) & table["method"].isin(UNCONDITIONAL)].dropna(subset=["var_usd"])
    if len(u99) > 1:
        lo, hi = u99.loc[u99["var_usd"].idxmin()], u99.loc[u99["var_usd"].idxmax()]
        L.append(f"- Unconditional 99% VaR runs from {_k(lo['var_usd'])} for {lo['label']} to {_k(hi['var_usd'])} "
                 f"for {hi['label']}, a ratio of {hi['var_usd'] / lo['var_usd']:.2f}.")
    if _ok(models["normal"]) and _ok(models["historical"]):
        h, n = t.loc[("historical", 0.99)], t.loc[("normal", 0.99)]
        z = stats.norm.ppf(0.99)
        ratios = ", ".join(f"{name} {t.loc[(m, 0.99), 'es_over_var']:.2f}" for m, name in
                           (("normal", "normal"), ("historical", "historical"), ("evt", "EVT")) if _ok(models[m]))
        L += [f"- Normal 99% VaR is {_versus(n['var_usd'], h['var_usd'])} historical simulation; normal 99% ES is "
              f"{_versus(n['es_usd'], h['es_usd'])}.",
              f"- ES/VaR at 99% (log units): {ratios}. For a normal model the ratio depends only on the confidence "
              f"level and the mean-to-volatility ratio ({stats.norm.pdf(z) / (0.01 * z):.3f} at 99% with zero "
              "mean); a larger ratio means a deeper tail beyond VaR."]
    if _ok(models["student_t"]) and _ok(models["normal"]):
        below = [a for a in CONF_LEVELS if t.loc[("student_t", a), "var"] < t.loc[("normal", a), "var"]]
        above = [a for a in CONF_LEVELS if a not in below]
        L.append(f"- Student-t VaR (ν = {models['student_t'].params['nu']:.1f}) is below normal VaR at "
                 f"{_levels(below)} and above it at {_levels(above)}: the fitted t has more mass near zero and in "
                 "the far tail, and less in between.")
    if mc_conv is not None and _ok(models["normal"]):
        c = mc_conv[(mc_conv["method"] == "mc_normal") & (mc_conv["alpha"] == 0.99)]
        big = c[c["n_sim"] == c["n_sim"].max()]
        spread = PORTFOLIO_VALUE * (loss_fraction(big["var"].max()) - loss_fraction(big["var"].min()))
        gap = max(abs(t.loc[("mc_normal", a), "var_usd"] - t.loc[("normal", a), "var_usd"]) for a in CONF_LEVELS)
        L.append(f"- Monte Carlo (normal) is within {_k(gap)} of parametric normal VaR at every level; across "
                 f"{len(big)} seeds at {int(big['n_sim'].iloc[0]):,} scenarios its 99% VaR moves by {_k(spread)}. "
                 "Exact agreement is not expected: Monte Carlo simulates the seven assets and aggregates simple "
                 "returns, while parametric normal fits the portfolio return directly.")
    if _ok(models["mc_t"]) and _ok(models["mc_normal"]):
        L.append(f"- Monte Carlo (Student-t) adds joint fat tails (ν = {models['mc_t'].params['nu']:.1f}): 99% ES "
                 f"{_k(t.loc[('mc_t', 0.99), 'es_usd'])} against {_k(t.loc[('mc_normal', 0.99), 'es_usd'])} under "
                 "the multivariate normal.")
    g = models.get("garch_evt")
    if _ok(g) and _ok(models.get("fhs")) and _ok(models["historical"]):
        nxt = last + pd.offsets.BDay(1)
        L.append(f"- The GARCH volatility forecast for {nxt:%d %b %Y}, the weekday after the data end, is "
                 f"{100 * g.filter.sigma_next:.2f}% against a sample average of {100 * d['vol_daily']:.2f}%, so "
                 f"conditional 99% VaR for that day is {_k(t.loc[('garch_evt', 0.99), 'var_usd'])} (GARCH-EVT) and "
                 f"{_k(t.loc[('fhs', 0.99), 'var_usd'])} (FHS), against "
                 f"{_k(t.loc[('historical', 0.99), 'var_usd'])} for whole-sample historical simulation.")
    est = table[np.isfinite(table["es"]) & table["es_usd"].notna()]
    if len(est):
        overstatement = PORTFOLIO_VALUE * loss_fraction(est["es"].to_numpy()) - est["es_usd"].to_numpy()
        i = int(np.argmax(overstatement))
        L.append(f"- Converting log ES into dollars, instead of averaging dollar losses, would overstate ES by up to "
                 f"${overstatement[i]:,.0f} ({est['label'].iloc[i]} at {est['alpha'].iloc[i]:.0%}).")

    L += ["", "## EVT", ""]
    ev = models["evt"]
    if _ok(ev) and chosen is not None:
        stable = scan[scan["stable"]]
        L += [f"- Threshold rule: {chosen['rule']}; every candidate needs at least {S.EVT_MIN_EXCEED} exceedances, "
              f"and stability needs at least {S.EVT_STABILITY_MIN_HIGHER} higher thresholds to compare with. Chosen: "
              f"the {100 * chosen['q']:g}th percentile of daily losses, u = {100 * chosen['u']:.2f}% log loss, "
              f"{int(chosen['n_exceed'])} exceedances.",
              f"- Tail index ξ = {ev.params['xi']:.3f} (s.e. {ev.params['xi_se']:.3f}). "
              + ("ξ > 0: a power-law tail. " if ev.params["xi"] > 0 else "")
              + ("ξ < 0.5: finite variance. " if ev.params["xi"] < 0.5 else "")
              + ("ξ < 1: log ES exists." if ev.params["xi"] < 1 else "ξ ≥ 1: log ES is infinite.")]
        if len(stable):
            L.append(f"- ξ is stable from the {100 * stable['q'].min():g}th to the {100 * stable['q'].max():g}th "
                     f"percentile. Across those thresholds 99% VaR stays within {_pct(stable['var_0.99'].min())}–"
                     f"{_pct(stable['var_0.99'].max())} and 99% ES within {100 * stable['es_fraction_0.99'].min():.2f}%–"
                     f"{100 * stable['es_fraction_0.99'].max():.2f}% of portfolio value: a sensitivity band, not a "
                     "confidence interval.")
        thumb = scan[scan["fit_ok"] & scan["q"].round(3).isin([0.9, 0.95])]
        if len(thumb):
            L.append("- Rules of thumb for comparison: " + "; ".join(
                f"the {100 * q:g}th percentile gives 99% VaR {_pct(v)}" for q, v in zip(thumb["q"], thumb["var_0.99"])) + ".")
        if _ok(models["historical"]) and _ok(models["normal"]):
            L.append(f"- At 99.9% (about one day in four years, an extrapolation with wider uncertainty): EVT VaR "
                     f"{_pct(ev.var(0.999))}, historical {_pct(models['historical'].var(0.999))}, normal "
                     f"{_pct(models['normal'].var(0.999))}.")
        if _ok(g):
            L.append(f"- After the GARCH filter, the residual tail index (fixed 90th-percentile threshold, as in McNeil "
                     f"& Frey) is ξ = {g.params['z_xi']:.3f} (s.e. {g.params['z_xi_se']:.3f}), against "
                     f"{ev.params['xi']:.3f} for raw losses; that fixed threshold has not been scanned like the raw one.")
    else:
        L.append(f"- EVT unavailable: {ev.status}")

    L += ["", "## Assumption checks", "",
          "A rejected null is evidence against it; a null that is not rejected is not proof of the assumption.", ""]
    c = checks.assign(statistic=checks["statistic"].map("{:,.2f}".format),
                      p_value=checks["p_value"].map(lambda p: "<0.0001" if p < 1e-4 else f"{p:.4f}"))
    L += _md_table(c[["assumption", "test", "null_hypothesis", "statistic", "p_value", "conclusion"]])
    i99 = inside[inside["alpha"] == 0.99]
    L += ["", "## In-sample breach rate of the full-sample 99% VaR (a fit check, not a backtest)", ""]
    L += _md_table(pd.DataFrame({"model": i99["method"].map(LABEL),
                                 "breaches": i99["breaches"].map(lambda b: "n/a" if pd.isna(b) else f"{b:.0f}"),
                                 "breach rate": i99["breach_pct"].map(lambda p: "n/a" if pd.isna(p) else f"{p:.2f}%"),
                                 "expected": "1.00%"}))
    L += ["", "## Rolling out-of-sample breaches (raw counts; formal tests are Person 4's)", ""]
    if bs is None:
        L.append("Not run in quick mode.")
    else:
        fails = fc.attrs.get("fit_failures", [])
        L += [f"{len(fc):,} forecast days, {fc.index[0]:%d %b %Y} to {fc.index[-1]:%d %b %Y}; window "
              f"{S.ROLL_WINDOW} days, slow models refitted every {S.ROLL_REFIT} days. Days without a forecast are "
              f"excluded, not counted as passes. Failed refits: {len(fails)} (listed in manifest.json).", ""]
        cells = bs.assign(cell=bs["breaches"].astype(int).astype(str) + " (" + bs["expected_breaches"].round(1).astype(str) + ")")
        p = cells.pivot(index="method", columns="alpha", values="cell")
        miss = bs.groupby("method")["missing_days"].max()
        L += _md_table(pd.DataFrame({"model": [LABEL[m] for m in p.index],
                                     **{f"{a:.0%} breaches (expected)": p[a].to_numpy() for a in p.columns},
                                     "days without forecast": miss.reindex(p.index).to_numpy()}))
    L += ["", "## Files", "",
          "`tables/`: risk_table, evt_threshold_scan, assumption_checks, worst_days, in_sample_breaches, "
          "model_parameters, mc_simulation_error, mc_convergence" + (", rolling_forecasts, rolling_breaches"
                                                                     if bs is not None else "")
          + ". `figures/`: one PNG per figure. `manifest.json`: inputs, hashes, settings, seeds, statuses.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Person 3: VaR, ES and EVT for the portfolio")
    ap.add_argument("--quick", action="store_true",
                    help="50 bootstrap resamples and no rolling forecasts; writes results/risk_quick/")
    ap.add_argument("--out", type=Path, help="output folder (default results/risk, or results/risk_quick with --quick)")
    ap.add_argument("--returns", type=Path, help="CSV of daily asset log returns, dates in the first column")
    ap.add_argument("--weights", type=Path, help='JSON object of weights, e.g. {"SPY": 0.3, "AGG": 0.7}')
    ap.add_argument("--refresh-data", action="store_true",
                    help="re-download the development prices (overwrites the development cache)")
    args = ap.parse_args(argv)
    if args.refresh_data and args.returns:
        ap.error("--refresh-data applies to the development cache only, not to --returns")
    started, t0 = datetime.now(timezone.utc), time.time()
    run_id, mode = started.strftime("%Y%m%dT%H%M%SZ"), "quick" if args.quick else "full"
    out = args.out or RESULTS_DIR / ("risk_quick" if args.quick else "risk")
    code = {"git_commit": _git("rev-parse", "HEAD"),
            "uncommitted_code_changes": bool(_git("status", "--porcelain", "--", "quanedge", "tests"))}

    x, w, info = load_inputs(args.returns, args.weights, args.refresh_data)
    r = portfolio_log_returns(x, w)
    models = fit_models(x, w)
    print(f"[{time.time() - t0:5.0f}s] fitted {len(models)} models on {len(r):,} days")

    tmp = out.with_name(f".{out.name}.partial-{run_id}")
    (tmp / "tables").mkdir(parents=True)
    (tmp / "figures").mkdir()
    try:
        ev = models["evt"]
        reps = 50 if args.quick else S.BOOT_REPS
        ci = bootstrap_intervals(x, w, reps=reps, evt_threshold_q=ev.params.get("threshold_q"))
        table = with_intervals(risk_table(models), ci)
        print(f"[{time.time() - t0:5.0f}s] bootstrap intervals ({reps} resamples)")

        scan = evt.threshold_scan(-r.to_numpy(), dollar_es=True)
        chosen = evt.select_threshold(scan) if scan["fit_ok"].any() else None
        filt = next((m.filter for m in (models["fhs"], models["garch_evt"]) if _ok(m)), None)
        checks = diagnostics.assumption_checks(r, z=None if filt is None else filt.z)
        inside = diagnostics.in_sample_breaches(r, {m: models[m] for m in UNCONDITIONAL}, CONF_LEVELS)
        params = pd.DataFrame([(m, k, v) for m, mod in models.items() for k, v in mod.params.items()],
                              columns=["method", "parameter", "value"])
        mc_ok = [m for m in ("mc_normal", "mc_t") if _ok(models[m])]
        mc_conv = mc_convergence(x, w) if len(mc_ok) == 2 else None
        mc_err = pd.DataFrame([(m, a, *batch_se(models[m], a)) for m in mc_ok for a in CONF_LEVELS],
                              columns=["method", "alpha", "var_se", "es_se"])
        outputs = {"risk_table": table, "evt_threshold_scan": scan, "assumption_checks": checks,
                   "worst_days": diagnostics.worst_days(r, x, w), "in_sample_breaches": inside,
                   "model_parameters": params, "mc_simulation_error": mc_err}
        if mc_conv is not None:
            outputs["mc_convergence"] = mc_conv
        fc = bs = None
        if not args.quick:
            fc = rolling.rolling_forecasts(r)
            bs = outputs["rolling_breaches"] = rolling.breach_summary(fc)
            rolling.save_forecasts(fc, tmp / "tables" / "rolling_forecasts.csv")   # exact: breaches survive a reload
            print(f"[{time.time() - t0:5.0f}s] rolling forecasts ({len(fc):,} days)")
        for name, df in outputs.items():
            df.to_csv(tmp / "tables" / f"{name}.csv", index=False, float_format="%.6g")

        figures = {"fig1_distribution": plots.fig_distribution(r, models),
                   "fig4_var_es_comparison": plots.fig_comparison(table),
                   "fig5_var_by_confidence": plots.fig_tail_curve(models)}
        if chosen is not None:
            figures["fig2_evt_threshold"] = plots.fig_threshold(scan, chosen)
        if _ok(ev) and _ok(models["normal"]):
            figures["fig3_evt_tail_fit"] = plots.fig_evt_fit(ev, models["normal"])
        if table["var_lo"].notna().any():
            figures["fig6_estimate_uncertainty"] = plots.fig_uncertainty(table)
        if fc is not None:
            figures["fig7_rolling_var"] = plots.fig_rolling(fc)
        for name, fig in sorted(figures.items()):
            fig.savefig(tmp / "figures" / f"{name}.png")

        (tmp / "summary.md").write_text(
            summary(info, mode, run_id, r, models, table, scan, chosen, checks, inside, mc_conv, bs, fc, reps),
            encoding="utf-8")
        manifest = {
            "schema_version": SCHEMA_VERSION, "run_id": run_id, "mode": mode,
            "started_utc": started.isoformat(timespec="seconds"),
            "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "runtime_seconds": round(time.time() - t0, 1), "output_dir": str(out),
            "code": code,
            "environment": {"python": sys.version.split()[0],
                            "packages": {p: version(p) for p in ("numpy", "pandas", "scipy", "arch",
                                                                  "statsmodels", "matplotlib")}},
            "inputs": info, "conventions": CONVENTIONS, "units": UNITS,
            "settings": {k: v for k, v in vars(S).items() if k.isupper()},
            "seeds": {"monte_carlo": S.SEED, "bootstrap": S.SEED,
                      "mc_convergence": list(range(S.SEED, S.SEED + S.MC_CONVERGENCE_SEEDS))},
            "models": {m: {"status": mod.status, "params": mod.params} for m, mod in models.items()},
            "evt_threshold": None if chosen is None else {k: chosen[k] for k in ("rule", "q", "u", "n_exceed")},
            "bootstrap": {"resamples": reps, "block_days": S.BOOT_BLOCK, "mc_scenarios": S.BOOT_N_SIM,
                          "level": S.CI_LEVEL,
                          "failed_resamples": table.groupby("method")["reps_failed"].max().dropna().to_dict()},
            "rolling": None if fc is None else {
                "window": S.ROLL_WINDOW, "refit_every": S.ROLL_REFIT, "forecast_days": len(fc),
                "first_forecast": fc.index[0], "last_forecast": fc.index[-1],
                "fit_failures": fc.attrs.get("fit_failures", [])},
        }
        manifest["files"] = sorted([str(p.relative_to(tmp).as_posix()) for p in tmp.rglob("*") if p.is_file()]
                                   + ["manifest.json"])
        (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2, default=_json_default), encoding="utf-8")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    publish(tmp, out)
    print(f"[{time.time() - t0:5.0f}s] wrote {out}")


if __name__ == "__main__":
    main()
