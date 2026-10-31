"""Final portfolio: monthly dynamic EWMA risk parity (candidate v4d, PLAN.md section 13e).

Streamlit-free calculations for dashboard.py. The expensive evidence (strategy path,
sequential risk forecasts and the check results) is read from results/recession-overlay-r1
(final model v6: the strategy plus the recession overlay) and verified by hash; everything else
here is cheap and recomputed from the frozen price snapshot.

The owner adopted v6 as the final model on 31 October 2026. Real returns deflate by the policy
inflation rate (config `inflation`); the CPI rate over a path's own dates is reported beside it.
"""
import hashlib
import json
import numpy as np
import pandas as pd
import yaml
from . import config
from .config import TICKERS
from .backtest import assess, model_pass
from .comparison import ewma_cov
from .portfolio import canonical_weights, replay, kpis
from .stress import SCENARIOS, attribution, hypothetical, reverse_stress, stress_tests

NAME = "v4d_monthly"
RUN = "dynamic-parity-r1"           # v5 core (without the recession overlay)
RUN_V6 = "recession-overlay-r1"     # v6 final model (owner decision 31 Oct 2026)
UNIVERSE = ["SPY", "AGG", "GLD", "XLE"]
BACKTEST_METHODS = ["historical", "normal", "evt", "fhs", "garch_evt"]


class EvidenceError(RuntimeError):
    """The saved evidence does not match the data or its own identifiers."""


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy():
    return yaml.safe_load((config.ROOT/"config/final.yaml").read_text(encoding="utf-8"))


def load_evidence(root=None, model="v6"):
    """Summary, metadata, daily path and forecasts of a strategy, after identity checks.

    model "v6" (default) reads the final model, the v5 core plus the recession overlay;
    "v5" reads the core strategy without the overlay."""
    from .risk import load_forecasts
    root = root or config.ROOT
    if model == "v6":
        from . import recession_overlay as ro
        try:
            e = ro.load_saved(root/"results"/RUN_V6)
        except ro.OverlayEvidenceError as err:
            raise EvidenceError(str(err)) from err
        if sha256(root/"data/clean/prices_clean.csv") != e["meta"]["data_hash"]:
            raise EvidenceError("price snapshot differs from the one the evidence was computed on")
        return {"summary": e["summary"], "meta": e["meta"], "strategy_hash": e["meta"]["strategy_hash"],
                "data_hash": e["meta"]["data_hash"], "path": e["path"], "forecasts": e["forecasts"],
                "folder": root/"results"/RUN_V6, "run": RUN_V6, "model": "v6"}
    folder = root/"results"/RUN
    summary = json.loads((folder/"summary.json").read_text(encoding="utf-8"))[NAME]
    meta = json.loads((folder/"metadata.json").read_text(encoding="utf-8"))
    sh = meta["strategy_hashes"][NAME]
    if summary["strategy_hash"] != sh:
        raise EvidenceError("summary strategy hash differs from metadata")
    data_hash = sha256(root/"data/clean/prices_clean.csv")
    if data_hash != meta["data_hash"]:
        raise EvidenceError("price snapshot differs from the one the evidence was computed on")
    path = pd.read_csv(folder/f"{NAME}_path.csv", index_col=0, parse_dates=True)
    forecasts = load_forecasts(folder/f"{NAME}_forecasts.csv")
    if not (forecasts["weight_hash"] == sh).all():
        raise EvidenceError("forecast rows carry a different strategy hash")
    return {"summary": summary, "meta": meta, "strategy_hash": sh, "data_hash": data_hash,
            "path": path, "forecasts": forecasts, "folder": folder, "run": RUN, "model": "v5"}


def load_market(root=None):
    """Frozen prices (all seven ETFs), simple returns, the daily risk-free rate and the CPI index."""
    from .data import load_clean_prices, load_macro_data
    cfg = policy()
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna()
    macro = load_macro_data().reindex(prices.index).ffill()
    return prices, returns, macro.rf_daily_effective.reindex(returns.index), macro.CPIAUCSL


def cpi_real(r, cpi):
    """Nominal CAGR, CPI inflation and real CAGR of a daily return path.

    Inflation is CPI(end)/CPI(base) - 1 with the base at the close before the first return,
    annualised over the same calendar years as the CAGR; real = (1+CAGR)/(1+inflation) - 1."""
    base = cpi.loc[:r.index[0]-pd.Timedelta(days=1)]
    base = base.iloc[-1] if len(base) else cpi.loc[r.index[0]]
    years = (r.index[-1]-r.index[0]).days/365.25
    cagr = float((1+r).prod()**(1/years)-1)
    inflation = float((cpi.loc[:r.index[-1]].iloc[-1]/base)**(1/years)-1)
    return cagr, inflation, (1+cagr)/(1+inflation)-1


def policy_real(cagr, cfg=None):
    """Real CAGR at the policy inflation rate (average US CPI from the data start)."""
    cfg = cfg or policy()
    return (1+cagr)/(1+cfg["inflation"])-1


def current_target(path):
    """Target weights in force after the last decision close (the allocation to hold now)."""
    w = canonical_weights({t: float(path[f"target_{t}"].iloc[-1]) for t in UNIVERSE})
    w = {t: w[t] for t in UNIVERSE}
    if "overlay_on" in path and bool(path["overlay_on"].iloc[-1]):     # v6: half of SPY and XLE held as cash
        w["SPY"] *= .5; w["XLE"] *= .5
    return w


