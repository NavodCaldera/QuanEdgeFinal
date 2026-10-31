"""Mandate v6: monthly dynamic EWMA risk parity plus a yield-curve recession overlay (PLAN.md section 13h).

Core: the v5 strategy exactly (quanedge.comparison.dynamic_parity_path, lambda 0.97, 750 days,
month-end decisions, first target from the first 500 return days).
Overlay, decided at each month-end close from data through that close only:
  warning      the 10-year Treasury minus 3-month T-bill spread (monthly mean, bond-equivalent T-bill yield)
               was negative in at least one of the last 24 months, including the decision month;
  confirmation SPY's month-end close is below the mean of its last 12 month-end closes.
  ON when warning and confirmation hold: hold the month's target with SPY and XLE halved; the freed
  weight is cash earning 0%. OFF at the first month-end with SPY above its 12-month mean.
Every number has a stated reason in section 13h. Retrospective: designed after the data were seen.

    python -m quanedge.recession_overlay      # writes results/recession-overlay-r1/
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from . import config
from .config import TICKERS
from .portfolio import canonical_weights, weight_hash, es, tail_weights, return_check, real_return
from .backtest import assess, model_pass, verdict
from .results import digest
from .risk import rolling_forecasts, save_forecasts
from .comparison import dynamic_parity_path
from .overlay_eval import window_stress, path_summary, METHODS

TAG = "prereg-v6"
OUT = "recession-overlay-r1"
OVERLAY = {"warning": "10y minus 3m T-bill (bond-equivalent) monthly mean < 0 in any of the last 24 months",
           "confirmation": "SPY month-end close < mean of last 12 month-end closes",
           "action": "SPY and XLE halved, freed weight held as cash at 0%",
           "exit": "first month-end with SPY month-end close > its 12-month mean",
           "warning_months": 24, "trend_months": 12, "cut": 0.5, "cash_rate": 0.0}
LABEL = ("Mandate v6 (prereg-v6): v5 strategy plus a pre-registered recession overlay; designed in a session "
         "that had seen the 2005-2026 data, so a retrospective portfolio evaluation, not an untouched test.")


def bond_equivalent(discount_pct):
    """DTB3 discount-basis quote (percent) to bond-equivalent yield (percent), 91-day bill."""
    d = discount_pct/100
    return 100*365*d/(360-91*d)


def _fred(name):
    s = pd.read_csv(config.DATA_DIR/"raw"/f"fred_{name}.csv", index_col=0, parse_dates=True).iloc[:, 0]
    return pd.to_numeric(s, errors="coerce")


def term_spread(end):
    """Monthly mean of DGS10 minus bond-equivalent DTB3, percentage points, data through `end`."""
    g, b = _fred("DGS10").loc[:end], _fred("DTB3").loc[:end]
    return (g.resample("ME").mean() - bond_equivalent(b).resample("ME").mean()).dropna()


def overlay_flags(decisions, spy_close, spread, warning_months=24, trend_months=12):
    """ON/OFF state at each decision date using only data through that date."""
    monthly = spy_close.resample("ME").last()
    state, flags = False, {}
    for d in decisions:
        m = d + pd.offsets.MonthEnd(0)
        past = monthly.loc[:m]          # month label m is the calendar month-end; its value is the close at d
        if len(past) < trend_months:
            flags[d] = False; continue
        below = bool(past.iloc[-1] < past.iloc[-trend_months:].mean())
        warn = bool((spread.loc[:m].iloc[-warning_months:] < 0).any())
        if state and not below:
            state = False
        elif not state and warn and below:
            state = True
        flags[d] = state
    return pd.Series(flags, dtype=bool)


def overlay_path(returns, prices, spread, cfg, use_overlay=True):
    """Daily path: base targets from the v5 strategy, modified at decision closes while the overlay is ON."""
    universe = cfg["universe"]; s = cfg["strategy"]
    base = dynamic_parity_path(returns[universe], s["rebalance"], s["ewma_lambda"], s["window"], s["min_history"], cfg["cost"])
    decisions = base.index[base.rebalanced]
    flags = overlay_flags(decisions, prices["SPY"], spread, OVERLAY["warning_months"], OVERLAY["trend_months"]) \
        if use_overlay else pd.Series(False, decisions)
    x = returns.loc[base.index, universe].to_numpy()
    tgt0 = base.iloc[0][[f"target_{t}" for t in universe]].to_numpy(float)
    # initial holdings are the first target bought at the close before the first path row (as dynamic_parity_path)
    pos, cash, on = tgt0.copy(), 0., False
    rows = []
    for i, d in enumerate(base.index):
        old = pos.sum() + cash; pos = pos*(1 + x[i]); nav = pos.sum() + cash; turnover = 0.
        if base.rebalanced.iloc[i]:
            on = bool(flags.get(d, False))
            tgt = base.iloc[i][[f"target_{t}" for t in universe]].to_numpy(float).copy()
            c = 0.
            if on:
                for t in ("SPY", "XLE"):
                    k = universe.index(t); c += tgt[k]*OVERLAY["cut"]; tgt[k] *= 1 - OVERLAY["cut"]
            turnover = float(np.abs(tgt - pos/nav).sum() + abs(c - cash/nav))
            pos, cash = tgt*nav, c*nav
        rows.append([nav/old - 1, turnover, bool(base.rebalanced.iloc[i]), on, cash/nav, *(pos/nav)])
    frame = pd.DataFrame(rows, index=base.index, columns=["return", "turnover", "rebalanced", "overlay_on", "cash", *universe])
    frame.insert(1, "wealth", (1 + frame["return"]).cumprod())
    for t in universe:
        frame[f"target_{t}"] = base[f"target_{t}"]
    for t in TICKERS:
        if t not in frame:
            frame[t] = 0.; frame[f"target_{t}"] = 0.
    return frame, flags


def strategy_hash(cfg):
    return digest({"mandate": "v6", "strategy": cfg["strategy"], "universe": cfg["universe"], "overlay": OVERLAY})


def held_target(row, cfg):
    """Effective target at a decision (ETF weights after the overlay; the remainder is cash)."""
    w = {t: float(row[f"target_{t}"]) for t in cfg["universe"]}
    if row["overlay_on"]:
        for t in ("SPY", "XLE"):
            w[t] *= 1 - OVERLAY["cut"]
    return canonical_weights({t: w.get(t, 0.) for t in TICKERS}) if not row["overlay_on"] else {t: w.get(t, 0.) for t in TICKERS}


def expected_geometric(returns, w, cfg):
    from .portfolio import estimates
    mu, cov = estimates(returns[TICKERS], cfg)
    v = np.array([w[t] for t in TICKERS])            # cash (1 - sum v) earns 0%
    net = float(v@mu - cfg.get("expected_annual_turnover", 0)*cfg["cost"])
    return float(np.expm1(np.log1p(net) - v@cov@v/2))


def evaluate(returns, prices, cfg, data_hash, out):
    value = cfg["value"]
    spread = term_spread(cfg["snapshot_end"])
    path, flags = overlay_path(returns, prices, spread, cfg)
    path.to_csv(out/"path.csv", float_format="%.10g")
    sh = strategy_hash(cfg)
    dec = path.loc[path.rebalanced]
    targets = [held_target(r, cfg) for _, r in dec.iterrows()]
    c1 = bool(all(min(w.values()) >= -1e-12 and sum(w.values()) <= 1 + 1e-9 and
                  all(w[t] == 0 for t in TICKERS if t not in cfg["universe"]) for w in targets))
    latest = held_target(path.iloc[-1] if path.rebalanced.iloc[-1] else dec.iloc[-1], cfg)

    print("Rolling forecasts for the v6 path", flush=True)
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
        s["assumption"] = "v6 path as run (overlay state included), from the scenario start close; zero cost"
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
    on_months = [str(d.date())[:7] for d, v in flags.items() if v]
    base_path, _ = overlay_path(returns, prices, spread, cfg, use_overlay=False)
    evaluation = slice(cfg["evaluation_start"], cfg["snapshot_end"])
    return {"strategy_hash": sh, "start": str(path.index[0].date()), "latest_target": latest,
            "latest_overlay_on": bool(path.overlay_on.iloc[-1]), "checks": checks, "outcome": verdict(checks),
            "es99": {"path": path_es, "path_usd": path_es*value, "latest_target_estimation": latest_es,
                     "latest_target_usd": latest_es*value, "budget": cfg["es_budget"]},
            "expected_geometric_latest_target": geo, "expected_real_latest_target": real_return(geo, cfg["inflation"]),
            "realised": path_summary(path["return"]), "realised_evaluation_period": path_summary(path.loc[evaluation, "return"]),
            "v5_core_same_period": path_summary(base_path["return"]),
            "overlay_months_on": on_months, "average_cash": float(path.cash.mean()),
            "turnover_per_year": float(path.turnover.sum()/years),
            "stress": stress, "validation": assessments, "fit_failures": failures,
            "model_used": cfg["primary"] if model_pass(primary) else cfg["challenger"] if model_pass(challenger) else None}


def run(out=None, tag=TAG):
    from .data import load_clean_prices
    cfg = config.frozen_policy(tag)
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna()
    out = out or config.RESULTS_DIR/OUT; out.mkdir(parents=True, exist_ok=True)
    data_hash = hashlib.sha256((config.ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()
    result = evaluate(returns, prices, cfg, data_hash, out)
    raw = {n: hashlib.sha256((config.DATA_DIR/"raw"/f"fred_{n}.csv").read_bytes()).hexdigest() for n in ("DGS10", "DTB3")}
    meta = {"task": "PORT-029", "prereg_tag": tag, "label": LABEL, "evaluation_label": "retrospective portfolio evaluation",
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "data_hash": data_hash,
            "macro_hashes": raw, "config_hash": digest(cfg), "strategy": cfg["strategy"], "overlay": OVERLAY,
            "strategy_hash": result["strategy_hash"],
            "departures_from_v5_evaluation": [
                "cash is held while the overlay is ON (C1 allows ETF weights summing below 1, the rest cash at 0%)",
                "C2 and C3 use the latest effective target including any cash",
                "forecasts and C4 use the v6 path's own daily returns, with the v6 strategy hash on every row"]}
    write = lambda p, o: p.write_text(json.dumps(o, indent=2, default=lambda x: x.item() if hasattr(x, "item") else str(x),
                                                  allow_nan=True)+"\n", encoding="utf-8")
    write(out/"summary.json", result); write(out/"metadata.json", meta)
    return result


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    r = run()
    print(json.dumps({k: r[k] for k in ("checks", "outcome", "es99", "expected_real_latest_target", "model_used",
                                        "overlay_months_on", "realised", "v5_core_same_period")}, indent=1, default=str))


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- read-only access for the dashboard
class OverlayEvidenceError(RuntimeError):
    pass


def load_saved(directory=None):
    """Saved v6 evidence, refused if the price file or any forecast row's strategy hash has changed."""
    from .risk import load_forecasts
    d = directory or config.RESULTS_DIR/OUT
    meta = json.loads((d/"metadata.json").read_text()); summary = json.loads((d/"summary.json").read_text())
    data_hash = hashlib.sha256((config.ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()
    if meta["data_hash"] != data_hash:
        raise OverlayEvidenceError("price file differs from the one used for results/recession-overlay-r1")
    fc = load_forecasts(d/"forecasts.csv")
    if (fc["weight_hash"] != meta["strategy_hash"]).any():
        raise OverlayEvidenceError("a forecast row carries a different strategy hash")
    path = pd.read_csv(d/"path.csv", index_col=0, parse_dates=True)
    return {"meta": meta, "summary": summary, "path": path, "forecasts": fc}


def core_path(cfg=None):
    """v5 core path on the same dates (overlay off), recomputed from the frozen prices."""
    from .data import load_clean_prices
    cfg = cfg or config.frozen_policy(TAG)
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna()
    return overlay_path(returns, prices, term_spread(cfg["snapshot_end"]), cfg, use_overlay=False)[0]


def signals(end="2026-09-30"):
    """Monthly signal table to `end`: term spread, warning, SPY vs its 12-month mean, Sahm rule (backup, 1-month lag)."""
    from .data import load_clean_prices
    spread = term_spread(end)
    spy = load_clean_prices().loc[:end, "SPY"].resample("ME").last()
    out = pd.DataFrame({"spread": spread}).loc["2005":]
    out["warning"] = (spread < 0).astype(int).rolling(OVERLAY["warning_months"], min_periods=1).max().astype(bool).reindex(out.index)
    out["spy"] = spy; out["spy_12m_mean"] = spy.rolling(OVERLAY["trend_months"]).mean()
    out["below_trend"] = out.spy < out.spy_12m_mean
    u = pd.read_csv(config.ROOT/"context/fred/UNRATE.csv", index_col=0, parse_dates=True).iloc[:, 0]
    u.index = u.index + pd.offsets.MonthEnd(0); u = u.ffill()
    u3 = u.rolling(3).mean(); gap = u3 - pd.concat([u3.shift(k) for k in range(13)], axis=1).min(axis=1)
    out["unemployment"] = u.reindex(out.index); out["sahm_gap"] = gap.shift(1).reindex(out.index)
    out["sahm"] = out.sahm_gap >= .5
    c = pd.to_numeric(pd.read_csv(config.ROOT/"context/fred/BAA10Y.csv", index_col=0, parse_dates=True).iloc[:, 0], errors="coerce")
    out["credit_spread"] = c.loc[:end].resample("ME").last().reindex(out.index)
    return out


def episodes(path, core):
    """One row per overlay episode: first and last month-end decision ON, the decision that
    switched it off, and the v6 and v5-core returns from the entry close to the exit close."""
    on = path.overlay_on.astype(bool); dec = path.index[path.rebalanced.astype(bool)]
    flags = on.loc[dec]; rows = []; start = None
    for d, f in flags.items():
        if f and start is None:
            start = d
        elif not f and start is not None:
            rows.append((start, d)); start = None
    if start is not None:
        rows.append((start, path.index[-1]))
    out = []
    for a, b in rows:
        r6 = float((1 + path["return"].loc[a:b].iloc[1:]).prod() - 1)
        r5 = float((1 + core["return"].loc[a:b].iloc[1:]).prod() - 1)
        out.append({"on": a.date(), "off": b.date(), "months": int(((dec > a) & (dec <= b)).sum()),
                    "v6_return": r6, "core_return": r5, "difference": r6 - r5})
    return pd.DataFrame(out)


def safeguard_backtest(fc, path, strategy_hash, alpha=.99):
    """Disclosed safeguard: in calendar months the overlay switches, the daily limit is the higher
    of the GARCH-EVT and FHS forecasts; other months use GARCH-EVT. Recomputed from saved forecasts."""
    from .backtest import assess
    on = path.overlay_on.astype(bool)
    switch_months = set(path.index[on != on.shift(1, fill_value=on.iloc[0])].to_period("M"))
    level = f"{alpha*100:g}"
    frame = fc.copy()
    in_switch = frame.index.to_period("M").isin(list(switch_months))
    frame[f"var_safeguard_{level}"] = np.where(in_switch, np.fmax(frame[f"var_garch_evt_{level}"], frame[f"var_fhs_{level}"]),
                                               frame[f"var_garch_evt_{level}"])
    res = assess(frame, strategy_hash, "safeguard", alpha)
    res["switch_days"] = int(in_switch.sum())
    return res


def warning_expiry(sig):
    """Month-end after which the yield-curve warning lapses (last inverted month + 24 months), or None."""
    inv = sig.index[sig.spread < 0]
    return None if not len(inv) else (inv[-1] + pd.offsets.MonthEnd(OVERLAY["warning_months"])).date()
