"""Candidate v4c: risk parity plus volatility overlay (task PORT-011, PLAN.md section 13d).

Pre-registered at tag prereg-v4c before this module first ran. Evaluated under the v3
policy frozen at prereg-v3; the v3 run and verdict are unchanged. The overlay and the
check definitions follow PORT-005 (overlay_eval), with the v3 C3 real-return floor.

    python -m quanedge.parity_overlay      # writes results/parity-overlay-r1/
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from . import config
from .config import TICKERS
from .portfolio import construct, canonical_weights, weight_hash, feasible, kpis, es, tail_weights, return_check, real_return
from .backtest import assess, model_pass, verdict
from .stress import hypothetical, attribution, reserve_survival
from .results import digest
from .risk import rolling_forecasts, save_forecasts
from .dynamic import simulate
from .hedging import vol_target
from .overlay_eval import OVERLAY, window_stress, path_summary, one_asset, METHODS

LABEL = ("Pre-registered candidate v4c (prereg-v4c) under v3 criteria; designed after the data were seen, "
         "so not the v3 verdict and not an untouched test.")
BASE_RUN = "final-v3-20261030"
BASE_FOLDER = "A1_near_parity"
BASE_HASH = "ece535c3eb7c2caab5cd5fa4c7e0cf9e107f51c1c01031eb724e104dc8005dc3"
WREC_FOLDER = "selected"
# Same windows as scripts/crisis_methods_study.py (PORT-010); descriptive only.
CRISES = [("GFC", "2007-10-09", "2009-03-09"), ("Lehman liquidity shock", "2008-09-09", "2008-10-10"),
          ("Gold bear market", "2011-08-22", "2015-12-17"), ("Oil collapse", "2014-06-23", "2016-01-20"),
          ("2018 trade tensions", "2018-01-26", "2018-12-24"), ("COVID crash", "2020-02-19", "2020-03-23"),
          ("COVID dash for cash", "2020-03-06", "2020-03-18"), ("Bond bear market", "2020-08-04", "2022-10-20"),
          ("China / global tightening", "2021-02-17", "2022-10-24"), ("Rates 2022", "2022-01-03", "2022-10-12"),
          ("Gold correction 2026", "2026-01-29", "2026-07-16")]


def strategy_hash(base):
    return digest({"candidate": "v4c", "base_weight_hash": weight_hash(base), "overlay": OVERLAY})


def window(wealth, start, end):
    w = wealth.loc[start:end]
    if w.empty or str(w.index[0].date()) != start or str(w.index[-1].date()) != end:
        return None, None
    growth = w/w.iloc[0]
    return float(growth.iloc[-1]-1), float((growth/growth.cummax()-1).min())


def walk_forward(returns, cfg):
    """Each year's near-parity weights use only earlier data; overlay state uses data through each close."""
    pieces, years = {"static_parity": [], "parity_overlay": []}, []
    for year in range(2017, returns.index[-1].year+1):
        base = construct(returns.loc[returns.index < pd.Timestamp(f"{year}-01-01")], cfg, "near_parity")
        years.append({"year": year, "status": base["status"], "weights": base["weights"]})
        if not base["weights"]:
            continue
        upto = returns.loc[:str(year)]
        for kind, path in (("static_parity", simulate(upto, base["weights"], cfg)),
                           ("parity_overlay", vol_target(upto, base["weights"], cfg))):
            piece = path.loc[str(year), ["return"]].copy()
            piece.iloc[0, 0] -= 2*cfg["cost"]
            pieces[kind].append(piece)
    return {k: pd.concat(v) for k, v in pieces.items()}, years


