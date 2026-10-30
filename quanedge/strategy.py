"""Mandate v5 recommendation: dynamic EWMA risk parity re-estimated each month-end (PLAN.md 13g).

The method, not a fixed weight vector, is the recommendation. Two identities are kept apart:
- weights / weight_hash: the latest target (the allocation to hold now). Risk table, historical
  attribution, hypothetical and reverse stress and bootstrap intervals describe these holdings.
- forecast_hash (strategy hash): the strategy itself. The sequential backtest (C4), path ES (C2)
  and path stresses (C5) use the strategy's own daily path, which changes weights monthly.
"""
import numpy as np
import pandas as pd
from .config import TICKERS
from .comparison import dynamic_parity_path
from .portfolio import (canonical_weights, weight_hash, feasible, es, tail_weights, estimates,
                        return_check, real_return, replay, kpis, money_weighted)
from .results import digest
from .stress import SCENARIOS, hypothetical, attribution
from .risk import fit_models, risk_table, rolling_forecasts, save_forecasts

METHODS = ["historical", "normal", "evt", "fhs", "garch_evt"]


def settings(cfg):
    return {**cfg["strategy"], "universe": list(cfg["universe"]),
            "risk_parity": "Spinu convex form, equal volatility contributions"}


def strategy_hash(cfg):
    return digest(settings(cfg))


def path(returns, cfg):
    """Daily strategy path over all seven tickers (excluded ETFs held at zero)."""
    s = cfg["strategy"]
    p = dynamic_parity_path(returns[list(cfg["universe"])], s["rebalance"], s["ewma_lambda"], s["window"],
                            s["min_history"], cfg["cost"])
    for t in TICKERS:
        if t not in p:
            p[t] = 0.; p["target_"+t] = 0.
    return p[["return", "wealth", "turnover", "rebalanced", *TICKERS, *[f"target_{t}" for t in TICKERS]]]


def targets(p):
    """Every target in force: the first and each re-estimation."""
    rows = p.loc[p.rebalanced | (p.index == p.index[0]), [f"target_{t}" for t in TICKERS]]
    return rows.rename(columns=lambda c: c[7:])


def latest_target(p):
    return canonical_weights({t: float(p[f"target_{t}"].iloc[-1]) for t in TICKERS})


def reserve_path(r, cfg):
    """Strategy returns with the 1 January cash reserve (fraction of the initial fund) withdrawn
    before that day's return, as portfolio.replay does for fixed weights. Starts on the first
    trading day of the first full calendar year, so the reserve is not drawn twice within days."""
    first = r.index[r.index.year > r.index[0].year][0] if r.index[0].month == 12 else r.index[0]
    r = r.loc[first:]; nav = 1.; year = -1; rows = []
    base = cfg["reserve_initial"]/cfg["fund_value"]
    for i, (date, x) in enumerate(r.items()):
        draw = 0.
        if i == 0 or r.index[i-1].year != date.year:
            year += 1; draw = min(nav, base*(1+cfg["reserve_growth"])**year); nav -= draw
        old = nav; nav = nav*(1+x) if nav > 0 else 0.
        rows.append((date, nav/old-1 if old > 0 else 0., nav, 0., draw))
    return pd.DataFrame(rows, columns=["date", "return", "wealth", "turnover", "spending"]).set_index("date")


def path_stress(p, returns, value):
    """Each scenario on the strategy path from the scenario start close, with dollar P&L by ETF
    (holdings at the prior close times that day's ETF return)."""
    rows = []
    for name, (start, end) in SCENARIOS.items():
        w = p.wealth.loc[start:end]
        if w.empty or str(w.index[0].date()) != start or str(w.index[-1].date()) != end:
            rows.append({"scenario": name, "status": "incomplete data coverage"}); continue
        growth = w/w.iloc[0]; dd = growth/growth.cummax()-1; ret = float(growth.iloc[-1]-1)
        days = w.index[1:]; prior = p.index[p.index.get_indexer(days)-1]
        held = p.loc[prior, TICKERS].to_numpy()*(p.wealth.loc[prior].to_numpy()/w.iloc[0])[:, None]
        pnl = (held*returns.loc[days, TICKERS].to_numpy()).sum(axis=0)*value
        rows.append({"scenario": name, "status": "ok", "start": start, "end": end, "return": ret,
                     "loss_usd": -value*ret, "drawdown": float(dd.min()),
                     "breach": bool(-ret > .20 or -dd.min() > .20),
                     "contributions_usd": dict(zip(TICKERS, (-pnl).tolist())),
                     "assumption": "strategy path as run (monthly targets, drift between), from the scenario start close; zero cost"})
    return rows


def expected(returns, w, cfg):
    mu, cov = estimates(returns[TICKERS], cfg)
    v = np.array([w[t] for t in TICKERS]); net = float(v@mu - cfg.get("expected_annual_turnover", 0)*cfg["cost"])
    variance = float(v@cov@v)
    return net, float(np.expm1(np.log1p(net) - variance/2)), float(np.sqrt(variance))


