"""Standalone long-history context, added after preregistration (task CTX-001).

Nothing here feeds the frozen run: no weights, forecasts, gates or verdicts read
these outputs. The snapshot lives under context/ rather than data/ because the
final pipeline hashes every file below data/ into its data identity.

    python -m quanedge.context --download   # new Yahoo snapshot, then analysis
    python -m quanedge.context              # analysis from the saved snapshot
"""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from . import config
from .config import TICKERS
from .portfolio import estimates, hurdle, weight_hash

def raw_dir():return config.ROOT/"context/raw"
def out_dir():return config.ROOT/"context/results"
SNAPSHOT_END = "2026-09-30"          # identical to the frozen snapshot; nothing later is kept
FROZEN_START = "2005-01-03"          # first common date of the frozen panel
LABEL = "Standalone historical context, added after preregistration; not part of the frozen analytical run."
# Project-chosen windows (US equity peak-to-trough where applicable); labels, not organiser definitions.
CRISES = {
    "Dot-com bear market": ("2000-03-24", "2002-10-09"),
    "September 2001 market closure": ("2001-09-10", "2001-09-21"),
    "Global financial crisis": ("2007-10-09", "2009-03-09"),
    "COVID crash": ("2020-02-19", "2020-03-23"),
    "2022 rate-hiking drawdown": ("2022-01-03", "2022-10-12"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(folder=None, start="1990-01-01"):
    """Fetch every eligible ticker's full adjusted history; keep each ETF's own dates."""
    import yfinance as yf
    folder = folder or raw_dir()
    retrieved = datetime.now(timezone.utc).isoformat()
    raw = yf.download(TICKERS, start=start, end="2026-10-01", auto_adjust=True, actions=False, progress=False)
    px = (raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw)[TICKERS]
    px.index = pd.DatetimeIndex(px.index).tz_localize(None).normalize()
    px = px.loc[:SNAPSHOT_END].dropna(how="all")      # rows where no ETF traded carry nothing
    missing = [t for t in TICKERS if px[t].notna().sum() == 0]
    if missing:
        raise RuntimeError(f"Download returned no prices for {missing}; no substitute source is used.")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/"prices_full_history.csv"
    px.to_csv(path, lineterminator="\n", float_format="%.10g")
    manifest = {
        "label": LABEL, "source": "Yahoo Finance via yfinance", "retrieved_at_utc": retrieved,
        "requested_start": start, "requested_end_exclusive": "2026-10-01", "cap_inclusive": SNAPSHOT_END,
        "adjustment": "auto_adjust=True: Close adjusted for splits and distributions (frozen-pipeline convention)",
        "missing_values": "NaN before each ETF's first price and on dates it did not trade; never filled",
        "tickers": TICKERS, "rows": int(len(px)),
        "actual_dates": {t: [px[t].first_valid_index().date().isoformat(), px[t].last_valid_index().date().isoformat()] for t in TICKERS},
        "versions": {"python": platform.python_version(), "yfinance": yf.__version__, "pandas": pd.__version__, "numpy": np.__version__},
        "files": {path.name: sha256(path)},
    }
    (folder/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return px


def load(folder=None):
    """Saved snapshot after hash check, or None when it is absent or altered."""
    folder = folder or raw_dir()
    path, meta = folder/"prices_full_history.csv", folder/"manifest.json"
    if not path.exists() or not meta.exists():
        return None
    if json.loads(meta.read_text(encoding="utf-8"))["files"].get(path.name) != sha256(path):
        return None
    px = pd.read_csv(path, index_col=0, parse_dates=True)
    validate(px)
    return px


def validate(px):
    if not px.index.is_monotonic_increasing or px.index.has_duplicates:
        raise ValueError("dates must be unique and increasing")
    if list(px.columns) != TICKERS:
        raise ValueError("columns must be the eligible tickers in fixed order")
    if px.index.max() > pd.Timestamp(SNAPSHOT_END):
        raise ValueError("context data must end on or before the frozen snapshot end")
    values = px.to_numpy()[px.notna().to_numpy()]     # NaN only marks "no price on this date"
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("prices must be finite and positive")


def own_returns(series):
    """Simple returns between an ETF's consecutive observed prices; nothing before its first price."""
    s = series.dropna()
    return s.pct_change().iloc[1:]


def audit(px):
    rows = []
    for t in TICKERS:
        s = px[t].dropna(); r = own_returns(px[t])
        inside = px.loc[s.index[0]:s.index[-1], t]
        runs = (s.diff() != 0).cumsum().value_counts()
        rows.append({"ticker": t, "observations": len(s), "gaps_inside_history": int(inside.isna().sum()),
                     "stale_runs_5plus": int((runs >= 5).sum()), "moves_over_15pct": int((r.abs() > .15).sum()),
                     "nonpositive_prices": int((s <= 0).sum())})
    return pd.DataFrame(rows)


def coverage(px):
    rows = []
    for t in TICKERS:
        s = px[t].dropna(); first, last = s.index[0], s.index[-1]
        row = {"ticker": t, "first_price_date": first.date(), "first_return_date": s.index[1].date(),
               "last_date": last.date(), "price_observations": len(s),
               "omitted_before_frozen_start": int((s.index < pd.Timestamp(FROZEN_START)).sum())}
        for name, (a, b) in CRISES.items():
            row[name] = "full" if first <= pd.Timestamp(a) else "partial" if first <= pd.Timestamp(b) else "none"
        rows.append(row)
    return pd.DataFrame(rows)


def drawdown(series):
    """Largest peak-to-trough fall of one price path, with recovery to the prior peak."""
    s = series.dropna()
    dd = s/s.cummax() - 1
    trough = dd.idxmin(); peak = s.loc[:trough].idxmax()
    after = s.loc[trough:]; back = after.index[after >= s[peak]]
    recovery = back[0] if len(back) else None
    end = recovery if recovery is not None else s.index[-1]
    return {"max_drawdown": float(dd.min()), "peak": peak.date(), "trough": trough.date(),
            "recovery": recovery.date() if recovery is not None else None, "recovered": recovery is not None,
            "under_water_trading_days": int(((s.index > peak) & (s.index <= end)).sum()),
            "under_water_years": round((end - peak).days/365.25, 2)}


def drawdowns(px):
    rows = []
    for t in TICKERS:
        for sample, s in [("full history", px[t]), ("since 2005", px[t].loc[FROZEN_START:])]:
            r = own_returns(s)
            rows.append({"ticker": t, "sample": sample, "start": s.dropna().index[0].date(), **drawdown(s),
                         "worst_daily_return": float(r.min()), "worst_daily_date": r.idxmin().date()})
    return pd.DataFrame(rows)


def overlap_check(px, frozen):
    """Compare returns, not price levels: later adjustments can rescale earlier adjusted prices."""
    rows = []
    for t in TICKERS:
        a = px[t].reindex(frozen.index).pct_change(); b = frozen[t].pct_change()
        d = (a - b).dropna().abs()
        rows.append({"ticker": t, "compared_returns": len(d), "missing_in_context": int(px[t].reindex(frozen.index).isna().sum()),
                     "max_abs_difference": float(d.max()), "days_over_1bp": int((d > 1e-4).sum()),
                     "days_over_10bp": int((d > 1e-3).sum()), "largest_on": d.idxmax().date() if len(d) else None})
    return pd.DataFrame(rows)


def dotcom_partial(run, px, window="Dot-com bear market"):
    """Buy-and-hold loss of only the sleeves that existed; the unobserved remainder is not estimated."""
    bundle = json.loads((run/"submission.json").read_text(encoding="utf-8")); value = bundle["policy"]["value"]
    a, b = (pd.Timestamp(d) for d in CRISES[window]); rows = []
    for name in dict.fromkeys(["selected", bundle["decision"].get("alternative", "selected")]):
        w = bundle["portfolios"][name]["weights"]
        for t, v in w.items():
            if not v:
                continue
            s = px[t].dropna(); seen = s.index[0] <= a
            path = s.loc[a:b] if seen else None
            change = float(path.iloc[-1]/path.iloc[0] - 1) if seen else None
            rows.append({"portfolio": name, "weight_hash": weight_hash(w), "window": f"{window} {a.date()} to {b.date()}",
                         "ticker": t, "weight": v, "observed": seen, "sleeve_return": change,
                         "sleeve_loss_usd": -value*v*change if seen else None,
                         "sleeve_max_drawdown": float((path/path.cummax() - 1).min()) if seen else None,
                         "note": "partial: unobserved sleeves are not estimated and no proxy is used; not a portfolio loss"})
    return pd.DataFrame(rows)


def estimator_sensitivity(run, prices):
    """Fixed-weight expected returns by window and shrinkage, recomputed with the frozen estimator.

    The frozen run exported this table only for its reported allocation; the recomputation is
    checked against that file before W_rec rows are added."""
    bundle = json.loads((run/"submission.json").read_text(encoding="utf-8")); cfg = bundle["policy"]
    returns = prices.pct_change().dropna(); end = pd.Timestamp(cfg["snapshot_end"]); rows = []
    for name in ["selected", bundle["decision"].get("alternative", "selected")]:
        w = bundle["portfolios"][name]["weights"]
        if weight_hash(w) != bundle["portfolios"][name]["weight_hash"]:
            raise ValueError(f"{name}: weight hash mismatch")
        v = np.array([w[t] for t in TICKERS])
        for shrink in [0., .25, .5, .75, 1.]:
            for years in [5, 10, None]:
                sample = returns if years is None else returns.loc[returns.index > end - pd.DateOffset(years=years)]
                mu, cov = estimates(sample, dict(cfg, mean_shrinkage=shrink))
                net = float(v@mu - cfg["cost"]*cfg["expected_annual_turnover"])
                rows.append({"portfolio": name, "weight_hash": bundle["portfolios"][name]["weight_hash"],
                             "mean_shrinkage": shrink, "lookback_years": years or "all", "expected_arithmetic": net,
                             "expected_geometric": float(np.expm1(np.log1p(net) - v@cov@v/2)),
                             "hurdle": hurdle(cfg["inflation"], cfg["spending"]), "frozen_setting": shrink == cfg["mean_shrinkage"]})
        if name == "selected" and name == bundle["decision"].get("alternative", "selected"):
            break
    table = pd.DataFrame(rows); table["meets_hurdle"] = table.expected_geometric >= table.hurdle
    saved = pd.read_csv(run/"estimator_sensitivity.csv")
    mine = table[table.weight_hash == saved.weight_hash.iloc[0]]
    if len(mine) != len(saved) or not np.allclose(mine.expected_geometric.to_numpy(), saved.expected_geometric.to_numpy(), rtol=0, atol=1e-12):
        raise ValueError("recomputation does not reproduce the frozen estimator_sensitivity.csv")
    return table


def risk_windows(run, log_returns, years=(3, 5, 10, None)):
    """Descriptive, non-gating historical/normal one-day VaR99/ES99 for fixed allocations by window."""
    from .risk import fit_models, risk_table
    bundle = json.loads((run/"submission.json").read_text(encoding="utf-8")); cfg = bundle["policy"]
    end = pd.Timestamp(cfg["snapshot_end"]); rows = []
    for name in dict.fromkeys(["selected", bundle["decision"].get("alternative", "selected")]):
        w = bundle["portfolios"][name]["weights"]
        for y in years:
            sample = log_returns if y is None else log_returns.loc[log_returns.index > end - pd.DateOffset(years=y)]
            t = risk_table(fit_models(sample, w, methods=["historical", "normal"]), value=cfg["value"])
            for r in t[t.alpha == .99].itertuples():
                rows.append({"portfolio": name, "weight_hash": weight_hash(w), "window": f"{y} years" if y else "full common history",
                             "start": sample.index[0].date(), "observations": len(sample), "method": r.method,
                             "var_pct": r.var_pct, "es_pct": r.es_pct, "var_usd": r.var_usd, "es_usd": r.es_usd,
                             "status": r.status, "note": "descriptive, non-gating; no traffic light"})
    return pd.DataFrame(rows)


def run(run_dir=None, refresh=False, out=None):
    root = config.ROOT; out = out or out_dir()
    run_dir = run_dir or root/"results"/(root/"results/latest.txt").read_text(encoding="utf-8").strip()
    px = download() if refresh else load()
    if px is None:
        raise SystemExit("No verified context snapshot; run with --download (needs network access).")
    validate(px)
    frozen = pd.read_csv(root/"data/clean/prices_clean.csv", index_col=0, parse_dates=True)
    logs = pd.read_csv(root/"data/clean/log_returns.csv", index_col=0, parse_dates=True)
    out.mkdir(parents=True, exist_ok=True)
    tables = {"coverage": coverage(px), "audit": audit(px), "drawdowns": drawdowns(px), "overlap_check": overlap_check(px, frozen),
              "dotcom_partial": dotcom_partial(run_dir, px), "estimator_sensitivity": estimator_sensitivity(run_dir, frozen), "risk_windows": risk_windows(run_dir, logs)}
    for name, table in tables.items():
        table.to_csv(out/f"{name}.csv", index=False, lineterminator="\n")
    manifest = {"label": LABEL, "created_at_utc": datetime.now(timezone.utc).isoformat(), "parent_run": run_dir.name,
                "parent_manifest_sha256": sha256(run_dir/"manifest.json"),
                "context_snapshot_sha256": sha256(raw_dir()/"prices_full_history.csv"),
                "frozen_prices_sha256": sha256(root/"data/clean/prices_clean.csv"),
                "files": {f"{n}.csv": sha256(out/f"{n}.csv") for n in tables}}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return tables


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--download", action="store_true", help="fetch a new Yahoo snapshot first")
    args = parser.parse_args()
    for name, table in run(refresh=args.download).items():
        print(f"\n{name}\n{table.to_string(index=False)}")
