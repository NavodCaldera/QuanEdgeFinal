"""Why the portfolio holds SPY, AGG, GLD and XLE and not EFA, EEM or XLK (mandate v3 universe).

Streamlit-free evidence for the dashboard's Decision page and the report. Everything is
recomputed from the frozen price and macro snapshot (2005-01-03 to 2026-09-30) except the
optimiser table, which reads the weight files of the seven-ETF runs final-20261027 (v1) and
final-v2-20261030 (v2). All of it is retrospective and descriptive: the four-ETF rule was
written on 30 October 2026 after these data were seen (PLAN.md section 13c).

Run: python -m quanedge.universe   (writes results/universe-r1/)
"""
import hashlib
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from . import config
from .config import TICKERS
from .comparison import dynamic_parity_path, risk_parity
from .portfolio import tail_weights
from .stress import SCENARIOS

KEEP = ["SPY", "AGG", "GLD", "XLE"]
DROP = ["EFA", "EEM", "XLK"]
EQUITY = ["SPY", "EFA", "EEM", "XLE", "XLK"]
OUT = "universe-r1"
SEVEN_ETF_RUNS = {"v1 (final-20261027)": "final-20261027", "v2 (final-v2-20261030)": "final-v2-20261030"}
OPTIMISERS = ["min_cvar", "min_variance", "selected", "max_sharpe"]

# Economic role of each ETF; the numbers that test each claim are in roles() and crises().
ROLE = {
    "SPY": ("US large-cap equity", "Growth: the equity risk premium on 500 US companies; the return engine."),
    "AGG": ("US investment-grade bonds", "Recession and deflation hedge: income plus the term premium; Treasuries rally when growth scares hit."),
    "GLD": ("Gold", "Monetary and crisis hedge: no credit or earnings risk; tends to hold value when real rates fall or confidence breaks."),
    "XLE": ("US energy equity", "Inflation hedge: earnings rise with oil and gas prices, the main driver of inflation shocks such as 2022."),
    "EFA": ("Developed ex-US equity", "Same growth risk as SPY, plus unhedged currency risk for a USD fund."),
    "EEM": ("Emerging-market equity", "Same growth risk as SPY with higher volatility, currency and political risk."),
    "XLK": ("US technology equity", "A sector already inside SPY; adds concentration in growth stocks, not a new risk."),
}


def log_returns(prices):
    return np.log(prices).diff().dropna()


def correlations(r):
    """Full-sample daily correlation, and the same on SPY's worst 5% of days."""
    stress = r[r.SPY <= r.SPY.quantile(.05)]
    return r.corr(), stress.corr(), len(stress)


def effective_bets(corr):
    """Effective number of independent bets: exp(entropy) of the correlation eigenvalue shares
    (Meucci 2009, applied to the correlation matrix). Equals N for uncorrelated assets, 1 for one factor."""
    ev = np.clip(np.linalg.eigvalsh(np.asarray(corr)), 1e-12, None); p = ev/ev.sum()
    return float(np.exp(-(p*np.log(p)).sum())), float(p.max())


def bets_table(r):
    """Effective bets of the four, the seven, and the four plus each excluded ETF."""
    sets = {"Four (SPY, AGG, GLD, XLE)": KEEP, **{f"Four + {t}": KEEP+[t] for t in DROP},
            "All seven": TICKERS, "Equity five (SPY, EFA, EEM, XLE, XLK)": EQUITY}
    rows = []
    for name, cols in sets.items():
        n, top = effective_bets(r[cols].corr())
        rows.append({"set": name, "etfs": len(cols), "effective_bets": n, "bets_per_etf": n/len(cols),
                     "first_factor_share": top})
    return pd.DataFrame(rows)


def spanning(r, lags=5):
    """Regress each excluded ETF's daily log return on the four held ETFs (HAC errors).

    R-squared is the share of its daily variance the four already explain; residual volatility
    is the risk it would add; alpha is the average return the four do not explain."""
    rows = []
    x = sm.add_constant(r[KEEP])
    for t in DROP:
        fit = sm.OLS(r[t], x).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        on_spy = sm.OLS(r[t], sm.add_constant(r[["SPY"]])).fit()
        rows.append({"etf": t, "r2_on_spy": on_spy.rsquared, "r2_on_four": fit.rsquared,
                     "beta_spy": fit.params["SPY"], "volatility": r[t].std()*np.sqrt(252),
                     "residual_volatility": fit.resid.std()*np.sqrt(252),
                     "alpha_annual": fit.params["const"]*252, "alpha_t": fit.tvalues["const"]})
    return pd.DataFrame(rows)