def current_holdings(path):
    return {t: float(path[t].iloc[-1]) for t in UNIVERSE}


def target_history(path):
    """Target weights at each decision close (first row is the starting target)."""
    keep = path.rebalanced.astype(bool) | (path.index == path.index[0])
    return path.loc[keep, [f"target_{t}" for t in UNIVERSE]].rename(columns=lambda c: c[7:])


def window(path, start=None, end=None):
    return path.loc[start:end]


def wealth_usd(returns, value):
    """USD wealth from the window's first close, so wealth starts exactly at value."""
    return value*pd.concat([pd.Series([1.], index=[returns.index[0]-pd.Timedelta(days=1)]), (1+returns).cumprod()])


def drawdown(wealth):
    return wealth/wealth.cummax()-1


def benchmark_returns(returns):
    """40/60 SPY/AGG, rebalanced quarterly or on a 5-point drift, zero cost."""
    return replay(returns[["SPY", "AGG"]], {"SPY": .4, "AGG": .6}, cost=0., drift=.05)["return"]


def same_risk_spy_weight(path, returns, step=.01):
    """SPY weight of the SPY/AGG mix whose volatility over the strategy's dates first reaches the
    strategy's own (grid of 1 point). Chosen after the fact, to compare return at equal risk."""
    x = returns.loc[path.index[0]:path.index[-1], ["SPY", "AGG"]]; target = path["return"].std()
    for w in np.arange(0, 1+step/2, step):
        if replay(x, {"SPY": w, "AGG": 1-w}, cost=0., drift=.05)["return"].std() >= target:
            return float(round(w, 2))
    return 1.


def benchmarks(path, returns, cfg=None):
    """Reference allocations; unavailable fits are isolated to their own entry.

    The approximate volatility match and static parity use full-history information.
    They are retrospective comparisons, not historically selected strategies.
    """
    from .portfolio import construct
    cfg = cfg or policy()
    result = {}
    errors = (ValueError, RuntimeError, np.linalg.LinAlgError)
    try:
        w = same_risk_spy_weight(path, returns)
        result[f"SPY/AGG {w:.0%}/{1-w:.0%} (approx. vol-matched)"] = (
            {"SPY": w, "AGG": 1-w},
            f"Volatility approximately matched on {path.index[0].date()} to {path.index[-1].date()} "
            "using a one-percentage-point weight grid; shorter periods need not match.")
    except errors as err:
        result["SPY/AGG volatility match"] = (None, f"Unavailable: {err}")
    try:
        fitted = construct(returns, cfg, "near_parity")
        if fitted.get("weights") is None:
            raise ValueError(fitted.get("reason", "static parity optimisation failed"))
        weights = {t: float(fitted["weights"][t]) for t in UNIVERSE}
        if not np.isfinite(list(weights.values())).all() or min(weights.values()) < 0 or not np.isclose(sum(weights.values()), 1):
            raise ValueError("static parity weights are invalid")
        result["Static risk parity"] = (weights,
            "Fixed full-sample risk parity on the same four ETFs; Ledoit-Wolf covariance, "
            "quarterly/drift rebalancing. Differences do not isolate monthly updating.")
    except errors as err:
        result["Static risk parity"] = (None, f"Unavailable: {err}")
    result["40/60 SPY/AGG"] = ({"SPY": .4, "AGG": .6}, "Conventional conservative stock/bond mix.")
    result["Permanent 25/50/25"] = ({"SPY": .25, "AGG": .5, "GLD": .25}, "Simple stock/bond/gold mix.")
    return result


def benchmark_path(weights, returns, start, end):
    """Daily returns of a fixed allocation started at target on the supplied full-history start."""
    return benchmark_frame(weights, returns, start, end)["return"]


def benchmark_frame(weights, returns, start, end):
    """Zero-cost fixed-weight replay; build on full strategy dates, then slice for display."""
    return replay(returns.loc[start:end, list(weights)], weights, cost=0., drift=.05)


def benchmark_window(frame, start=None, end=None):
    """A view of an already-invested benchmark; preserves opening holdings and trade dates."""
    return frame.loc[start:end].copy()


def with_cost(r, turnover, cost):
    """Exact proportional-cost sensitivity on the recorded, scale-invariant trade path."""
    traded = turnover.reindex(r.index)
    if not np.isfinite(cost) or cost < 0 or traded.isna().any() or not np.isfinite(traded).all() or (traded < 0).any():
        raise ValueError("nonnegative finite costs and complete turnover history are required")
    if (cost*traded >= 1).any():
        raise ValueError("trading costs exhaust portfolio wealth")
    return (1+r)*(1-cost*traded)-1


def cagr(r):
    if len(r) < 2:
        return np.nan
    years = (r.index[-1]-r.index[0]).days/365.25
    return float(np.expm1(np.log1p(r).sum()/years)) if years > 0 else np.nan


def page_kpis(r, rf, market, cpi, cfg=None):
    """Page-only KPIs, separating actual CPI adjustment from the fixed planning assumption."""
    out = kpis(r, rf, market, r)
    if out.get("status"):
        return out
    _, inflation, real = cpi_real(r, cpi)
    excess = (r-rf.reindex(r.index)).dropna()
    downside = np.sqrt(np.mean(np.minimum(excess, 0)**2))*np.sqrt(252)
    out.update(cpi_inflation=inflation, real_cagr_cpi=real, real_cagr_policy=policy_real(out["cagr"], cfg),
               sortino_excess=float(excess.mean()*252/downside) if downside > 1e-12 else None)
    return out


