"""Mandate v4 (prereg-v4): apply the realised real CAGR floor to every allocation of final-v3-20261030.

Only C3 changed between v3 and v4, and the selection rule, data and weights are identical, so C1, C2,
C4 and C5 are carried over from the v3 run unchanged. C3 is recomputed from each allocation's saved
replay (performance.csv: quarterly or 5-point drift rebalancing, 0% cost, no reserve withdrawals).
Writes results/v4-c3-recheck/. Run: python scripts/mandate_v4_c3_recheck.py
"""
import json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.getcwd())
import pandas as pd
from quanedge.config import frozen_policy
from quanedge.portfolio import realised_real_cagr, return_check
from quanedge.backtest import verdict

cfg = frozen_policy("prereg-v4"); run = "results/final-v3-20261030"; out = "results/v4-c3-recheck"
bundle = json.load(open(f"{run}/submission.json")); rows = {}; checks = {}
for name, p in bundle["portfolios"].items():
    if not p.get("weights"):
        continue
    r = pd.read_csv(f"{run}/{name}/performance.csv", index_col=0, parse_dates=True)["return"]
    real = realised_real_cagr(r, cfg["inflation"])
    checks[name] = dict(p["checks"], C3=return_check(p.get("expected_geometric", -1), cfg, real))
    rows[name] = {"weights": " / ".join(f"{t} {100*v:.1f}" for t, v in p["weights"].items() if v > 5e-4),
                  "weight_hash": p["weight_hash"], "realised_real_cagr_pct": round(100*real, 2),
                  **{k: checks[name][k] for k in ("C1", "C2", "C3", "C4", "C5")}}
alternatives = [(n, checks[n]) for n in ("A1_min_cvar", "A1_min_variance", "A1_max_sharpe", "A1_near_parity", "A2") if n in checks]
decision = verdict(checks["selected"], alternatives)
os.makedirs(out, exist_ok=True)
pd.DataFrame(rows).T.rename_axis("allocation").to_csv(f"{out}/checks.csv")
json.dump({"prereg_tag": "prereg-v4", "source_run": run, "real_cagr_floor": cfg["real_cagr_floor"],
           "evaluation_label": "retrospective portfolio evaluation", "decision": decision,
           "note": "C1, C2, C4, C5 carried over from the v3 run; only C3 recomputed"}, open(f"{out}/decision.json", "w"), indent=2)
print(pd.DataFrame(rows).T.drop(columns=["weight_hash"]).to_string()); print(decision)
