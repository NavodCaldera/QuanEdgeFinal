import numpy as np
import pandas as pd
import pytest
from quanedge.backtest import assess
from quanedge.hedging import vol_target
from quanedge.overlay_eval import strategy_hash as v1_strategy_hash
from quanedge.parity_overlay import strategy_hash, walk_forward, window
from quanedge.portfolio import canonical_weights, feasible, weight_hash
from test_dynamic import synthetic

PARITY = canonical_weights({"SPY": .14, "AGG": .61, "GLD": .16, "XLE": .09})


def test_strategy_hash_is_distinct_and_refused_for_other_hashes():
    sh = strategy_hash(PARITY)
    assert sh not in (weight_hash(PARITY), v1_strategy_hash(PARITY))
    fc = pd.DataFrame({"return": [-.02, .01], "var_fhs_99": [.01, .01], "weight_hash": weight_hash(PARITY)},
                      index=pd.bdate_range("2020-01-01", periods=2))
    with pytest.raises(ValueError):
        assess(fc, sh)


def test_v3_overlay_moves_freed_equity_to_agg_and_stays_in_universe(cfg):
    path = vol_target(synthetic(), PARITY, cfg)
    scaled = path[path.basis != "base"]
    assert len(scaled) > 0
    assert np.allclose(scaled.GLD, PARITY["GLD"], atol=1e-6)        # no caps under v3: GLD untouched
    assert (scaled.AGG > PARITY["AGG"]).all()
    assert all(feasible(dict(zip(path.columns[-7:], row)), cfg) for row in path.iloc[:, -7:].drop_duplicates().to_numpy())


def test_window_requires_exact_coverage():
    wealth = pd.Series([1., .9, .95, .8], index=pd.bdate_range("2020-01-01", periods=4))
    ret, dd = window(wealth, "2020-01-01", "2020-01-06")
    assert ret == pytest.approx(-.2) and dd == pytest.approx(-.2)
    assert window(wealth, "2019-12-31", "2020-01-06") == (None, None)


def test_walk_forward_year_ignores_later_data(cfg):
    r = synthetic(1400); r.index = pd.bdate_range("2014-06-02", periods=len(r))
    _, years = walk_forward(r, cfg)
    changed = r.copy(); changed.loc["2018-01-01":] *= -2
    _, again = walk_forward(changed, cfg)
    assert [y["weights"] for y in years if y["year"] <= 2018] == [y["weights"] for y in again if y["year"] <= 2018]
