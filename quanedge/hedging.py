"""Long-only risk mitigation: exploratory mandate-change comparison (task PORT-004).

Not part of the frozen prereg-v1 run, and nothing there reads these outputs. All
results are retrospective portfolio evaluations; the variants below were fixed in
code before the first run and are recorded in metadata.json.

1. Crisis-diversifier sleeve: XLE 0/5/10% funded from SPY (inflation-shock hedge).
2. Scenario-robust selection: frozen return-maximising CVaR LP plus a cap on the
   buy-and-hold loss in each named stress scenario. The scenarios are crises that
   are already known, so this is fitted to them by construction.
3. Volatility targeting: scale the equity sleeve down when EWMA volatility exceeds
   the expanding-window volatility; freed weight goes to AGG, then GLD, within caps.

    python -m quanedge.hedging            # writes results/hedging-r1/
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yaml
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, eye, hstack, vstack
from . import config
from .config import TICKERS
from .portfolio import estimates, canonical_weights, weight_hash, es, feasible, bounds, tail_weights
from .stress import SCENARIOS, hypothetical
from .dynamic import simulate, metrics, portfolios

LABEL = ("Exploratory mandate-change comparison, added after preregistration; "
         "retrospective portfolio evaluation, not part of the frozen analytical run.")
EQUITY = ["SPY", "EFA", "EEM", "XLE", "XLK"]
XLE_LEVELS = (.05, .10)
SCENARIO_CAPS = (.15, .12)
EWMA_LAMBDA = .94            # RiskMetrics daily decay
REVIEW = "W"                 # volatility target re-checked at each week's last trading day
MIN_EQUITY_CHANGE = .05      # trade the overlay only when equity weight moves at least 5 points
MIN_HISTORY = 252


def with_xle(w, level):
    if w["SPY"] < level-1e-12:
        return None
    return canonical_weights(dict(w, SPY=w["SPY"]-level, XLE=w["XLE"]+level))


def scenario_shocks(prices, train):
    out = {n: (prices.loc[b]/prices.shift(1).loc[a]-1)[TICKERS].to_numpy() for n, (a, b) in SCENARIOS.items()}
    hyp = hypothetical(train, {t: 1/7 for t in TICKERS})
    out["Hypothetical"] = np.array([hyp["shocks"][t] for t in TICKERS])
    return out


def robust(returns, cfg, shocks, cap):
    """Frozen selection LP with one extra row per scenario: -w.shock <= cap."""
    x = returns[TICKERS].to_numpy(); n, k = x.shape; mu, _ = estimates(returns, cfg)
    equity = np.array([1, 1, 1, 0, 0, 1, 1.]); tail = 1/(n*.01)
    scen = hstack([csr_matrix(-x), csr_matrix(-np.ones((n, 1))), -eye(n)], format="csr")
    risk = np.r_[np.zeros(k), 1, np.full(n, tail)]
    stress = np.array([np.r_[-s, np.zeros(n+1)] for s in shocks.values()])
    A = vstack([scen, csr_matrix(np.r_[equity, np.zeros(n+1)][None, :]), csr_matrix(risk[None, :]),
                csr_matrix(stress)], format="csr")
    b = np.r_[np.zeros(n), cfg["equity_cap"], cfg["es_budget"], np.full(len(shocks), cap)]
    eq = np.r_[np.ones(k), np.zeros(n+1)][None, :]; vb = bounds(cfg)+[(None, None)]+[(0, None)]*n
    sol = linprog(np.r_[-mu, np.zeros(n+1)], A_ub=A, b_ub=b, A_eq=eq, b_eq=[1], bounds=vb, method="highs")
    if not sol.success:
        return {"status": "infeasible", "reason": sol.message, "weights": None}
    A = vstack([A, csr_matrix(np.r_[-mu, np.zeros(n+1)][None, :])]); b = np.r_[b, sol.fun+1e-8]
    sol = linprog(risk, A_ub=A, b_ub=b, A_eq=eq, b_eq=[1], bounds=vb, method="highs")
    if not sol.success:
        return {"status": "infeasible", "reason": sol.message, "weights": None}
    w = canonical_weights(dict(zip(TICKERS, sol.x[:k])))
    if not feasible(w, cfg):
        return {"status": "failed", "reason": "rounded weights violate constraints", "weights": None}
    return {"status": "ok", "weights": w}


def scaled(base, k, cfg):
    """Equity sleeve times k; freed weight to AGG up to its cap, then GLD; any rest stays in equity."""
    w = dict(base); freed = sum(base[t] for t in EQUITY)*(1-k)
    for t in EQUITY:
        w[t] = base[t]*k
    for t, cap in (("AGG", cfg["agg_max"]), ("GLD", min(cfg["gold_cap"], cfg["single_cap"]))):
        add = min(freed, max(cap-w[t], 0)); w[t] += add; freed -= add
    if freed > 1e-12:                       # caps bind: return the remainder pro rata to equity
        held = sum(base[t] for t in EQUITY)
        for t in EQUITY:
            w[t] += freed*base[t]/held
    return canonical_weights(w)


def vol_target(returns, base, cfg):
    """Same accounting as dynamic.simulate; overlay decisions use returns through that close."""
    cost, drift = cfg["cost"], cfg["drift"]
    port = returns[TICKERS]@np.array([base[t] for t in TICKERS])
    ewma = np.sqrt((port**2).ewm(alpha=1-EWMA_LAMBDA, adjust=False).mean()).to_numpy()
    longrun = port.expanding(MIN_HISTORY).std().to_numpy()
    review = set(returns.index.to_series().groupby(returns.index.to_period(REVIEW)).max())
    base_equity = sum(base[t] for t in EQUITY)
    target = base; positions = np.array([base[t] for t in TICKERS]); nav = peak = 1.; rows = []
    dates = returns.index
    for i, (date, row) in enumerate(returns[TICKERS].iterrows()):
        old = nav; positions = positions*(1+row.to_numpy()); gross = positions.sum()
        quarter_end = i == len(dates)-1 or dates[i+1].quarter != date.quarter
        retarget = False; k = None
        if date in review and np.isfinite(longrun[i]):
            k = min(1., longrun[i]/ewma[i])
            proposal = scaled(base, k, cfg)
            if abs(sum(proposal[t]-target[t] for t in EQUITY)) >= MIN_EQUITY_CHANGE-1e-12 or (k == 1 and target != base):
                target, retarget = proposal, True
        w = np.array([target[t] for t in TICKERS]); current = positions/gross; turnover = 0.
        if retarget or quarter_end or np.max(abs(current-w)) > drift:
            turnover = float(np.abs(w-current).sum()); positions = w*gross*(1-cost*turnover)
        nav = float(positions.sum()); peak = max(peak, nav)
        equity_share = sum(target[t] for t in EQUITY)
        basis = "base" if target == base else f"equity {equity_share:.3f} of {base_equity:.3f}"
        rows.append((date, nav/old-1, nav, 1-nav/peak, turnover, None, k, basis, *w))
    cols = ["date", "return", "wealth", "decline", "turnover", "band", "scale", "basis", *TICKERS]
    return pd.DataFrame(rows, columns=cols).set_index("date")


def extra(path, w, shocks):
    loss = -path["return"].to_numpy()
    out = {"realised_es99": float(tail_weights(loss)@loss)}
    if w is not None:
        for name, s in shocks.items():
            out[f"buy_hold_{name}_loss"] = float(-np.array([w[t] for t in TICKERS])@s)
    return out


def run(out=None):
    from .data import load_clean_prices
    cfg = config.frozen_policy("prereg-v1")       # mandate v1 comparison
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna(); train = returns.loc[:cfg["training_end"]]
    shocks = scenario_shocks(prices, train)
    out = out or config.RESULTS_DIR/"hedging-r1"; out.mkdir(parents=True, exist_ok=True)
    bases = portfolios(returns, cfg)
    static, overlay = {}, {}
    for name in ("A1_min_cvar", "selected"):
        w, c = bases[name]; static[name] = (w, c)
        for level in XLE_LEVELS:
            v = with_xle(w, level)
            static[f"{name}+XLE{level:.0%}"] = (v, c) if v else (None, c)
    for cap in SCENARIO_CAPS:
        r = robust(returns, cfg, shocks, cap)
        static[f"scenario_cap_{cap:.0%}"] = (r["weights"], cfg)
    for name in ("A1_min_cvar", "selected", "open_bounds_es2.5"):
        overlay[name] = bases[name]
    rows, hashes = [], {}
    for name, (w, c) in static.items():
        if w is None:
            rows.append({"portfolio": name, "technique": "static", "status": "infeasible"}); continue
        hashes[name] = {"weights": w, "weight_hash": weight_hash(w)}
        path = simulate(returns, w, c, "static"); path.to_csv(out/f"{name}__static.csv", float_format="%.10g")
        rows.append({"portfolio": name, "technique": "static", "status": "ok", **metrics(path, cfg["spending"]),
                     **extra(path, w, shocks), "es99_weights": es(returns[TICKERS].to_numpy(), w)})
    for name, (w, c) in overlay.items():
        path = vol_target(returns, w, c); path.to_csv(out/f"{name}__vol_target.csv", float_format="%.10g")
        rows.append({"portfolio": name, "technique": "vol_target", "status": "ok", **metrics(path, cfg["spending"]),
                     **extra(path, None, shocks), "share_weeks_scaled": float((path.basis != "base").mean())})
    table = pd.json_normalize(rows); table.to_csv(out/"comparison.csv", index=False, float_format="%.6g")
    meta = {"label": LABEL, "evaluation_label": "retrospective portfolio evaluation", "task": "PORT-004",
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_returns_sha256": hashlib.sha256(returns.to_numpy().tobytes()).hexdigest(),
            "period": [str(returns.index[0].date()), str(returns.index[-1].date())],
            "portfolios": hashes, "xle_levels": XLE_LEVELS, "scenario_caps": SCENARIO_CAPS,
            "scenario_shocks": {k: dict(zip(TICKERS, v.tolist())) for k, v in shocks.items()},
            "ewma_lambda": EWMA_LAMBDA, "review": REVIEW, "min_equity_change": MIN_EQUITY_CHANGE,
            "min_history": MIN_HISTORY,
            "notes": ["scenario-robust weights use full-sample estimates and crises already observed",
                      "volatility overlay only de-risks (scale <= 1); weights stay within the base portfolio's bounds",
                      "static paths: quarterly or 5-point drift rebalancing at 5 bp, as portfolio.replay"]}
    (out/"metadata.json").write_text(json.dumps(meta, indent=2)+"\n", encoding="utf-8")
    return table


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60)
    print(run().to_string())


if __name__ == "__main__":
    main()