def relative(r, b):
    """Descriptive return differences and information ratio; no significance inference."""
    frame = pd.concat([r.rename("portfolio"), b.rename("benchmark")], axis=1).dropna()
    if len(frame) < 2:
        return {k: None for k in ("cagr_diff", "mean_diff", "tracking_error", "information_ratio")}
    active = frame.portfolio-frame.benchmark
    te = float(active.std()*np.sqrt(252))
    return {"cagr_diff": cagr(frame.portfolio)-cagr(frame.benchmark), "mean_diff": float(active.mean()*252),
            "tracking_error": te, "information_ratio": float(active.mean()*252/te) if te > 1e-12 else None}


def reserve_ledger(r, cfg=None):
    """Actual fund-balance replay with fixed calendar-anchored withdrawals and visible shortfalls.

    Start with the full fund in the first full calendar year of the strategy history,
    matching reserve_history. Year-1 payment is deducted before that day's return.
    Build this ledger once on the full path; date filters must only slice it.
    """
    cfg = cfg or policy()
    columns = ["balance", "required_payment", "paid_payment", "shortfall", "depleted"]
    if r.empty:
        return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], name="date"))
    if not np.isfinite(r).all() or (r <= -1).any() or r.index.has_duplicates or not r.index.is_monotonic_increasing:
        raise ValueError("reserve replay needs finite, chronological returns above -100%")
    # The saved strategy begins in a partial year; its first full year funds payment one.
    first_year = r.index[0].year if r.index[0].month == 1 and r.index[0].day <= 7 else r.index[0].year+1
    invest = r.loc[r.index.year >= first_year]
    if invest.empty:
        return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], name="date"))
    nav = float(cfg["fund_value"])
    rows = []; year = invest.index[0].year
    pos = r.index.get_loc(invest.index[0])
    base = r.index[pos-1] if pos > 0 else invest.index[0]-pd.Timedelta(days=1)
    rows.append((base, nav, 0., 0., 0., False))
    previous_year = None
    for date, ret in invest.items():
        need = paid = short = 0.
        if date.year != previous_year:
            need = cfg["reserve_initial"]*(1+cfg["reserve_growth"])**(date.year-year)
            paid = min(nav, need); short = max(need-paid, 0.)
            nav -= paid
        nav = max(0., nav*(1+ret))
        rows.append((date, nav, need, paid, short, nav <= 0))
        previous_year = date.year
    return pd.DataFrame(rows, columns=["date", *columns]).set_index("date")


def reserve_window(ledger, start=None, end=None):
    """Zoom an existing fund history without resetting payment years or rebasing balances."""
    view = ledger.loc[start:end]
    if view.empty:
        return view.copy()
    pos = ledger.index.get_loc(view.index[0])
    return ledger.iloc[max(0, pos-1):ledger.index.get_loc(view.index[-1])+1].copy()


def takeaway(name_k, bench_k, rel):
    """Factual comparison only; small observed gaps are not evidence of future superiority."""
    ahead = [n for n in bench_k if rel[n]["cagr_diff"] > 0]
    behind = [n for n in bench_k if rel[n]["cagr_diff"] <= 0]
    shallower = [n for n in bench_k if name_k["maximum_drawdown"] > bench_k[n]["maximum_drawdown"]]
    deeper = [n for n in bench_k if n not in shallower]
    gap = lambda xs: ", ".join(f"{n} ({100*rel[n]['cagr_diff']:+.2f} pp)" for n in xs) if xs else "none"
    fall = lambda xs: ", ".join(f"{n} ({100*-bench_k[n]['maximum_drawdown']:.1f}%)" for n in xs) if xs else "none"
    return {"ahead": gap(ahead), "behind": gap(behind), "shallower": fall(shallower), "deeper": fall(deeper)}


def performance(path, returns, rf, cpi, start=None, end=None):
    """KPIs of the strategy path against SPY (market) and 40/60 SPY/AGG (benchmark)."""
    r = window(path, start, end)["return"]
    out = kpis(r, rf, returns.SPY, benchmark_returns(returns))
    out["path_cpi_inflation"] = cpi_real(r, cpi)[1] if len(r) > 1 else np.nan
    out["cpi_inflation"] = policy()["inflation"]
    out["real_cagr"] = policy_real(out["cagr"]) if len(r) > 1 else np.nan
    years = (r.index[-1]-r.index[0]).days/365.25 if len(r) > 1 else np.nan
    w = window(path, start, end)
    out["rebalances"] = int(w.rebalanced.astype(bool).sum())
    out["turnover_per_year"] = float(w.turnover.sum()/years) if years else np.nan
    return out


def risk_now(returns, weights, value, start=None, end=None):
    """Every risk model fitted to the current target held over the estimation window."""
    from .risk import fit_models, risk_table
    logs = np.log1p(returns.loc[start:end, UNIVERSE])
    cfg = policy()
    models = fit_models(logs, weights, n_sim=cfg["n_sim"], seed=cfg["seed"])
    return models, risk_table(models, value=value)