def crises(prices):
    """Buy-and-hold return and maximum fall of each ETF in the three frozen scenarios, plus its
    largest fall over the whole sample."""
    rows = []
    for t in TICKERS:
        p = prices[t]; row = {"etf": t}
        for name, (a, b) in SCENARIOS.items():
            w = p.loc[a:b]
            row[f"{name} return"] = w.iloc[-1]/w.iloc[0]-1
            row[f"{name} max fall"] = -(w/w.cummax()-1).min()
        row["max fall 2005-2026"] = -(p/p.cummax()-1).min()
        row["annual return 2005-2026"] = (p.iloc[-1]/p.iloc[0])**(365.25/(p.index[-1]-p.index[0]).days)-1
        row["annual volatility"] = p.pct_change().std()*np.sqrt(252)
        rows.append(row)
    return pd.DataFrame(rows)


def regimes(prices, macro):
    """Average monthly simple return of each ETF by macro regime (month-end classification).

    Inflation: CPI year-on-year at or above 3% (CPI as available on each date, revised data).
    Rate shock: 10-year Treasury yield up more than 0.25 points in the month.
    Equity stress: VIX month-end above 30 or SPY down more than 5% in the month."""
    m = prices.resample("ME").last()
    ret = m.pct_change().dropna()
    mac = macro.reindex(prices.index).ffill().resample("ME").last().reindex(ret.index)
    cpi = macro.CPIAUCSL.reindex(prices.index).ffill().resample("ME").last()
    yoy = (cpi/cpi.shift(12)-1).reindex(ret.index)
    dy = mac.DGS10.diff()
    labels = {"High inflation (CPI y/y >= 3%)": yoy >= .03,
              "Low inflation (CPI y/y < 3%)": yoy < .03,
              "Rate shock (10y yield +0.25 pt)": dy > .25,
              "Equity stress (VIX > 30 or SPY < -5%)": (mac.VIXCLS > 30) | (ret.SPY < -.05),
              "All months": pd.Series(True, index=ret.index)}
    rows = []
    for name, mask in labels.items():
        mask = mask.fillna(False).astype(bool)
        rows.append({"regime": name, "months": int(mask.sum()), **(ret[mask].mean()).to_dict()})
    return pd.DataFrame(rows)


def monthly_negative(r):
    """Within-month correlation of daily log returns for every pair; share of months below 0."""
    g = r.groupby(r.index.to_period("M")); rows = []
    for i, a in enumerate(TICKERS):
        for b in TICKERS[i+1:]:
            c = g.apply(lambda d: d[a].corr(d[b]))
            rows.append({"pair": f"{a}-{b}", "months": int(c.notna().sum()), "negative_months": int((c < 0).sum()),
                         "negative_share": float((c < 0).mean()), "median": float(c.median()),
                         "both_held": a in KEEP and b in KEEP})
    return pd.DataFrame(rows).sort_values("negative_share", ascending=False)


def es99(x):
    losses = -np.asarray(x, float)
    return float(tail_weights(losses, .99)@losses)


def parity_comparison(simple, value=9.6e6):
    """Static full-sample risk parity and monthly dynamic EWMA risk parity (the final rule) over
    the four and over all seven ETFs. In risk parity each ETF carries 1/N of the volatility, so
    with seven ETFs five-sevenths of the risk budget sits in equities."""
    static, dyn = [], {}
    for name, cols in {"Four ETFs": KEEP, "All seven ETFs": TICKERS}.items():
        w = pd.Series(risk_parity(simple[cols].cov().to_numpy()), index=cols)
        cov = simple[cols].cov().to_numpy(); rc = w.to_numpy()*(cov@w.to_numpy()); rc /= rc.sum()
        eq = [c for c in cols if c in EQUITY]
        static.append({"universe": name, **{t: float(w.get(t, 0.)) for t in TICKERS},
                       "equity_weight": float(w[eq].sum()), "equity_risk_share": float(rc[[cols.index(c) for c in eq]].sum())})
        path = dynamic_parity_path(simple[cols])
        dyn[name] = path
    start = max(p.index[0] for p in dyn.values())
    rows = []
    for name, path in dyn.items():
        r = path["return"].loc[start:]
        wealth = (1+r).cumprod(); years = (r.index[-1]-r.index[0]).days/365.25
        row = {"universe": name, "start": str(r.index[0].date()), "cagr": wealth.iloc[-1]**(1/years)-1,
               "volatility": r.std()*np.sqrt(252), "max_fall": -(wealth/wealth.cummax()-1).min(),
               "es99_daily": es99(r), "es99_usd": value*(es99(r))}
        for label, (a, b) in SCENARIOS.items():
            w = (1+r.loc[a:b]).prod()-1
            row[f"{label} return"] = w
        tgt = [c for c in path.columns if c.startswith("target_")]
        eq = [f"target_{c}" for c in EQUITY if f"target_{c}" in tgt]
        row["average_equity_target"] = float(path[eq].sum(axis=1).mean())
        rows.append(row)
    return pd.DataFrame(static), pd.DataFrame(rows)


