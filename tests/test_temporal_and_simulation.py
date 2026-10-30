import numpy as np
import pandas as pd
import pytest
from quanedge.portfolio import construct,canonical_weights
from quanedge.pipeline import walk_forward,load_inputs
from quanedge.risk.var_es import monte_carlo,Normal,batch_se
from quanedge.config import TICKERS


def test_psd_sampler_identical_assets_and_zero_weight():
    idx=pd.bdate_range("2000-01-01",periods=1000)
    x=pd.Series(np.random.default_rng(31).normal(.0002,.01,1000),index=idx)
    same=pd.DataFrame({"A":x,"B":x})
    m=monte_carlo(same,{"A":.5,"B":.5},n_sim=20000)
    assert m.scenarios[:,0]==pytest.approx(m.scenarios[:,1])
    full=pd.DataFrame(np.random.default_rng(12).normal(0,.01,(1000,7)),index=idx,columns=TICKERS)
    one=monte_carlo(full[["SPY"]],{"SPY":1},n_sim=20000)
    seven=monte_carlo(full,{"SPY":1},n_sim=20000)
    assert one.losses==pytest.approx(seven.losses)


def test_matching_one_asset_monte_carlo():
    x=pd.DataFrame({"A":np.random.default_rng(1).normal(.0003,.01,2000)})
    analytical=Normal(x.A)
    for n in [10000,100000,1000000]:
        m=monte_carlo(x,{"A":1},n_sim=n,seed=1234)
        for alpha in [.95,.99]:
            sv,se=batch_se(m,alpha,n_batches=10)
            assert abs(m.var(alpha)-analytical.var(alpha))<=4*sv
            assert abs(m.es(alpha)-analytical.es(alpha))<=4*se


def test_walk_forward_weights_ignore_current_year(cfg):
    idx=pd.bdate_range("2012-01-01","2017-12-29")
    x=pd.DataFrame(np.random.default_rng(7).normal(.0004,.005,(len(idx),7)),index=idx,columns=TICKERS)  # reaches the v2 real target
    _,first=walk_forward(x,cfg)
    x.loc["2017":]*=-3
    _,second=walk_forward(x,cfg)
    assert first[0]["weight_hash"]==second[0]["weight_hash"]


def test_post_snapshot_data_refused(cfg,monkeypatch):
    import quanedge.data as data
    p=pd.DataFrame(100.,index=pd.bdate_range("2026-09-30",periods=2),columns=TICKERS)
    monkeypatch.setattr(data,"load_clean_prices",lambda:p)
    with pytest.raises(ValueError,match="post-snapshot"):load_inputs(cfg)