def risk_contributions(returns, weights, alpha, value, lam=.97, window_days=750):
    """Volatility contributions under the EWMA covariance the rule uses, and historical
    dollar ES contributions from joint asset rows (shared tail weights)."""
    x = returns[UNIVERSE]
    cov = ewma_cov(x.to_numpy()[-window_days:], lam)
    w = np.array([weights[t] for t in UNIVERSE]); sigma = float(np.sqrt(w@cov@w))
    vol = w*(cov@w)/sigma
    es = attribution(x, weights, alpha, value)
    rows = pd.DataFrame({"weight": w, "vol_contribution": vol/sigma,
                         "es_usd": [es["components"][t] for t in UNIVERSE],
                         "marginal_es_per_usd": [es["marginal_es_usd_per_dollar"][t] for t in UNIVERSE]}, index=UNIVERSE)
    rows["es_share"] = rows.es_usd/es["es_usd"]
    return rows, {"portfolio_vol_annual": sigma*np.sqrt(252), "es_usd": es["es_usd"], "residual_usd": es["residual_usd"],
                  "diversification_benefit_usd": es["diversification_benefit_usd"]}


def backtest(forecasts, strategy_hash, method, alpha, start, end):
    """Kupiec/Christoffersen/traffic light on the strategy's own forecasts; refuses another hash."""
    result = assess(forecasts, strategy_hash, method, alpha, start, end)
    col = f"var_{method}_{alpha*100:g}"
    frame = forecasts.loc[start:end, ["return", col]].rename(columns={col: "var"})
    frame["loss"] = -frame["return"]
    frame["breach"] = frame.loss > frame["var"]
    result["passes_gate"] = model_pass(result)
    return result, frame


def binomial_zone(result, alpha):
    """Plain binomial reading for levels or samples outside the Basel 99%/250-day calibration."""
    p = result.get("binomial_p")
    if p is None:
        return "unavailable"
    return "consistent with the confidence level" if p > .05 else "inconsistent with the confidence level"


def scenario_pnl(path, asset_returns, start, end, value):
    """Path return, maximum fall and per-ETF dollar P&L from the scenario start close to its
    end close (the convention of the frozen scenario evaluation).

    P&L_i = sum_t V_(t-1) h_(i,t-1) R_(i,t), with h the end-of-day holdings; the parts add
    up to the path's wealth change exactly because trading costs are zero."""
    frame = path.loc[:end]
    first = frame.index.get_indexer([pd.Timestamp(start)], method="bfill")[0]
    days = frame.iloc[first+1:]
    held = frame[UNIVERSE].iloc[first:-1].to_numpy()
    ret = asset_returns.loc[days.index, UNIVERSE].to_numpy()
    growth = np.r_[1., (1+days["return"]).cumprod().to_numpy()]
    pnl = (held*ret*value*growth[:-1, None]).sum(axis=0)
    return {"return": float(growth[-1]-1), "loss_usd": float(-value*(growth[-1]-1)),
            "max_fall": float(-(growth/np.maximum.accumulate(growth)-1).min()),
            "pnl_usd": dict(zip(UNIVERSE, pnl.tolist())),
            "holdings_at_start": {t: float(frame[t].iloc[first]) for t in UNIVERSE},
            "worst_day": str(days["return"].idxmin().date()), "worst_day_return": float(days["return"].min())}


def stress_panel(path, prices, returns, weights, value):
    """Historical scenarios (strategy path, and today's target held buy-and-hold), the frozen
    hypothetical shock and a reverse stress for today's target."""
    w7 = canonical_weights(weights)
    rows = []
    held = {s["scenario"]: s for s in stress_tests(prices[UNIVERSE], weights, value)}
    for name, (start, end) in SCENARIOS.items():
        row = {"scenario": name, "start": start, "end": end}
        if path.index[0] < pd.Timestamp(start):
            row["path"] = scenario_pnl(path, returns, start, end, value)
        row["today_buy_hold"] = held.get(name)
        rows.append(row)
    cfg = policy()
    hyp = hypothetical(returns.loc[:cfg["training_end"]], w7, value)
    rev = reverse_stress(returns.loc[:cfg["training_end"]], w7, cfg["drawdown_limit"])
    return rows, hyp, rev


def custom_shock(weights, shocks, value):
    """Deterministic one-step shock: USD loss by ETF for simple-return shocks."""
    pnl = {t: value*weights[t]*shocks[t] for t in UNIVERSE}
    return {"return": sum(pnl.values())/value, "loss_usd": -sum(pnl.values()), "pnl_usd": pnl}


def adf(path):
    from statsmodels.tsa.stattools import adfuller
    r = np.log1p(path["return"])
    stat, p, lags, n, *_ = adfuller(r, autolag="AIC")
    return {"statistic": float(stat), "p_value": float(p), "lags": int(lags), "observations": int(n)}


# ---------------------------------------------------------------- evidence added for the technical report
# Shared with dashboard.py so the report and the dashboard quote the same numbers.

FIXED_COMPARISONS = {"40/60 SPY/AGG": {"SPY": .4, "AGG": .6}, "60/40 SPY/AGG": {"SPY": .6, "AGG": .4},
                     "Equal weight": {t: .25 for t in UNIVERSE}, "Permanent 25/50/25": {"SPY": .25, "AGG": .5, "GLD": .25},
                     "Balanced 35/50/15": {"SPY": .35, "AGG": .5, "GLD": .15}}


def latest_forecast(forecasts, method, alpha, value):
    """The newest sequential forecast of the validated specification (750-day rolling refit on the strategy's
    own path). VaR converts exactly; the saved ES is in log units, so its dollar value is approximate."""
    row = forecasts.iloc[-1]; tag = f"{method}_{alpha*100:g}"
    return {"date": str(forecasts.index[-1].date()), "data_through": str(pd.Timestamp(row["train_end"]).date()),
            "var_usd": float(value*(1-np.exp(-row["var_"+tag]))), "es_usd_approx": float(value*(1-np.exp(-row["es_"+tag])))}


