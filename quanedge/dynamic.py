"""Drawdown-contingent risk budgets: exploratory mandate-change comparison (task PORT-003).

Proposed rule, not part of the frozen prereg-v1 policy. Nothing in the frozen run
reads these outputs. Every result is a retrospective portfolio evaluation: base
weights were estimated on the full sample and the rule was designed after the
data had been seen.

Rule: the 99% one-day historical ES budget (fraction of current NAV) depends on
the decline from the high-water mark of the pre-spending wealth index. When the
base allocation exceeds the budget, the target is the largest blend of base and
minimum-CVaR weights (same bounds, trailing data only) that meets it.

    python -m quanedge.dynamic            # writes results/dynamic-risk-r1/
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yaml
from . import config
from .config import TICKERS
from .portfolio import construct, canonical_weights, weight_hash, es

LABEL = ("Exploratory mandate-change comparison, added after preregistration; "
         "retrospective portfolio evaluation, not part of the frozen analytical run.")
# Upper decline bound of each band and its ES99 budget; None means minimum-risk weights.
TIERS = ((.05, .025), (.10, .020), (.15, .015), (.20, None))
EMERGENCY = .15          # at or beyond this decline, re-target immediately rather than at quarter-end
HYSTERESIS = .025        # loosen to band j only once the decline is this far inside it
CPPI_MULTIPLIER = 8      # budget = remaining room / 8; 2022 loss was about 10x ES99, COVID about 5x
LIMIT = .20
MIN_HISTORY = 252
SCENARIOS = {"GFC": ("2007-10-09", "2009-03-09"), "COVID": ("2020-02-19", "2020-03-23"),
             "Rates 2022": ("2022-01-03", "2022-10-12")}


def raw_band(decline):
    return next((i for i, (hi, _) in enumerate(TIERS) if decline < hi), len(TIERS)-1)


def step_band(decline, previous):
    """Tighten at once; loosen only to the band whose bound the decline is HYSTERESIS inside."""
    raw = raw_band(decline)
    if previous is None or raw >= previous:
        return raw
    relaxed = next((i for i, (hi, _) in enumerate(TIERS) if decline < hi-HYSTERESIS), len(TIERS)-1)
    return min(previous, max(raw, relaxed))


def cppi_budget(decline):
    room = LIMIT-decline
    return None if decline >= EMERGENCY else min(TIERS[0][1], max(room, 0)/CPPI_MULTIPLIER)


class Targets:
    """Weights meeting an ES budget, estimated only from returns up to the decision date."""
    def __init__(self, returns, base, cfg):
        self.r, self.base, self.cfg, self.cache = returns, base, cfg, {}

    def min_risk(self, date):
        if date not in self.cache:
            result = construct(self.r.loc[:date], self.cfg, "min_cvar")
            if result["weights"] is None:
                raise RuntimeError(f"minimum-CVaR solve failed at {date.date()}: {result['reason']}")
            self.cache[date] = result["weights"]
        return self.cache[date]

    def __call__(self, date, budget, emergency):
        x = self.r.loc[:date][TICKERS].to_numpy()
        if len(x) < MIN_HISTORY:
            return self.base, "insufficient history; base weights"
        if emergency:
            return self.min_risk(date), "minimum risk"
        if es(x, self.base) <= budget:
            return self.base, "base"
        low = self.min_risk(date)
        if es(x, low) > budget:
            return low, "budget infeasible; minimum risk"
        a, b = 0., 1.               # ES is convex in weights, so feasible blends form an interval from 0
        mix = lambda s: {t: s*self.base[t]+(1-s)*low[t] for t in TICKERS}
        for _ in range(40):
            m = (a+b)/2
            a, b = (m, b) if es(x, mix(m)) <= budget else (a, m)
        return canonical_weights(mix(a)), f"blend {a:.3f}"


def simulate(returns, base, cfg, rule="static"):
    """Same accounting as portfolio.replay: quarter-end or 5-point drift rebalancing, costs on
    turnover. Decisions use returns through the day's close and trade at that close."""
    cost, drift = cfg["cost"], cfg["drift"]
    targets = Targets(returns, base, cfg)
    target = base; positions = np.array([base[t] for t in TICKERS])
    nav = peak = 1.; band = 0; budget = TIERS[0][1]; basis = "base"; rows = []; dates = returns.index
    for i, (date, row) in enumerate(returns[TICKERS].iterrows()):
        old = nav; positions = positions*(1+row.to_numpy()); gross = positions.sum()
        decline = 1-gross/peak
        quarter_end = i == len(dates)-1 or dates[i+1].quarter != date.quarter
        retarget = False
        if rule == "flat":          # fixed 2.5% budget re-checked each quarter: isolates the decline bands
            retarget = quarter_end
        elif rule == "steps":
            new = step_band(decline, band)
            if new != band and (quarter_end or new >= raw_band(EMERGENCY)):
                band, retarget = new, True
            budget = TIERS[band][1]
        elif rule == "cppi":
            new = cppi_budget(decline)
            if quarter_end or (new is None and budget is not None):
                retarget, budget = True, new
        if retarget:
            target, basis = targets(date, budget, budget is None)
        w = np.array([target[t] for t in TICKERS]); turnover = 0.
        current = positions/gross
        if retarget or quarter_end or np.max(abs(current-w)) > drift:
            turnover = float(np.abs(w-current).sum())
            positions = w*gross*(1-cost*turnover)
        nav = float(positions.sum()); peak = max(peak, nav)
        rows.append((date, nav/old-1, nav, 1-nav/peak, turnover, band if rule == "steps" else None,
                     budget, basis, *w))
    cols = ["date", "return", "wealth", "decline", "turnover", "band", "es_budget", "basis", *TICKERS]
    return pd.DataFrame(rows, columns=cols).set_index("date")