def evaluate(cfg, prices, returns, macro, out, meta):
    """C1-C5 for the strategy (PLAN.md 13g) and the run artifacts of the 'selected' folder."""
    from .backtest import assess, model_pass
    from .pipeline import write_json
    folder = out/"selected"; folder.mkdir(parents=True)
    value = cfg["value"]; p = path(returns, cfg); sh = strategy_hash(cfg)
    w = latest_target(p); wh = weight_hash(w); history = targets(p)
    print(f"Evaluating dynamic strategy {sh[:8]} (latest target {wh[:8]})", flush=True)
    write_json(folder/"weights.json", dict(weights=w, weight_hash=wh, strategy_hash=sh, strategy=settings(cfg),
                                           effective_date=cfg["snapshot_end"], estimation_end=cfg["snapshot_end"],
                                           note="latest monthly target; the method re-estimates it each month-end"))
    history.to_csv(folder/"targets.csv", float_format="%.10g")
    p.to_csv(folder/"path.csv", float_format="%.10g")
    p[["return", "wealth", "turnover"]].to_csv(folder/"performance.csv")
    draw = reserve_path(p["return"], cfg); draw.to_csv(folder/"spending.csv")
    benchmark = replay(returns, canonical_weights({"SPY": .4, "AGG": .6}), cfg["cost"], cfg["drift"])["return"]
    performance = kpis(p["return"], macro.rf_daily_effective.reindex(returns.index), returns.SPY, benchmark)
    performance["money_weighted_return"] = money_weighted(draw)
    performance["period_start"] = str(p.index[0].date())

    logs = np.log1p(returns)
    models = fit_models(logs, w, n_sim=cfg["n_sim"], seed=cfg["seed"])
    table = risk_table(models, value=value); table.to_csv(folder/"risk.csv", index=False)
    print("  rolling forecasts on the strategy path", flush=True)
    forecasts = rolling_forecasts(np.log1p(p["return"]), methods=METHODS, window=cfg["window"], refit=cfg["refit"])
    failures = forecasts.attrs.get("fit_failures", [])
    forecasts["weight_hash"] = sh; forecasts["data_hash"] = meta["data_hash"]
    forecasts["evaluation_label"] = "sequential risk-forecast evaluation"
    forecasts["allocation_cutoff"] = "each month-end decision close"
    forecasts["config_hash"] = meta["config_hash"]; forecasts["code_rev"] = meta["code_rev"]
    save_forecasts(forecasts, folder/"forecasts.csv")
    assessments = [assess(forecasts, sh, m, a, cfg["evaluation_start"], cfg["snapshot_end"])
                   for m in METHODS for a in (.90, .95, .99)]
    primary = next(v for v in assessments if v["method"] == cfg["primary"] and v["alpha"] == .99)
    challenger = next(v for v in assessments if v["method"] == cfg["challenger"] and v["alpha"] == .99)

    stress = path_stress(p, returns, value)
    hyp = hypothetical(returns.loc[:cfg["training_end"]], w, value)
    hyp["assumption"] += "; applied to the latest target"
    loss = -p["return"].to_numpy(); path_es = float(tail_weights(loss)@loss)
    latest_es = es(returns, w); arithmetic, geometric, vol = expected(returns, w, cfg)
    gfc = next(s for s in stress if s["scenario"] == "GFC")
    checks = {"C1": bool(all(feasible(dict(zip(TICKERS, row)), cfg) for row in history.to_numpy())),
              "C2": bool(path_es <= cfg["es_budget"]+1e-6 and latest_es <= cfg["es_budget"]+1e-6),
              "C3": return_check(geometric, cfg),
              "C4": bool(model_pass(primary) or model_pass(challenger)),
              "C5": bool(all(s.get("status") == "ok" for s in stress) and
                         all(s["loss_usd"] <= cfg["drawdown_limit"]*value for s in stress) and
                         -gfc.get("drawdown", -1) <= cfg["drawdown_limit"])}
    years = (p.index[-1]-p.index[0]).days/365.25
    return {"status": "ok", "kind": "dynamic strategy", "strategy": settings(cfg), "forecast_hash": sh,
            "weights": w, "weight_hash": wh, "estimation_end": cfg["snapshot_end"],
            "expected_arithmetic": arithmetic, "expected_geometric": geometric, "volatility": vol,
            "expected_real": real_return(geometric, cfg["inflation"]),
            "es99": {"path": path_es, "path_usd": path_es*value, "latest_target": latest_es,
                     "latest_target_usd": latest_es*value, "budget": cfg["es_budget"]},
            "checks": checks, "policy": cfg, "performance": performance,
            "realised_real_cagr": real_return(performance["cagr"], cfg["inflation"]),
            "stress": stress+[hyp], "attribution": attribution(returns, w, value=value),
            "policy_es99_usd": latest_es*value, "validation": assessments,
            "model_used": cfg["primary"] if model_pass(primary) else cfg["challenger"] if model_pass(challenger) else None,
            "model_parameters": {n: {"status": m.status, "params": m.params} for n, m in models.items()},
            "fit_failures": failures, "rebalances": int(p.rebalanced.sum()),
            "turnover_per_year": float(p.turnover.sum()/years),
            "target_range": {t: [float(history[t].min()), float(history[t].max())] for t in cfg["universe"]},
            "risk_replay": "risk table: latest target at fixed weights; backtest: the strategy's own daily path",
            "c2_c5_basis": "C2 path ES99 and latest-target estimation-sample ES99; C5 strategy path from each scenario start",
            "evaluation_label": "retrospective portfolio evaluation"}