def distribution_yield(weights, root=None):
    """Trailing 12-month cash distributions over the latest unadjusted close (as the pipeline's evidence step)."""
    root = root or config.ROOT; end = pd.Timestamp(policy()["snapshot_end"])
    d = pd.read_csv(root/"data/raw/distributions.csv", parse_dates=["date"]); d = d[d.date <= end]
    per = {t: float(g[g.date > end-pd.Timedelta(days=365)].dividend.sum()/g.sort_values("date").close.iloc[-1])
           for t, g in d.groupby("ticker") if t in UNIVERSE}
    return {"by_etf": per, "portfolio": float(sum(weights[t]*per[t] for t in UNIVERSE))}


def mc_error(returns, weights, value, seeds=(1, 2, 3, 4, 5)):
    """Monte Carlo simulation error: the 99% VaR and ES of today's target under different seeds."""
    from .risk import fit_models, risk_table
    cfg = policy(); rows = []
    for seed in seeds:
        t = risk_table(fit_models(np.log1p(returns[UNIVERSE]), weights, ["mc_normal", "mc_t"], n_sim=cfg["n_sim"], seed=seed), value=value)
        rows.append(t[np.isclose(t.alpha, .99)].assign(seed=seed))
    out = pd.concat(rows)
    return out.groupby("method").agg(var_min=("var_usd", "min"), var_max=("var_usd", "max"), es_min=("es_usd", "min"),
                                      es_max=("es_usd", "max")).reset_index()


def frontier(returns, points=40):
    """Ex-ante long-only efficient frontier of the four ETFs under the frozen estimator (means shrunk 50% toward
    the seven-ETF average, Ledoit-Wolf covariance, full sample): the inputs of the Markowitz comparisons."""
    from scipy.optimize import minimize
    from .portfolio import estimates
    cfg = policy(); mu7, cov7 = estimates(returns[TICKERS], cfg); idx = [TICKERS.index(t) for t in UNIVERSE]
    mu, cov = mu7[idx], cov7[np.ix_(idx, idx)]; k = len(UNIVERSE); rows = []
    w0 = np.full(k, 1/k); bounds = [(0, 1)]*k
    low = minimize(lambda w: w@cov@w, w0, bounds=bounds, constraints=[{"type": "eq", "fun": lambda w: w.sum()-1}], method="SLSQP").x
    for target in np.linspace(float(low@mu), float(mu.max()), points):
        s = minimize(lambda w: w@cov@w, w0, bounds=bounds, method="SLSQP",
                     constraints=[{"type": "eq", "fun": lambda w: w.sum()-1}, {"type": "ineq", "fun": lambda w, t=target: w@mu-t}])
        if s.success:
            rows.append({"volatility": float(np.sqrt(s.x@cov@s.x)), "expected": float(s.x@mu)})
    point = lambda w: (float(np.sqrt(np.array([w.get(t, 0) for t in UNIVERSE])@cov@np.array([w.get(t, 0) for t in UNIVERSE]))),
                       float(np.array([w.get(t, 0) for t in UNIVERSE])@mu))
    return pd.DataFrame(rows), {"mu": dict(zip(UNIVERSE, mu.tolist())), "vol": dict(zip(UNIVERSE, np.sqrt(np.diag(cov)).tolist()))}, point
OPTIMISED_COMPARISONS = {"Static risk parity": "near_parity", "Minimum variance": "min_variance", "Maximum Sharpe": "max_sharpe"}


def window_return(wealth, start, end):
    """Return from the scenario start close to its end close (the stress-test convention)."""
    return float(wealth.loc[:end].iloc[-1]/wealth.loc[start:].iloc[0]-1)


def comparison(path, returns, rf, cpi):
    """The strategy beside fixed-weight alternatives over the strategy's own dates.

    Optimised weights (Markowitz minimum variance and maximum Sharpe, static risk parity) use the
    whole November 2004 to September 2026 sample, so they are hindsight comparisons; all fixed weights rebalance quarterly
    or on a 5-point drift at zero cost. Retrospective portfolio evaluation."""
    from .portfolio import construct, replay, tail_weights
    cfg = policy(); start = path.index[0]; x = returns.loc[start:]
    candidates = {"Final portfolio (monthly dynamic risk parity)": None}
    for label, kind in OPTIMISED_COMPARISONS.items():
        fit = construct(returns, cfg, kind)
        if fit.get("weights"):
            candidates[label] = {t: fit["weights"][t] for t in UNIVERSE}
    candidates.update(FIXED_COMPARISONS)
    bench = benchmark_returns(returns)
    rows = []
    for label, w in candidates.items():
        r = path["return"] if w is None else replay(x[list(w)], w, cost=cfg["cost"], drift=cfg["drift"])["return"]
        k = kpis(r, rf, returns.SPY, bench); wealth = (1+r).cumprod(); loss = -r.to_numpy()
        row = {"portfolio": label, "weights": None if w is None else {t: float(w.get(t, 0.)) for t in UNIVERSE},
               "cagr": k["cagr"], "real_cagr": policy_real(k["cagr"], cfg), "volatility": k["annual_volatility"],
               "max_drawdown": -k["maximum_drawdown"], "sharpe": k["sharpe"],
               "es99_daily": float(tail_weights(loss)@loss)}
        for name, (a, b) in SCENARIOS.items():
            row[name] = window_return(wealth, a, b)
        rows.append(row)
    return pd.DataFrame(rows)