def metrics(path, spending):
    x = path["return"]; years = (x.index[-1]-x.index[0]).days/365.25
    worst = path.decline.sort_values(ascending=False)
    december_ends = sum(1 for i, d in enumerate(x.index[:-1]) if d.month == 12 and x.index[i+1].year != d.year)
    yearly = (1+x).groupby(x.index.year).prod()-1
    out = {"cagr": float(path.wealth.iloc[-1]**(1/years)-1), "annual_volatility": float(x.std()*np.sqrt(252)),
           "maximum_decline": float(path.decline.max()),
           "average_worst_5pct_decline": float(worst.iloc[:max(1, int(len(worst)*.05))].mean()),
           "days_beyond_limit": int((path.decline > LIMIT).sum()),
           "worst_calendar_year": float(yearly.min()), "worst_year": int(yearly.idxmin()),
           "annual_turnover": float(path.turnover.sum()/years), "target_changes": int((path[TICKERS].diff().abs().sum(axis=1) > 1e-9).sum()),
           "share_days_below_base": float((path.basis.ne("base") & ~path.basis.str.startswith("insufficient")).mean()),
           "end_nav_usd_after_spending": float(path.wealth.iloc[-1]*(1-spending)**december_ends*config.PORTFOLIO_VALUE)}
    for name, (a, b) in SCENARIOS.items():
        w = path.wealth.loc[:b]; start = w.loc[:a].iloc[-2] if len(w.loc[:a]) > 1 else 1.
        out[f"{name}_return"] = float(w.iloc[-1]/start-1)
    if path.band.notna().any():
        out["band_share"] = {f"band_{int(k)}": float(v) for k, v in path.band.value_counts(normalize=True).sort_index().items()}
    return out


def portfolios(returns, cfg):
    folder = config.RESULTS_DIR/"final-20261027"
    load = lambda n: json.loads((folder/n/"weights.json").read_text())["weights"]
    open_cfg = dict(cfg, single_cap=1., gold_cap=1., sector_cap=1., agg_min=0., agg_max=1., equity_cap=1.)
    unconstrained = construct(returns, open_cfg)
    if unconstrained["weights"] is None:
        raise RuntimeError("open-bounds solve failed: "+str(unconstrained["reason"]))
    return {"A1_min_cvar": (canonical_weights(load("A1_min_cvar")), cfg),
            "selected": (canonical_weights(load("selected")), cfg),
            "open_bounds_es2.5": (unconstrained["weights"], open_cfg)}


def run(out=None):
    from .data import load_clean_prices
    cfg = yaml.safe_load((config.ROOT/"config/final.yaml").read_text())
    prices = load_clean_prices().loc[:cfg["snapshot_end"], TICKERS]
    returns = prices.pct_change().dropna()
    out = out or config.RESULTS_DIR/"dynamic-risk-r1"; out.mkdir(parents=True, exist_ok=True)
    rows, hashes = [], {}
    for name, (w, bounds_cfg) in portfolios(returns, cfg).items():
        hashes[name] = {"weights": w, "weight_hash": weight_hash(w)}
        for rule in ("static", "flat", "steps", "cppi"):
            path = simulate(returns, w, bounds_cfg, rule)
            path.to_csv(out/f"{name}__{rule}.csv", float_format="%.10g")
            rows.append({"portfolio": name, "rule": rule, **metrics(path, cfg["spending"])})
    table = pd.json_normalize(rows)
    table.to_csv(out/"comparison.csv", index=False, float_format="%.6g")
    meta = {"label": LABEL, "evaluation_label": "retrospective portfolio evaluation", "task": "PORT-003",
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_returns_sha256": hashlib.sha256(returns.to_numpy().tobytes()).hexdigest(),
            "period": [str(returns.index[0].date()), str(returns.index[-1].date())],
            "portfolios": hashes, "tiers": TIERS, "emergency": EMERGENCY, "hysteresis": HYSTERESIS,
            "cppi_multiplier": CPPI_MULTIPLIER, "limit": LIMIT, "min_history": MIN_HISTORY,
            "es": "historical 99% one-day, expanding window from 2005, simple returns",
            "decline_basis": "pre-spending wealth index after costs, from running high-water mark",
            "timing": "decision on returns through the close; trade at that close",
            "spending": "4% at December year-ends applied to reported end NAV only; rule unaffected"}
    (out/"metadata.json").write_text(json.dumps(meta, indent=2)+"\n", encoding="utf-8")
    return table


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(run().to_string())


if __name__ == "__main__":
    main()
