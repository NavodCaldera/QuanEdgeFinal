import numpy as np
import pandas as pd
import pytest
from quanedge.backtest import assess
from quanedge.overlay_eval import strategy_hash, window_stress, walk_forward
from quanedge.portfolio import weight_hash
from test_dynamic import synthetic, BASE


@pytest.fixture
def cfg(cfg_v1):
    """These are mandate v1 comparisons: use the policy frozen at prereg-v1."""
    return cfg_v1


def test_strategy_hash_is_distinct_and_forecasts_refuse_other_hashes():
    sh = strategy_hash(BASE)
    assert sh != weight_hash(BASE) and sh == strategy_hash(dict(reversed(list(BASE.items()))))
    fc = pd.DataFrame({"return": [-.02, .01], "var_fhs_99": [.01, .01], "weight_hash": weight_hash(BASE)},
                      index=pd.bdate_range("2020-01-01", periods=2))
    with pytest.raises(ValueError):
        assess(fc, sh)


def test_window_stress_uses_path_from_scenario_start():
    dates = pd.bdate_range("2007-10-08", "2009-03-10")
    wealth = pd.Series(np.linspace(1, .8, len(dates)), index=dates); wealth.iloc[-1] = .9
    rows = window_stress(pd.DataFrame({"wealth": wealth}), 1e7)
    gfc = rows[0]; w = wealth.loc["2007-10-09":"2009-03-09"]
    assert gfc["return"] == pytest.approx(w.iloc[-1]/w.iloc[0]-1)
    assert gfc["drawdown"] == pytest.approx((w/w.iloc[0]).min()-1)
    assert all(r["status"] == "incomplete data coverage" for r in rows[1:])


def test_walk_forward_year_ignores_later_data(cfg):
    r = synthetic(1400); r.index = pd.bdate_range("2014-06-02", periods=len(r))
    _, years = walk_forward(r, cfg)
    changed = r.copy(); changed.loc["2018-01-01":] *= -2
    _, again = walk_forward(changed, cfg)
    assert [y["weights"] for y in years if y["year"] <= 2018] == [y["weights"] for y in again if y["year"] <= 2018]
