"""Full evaluation of the original selection plus volatility overlay (task PORT-005).

Mandate-change candidate, not part of the frozen prereg-v1 run: the overlay was
designed after the data were seen (PORT-004). Evidence follows the frozen checks
C1-C5 as closely as a time-varying strategy allows; every departure is recorded
in metadata.json. The outcome is labelled as a check under frozen criteria, not
as the frozen verdict.

    python -m quanedge.overlay_eval        # writes results/overlay-eval-r1/
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yaml
from . import config
from .config import TICKERS
from .portfolio import construct, canonical_weights, weight_hash, hurdle, feasible, kpis, es, tail_weights
from .backtest import assess, model_pass, verdict
from .stress import SCENARIOS, hypothetical, attribution, survival
from .results import digest
from .risk import fit_models, risk_table, rolling_forecasts, save_forecasts
from .dynamic import simulate
from .hedging import vol_target, EWMA_LAMBDA, REVIEW, MIN_EQUITY_CHANGE, MIN_HISTORY

LABEL = ("Mandate-change candidate evaluated after preregistration; checks follow the frozen criteria "
         "but the strategy was designed after the data were seen.")
METHODS = ["historical", "normal", "evt", "fhs", "garch_evt"]
OVERLAY = {"type": "ewma_volatility_target", "ewma_lambda": EWMA_LAMBDA, "review": REVIEW,
           "min_equity_change": MIN_EQUITY_CHANGE, "min_history": MIN_HISTORY,
           "scale": "min(1, expanding vol / EWMA vol)", "freed_weight": "AGG then GLD within caps"}


def strategy_hash(base):
    return digest({"base_weight_hash": weight_hash(base), "overlay": OVERLAY})


def window_stress(path, value):
    rows = []
    for name, (start, end) in SCENARIOS.items():
        w = path.wealth.loc[start:end]
        if w.empty or str(w.index[0].date()) != start or str(w.index[-1].date()) != end:
            rows.append({"scenario": name, "status": "incomplete data coverage"}); continue
        growth = w/w.iloc[0]; dd = growth/growth.cummax()-1; ret = float(growth.iloc[-1]-1)
        rows.append({"scenario": name, "status": "ok", "start": start, "end": end, "return": ret,
                     "loss_usd": -value*ret, "drawdown": float(dd.min()),
                     "breach": bool(-ret > .20 or -dd.min() > .20),
                     "assumption": "overlay path as run, from the scenario start close; costs included"})
    return rows


def walk_forward(returns, cfg):
    """Each year's base weights use only earlier data; overlay state uses data through each close."""
    pieces, years = {"static": [], "overlay": []}, []
    for year in range(2017, returns.index[-1].year+1):
        base = construct(returns.loc[returns.index < pd.Timestamp(f"{year}-01-01")], cfg)
        years.append({"year": year, "status": base["status"], "weights": base["weights"]})
        if not base["weights"]:
            continue
        upto = returns.loc[:str(year)]
        for kind, path in (("static", simulate(upto, base["weights"], cfg)), ("overlay", vol_target(upto, base["weights"], cfg))):
            piece = path.loc[str(year), ["return"]].copy()
            piece.iloc[0, 0] -= 2*cfg["cost"]           # annual re-selection trade, as the frozen walk-forward
            pieces[kind].append(piece)
    return {k: pd.concat(v) for k, v in pieces.items()}, years


def path_summary(r):
    wealth = (1+r).cumprod(); years = (r.index[-1]-r.index[0]).days/365.25
    return {"cagr": float(wealth.iloc[-1]**(1/years)-1), "maximum_decline": float(1-(wealth/wealth.cummax()).min()),
            "annual_volatility": float(r.std()*np.sqrt(252))}


def one_asset(monthly):
    frame = pd.DataFrame(0., index=monthly.index, columns=TICKERS); frame["SPY"] = monthly
    return frame