def run(out=None):
    from .data import load_clean_prices, load_macro_data
    cfg = config.frozen_policy("prereg-v3")
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna(); macro = load_macro_data(); train = returns.loc[:cfg["training_end"]]
    folder = config.RESULTS_DIR/BASE_RUN/BASE_FOLDER
    base = canonical_weights(json.loads((folder/"weights.json").read_text())["weights"])
    if weight_hash(base) != BASE_HASH:
        raise ValueError("base weights differ from the pre-registered hash")
    frozen = json.loads((folder/"summary.json").read_text())
    wrec = canonical_weights(json.loads((config.RESULTS_DIR/BASE_RUN/WREC_FOLDER/"weights.json").read_text())["weights"])
    sh = strategy_hash(base); value = cfg["value"]
    out = out or config.RESULTS_DIR/"parity-overlay-r1"; out.mkdir(parents=True, exist_ok=True)
    data_hash = hashlib.sha256((config.ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()

    path = vol_target(returns, base, cfg); static = simulate(returns, base, cfg); held_wrec = simulate(returns, wrec, cfg)
    path.to_csv(out/"overlay_path.csv", float_format="%.10g")
    held = canonical_weights({t: float(path[t].iloc[-1]) for t in TICKERS})
    targets = path[TICKERS].drop_duplicates()
    c1 = all(feasible(dict(zip(TICKERS, row)), cfg) for row in targets.to_numpy())

    print("Rolling forecasts for the parity-overlay path", flush=True)
    forecasts = rolling_forecasts(np.log1p(path["return"]), methods=METHODS, window=cfg["window"], refit=cfg["refit"])
    failures = forecasts.attrs.get("fit_failures", [])
    forecasts["weight_hash"] = sh; forecasts["data_hash"] = data_hash
    forecasts["evaluation_label"] = "sequential risk-forecast evaluation"
    forecasts["allocation_cutoff"] = cfg["snapshot_end"]
    save_forecasts(forecasts, out/"forecasts.csv")
    assessments = [assess(forecasts, sh, m, a, cfg["evaluation_start"], cfg["snapshot_end"])
                   for m in METHODS for a in (.90, .95, .99)]
    primary = next(v for v in assessments if v["method"] == cfg["primary"] and v["alpha"] == .99)
    challenger = next(v for v in assessments if v["method"] == cfg["challenger"] and v["alpha"] == .99)

    stress = window_stress(path, value)
    for s in stress:
        s["assumption"] = "overlay path as run, from the scenario start close; zero cost under v3"
    hyp = {k: hypothetical(train, w, value) for k, w in (("base", base), ("current_holdings", held))}
    loss = -path["return"].to_numpy(); path_es = float(tail_weights(loss)@loss)
    drag = float(np.log1p(path_summary(static["return"])["cagr"])-np.log1p(path_summary(path["return"])["cagr"]))
    base_geo = frozen["expected_geometric"]; overlay_geo = float(np.expm1(np.log1p(base_geo)-drag))
    gfc = next(s for s in stress if s["scenario"] == "GFC")
    checks = {"C1": bool(c1),
              "C2": bool(path_es <= cfg["es_budget"]+1e-6 and es(returns, base) <= cfg["es_budget"]+1e-6),
              "C3": return_check(overlay_geo, cfg),
              "C4": bool(model_pass(primary) or model_pass(challenger)),
              "C5": bool(all(s.get("status") == "ok" for s in stress) and
                         all(s["loss_usd"] <= cfg["drawdown_limit"]*value for s in stress) and
                         -gfc["drawdown"] <= cfg["drawdown_limit"])}

    crises = []
    for name, start, end in CRISES:
        row = {"crisis": name, "start": start, "end": end}
        for label, p in (("parity_overlay", path), ("static_parity", static), ("w_rec", held_wrec)):
            ret, dd = window(p.wealth, start, end)
            row[f"{label}_return"] = ret; row[f"{label}_drawdown"] = dd
        row["overlay_min_equity"] = float(path.loc[start:end, ["SPY", "XLE"]].sum(axis=1).min())
        crises.append(row)
    pd.DataFrame(crises).to_csv(out/"crisis_paths.csv", index=False, float_format="%.6g")

    wf, wf_years = walk_forward(returns, cfg)
    for k, v in wf.items():
        v.to_csv(out/f"walk_forward_{k}.csv", float_format="%.10g")
    monthly = lambda p: (1+p["return"]).resample("ME").prod()-1
    spy_only = {t: float(t == "SPY") for t in TICKERS}
    survival = {k: reserve_survival(one_asset(monthly(p)), spy_only, cfg)
                for k, p in (("parity_overlay", path), ("static_parity", static), ("w_rec", held_wrec))}

    rf = macro.rf_daily_effective.reindex(returns.index)
    bench = simulate(returns, canonical_weights({"SPY": .4, "AGG": .6}), cfg)["return"]
    evaluation = slice(cfg["evaluation_start"], cfg["snapshot_end"])
    years = lambda p: (p.index[-1]-p.index[0]).days/365.25
    result = {"label": LABEL, "evaluation_label": "retrospective portfolio evaluation",
              "strategy_hash": sh, "base_weights": base, "base_weight_hash": weight_hash(base),
              "current_holdings": held, "current_holdings_hash": weight_hash(held),
              "checks": checks, "outcome_under_v3_criteria": verdict(checks),
              "frozen_static_parity_checks": frozen["checks"],
              "expected_geometric": {"base": base_geo, "overlay_approx": overlay_geo, "historical_drag_log": drag,
                                     "overlay_real": real_return(overlay_geo, cfg["inflation"]),
                                     "real_floor": cfg["real_return_floor"]},
              "es99": {"overlay_path": path_es, "base_weights_estimation": es(returns, base), "budget": cfg["es_budget"]},
              "performance": {k: kpis(p["return"], rf, returns.SPY, bench)
                              for k, p in (("parity_overlay", path), ("static_parity", static), ("w_rec", held_wrec))},
              "evaluation_period": {k: path_summary(p.loc[evaluation, "return"])
                                    for k, p in (("parity_overlay", path), ("static_parity", static), ("w_rec", held_wrec))},
              "turnover_per_year": {k: float(p.turnover.sum()/years(p)) for k, p in (("parity_overlay", path), ("static_parity", static))},
              "share_days_scaled": float((path.basis != "base").mean()),
              "stress": stress, "hypothetical": hyp,
              "attribution": {k: attribution(returns, w, value=value) for k, w in (("base", base), ("current_holdings", held))},
              "attribution_note": "historical attribution on fixed weights; the overlay path itself has no single weight vector",
              "crisis_paths": crises, "validation": assessments, "fit_failures": failures,
              "model_used": cfg["primary"] if model_pass(primary) else cfg["challenger"] if model_pass(challenger) else None,
              "walk_forward": {"summary": {k: path_summary(v["return"]) for k, v in wf.items()}, "years": wf_years},
              "reserve_survival": survival}
    meta = {"task": "PORT-011", "prereg_tag": "prereg-v4c", "label": LABEL,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_hash": data_hash, "config_hash": digest(cfg), "overlay": OVERLAY, "strategy_hash": sh,
            "base": f"{BASE_RUN}/{BASE_FOLDER}", "base_weight_hash": BASE_HASH,
            "departures_from_fixed_weight_evaluation": [
                "risk forecasts use the overlay path's realised daily returns, not a fixed-weight replay",
                "C2 requires both the base weights' estimation-sample ES99 and the path's realised ES99 within budget",
                "C3 subtracts the overlay's realised log-return drag against static parity from the base expected return",
                "C5 uses the overlay path from each scenario start close, with rebalancing, not buy-and-hold",
                "reserve survival bootstraps each strategy's monthly returns as one asset"]}
    write = lambda p, o: p.write_text(json.dumps(o, indent=2, default=lambda x: x.item() if hasattr(x, "item") else str(x),
                                                  allow_nan=True)+"\n", encoding="utf-8")
    write(out/"summary.json", result); write(out/"metadata.json", meta)
    return result


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    r = run()
    print(json.dumps({k: r[k] for k in ("checks", "outcome_under_v3_criteria", "expected_geometric", "es99", "model_used")}, indent=1, default=str))


if __name__ == "__main__":
    main()
