"""Exploratory study: allocating SPY/XLE/AGG/GLD under mandate v2 by variance-based and other methods.

Each candidate goes through quanedge.pipeline.evaluate, so C1-C5 (including C4, the candidate's own
sequential FHS/GARCH-EVT forecasts) are computed exactly as in the official run. Heavy per-portfolio
artefacts go to a temporary folder; a compact table is written to results/four-etf-v2-r1/.
Retrospective: the owner has seen the full sample. Not part of a frozen run; no policy change.
Run from the repository root: python scripts/four_etf_v2_study.py
"""
import os, sys, json, hashlib, tempfile
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy.optimize import minimize
import quanedge.portfolio as qp
from quanedge import pipeline
from quanedge.config import TICKERS

FOUR = ["SPY", "XLE", "AGG", "GLD"]
cfg = yaml.safe_load(open("config/final.yaml"))          # mandate v2, frozen at prereg-v2
assert cfg.get("mandate") == "v2", "this study assumes mandate v2"
_bounds = qp.bounds
qp.bounds = lambda c: [b if t in FOUR else (0, 0) for t, b in zip(TICKERS, _bounds(c))]
IDX = [TICKERS.index(t) for t in FOUR]


def describe(w, x, c):
    """Expected nominal/real geometric return, volatility and ES99 with the frozen v2 estimator."""
    mu, cov = qp.estimates(x, c); v = np.array([w[t] for t in TICKERS])
    net = float(v @ mu - c["expected_annual_turnover"] * c["cost"]); var = float(v @ cov @ v)
    g = float(np.expm1(np.log1p(net) - var / 2))
    return {"status": "ok", "weights": w, "weight_hash": qp.weight_hash(w), "expected_arithmetic": net,
            "expected_geometric": g, "expected_real": qp.real_return(g, c["inflation"]),
            "volatility": var ** .5, "es99": qp.es(x[TICKERS].to_numpy(), w)}


def heuristic(x, c, kind):
    _, cov = qp.estimates(x, c); S = cov[np.ix_(IDX, IDX)]; s = np.sqrt(np.diag(S))
    if kind == "inverse_variance": raw = 1 / s ** 2
    elif kind == "inverse_volatility": raw = 1 / s
    else:  # equal risk contribution: each ETF supplies 1/4 of portfolio variance
        f = lambda w: np.sum((w * (S @ w) / (w @ S @ w) - .25) ** 2)
        sol = minimize(f, (1 / s) / (1 / s).sum(), bounds=[(0, 1)] * 4, method="SLSQP",
                       constraints={"type": "eq", "fun": lambda w: w.sum() - 1}, options={"ftol": 1e-15, "maxiter": 3000})
        if not sol.success: return {"status": "failed", "reason": sol.message, "weights": None}
        raw = sol.x
    w = qp.canonical_weights({t: raw[i] / raw.sum() for i, t in enumerate(FOUR)})
    return describe(w, x, c)


METHODS = {"inverse_variance": "Inverse variance (1/sigma^2)", "inverse_volatility": "Inverse volatility (1/sigma)",
           "risk_parity": "Risk parity (equal risk contribution)", "min_variance": "Minimum variance",
           "min_cvar": "Minimum CVaR99", "selected": "Mandate v2 rule (min CVaR99, 3% real target)",
           "max_sharpe": "Maximum Sharpe"}


def build(x, c):
    out = {}
    for k in METHODS:
        if k in ("inverse_variance", "inverse_volatility", "risk_parity"): out[k] = heuristic(x, c, k)
        else:
            r = qp.construct(x, c, k)
            out[k] = describe(r["weights"], x, c) if r.get("weights") else r
    return out


if __name__ == "__main__":
    prices, returns, macro = pipeline.load_inputs(cfg)
    train = returns.loc[:cfg["training_end"]]
    full, trained = build(returns, cfg), build(train, cfg)
    meta = {"data_hash": hashlib.sha256(Path("data/clean/prices_clean.csv").read_bytes()).hexdigest(),
            "config_hash": pipeline.digest(cfg), "code_rev": pipeline.git("rev-parse", "HEAD")}
    rows, cache = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for k, label in METHODS.items():
            cand = full[k]
            if cand.get("weights") is None:
                rows.append({"method": label, "weights": cand.get("reason", "failed")}); continue
            res = pipeline.evaluate(k, cand, cfg, prices, returns, macro, Path(tmp), meta, cache)
            v = {(a["method"], a["alpha"]): a for a in res["validation"]}
            fhs, ge = v[("fhs", .99)], v[("garch_evt", .99)]
            st = {s["scenario"]: s for s in res["stress"]}
            tw = trained[k].get("weights") or {}
            rows.append({
                "method": label,
                "weights (2005-2026 estimate)": " / ".join(f"{t} {100*cand['weights'][t]:.0f}" for t in FOUR if cand["weights"][t] > 5e-4),
                "weights (2005-2016 estimate)": " / ".join(f"{t} {100*tw[t]:.0f}" for t in FOUR if tw.get(t, 0) > 5e-4),
                "exp real %": 100 * cand["expected_real"], "exp vol %": 100 * cand["volatility"], "ES99 %": 100 * cand["es99"],
                "CAGR 2005-26 %": 100 * res["performance"]["cagr"], "max DD %": 100 * res["performance"]["max_drawdown"],
                "GFC DD %": 100 * st["GFC"]["drawdown"], "2022 %": 100 * st["Rates 2022"]["return"],
                "FHS breaches (24.5 exp)": fhs["breaches"], "FHS Kupiec p": fhs["kupiec_p"], "FHS CC p": fhs["conditional_coverage_p"],
                "GARCH-EVT breaches": ge["breaches"], "GARCH-EVT Kupiec p": ge["kupiec_p"], "GARCH-EVT CC p": ge["conditional_coverage_p"],
                **{k2: res["checks"][k2] for k2 in ("C1", "C2", "C3", "C4", "C5")},
                "all pass": all(res["checks"].values()), "weight_hash": res["weight_hash"]})
    table = pd.DataFrame(rows).set_index("method")
    out = Path("results/four-etf-v2-r1"); out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "summary.csv")
    (out / "metadata.json").write_text(json.dumps({**meta, "universe": FOUR, "mandate": "v2", "prereg_tag": cfg["prereg_tag"],
        "label": "retrospective portfolio evaluation; C4 uses each candidate's own sequential forecasts",
        "python": sys.version.split()[0]}, indent=1))
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40); pd.set_option("display.precision", 3)
    print(table.T.to_string())
