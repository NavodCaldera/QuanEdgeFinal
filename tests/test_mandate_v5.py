"""Mandate v5: dynamic EWMA risk parity, monthly, as the recommendation (PLAN.md section 13g)."""
import numpy as np
import pandas as pd
import pytest
from quanedge import strategy
from quanedge.config import TICKERS
from quanedge.portfolio import replay, weight_hash, return_check, real_return


def synthetic(n=900, seed=3):
    idx = pd.bdate_range("2005-01-03", periods=n)
    x = np.random.default_rng(seed).normal(.0003, [.011, .007, .013, .003, .010, .016, .015], (n, 7))
    return pd.DataFrame(x, index=idx, columns=TICKERS)


def small(cfg):
    return dict(cfg, strategy=dict(cfg["strategy"], window=300, min_history=200))


def test_config_records_v5_policy(cfg):
    from quanedge.dynamic_parity_eval import SETTINGS
    assert cfg["mandate"] == "v5" and cfg["prereg_tag"] == "prereg-v5"
    assert cfg["es_budget"] == .03 and cfg["inflation"] == .0259 and cfg["reserve_growth"] == .0364
    assert "real_cagr_floor" not in cfg and cfg["real_return_floor"] == .01
    s = cfg["strategy"]       # exactly the v4d registration (PLAN.md 13e), not retuned
    assert (s["rebalance"], s["ewma_lambda"], s["window"], s["min_history"]) == ("M", SETTINGS["ewma_lambda"], SETTINGS["window"], SETTINGS["min_history"])
    assert cfg["universe"] == SETTINGS["universe"] and (cfg["primary"], cfg["challenger"]) == ("fhs", "garch_evt")


def test_v5_c3_uses_expected_real_over_cpi(cfg):
    floor = 1.01*1.0259-1
    assert return_check(floor+1e-9, cfg) and not return_check(floor-1e-6, cfg)
    assert real_return(.0870, cfg["inflation"]) == pytest.approx(1.087/1.0259-1)


def test_targets_use_only_data_through_their_decision_close(cfg):
    cfg = small(cfg); x = synthetic(); first = strategy.path(x, cfg)
    y = x.copy(); y.loc["2007-06-01":] *= -4
    second = strategy.path(y, cfg)
    before = strategy.targets(first).loc[:"2007-05-31"]
    pd.testing.assert_frame_equal(before, strategy.targets(second).loc[:"2007-05-31"])
    assert not strategy.targets(first).loc["2007-06-01":].equals(strategy.targets(second).loc["2007-06-01":])
    t = strategy.targets(first)
    assert np.allclose(t.sum(axis=1), 1) and (t[["EFA", "EEM", "XLK"]] == 0).all().all()
    later = t.index[1:]                                                         # after the initial target, one decision per month
    assert (later[1:].to_period("M") != later[:-1].to_period("M")).all()


def test_equal_risk_contributions_at_each_target(cfg):
    from quanedge.comparison import ewma_cov
    cfg = small(cfg); x = synthetic(); p = strategy.path(x, cfg); u = cfg["universe"]
    date = strategy.targets(p).index[5]; i = x.index.get_loc(date)
    S = ewma_cov(x[u].to_numpy()[max(0, i+1-300):i+1], .97); w = strategy.targets(p).loc[date, u].to_numpy()
    rc = w*(S@w)/(w@S@w)
    assert rc == pytest.approx(np.full(4, .25), abs=1e-5)


def test_path_stress_contributions_reconcile(cfg):
    from quanedge.stress import SCENARIOS
    idx = pd.bdate_range("2005-01-03", "2022-12-30")
    x = pd.DataFrame(np.random.default_rng(5).normal(0, .008, (len(idx), 7)), index=idx, columns=TICKERS)
    p = strategy.path(x, cfg)
    for s in strategy.path_stress(p, x, cfg["value"]):
        assert s["status"] == "ok" and s["scenario"] in SCENARIOS
        assert sum(s["contributions_usd"].values()) == pytest.approx(s["loss_usd"], abs=1e-6)


def test_reserve_path_matches_fixed_weight_replay(cfg):
    idx = pd.bdate_range("2006-12-27", "2012-12-31")
    r = pd.Series(np.random.default_rng(2).normal(.0003, .006, len(idx)), index=idx)
    got = strategy.reserve_path(r, cfg)
    assert got.index[0] == pd.Timestamp("2007-01-01")               # first full calendar year, not a December stub
    want = replay(pd.DataFrame({"SPY": r.loc["2007":]}), {"SPY": 1.}, 0, .05, reserve=(.04, cfg["reserve_growth"]))
    assert np.allclose(got.wealth, want.wealth) and np.allclose(got.spending, want.spending)


def test_strategy_forecasts_refuse_the_latest_target_hash(cfg):
    from quanedge.backtest import assess
    cfg = small(cfg); p = strategy.path(synthetic(), cfg)
    fc = pd.DataFrame({"return": np.log1p(p["return"]), "var_fhs_99": .02}, index=p.index)
    fc["weight_hash"] = strategy.strategy_hash(cfg)
    assert assess(fc, strategy.strategy_hash(cfg), "fhs", .99)["days"] == len(p)
    with pytest.raises(ValueError, match="hash mismatch"):
        assess(fc, weight_hash(strategy.latest_target(p)), "fhs", .99)