def optimiser_choices(root=None):
    """Weights the seven-ETF optimisers chose in the v1 and v2 runs, before the four-ETF rule."""
    root = root or config.ROOT; rows = []
    for label, run in SEVEN_ETF_RUNS.items():
        for kind in OPTIMISERS:
            f = root/"results"/run/kind/"weights.json"
            if not f.exists():
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            w = data.get("weights", data)
            rows.append({"run": label, "allocation": kind, **{t: float(w.get(t, 0.)) for t in TICKERS},
                         "excluded_weight": float(sum(w.get(t, 0.) for t in DROP)),
                         "weight_hash": data.get("weight_hash", "")[:8]})
    return pd.DataFrame(rows)


def evidence(prices, macro):
    """All tables, from the frozen prices (seven ETFs) and macro panel."""
    r = log_returns(prices[TICKERS]); simple = prices[TICKERS].pct_change().dropna()
    full, stress, n_stress = correlations(r)
    static, dynamic = parity_comparison(simple)
    return {"correlation": full, "stress_correlation": stress, "stress_days": n_stress,
            "bets": bets_table(r), "spanning": spanning(r), "crises": crises(prices[TICKERS]),
            "regimes": regimes(prices[TICKERS], macro), "monthly_negative": monthly_negative(r),
            "parity_static": static, "parity_dynamic": dynamic, "optimisers": optimiser_choices(),
            "start": str(r.index[0].date()), "end": str(r.index[-1].date()), "days": len(r)}


def load_saved(price_hash, folder=None):
    """Saved tables from results/universe-r1, or None if absent or computed on other prices."""
    folder = folder or config.ROOT/"results"/OUT
    try:
        meta = json.loads((folder/"metadata.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    files = sorted(folder.glob("*.csv"))
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if meta.get("price_hash") != price_hash or meta.get("outputs") != {p.name: h(p) for p in files}:
        return None
    ev = {k: meta[k] for k in ("start", "end", "days", "stress_days")}
    for f in files:
        square = f.stem in ("correlation", "stress_correlation")
        ev[f.stem] = pd.read_csv(f, index_col=0 if square else None)
    return ev


def load():
    from .data import load_clean_prices, load_macro_data
    end = "2026-09-30"
    return load_clean_prices().loc[:end, TICKERS], load_macro_data().loc[:end]


def save(ev, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for k, v in ev.items():
        if isinstance(v, pd.DataFrame):
            v.to_csv(folder/f"{k}.csv", index=k in ("correlation", "stress_correlation"))
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    meta = {"description": "Why SPY, AGG, GLD and XLE: retrospective descriptive evidence (quanedge.universe)",
            "start": ev["start"], "end": ev["end"], "days": ev["days"], "stress_days": ev["stress_days"],
            "price_hash": h(config.ROOT/"data/clean/prices_clean.csv"),
            "source_hash": h(config.ROOT/"quanedge/universe.py"),
            "outputs": {p.name: h(p) for p in sorted(folder.glob("*.csv"))}}
    (folder/"metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prices, macro = load()
    ev = evidence(prices, macro)
    save(ev, config.ROOT/"results"/OUT)
    pd.set_option("display.width", 200, "display.max_columns", 30, "display.precision", 3)
    for k in ["bets", "spanning", "crises", "regimes", "parity_static", "parity_dynamic", "optimisers"]:
        print(f"\n== {k}\n", ev[k])
    print("\n== correlation\n", ev["correlation"].round(2), "\n== stress correlation\n", ev["stress_correlation"].round(2))
    print("\n== monthly negative\n", ev["monthly_negative"].head(10))