def expected_returns(returns, weights, cfg=None):
    """Expected nominal and real geometric return of fixed weights under the frozen estimator
    (50% mean shrinkage, Ledoit-Wolf) and raw historical means, on three look-back windows."""
    from .portfolio import estimates
    cfg = cfg or policy(); end = returns.index[-1]
    v = np.array([canonical_weights(weights)[t] for t in TICKERS]); rows = []
    for label, years in (("Full sample", None), ("Last 10 years", 10), ("Last 5 years", 5)):
        x = returns if years is None else returns.loc[returns.index > end-pd.DateOffset(years=years)]
        for estimator, shrink in (("Raw historical means", 0.), (f"{cfg['mean_shrinkage']:.0%} shrinkage (frozen)", cfg["mean_shrinkage"])):
            mu, cov = estimates(x[TICKERS], dict(cfg, mean_shrinkage=shrink))
            arithmetic = float(v@mu); geometric = float(np.expm1(np.log1p(arithmetic)-v@cov@v/2))
            rows.append({"window": label, "start": str(x.index[0].date()), "estimator": estimator,
                         "arithmetic": arithmetic, "geometric": geometric,
                         "real": (1+geometric)/(1+cfg["inflation"])-1})
    return pd.DataFrame(rows)


def reserve_test(path, cfg=None):
    """25-year cash-reserve survival on the strategy's own monthly returns: joint non-circular
    12-month blocks, the 1 January reserve paid first, real values deflated by the policy CPI
    rate. Uses the active policy and the same accounting as pipeline.survival_of."""
    from .stress import reserve_survival
    cfg = cfg or policy()
    m = ((1+path["return"]).resample("ME").prod()-1).iloc[1:]       # the first month is partial
    frame = pd.DataFrame(0., index=m.index, columns=TICKERS); frame["SPY"] = m
    out = reserve_survival(frame, canonical_weights({"SPY": 1.}), cfg)
    out.update(sample=f"{m.index[0]:%Y-%m} to {m.index[-1]:%Y-%m}", months=len(m))
    return out


def reserve_history(path, cpi, cfg=None):
    """The USD 10m fund on the strategy's actual path from its first full calendar year, paying
    the 1 January reserve before that day's return; real value deflated by actual US CPI."""
    cfg = cfg or policy(); r = path["return"]
    r = r.loc[r.index[r.index.year > r.index[0].year][0]:]
    nav = 1.; year = -1; paid = []
    for i, (date, x) in enumerate(r.items()):
        if i == 0 or r.index[i-1].year != date.year:
            year += 1; draw = min(nav, cfg["reserve_initial"]/cfg["fund_value"]*(1+cfg["reserve_growth"])**year)
            nav -= draw; paid.append(draw)
        nav *= 1+x
    base = cpi.loc[:r.index[0]-pd.Timedelta(days=1)].iloc[-1]; ratio = float(cpi.loc[:r.index[-1]].iloc[-1]/base)
    fund = cfg["fund_value"]
    return {"start": str(r.index[0].date()), "end": str(r.index[-1].date()), "payments": len(paid),
            "paid_usd": fund*sum(paid), "end_usd": fund*nav, "cpi_ratio": ratio, "end_real_usd": fund*nav/ratio,
            "first_payment_usd": fund*paid[0], "last_payment_usd": fund*paid[-1]}


def bootstrap(returns, weights, value, cfg=None):
    """95% moving-block bootstrap intervals for the current target held fixed (500 resamples of
    circular 20-day blocks of whole asset rows). Same call and inputs as the mandate v5 run, so its
    intervals are reproduced exactly; USD columns convert log VaR and exact fractional ES."""
    from .risk.uncertainty import bootstrap_intervals
    cfg = cfg or policy()
    out = bootstrap_intervals(np.log1p(returns[TICKERS]), canonical_weights(weights), methods=["historical", "normal", "evt"],
                              reps=cfg["bootstrap_reps"], block=cfg["bootstrap_block"], seed=cfg["seed"])
    for side in ("lo", "hi"):
        out[f"var_usd_{side}"] = value*(1-np.exp(-out[f"var_{side}"]))
        out[f"es_usd_{side}"] = value*out[f"es_frac_{side}"]
    return out



def strategy_risk(path, value, alphas=(.90, .95, .99), start=None, end=None):
    """Historical one-day risk of the recorded monthly strategy, before withdrawals."""
    from .risk.var_es import historical
    from .risk.portfolio import loss_fraction
    r = path.loc[start:end, "return"]
    model = historical(np.log1p(r))
    return pd.DataFrame([dict(alpha=a, var=model.var(a), es=model.es(a),
        es_fraction=model.es_fraction(a), var_usd=value*loss_fraction(model.var(a)),
        es_usd=value*model.es_fraction(a), n=len(r), effective_tail_count=len(r)*(1-a),
        first=r.index[0], last=r.index[-1]) for a in alphas])


def risk_scope(returns, start=None, end=None, *, price_start=None, strategy_start=None):
    """Dates and sample count for the selected return window."""
    r = returns.loc[start:end]
    return dict(first=r.index[0], last=r.index[-1], n=len(r),
                price_start=price_start, strategy_start=strategy_start)


