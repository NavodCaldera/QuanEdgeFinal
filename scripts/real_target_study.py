"""Exploratory study: can a 4% real return (to cover the 4% reserve) coexist with the v3 risk limits? (task PORT-016)

For each allocation: realised real CAGR at the mandate's 3.64% inflation assumption (2005-2026 and
2017-2026), expected real return under the frozen estimator (50% mean shrinkage) and under raw means,
historical ES99, GFC drawdown and 2022 loss (buy-and-hold, quarterly+drift for CAGR), and 25-year
reserve survival (quanedge.stress.reserve_survival). Includes minimum CVaR subject to a 4% real
expected return under both estimators (v3 config, ES budget 2.5%).

Break-even arithmetic: the reserve is 4% of the initial fund taken before each year's returns,
so a constant real return r keeps real capital only if 0.96(1+r) >= 1, i.e. r >= 4.17%.
Nominal equivalent of 4% real at 3.64% inflation: 1.0364 x 1.04 - 1 = 7.79%.

Retrospective and descriptive; weights from full-sample estimates contain the tested crises.
Run from the repository root: python scripts/real_target_study.py
"""
import hashlib, json, os, sys, warnings
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yaml
import quanedge.portfolio as qp
from quanedge.config import TICKERS
from quanedge.stress import stress_tests, reserve_survival

OUT = "results/real-target-r1"
RUN = "results/final-v3-20261030"
FOUR = ["SPY", "XLE", "AGG", "GLD"]


def main():
    cfg = yaml.safe_load(open("config/final.yaml"))
    prices = pd.read_csv("data/clean/prices_clean.csv", index_col=0, parse_dates=True)[TICKERS]
    R = prices.pct_change().dropna(); monthly = (1+R).resample("ME").prod()-1; infl = cfg["inflation"]
    raw = dict(cfg, mean_shrinkage=0.)
    allocations = {n: json.load(open(f"{RUN}/{f}/weights.json"))["weights"] for n, f in
                   (("Min CVaR (v3 W_rec)", "selected"), ("Risk parity", "A1_near_parity"),
                    ("SPY 35 / AGG 50 / GLD 15", "balanced_35_50_15"), ("SPY 25 / AGG 50 / GLD 25", "permanent"),
                    ("60/40 SPY/AGG", "60_40"))}
    for t in FOUR:
        allocations[f"100% {t}"] = {t: 1.}
    selections = {}
    for label, c in (("frozen estimator", cfg), ("raw means", raw)):
        r = qp.construct(R, dict(c, real_return_target=.04))
        selections[label] = {"status": r["status"], "reason": r.get("reason")}
        if r["weights"]:
            allocations[f"Min CVaR s.t. 4% real ({label})"] = r["weights"]
    rows = []
    for name, w in allocations.items():
        w = qp.canonical_weights(w); v = np.array([w[t] for t in TICKERS])
        s = qp.replay(R, w, 0., cfg["drift"])["return"]; e = s.loc["2017":]
        cagr = lambda x: (1+x).prod()**(365.25/(x.index[-1]-x.index[0]).days)-1
        expected = {}
        for label, c in (("shrunk", cfg), ("raw", raw)):
            mu, cov = qp.estimates(R, c); expected[label] = qp.real_return(float(np.expm1(np.log1p(v@mu)-v@cov@v/2)), infl)
        st = {x["scenario"]: x for x in stress_tests(prices, w, cfg["value"])}
        sv = reserve_survival(monthly, w, cfg)["results"][-1]
        rows.append({"allocation": name, **{t: w[t] for t in FOUR}, "weight_hash": qp.weight_hash(w),
                     "real_cagr_2005_2026": qp.real_return(cagr(s), infl), "real_cagr_2017_2026": qp.real_return(cagr(e), infl),
                     "expected_real_shrunk": expected["shrunk"], "expected_real_raw": expected["raw"],
                     "es99": qp.es(R.to_numpy(), w), "gfc_drawdown": st["GFC"]["drawdown"], "rates_2022": st["Rates 2022"]["return"],
                     "reserve_all_paid_25y": sv["all_payments_funded"], "real_capital_kept_25y": sv["real_capital_preserved"]})
    M = pd.DataFrame(rows); os.makedirs(OUT, exist_ok=True); M.to_csv(f"{OUT}/real_target.csv", index=False, float_format="%.6g")
    json.dump({"task": "PORT-016", "inflation_assumption": infl, "nominal_for_4pct_real": (1+infl)*1.04-1,
               "break_even_real_with_4pct_start_of_year_draw": 1/.96-1, "selections": selections,
               "sources_sha256": {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in ("data/clean/prices_clean.csv", "config/final.yaml")},
               "label": "retrospective portfolio evaluation"}, open(f"{OUT}/metadata.json", "w"), indent=2)
    pct = lambda x: f"{100*x:.1f}%"
    lines = ["# 4% real return versus the v3 risk limits", "",
             f"Inflation assumption {pct(infl)} (mandate v3). 4% real = {pct((1+infl)*1.04-1)} nominal. Break-even real return with the 4% start-of-year reserve: {100*(1/.96-1):.2f}%.", "",
             "| Allocation | Weights (SPY/XLE/AGG/GLD) | Real CAGR 05-26 | 17-26 | Expected real (shrunk) | (raw) | ES99 | GFC fall | 2022 | All reserves paid 25y | Real capital kept |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in M.iterrows():
        lines.append(f"| {r.allocation} | {' / '.join(f'{100*r[t]:.0f}' for t in FOUR)} | {pct(r.real_cagr_2005_2026)} | {pct(r.real_cagr_2017_2026)} | {pct(r.expected_real_shrunk)} | {pct(r.expected_real_raw)} | {100*r.es99:.2f}% | {pct(r.gfc_drawdown)} | {pct(r.rates_2022)} | {pct(r.reserve_all_paid_25y)} | {pct(r.real_capital_kept_25y)} |")
    lines += ["", "Limits: ES99 2.5%, GFC drawdown 20%. Retrospective; weights estimated on data containing these crises."]
    open(f"{OUT}/report.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines)); print(selections)


if __name__ == "__main__":
    main()
