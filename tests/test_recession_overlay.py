import numpy as np
import pandas as pd
import pytest
from quanedge import recession_overlay as ro
from quanedge.comparison import dynamic_parity_path

CFG = {"universe": ["SPY", "AGG", "GLD", "XLE"], "cost": 0.0,
       "strategy": {"rebalance": "M", "ewma_lambda": .97, "window": 750, "min_history": 300}}


def synthetic(n=900, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    r = pd.DataFrame(rng.normal(3e-4, [.012, .003, .009, .016], (n, 4)), idx, CFG["universe"])
    for t in ("EFA", "EEM", "XLK"):
        r[t] = 0.
    prices = (1 + r).cumprod()*100
    return r, prices


def test_bond_equivalent_known_value():
    # 5% discount, 91-day bill: 365*0.05/(360-91*0.05) = 5.1339...%
    assert ro.bond_equivalent(5.0) == pytest.approx(100*365*.05/(360-91*.05))
    assert ro.bond_equivalent(5.0) > 5.0


def test_overlay_off_reproduces_v5_core_path():
    r, p = synthetic()
    spread = pd.Series(1.0, pd.date_range("2008-01-31", "2014-12-31", freq="ME"))
    path, flags = ro.overlay_path(r, p, spread, CFG, use_overlay=False)
    base = dynamic_parity_path(r[CFG["universe"]], "M", .97, 750, 300, 0.)
    assert not flags.any()
    np.testing.assert_allclose(path["return"].to_numpy(), base["return"].to_numpy(), atol=1e-12)
    assert (path.cash == 0).all()


def test_no_warning_means_no_overlay_and_inverted_curve_can_switch_on():
    r, p = synthetic()
    pos = pd.Series(1.0, pd.date_range("2008-01-31", "2014-12-31", freq="ME"))
    _, flags = ro.overlay_path(r, p, pos, CFG)
    assert not flags.any()
    neg = -pos
    path, flags = ro.overlay_path(r, p, neg, CFG)
    if flags.any():                     # whenever ON: cash equals half of the SPY and XLE targets
        d = flags[flags].index[0]
        row = path.loc[d]
        assert row.cash == pytest.approx(.5*(row.target_SPY + row.target_XLE), rel=1e-9)
        assert row.SPY == pytest.approx(.5*row.target_SPY, rel=1e-9)
        assert row[["SPY", "AGG", "GLD", "XLE"]].sum() + row.cash == pytest.approx(1.0)


def test_flags_use_only_data_through_each_decision():
    r, p = synthetic()
    spread = pd.Series(-0.5, pd.date_range("2008-01-31", "2014-12-31", freq="ME"))
    decisions = pd.DatetimeIndex(p.resample("ME").last().index)
    decisions = pd.DatetimeIndex([p.index[p.index <= d][-1] for d in decisions if (p.index <= d).any()])
    cut = decisions[len(decisions)//2]
    f1 = ro.overlay_flags(decisions, p["SPY"], spread)
    p2 = p.copy(); p2.loc[p2.index > cut, "SPY"] *= 0.3          # crash after the cut date
    s2 = spread.copy(); s2.loc[s2.index > cut] = 5.0
    f2 = ro.overlay_flags(decisions, p2["SPY"], s2)
    pd.testing.assert_series_equal(f1.loc[:cut], f2.loc[:cut])


def test_decision_uses_its_own_month_end_close():
    # the last trading day (28 Feb 2020) precedes the calendar label (29 Feb); the February close must be used
    idx = pd.bdate_range("2019-01-01", "2020-03-31")
    spy = pd.Series(100.0, idx); spy.loc["2020-02-28"] = 50.0          # only the Feb close is below its mean
    spread = pd.Series(-1.0, pd.date_range("2018-01-31", "2020-03-31", freq="ME"))
    f = ro.overlay_flags(pd.DatetimeIndex([pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-28")]), spy, spread)
    assert not f.loc["2020-01-31"] and f.loc["2020-02-28"]