def run(out=None):
    from .data import load_clean_prices, load_macro_data
    cfg = config.frozen_policy("prereg-v1")       # mandate v1 comparison
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna(); macro = load_macro_data(); train = returns.loc[:cfg["training_end"]]
    folder = config.RESULTS_DIR/"final-20261027"/"selected"
    base = canonical_weights(json.loads((folder/"weights.json").read_text())["weights"])
    frozen = json.loads((folder/"summary.json").read_text())
    sh = strategy_hash(base); value = cfg["value"]
    out = out or config.RESULTS_DIR/"overlay-eval-r1"; out.mkdir(parents=True, exist_ok=True)
    data_hash = hashlib.sha256((config.ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()

    path = vol_target(returns, base, cfg); static = simulate(returns, base, cfg)
    path.to_csv(out/"overlay_path.csv", float_format="%.10g")
    held = canonical_weights({t: float(path[t].iloc[-1]) for t in TICKERS})
    targets = path[TICKERS].drop_duplicates()
    c1 = all(feasible(dict(zip(TICKERS, row)), cfg) for row in targets.to_numpy())

    print("Rolling forecasts for the overlay path", flush=True)
    r = np.log1p(path["return"])
    forecasts = rolling_forecasts(r, methods=METHODS, window=cfg["window"], refit=cfg["refit"])
    failures = forecasts.attrs.get("fit_failures", [])
    forecasts["weight_hash"] = sh; forecasts["data_hash"] = data_hash
    forecasts["evaluation_label"] = "sequential risk-forecast evaluation"
    forecasts["allocation_cutoff"] = cfg["snapshot_end"]
    save_forecasts(forecasts, out/"forecasts.csv")
    assessments = [assess(forecasts, sh, m, a, cfg["evaluation_start"], cfg["snapshot_end"])
                   for m in METHODS for a in (.90, .95, .99)]
    primary = next(v for v in assessments if v["method"] == cfg["primary"] and v["alpha"] == .99)
    challenger = next(v for v in assessments if v["method"] == cfg["challenger"] and v["alpha"] == .99)

    logs = np.log1p(returns)
    table = risk_table(fit_models(logs, held, n_sim=cfg["n_sim"], seed=cfg["seed"]), value=value)
    table.to_csv(out/"risk_current_holdings.csv", index=False)

    stress = window_stress(path, value)
    hyp = {k: hypothetical(train, w, value) for k, w in (("base", base), ("current_holdings", held))}
    estimation = returns.loc[:cfg["snapshot_end"]]
    loss = -path["return"].to_numpy(); path_es = float(tail_weights(loss)@loss)
    drag = float(np.log1p(path_summary(static["return"])["cagr"])-np.log1p(path_summary(path["return"])["cagr"]))
    base_geo = frozen["expected_geometric"]; overlay_geo = float(np.expm1(np.log1p(base_geo)-drag))
    h = hurdle(cfg["inflation"], cfg["spending"])
    gfc = next(s for s in stress if s["scenario"] == "GFC")
    checks = {"C1": bool(c1), "C2": bool(path_es <= cfg["es_budget"]+1e-6 and es(estimation, base) <= cfg["es_budget"]+1e-6),
              "C3": bool(overlay_geo >= h), "C4": bool(model_pass(primary) or model_pass(challenger)),
              "C5": bool(all(s.get("status") == "ok" for s in stress) and
                         all(s["loss_usd"] <= cfg["drawdown_limit"]*value for s in stress) and
                         -gfc["drawdown"] <= cfg["drawdown_limit"])}

    wf, wf_years = walk_forward(returns, cfg)
    for k, v in wf.items():
        v.to_csv(out/f"walk_forward_{k}.csv", float_format="%.10g")
    monthly = lambda p: (1+p["return"]).resample("ME").prod()-1
    cpi = macro.CPIAUCSL.resample("ME").last().pct_change()
    shortfall = {k: survival(one_asset(monthly(p)), cpi, {t: float(t == "SPY") for t in TICKERS}, cfg)
                 for k, p in (("overlay", path), ("static_selected", static))}

    rf = macro.rf_daily_effective.reindex(returns.index)
    bench = simulate(returns, canonical_weights({"SPY": .4, "AGG": .6}), cfg)["return"]
    result = {"label": LABEL, "evaluation_label": "retrospective portfolio evaluation",
              "strategy_hash": sh, "base_weights": base, "base_weight_hash": weight_hash(base),
              "current_holdings": held, "current_holdings_hash": weight_hash(held),
              "checks": checks, "outcome_under_frozen_criteria": verdict(checks),
              "frozen_selected_checks": frozen["checks"],
              "expected_geometric": {"base": base_geo, "overlay_approx": overlay_geo, "historical_drag_log": drag, "hurdle": h},
              "es99": {"overlay_path": path_es, "base_weights_estimation": es(estimation, base), "budget": cfg["es_budget"]},
              "performance": {"overlay": kpis(path["return"], rf, returns.SPY, bench),
                              "static_selected": kpis(static["return"], rf, returns.SPY, bench)},
              "turnover_per_year": {k: float(p.turnover.sum()/((p.index[-1]-p.index[0]).days/365.25)) for k, p in (("overlay", path), ("static", static))},
              "share_weeks_scaled": float((path.basis != "base").mean()),
              "stress": stress, "stress_frozen_static": frozen["stress"], "hypothetical": hyp,
              "attribution": {k: attribution(returns, w, value=value) for k, w in (("base", base), ("current_holdings", held))},
              "attribution_note": "historical attribution on fixed weights; the overlay path itself has no single weight vector",
              "validation": assessments, "fit_failures": failures,
              "model_used": cfg["primary"] if model_pass(primary) else cfg["challenger"] if model_pass(challenger) else None,
              "walk_forward": {"summary": {k: path_summary(v["return"]) for k, v in wf.items()}, "years": wf_years},
              "real_capital_survival": shortfall}
    meta = {"task": "PORT-005", "label": LABEL, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_hash": data_hash, "config_hash": digest(cfg), "overlay": OVERLAY, "strategy_hash": sh,
            "departures_from_frozen_evaluation": [
                "risk forecasts use the overlay's realised daily returns after costs, not a fixed-weight replay",
                "C2 requires both the base weights' estimation-sample ES99 and the overlay path's realised ES99 within budget",
                "C3 subtracts the overlay's realised historical log-return drag from the frozen base expected geometric return",
                "C5 uses the overlay path from each scenario start close, with rebalancing and costs, not buy-and-hold",
                "risk table and attribution are for the end-of-snapshot holdings",
                "real-capital shortfall bootstraps the strategy's monthly returns as one asset"]}
    write = lambda p, o: p.write_text(json.dumps(o, indent=2, default=lambda x: x.item() if hasattr(x, "item") else str(x),
                                                  allow_nan=True)+"\n", encoding="utf-8")
    write(out/"summary.json", result); write(out/"metadata.json", meta)
    return result


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    r = run()
    print(json.dumps({k: r[k] for k in ("checks", "outcome_under_frozen_criteria", "expected_geometric", "es99", "model_used")}, indent=1, default=str))


if __name__ == "__main__":
    main()
