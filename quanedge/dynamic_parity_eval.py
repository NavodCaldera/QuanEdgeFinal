"""Candidates v4d/v4e: dynamic EWMA risk parity, monthly and weekly (task PORT-015, PLAN.md section 13e).

Pre-registered at tag prereg-v4de before any risk forecast on these strategies was computed.
Evaluated under the v3 policy frozen at prereg-v3; the v3 run and verdict are unchanged.

    python -m quanedge.dynamic_parity_eval      # writes results/dynamic-parity-r1/
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from . import config
from .config import TICKERS
from .portfolio import canonical_weights, weight_hash, feasible, es, tail_weights, estimates, return_check, real_return
from .backtest import assess, model_pass, verdict
from .results import digest
from .risk import rolling_forecasts, save_forecasts
from .dynamic import simulate
from .comparison import dynamic_parity_path
from .overlay_eval import window_stress, path_summary, METHODS

LABEL = ("Pre-registered candidates v4d/v4e (prereg-v4de) under v3 criteria; designed after the data were seen, "
         "so not the v3 verdict and not an untouched test.")
SETTINGS = {"type": "dynamic_ewma_risk_parity", "ewma_lambda": .97, "window": 750, "min_history": 500,
            "risk_parity": "Spinu convex form, equal volatility contributions", "universe": ["SPY", "AGG", "GLD", "XLE"]}
CANDIDATES = {"v4d_monthly": "M", "v4e_weekly": "W"}
BASE_RUN = "final-v3-20261030"


def strategy_hash(name, freq):
    return digest({"candidate": name, "rebalance": freq, **SETTINGS})


def as_weights(row, prefix=""):
    return canonical_weights({t: float(row.get(prefix+t, 0.)) for t in TICKERS})


def expected_geometric(returns, w, cfg):
    """Frozen-estimator expected geometric return of fixed weights w (as portfolio.target_selection)."""
    mu, cov = estimates(returns[TICKERS], cfg)
    v = np.array([w[t] for t in TICKERS]); net = float(v@mu - cfg.get("expected_annual_turnover", 0)*cfg["cost"])
    return float(np.expm1(np.log1p(net) - v@cov@v/2))


def evaluate(name, freq, returns, cfg, data_hash, out):
    universe = SETTINGS["universe"]; value = cfg["value"]
    path = dynamic_parity_path(returns[universe], freq, SETTINGS["ewma_lambda"], SETTINGS["window"],
                               SETTINGS["min_history"], cfg["cost"])
    for t in TICKERS:
        if t not in path:
            path[t] = 0.; path["target_"+t] = 0.
    path.to_csv(out/f"{name}_path.csv", float_format="%.10g")
    sh = strategy_hash(name, freq)
    targets = path.loc[path.rebalanced | (path.index == path.index[0]), [f"target_{t}" for t in TICKERS]]
    initial = as_weights(path.iloc[0], "target_"); latest = as_weights(path.iloc[-1], "target_")
    c1 = bool(all(feasible(dict(zip(TICKERS, row)), cfg) for row in targets.to_numpy()))

    print(f"Rolling forecasts for {name}", flush=True)
    forecasts = rolling_forecasts(np.log1p(path["return"]), methods=METHODS, window=cfg["window"], refit=cfg["refit"])
    failures = forecasts.attrs.get("fit_failures", [])
    forecasts["weight_hash"] = sh; forecasts["data_hash"] = data_hash
    forecasts["evaluation_label"] = "sequential risk-forecast evaluation"
    forecasts["allocation_cutoff"] = cfg["snapshot_end"]
    save_forecasts(forecasts, out/f"{name}_forecasts.csv")
    assessments = [assess(forecasts, sh, m, a, cfg["evaluation_start"], cfg["snapshot_end"])
                   for m in METHODS for a in (.90, .95, .99)]
    primary = next(v for v in assessments if v["method"] == cfg["primary"] and v["alpha"] == .99)
    challenger = next(v for v in assessments if v["method"] == cfg["challenger"] and v["alpha"] == .99)

    stress = window_stress(path, value)
    for s in stress:
        s["assumption"] = "strategy path as run, from the scenario start close; zero cost under v3"
    loss = -path["return"].to_numpy(); path_es = float(tail_weights(loss)@loss)
    latest_es = es(returns, latest); geo = expected_geometric(returns, latest, cfg)
    gfc = next(s for s in stress if s["scenario"] == "GFC")
    checks = {"C1": c1,
              "C2": bool(path_es <= cfg["es_budget"]+1e-6 and latest_es <= cfg["es_budget"]+1e-6),
              "C3": return_check(geo, cfg),
              "C4": bool(model_pass(primary) or model_pass(challenger)),
              "C5": bool(all(s.get("status") == "ok" for s in stress) and
                         all(s["loss_usd"] <= cfg["drawdown_limit"]*value for s in stress) and
                         -gfc["drawdown"] <= cfg["drawdown_limit"])}
    years = (path.index[-1]-path.index[0]).days/365.25
    evaluation = slice(cfg["evaluation_start"], cfg["snapshot_end"])
    return {"candidate": name, "rebalance": {"M": "month-end", "W": "week-end"}[freq], "strategy_hash": sh,
            "start": str(path.index[0].date()), "initial_target": initial, "latest_target": latest,
            "latest_target_hash": weight_hash(latest), "checks": checks, "outcome_under_v3_criteria": verdict(checks),
            "es99": {"path": path_es, "path_usd": path_es*value, "latest_target_estimation": latest_es,
                     "latest_target_usd": latest_es*value, "budget": cfg["es_budget"]},
            "expected_geometric_latest_target": geo, "expected_real_latest_target": real_return(geo, cfg["inflation"]),
            "realised": path_summary(path["return"]), "realised_evaluation_period": path_summary(path.loc[evaluation, "return"]),
            "rebalances": int(path.rebalanced.sum()), "turnover_per_year": float(path.turnover.sum()/years),
            "target_range": {t: [float(targets[f"target_{t}"].min()), float(targets[f"target_{t}"].max())] for t in universe},
            "stress": stress, "validation": assessments, "fit_failures": failures,
            "model_used": cfg["primary"] if model_pass(primary) else cfg["challenger"] if model_pass(challenger) else None}


def run(out=None):
    from .data import load_clean_prices
    cfg = config.frozen_policy("prereg-v3")
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna()
    out = out or config.RESULTS_DIR/"dynamic-parity-r1"; out.mkdir(parents=True, exist_ok=True)
    data_hash = hashlib.sha256((config.ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()
    results = {name: evaluate(name, freq, returns, cfg, data_hash, out) for name, freq in CANDIDATES.items()}
    wrec = canonical_weights(json.loads((config.RESULTS_DIR/BASE_RUN/"selected"/"weights.json").read_text())["weights"])
    parity = canonical_weights(json.loads((config.RESULTS_DIR/BASE_RUN/"A1_near_parity"/"weights.json").read_text())["weights"])
    start = min(r["start"] for r in results.values())
    results["comparison_fixed_weights"] = {k: path_summary(simulate(returns, w, cfg).loc[start:, "return"])
                                           for k, w in (("w_rec", wrec), ("static_parity", parity))}
    meta = {"task": "PORT-015", "prereg_tag": "prereg-v4de", "label": LABEL, "evaluation_label": "retrospective portfolio evaluation",
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "data_hash": data_hash,
            "config_hash": digest(cfg), "settings": SETTINGS,
            "strategy_hashes": {n: strategy_hash(n, f) for n, f in CANDIDATES.items()},
            "departures_from_fixed_weight_evaluation": [
                "risk forecasts use each strategy path's realised daily returns, not a fixed-weight replay",
                "C2 requires both the path's realised ES99 and the latest target's estimation-sample ES99 within budget",
                "C3 applies the frozen estimator to the latest target",
                "C5 uses the strategy path from each scenario start close, not buy-and-hold"]}
    write = lambda p, o: p.write_text(json.dumps(o, indent=2, default=lambda x: x.item() if hasattr(x, "item") else str(x),
                                                  allow_nan=True)+"\n", encoding="utf-8")
    write(out/"summary.json", results); write(out/"metadata.json", meta)
    return results


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    r = run()
    for name in CANDIDATES:
        print(name, json.dumps({k: r[name][k] for k in ("checks", "outcome_under_v3_criteria", "es99", "expected_real_latest_target", "model_used")}, default=str))


if __name__ == "__main__":
    main()
