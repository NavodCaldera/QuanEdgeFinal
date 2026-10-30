import numpy as np
import pandas as pd
import pytest
from quanedge.config import TICKERS
from quanedge.dynamic import simulate
from quanedge.hedging import with_xle, scaled, robust, vol_target, EQUITY
from quanedge.portfolio import canonical_weights, feasible
from test_dynamic import synthetic, BASE

CORNER = canonical_weights({"SPY": .15, "AGG": .70, "GLD": .15})


def test_xle_sleeve_is_funded_from_spy():
    w = with_xle(CORNER, .10)
    assert w["SPY"] == pytest.approx(.05) and w["XLE"] == pytest.approx(.10) and w["AGG"] == .70
    assert with_xle(CORNER, .20) is None


def test_scaling_fills_agg_then_gold_and_respects_caps(cfg):
    w = scaled(BASE, .5, cfg)
    assert sum(w[t] for t in EQUITY) == pytest.approx(.225) and w["AGG"] == pytest.approx(.625)
    assert feasible(w, cfg) and scaled(BASE, 1., cfg) == BASE
    assert scaled(CORNER, .3, cfg) == CORNER          # AGG and GLD already at their caps
    w = scaled(canonical_weights({"SPY": .40, "AGG": .55, "GLD": .05}), 0., cfg)
    assert w["AGG"] == pytest.approx(.70) and w["GLD"] == pytest.approx(.15) and w["SPY"] == pytest.approx(.15)


def test_scenario_caps_hold_and_infeasibility_is_reported(cfg):
    r = synthetic()
    shocks = {"crash": np.array([-.5, -.5, -.6, .05, .2, -.45, -.5]),
              "inflation": np.array([-.25, -.28, -.28, -.15, -.09, .49, -.32])}
    result = robust(r, cfg, shocks, .12)
    assert result["status"] == "ok" and feasible(result["weights"], cfg)
    w = np.array([result["weights"][t] for t in TICKERS])
    assert all(-w@s <= .12+1e-6 for s in shocks.values())
    assert robust(r, cfg, shocks, .01)["status"] == "infeasible"


def test_volatility_overlay_uses_no_future_data(cfg):
    r = synthetic(); cut = r.index[500]
    path = vol_target(r, BASE, cfg)
    assert (path.basis != "base").any()
    changed = r.copy(); changed.loc[changed.index > cut] *= -3
    pd.testing.assert_frame_equal(path.loc[:cut], vol_target(changed, BASE, cfg).loc[:cut])


def test_overlay_at_capped_corner_equals_static(cfg):
    r = synthetic()
    np.testing.assert_allclose(vol_target(r, CORNER, cfg).wealth, simulate(r, CORNER, cfg).wealth, atol=1e-12)