def disagreement_notes(table, models, alpha):
    """Evidence-driven comparisons; failed fits never supply narrative parameters."""
    selected = table[np.isclose(table.alpha, alpha)].set_index("method")
    notes = []
    def valid(method):
        if method not in selected.index:
            return False
        row = selected.loc[method]
        return str(row.status).lower().startswith(("ok", "warning")) and np.isfinite(row.es_usd)
    for method, row in selected.iterrows():
        if not valid(method):
            notes.append(f"Unavailable: {method}: {row.status}")
    if valid("normal") and valid("historical") and selected.loc["normal", "es_usd"] > 0:
        ratio = selected.loc["historical", "es_usd"]/selected.loc["normal", "es_usd"]
        ratios = []
        for a in sorted(table.alpha.unique()):
            q = table[np.isclose(table.alpha, a)].set_index("method")
            if all(m in q.index and str(q.loc[m, "status"]).lower().startswith(("ok", "warning"))
                   and np.isfinite(q.loc[m, "es_usd"]) for m in ("normal", "historical")) and q.loc["normal", "es_usd"] > 0:
                ratios.append((a, q.loc["historical", "es_usd"]/q.loc["normal", "es_usd"]))
        detail = ", ".join(f"{a:.0%}: {v:.2f}x" for a, v in ratios)
        widens = len(ratios) > 1 and all(y[1] > x[1] for x, y in zip(ratios, ratios[1:]))
        notes.append(f"Normal versus history: historical ES is {ratio:.2f}x normal ES. Ratios ({detail}). "
                     + ("The relative gap widens with confidence." if widens else "No consistent increase in the relative gap across confidence levels."))
    if valid("mc_normal") and valid("normal") and selected.loc["normal", "es_usd"] > 0:
        gap = abs(selected.loc["mc_normal", "es_usd"]/selected.loc["normal", "es_usd"]-1)*100
        word = "is within" if gap <= 5 else "differs by"
        notes.append(f"Monte Carlo normal ES {word} {gap:.2f}% of the normal fit. Joint ETF log-return scenarios "
                     "aggregated through simple returns use different portfolio accounting from a normal fit to portfolio log returns.")
    if valid("evt") and valid("historical") and selected.loc["historical", "es_usd"] > 0:
        gap = (selected.loc["evt", "es_usd"]/selected.loc["historical", "es_usd"]-1)*100
        params = models["evt"].params
        xi, se = params.get("xi"), params.get("xi_se")
        shape = f" Shape xi = {xi:.3f}" if xi is not None and np.isfinite(xi) else ""
        if shape and se is not None and np.isfinite(se):
            shape += f" +/- {1.96*se:.3f} (approximate 95% interval)."
        notes.append(f"EVT ES differs from historical ES by {gap:+.2f}%.{shape} Basis: {selected.loc['evt', 'basis']}.")
    return notes


# APP-018: EVT page diagnostics; frozen risk implementations remain unchanged.
def evt_scan(losses, value, alpha):
    from .risk.evt import threshold_scan
    from .risk.portfolio import loss_fraction
    scan = threshold_scan(losses, alphas=(alpha,), dollar_es=True)
    scan["var_usd"] = value * loss_fraction(scan[f"var_{alpha:g}"])
    scan["es_usd"] = value * scan[f"es_fraction_{alpha:g}"]
    return scan


def gpd_tail_prob(x, fit, zeta):
    from scipy.stats import genpareto
    return zeta * genpareto.sf(np.asarray(x)-fit.u, c=fit.xi, scale=fit.sigma)


def gpd_qq(fit, losses, reps=200, seed=None):
    """Pointwise parametric envelope, refitting every simulated tail sample.

    Refit-standardised order statistics are mapped back to the original fitted
    GPD units using its inverse CDF. Failed refits remain in the counts.
    """
    from scipy.stats import genpareto
    from .risk.evt import fit_gpd, gpd_ppf
    from .risk.validation import ModelFitError
    seed = policy()["seed"] if seed is None else seed
    observed = np.sort(np.asarray(losses)[np.asarray(losses) > fit.u]-fit.u)
    n = len(observed); probs = (np.arange(n)+.5)/n
    theoretical = gpd_ppf(probs, fit.xi, fit.sigma)
    rng = np.random.default_rng(seed); samples = []; failures = []
    for _ in range(reps):
        y = genpareto.rvs(fit.xi, scale=fit.sigma, size=n, random_state=rng)
        try:
            refit = fit_gpd(y, 0.)
            pit = genpareto.cdf(np.sort(y), refit.xi, scale=refit.sigma)
            standardised = gpd_ppf(pit, fit.xi, fit.sigma)
            if not np.isfinite(standardised).all():
                raise ModelFitError("non-finite refitted order statistics")
            samples.append(standardised)
        except (ModelFitError, ValueError, FloatingPointError) as err:
            failures.append(str(err))
    out = dict(theoretical=theoretical, observed=observed, reps_ok=len(samples),
               reps_failed=len(failures), failures=failures, seed=seed)
    if not samples:
        return dict(out, status="unavailable: all parametric-bootstrap refits failed")
    lo, hi = np.quantile(samples, [.025, .975], axis=0)
    return dict(out, status="ok", lo=lo, hi=hi, outside=(observed < lo) | (observed > hi))


