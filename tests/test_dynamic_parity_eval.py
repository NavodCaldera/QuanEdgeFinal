"""Candidates v4d/v4e: weekly and monthly dynamic risk parity paths, timing and identities."""
import numpy as np
import pandas as pd
import pytest
from quanedge.comparison import dynamic_parity_path
from quanedge.dynamic_parity_eval import strategy_hash, as_weights


@pytest.fixture
def returns():
    rng=np.random.default_rng(11)
    return pd.DataFrame(rng.normal(.0003,[.01,.003,.008,.015],(800,4)),
                        index=pd.bdate_range("2012-01-02",periods=800),columns=["SPY","AGG","GLD","XLE"])


def test_weekly_and_monthly_decisions(returns):
    m=dynamic_parity_path(returns,"M");w=dynamic_parity_path(returns,"W")
    assert m.index[0]==w.index[0]==returns.index[500]
    assert w.rebalanced.sum()>3*m.rebalanced.sum()
    days=w.index[w.rebalanced]
    assert all(d.to_period("W")!=n.to_period("W") for d,n in zip(days,[returns.index[returns.index.get_loc(d)+1] for d in days]))
    for p in (m,w):
        holdings=p[["SPY","AGG","GLD","XLE"]].sum(axis=1);targets=p[[f"target_{t}" for t in ["SPY","AGG","GLD","XLE"]]]
        assert np.allclose(holdings,1) and np.allclose(targets.sum(axis=1),1) and (targets.to_numpy()>0).all()
        assert p.wealth.iloc[-1]==pytest.approx((1+p["return"]).prod())


def test_weekly_uses_only_past_data(returns):
    base=dynamic_parity_path(returns,"W");cut=returns.index[650]
    shocked=returns.copy();shocked.loc[cut:]*=4
    moved=dynamic_parity_path(shocked,"W")
    pd.testing.assert_frame_equal(base.loc[:returns.index[649]],moved.loc[:returns.index[649]])


def test_identities():
    assert strategy_hash("v4d_monthly","M")!=strategy_hash("v4e_weekly","W")
    w=as_weights({"target_SPY":.2,"target_AGG":.5,"target_GLD":.1,"target_XLE":.2},"target_")
    assert w["EFA"]==0 and sum(w.values())==pytest.approx(1)
