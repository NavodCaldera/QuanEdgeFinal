"""Final portfolio: monthly dynamic EWMA risk parity (candidate v4d, PLAN.md section 13e).

Streamlit-free calculations for dashboard.py. The expensive evidence (strategy path,
sequential risk forecasts and the frozen check results) is read from the pre-registered
run results/dynamic-parity-r1 and verified by hash; everything else here is cheap and
recomputed from the frozen price snapshot.

The owner chose this strategy as the final portfolio on 31 October 2026. Real returns
deflate by US CPI (FRED CPIAUCSL index ratios, as available on each date).
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
RUN = "dynamic-parity-r1"
UNIVERSE = ["SPY", "AGG", "GLD", "XLE"]
BACKTEST_METHODS = ["historical", "normal", "evt", "fhs", "garch_evt"]


class EvidenceError(RuntimeError):
    """The saved evidence does not match the data or its own identifiers."""


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy():
    return yaml.safe_load((config.ROOT/"config/final.yaml").read_text(encoding="utf-8"))


def load_evidence(root=None):
    """Summary, metadata, daily path and forecasts of the final strategy, after identity checks."""
    from .risk import load_forecasts
    root = root or config.ROOT
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
            "path": path, "forecasts": forecasts, "folder": folder}


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


def current_target(path):
    """Target weights in force after the last decision close (the allocation to hold now)."""
    w = canonical_weights({t: float(path[f"target_{t}"].iloc[-1]) for t in UNIVERSE})
    return {t: w[t] for t in UNIVERSE}


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


def performance(path, returns, rf, cpi, start=None, end=None):
    """KPIs of the strategy path against SPY (market) and 40/60 SPY/AGG (benchmark)."""
    r = window(path, start, end)["return"]
    out = kpis(r, rf, returns.SPY, benchmark_returns(returns))
    out["cpi_inflation"], out["real_cagr"] = cpi_real(r, cpi)[1:] if len(r) > 1 else (np.nan, np.nan)
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
    whole 2005-2026 sample, so they are hindsight comparisons; all fixed weights rebalance quarterly
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
               "cagr": k["cagr"], "real_cagr": cpi_real(r, cpi)[2], "volatility": k["annual_volatility"],
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
    rate. Identical to the mandate v5 run's calculation (pipeline.survival_of)."""
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

