import numpy as np
import pandas as pd
import pytest
from quanedge.config import TICKERS
from quanedge.dynamic import step_band, cppi_budget, simulate, Targets
from quanedge.portfolio import replay, es, canonical_weights


@pytest.fixture
def cfg(cfg_v1):
    """These are mandate v1 comparisons: use the policy frozen at prereg-v1."""
    return cfg_v1

BASE = canonical_weights({"SPY": .35, "AGG": .40, "GLD": .15, "XLK": .10})


def synthetic(n=700, seed=7):
    """Calm, then a joint equity crash with stress-scale bonds, then recovery."""
    rng = np.random.default_rng(seed)
    vol = np.array([.010, .011, .014, .003, .009, .015, .014])
    x = rng.standard_normal((n, 7))*vol+.0003
    x[400:440] += np.array([-.012, -.012, -.015, -.002, -.003, -.014, -.016])
    return pd.DataFrame(x, index=pd.bdate_range("2010-01-01", periods=n), columns=TICKERS)


def test_bands_tighten_at_once_and_loosen_with_hysteresis():
    assert [step_band(d, 0) for d in (.0, .049, .05, .12, .17, .25)] == [0, 0, 1, 2, 3, 3]
    assert step_band(.12, 0) == 2
    assert step_band(.09, 2) == 2          # inside band 1, but not 2.5 points inside band 2's edge
    assert step_band(.07, 2) == 1
    assert step_band(.01, 3) == 0
    assert step_band(.14, 3) == 3
    assert cppi_budget(0) == pytest.approx(.025) and cppi_budget(.10) == pytest.approx(.0125)
    assert cppi_budget(.15) is None


def test_static_rule_matches_portfolio_replay(cfg):
    r = synthetic()
    ours = simulate(r, BASE, cfg, "static")
    theirs = replay(r, BASE, cfg["cost"], cfg["drift"])
    np.testing.assert_allclose(ours.wealth.to_numpy(), theirs.wealth.to_numpy(), rtol=0, atol=1e-12)
    np.testing.assert_allclose(ours.turnover.to_numpy(), theirs.turnover.to_numpy(), atol=1e-12)


def test_blend_meets_budget_and_flags_infeasible(cfg):
    r = synthetic(); date = r.index[-1]; x = r[TICKERS].to_numpy()
    targets = Targets(r, BASE, cfg)
    budget = (es(x, BASE)+es(x, targets.min_risk(date)))/2
    w, basis = targets(date, budget, False)
    assert basis.startswith("blend") and es(x, w) <= budget+1e-6 and w != BASE
    w, basis = targets(date, es(x, targets.min_risk(date))/2, False)
    assert basis.startswith("budget infeasible") and w == targets.min_risk(date)
    assert targets(r.index[10], .0001, False)[1].startswith("insufficient history")


@pytest.mark.parametrize("rule", ["steps", "cppi"])
def test_no_future_data_and_rule_binds(cfg, rule):
    r = synthetic(); cut = r.index[500]
    path = simulate(r, BASE, cfg, rule)
    assert (path.basis != "base").any() and path.decline.max() > .05
    changed = r.copy(); changed.loc[changed.index > cut] *= -3
    again = simulate(changed, BASE, cfg, rule)
    pd.testing.assert_frame_equal(path.loc[:cut], again.loc[:cut])