def strategy_evt(path):
    """Rule-chosen EVT on the strategy's own daily path; flags a choice at either end of the grid."""
    from .risk import settings as S
    from .risk.evt import fit_evt
    from .risk.validation import ModelFitError
    try:
        model = fit_evt(-np.log1p(path["return"]).to_numpy())
    except (ModelFitError, ValueError) as err:
        return {"status": f"unavailable: {err}"}
    q, grid = model.params["threshold_q"], S.EVT_THRESHOLD_GRID
    if abs(q-grid[0]) < 1e-3:
        model.status = f"ok; selected at the lowest grid point ({grid[0]:.1%}); a lower threshold was not examined"
    elif abs(q-grid[-1]) < 1e-3:
        model.status = f"ok; selected at the highest grid point ({grid[-1]:.1%}); a higher threshold was not examined"
    return model


def evt_notes(model, scan, alpha, value, alt_fits, boot_row, qq):
    """Generate page conclusions and captions from the actual fitted evidence."""
    from .risk.portfolio import loss_fraction
    if not hasattr(model, "fit"):
        reason = model.get("status", "failed fit") if isinstance(model, dict) else getattr(model, "status", "failed fit")
        return {"conclusion": f"EVT result unavailable: {reason}"}
    f = model.fit; base = value*model.es_fraction(alpha)
    words = [f"At {alpha:.0%}, EVT VaR is USD {value*loss_fraction(model.var(alpha)):,.0f} and ES is USD {base:,.0f}; basis: {model.basis(alpha)}."]
    for label, alt in alt_fits.items():
        if not hasattr(alt, "fit"):
            words.append(f"{label}: unavailable ({alt.get('status', 'failed fit')}).")
        elif np.isfinite(base) and base != 0:
            words.append(f"{label}: ES changes by {(value*alt.es_fraction(alpha)/base-1):+.2%} from the selected threshold.")
    # Above q = alpha the model answers from the empirical body, so only q <= alpha rows are GPD-tail estimates.
    stable = scan.loc[scan.fit_ok & scan.stable & (scan.q <= alpha + 1e-12), "es_usd"].dropna()
    words.append(f"GPD-tail ES across thresholds meeting the stability heuristic: USD {stable.min():,.0f} to USD {stable.max():,.0f}."
                 if len(stable) else "Stable-region GPD-tail ES range unavailable at this confidence level.")
    if boot_row is not None and np.isfinite([boot_row.es_usd_lo, boot_row.es_usd_hi]).all():
        words.append(f"Full-sample 95% bootstrap ES interval: USD {boot_row.es_usd_lo:,.0f} to USD {boot_row.es_usd_hi:,.0f} (threshold percentile fixed; {int(boot_row.reps_ok)} successful, {int(boot_row.reps_failed)} failed resamples).")
    else:
        words.append("Full-sample bootstrap ES interval unavailable.")
    words.append("This does not establish forecast calibration or protection against future crises.")
    ok = scan.loc[scan.fit_ok]; above = ok.loc[ok.u >= f.u]
    slope = np.polyfit(above.u, above.mean_excess, 1)[0] if len(above)>1 else np.nan
    direction = "rising" if slope > 0 else "falling" if slope < 0 else "flat" if slope == 0 else "unavailable"
    drift = ""
    if len(ok) > 1:
        scale = ok.sigma_star
        drift = (f" Across valid fits ξ ranges from {ok.xi.min():.2f} to {ok.xi.max():.2f} and σ* from {scale.min():.3%} to "
                 f"{scale.max():.3%} log loss{', changing sign' if scale.min() < 0 < scale.max() else ''}; both would be flat if a "
                 "single GPD held from the lowest threshold upward.")
        top = ok.loc[ok.stable & (ok.u >= f.u)]
        if len(top) > 1:
            hi = top.iloc[-1]; lo = ok.iloc[(ok.u-f.u).abs().argmin()]
            drift += (f" From the selected threshold to the highest one meeting the heuristic ({hi.q:.1%}), ξ moves "
                      f"{hi.xi-lo.xi:+.2f} and σ* {hi.sigma_star-lo.sigma_star:+.3%}; the heuristic accepts this because the "
                      "higher-threshold standard errors are wide.")
    shape = "positive (power-law tail)" if f.xi > 0 else "zero (exponential tail)" if f.xi == 0 else "negative (finite upper endpoint)"
    shape += "; fitted log-loss variance " + ("finite" if f.xi < .5 else "not finite")
    shape += "; fitted log ES " + ("finite" if f.xi < 1 else "not finite") + "."
    if qq.get("status") == "ok":
        outside = qq["outside"]; upper = np.arange(len(outside)) >= .9*len(outside)
        where = f"{int((outside & upper).sum())} in the upper 10% and {int((outside & ~upper).sum())} in the remaining body of the fitted tail"
        caption = (f"{outside.mean():.1%} of excesses fall outside the pointwise 95% envelope (about 5% would by chance "
                   f"if the fitted GPD were correct): {where}.")
    else:
        caption = f"QQ envelope unavailable: {qq.get('status', 'failed refits')}."
    maximum = float(model.losses.max()); extension = .3*maximum
    return dict(conclusion=" ".join(words), shape=shape,
                diagnostics=f"Mean-excess slope above u is {direction}.{drift}",
                qq=caption+f" Successful refits: {qq.get('reps_ok', 0)}; failed: {qq.get('reps_failed', 0)}. In-sample diagnostic; extrapolation remains uncertain.",
                survival=f"Dashed extrapolation extends {extension:.3%} log-loss units (30%) beyond the largest observed loss of {maximum:.3%}. In-sample diagnostic; extrapolation remains uncertain.")
