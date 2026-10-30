"""Portfolio comparison helpers: risk parity, EWMA, timing of the dynamic strategy and summary arithmetic."""
import numpy as np
import pandas as pd
import pytest
from quanedge import comparison
from quanedge.portfolio import replay


@pytest.fixture
def returns():
    rng=np.random.default_rng(7)
    return pd.DataFrame(rng.normal(.0003,[.01,.003,.008,.015],(900,4)),
                        index=pd.bdate_range("2010-01-01",periods=900),columns=["SPY","AGG","GLD","XLE"])


def test_risk_parity_equalises_contributions():
    cov=np.array([[.04,.006,.002],[.006,.0025,.0005],[.002,.0005,.0225]])
    w=comparison.risk_parity(cov);rc=w*(cov@w)/(w@cov@w)
    assert w.sum()==pytest.approx(1) and (w>0).all()
    assert rc==pytest.approx(np.full(3,1/3),abs=1e-7)


def test_ewma_cov_matches_hand_weights():
    x=np.array([[1.,2.],[3.,1.],[2.,5.]]);lam=.5
    w=np.array([.25,.5,1.]);w/=w.sum();d=x-w@x
    assert comparison.ewma_cov(x,lam)==pytest.approx((d*w[:,None]).T@d)


def test_dynamic_uses_only_past_data(returns):
    base=comparison.dynamic_risk_parity(returns,min_history=500)
    cut=returns.index[700];shocked=returns.copy();shocked.loc[cut:]*=5
    moved=comparison.dynamic_risk_parity(shocked,min_history=500)
    assert base.index[0]==returns.index[500]
    pd.testing.assert_series_equal(base.loc[:returns.index[699]],moved.loc[:returns.index[699]])
    assert comparison.dynamic_risk_parity(returns.iloc[:500]).empty


def test_wealth_paths_and_summary(returns):
    w={"SPY":.5,"AGG":.5,"GLD":0.,"XLE":0.}
    wealth=comparison.wealth_paths(returns,{"half":w},cost=0.)
    assert wealth["half"].to_numpy()==pytest.approx(1e7*replay(returns,w,0.,.05)["wealth"].to_numpy())
    flat=pd.DataFrame({"x":1e7*1.1**(np.arange(4)/1)},index=pd.to_datetime(["2001-01-01","2002-01-01","2003-01-01","2004-01-01"]))
    row=comparison.summary(flat,inflation=.1).iloc[0]
    assert row["CAGR %"]==pytest.approx(10,abs=.01) and row["Real CAGR %"]==pytest.approx(0,abs=.01)
    assert row["Max drawdown %"]==0 and np.isnan(row["GFC %"])
