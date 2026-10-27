import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
from quanedge.portfolio import canonical_weights,weight_hash,hurdle,tail_weights,construct,replay,kpis,feasible
from quanedge.backtest import exception_tests,assess,verdict
from quanedge.stress import attribution
from quanedge.results import result_state
from quanedge.config import TICKERS


@pytest.fixture
def cfg():return yaml.safe_load(Path("config/final.yaml").read_text())


def test_policy_accounting():
    h=hurdle();assert h==pytest.approx(.0677083333333333)
    assert (1+h)*.96==pytest.approx(1.025)
    with pytest.raises(ValueError):hurdle(300)
    assert .96==pytest.approx((.96**(1/12))**12)


def test_hash_and_inputs():
    assert weight_hash({"SPY":1})==weight_hash(dict(reversed(list(canonical_weights({"SPY":1}).items()))))
    assert weight_hash({"SPY":1})!=weight_hash({"SPY":.999999,"AGG":.000001})
    for w in ({"BTC":1},{"SPY":float("nan")},{"SPY":.5},{"SPY":-.1,"AGG":1.1}):
        with pytest.raises(ValueError):canonical_weights(w)


def test_tied_tail_attribution():
    returns=pd.DataFrame([[-.2,.0],[-.4,.2],[.2,-.1]],columns=["SPY","AGG"])
    result=attribution(returns,{"SPY":.5,"AGG":.5},alpha=.5,value=100)
    assert result["es_usd"]==pytest.approx(10)
    assert result["components"]["AGG"]==pytest.approx(-5)
    assert result["residual_usd"]==pytest.approx(0)
    assert tail_weights([2,2,0],.5)==pytest.approx([.5,.5,0])


def test_solver_constraints_and_infeasibility(cfg):
    x=pd.DataFrame(np.random.default_rng(4).normal(.0002,.006,(500,7)),columns=TICKERS)
    r=construct(x,cfg)
    assert r["status"]=="ok" and feasible(r["weights"],cfg)
    assert r["es99"]<=cfg["es_budget"]+1e-6
    bad=dict(cfg,agg_min=.9,agg_max=.7)
    assert construct(x,bad)["status"]=="infeasible"


def test_buy_hold_and_drawdown_hand_example():
    x=pd.DataFrame({"SPY":[-.1,.1],"AGG":[0,0]},index=pd.bdate_range("2020-01-01",periods=2))
    p=replay(x,{"SPY":.5,"AGG":.5},buy_hold=True)
    assert p.wealth.tolist()==pytest.approx([.95,.995])
    rf=pd.Series(0,index=x.index)
    k=kpis(p["return"],rf,x.SPY,x.AGG)
    assert k["maximum_drawdown"]==pytest.approx(-.05)


def test_backtest_edges_and_hash():
    assert exception_tests([False]*250)["independence_p"] is None
    assert np.isfinite(exception_tests([True]*250)["kupiec_lr"])
    assert exception_tests([])["status"]=="unavailable"
    idx=pd.bdate_range("2020-01-01",periods=250)
    f=pd.DataFrame({"return":0.,"var_fhs_99":.01,"weight_hash":"a"},index=idx)
    assert assess(f,"a")["zone"]=="green"
    with pytest.raises(ValueError,match="hash"):assess(f,"b")
    f.loc[idx[-1],"var_fhs_99"]=np.nan
    assert assess(f,"a")["zone"]=="unavailable"


def test_verdict_exhaustive():
    good={f"C{i}":True for i in range(1,6)}
    assert verdict(good)["outcome"]=="Accept"
    assert verdict(dict(good,C4=False))["outcome"]=="evaluation incomplete"
    for i in (1,2,3,5):
        failed=dict(good,**{f"C{i}":False})
        assert verdict(failed,[("A1",good)])["outcome"]=="Adjust"
        assert verdict(failed,[(f"A{j}",failed) for j in range(1,6)])["outcome"]=="Reject"
    import itertools
    for values in itertools.product([True,False,None],repeat=5):
        assert verdict(dict(zip(good,values)))["outcome"] in {"Accept","Reject","Adjust","evaluation incomplete"}


def test_result_states():
    assert result_state({"artifact_key":"a"},{"a":{}})=="RERUN_REQUIRED" # empty entries are not evidence
    assert result_state({"artifact_key":"a"},{"a":{"path":"x"}})=="MATCHED"
    assert result_state({"artifact_key":"a"},{"a":{"failed":True}})=="FAILED"
    assert result_state({"cheap":True},{})=="LIVE"
    assert result_state({"input_error":True},{})=="INPUT_ERROR"


def test_money_weighted_cashflows_constant_return():
    from quanedge.portfolio import money_weighted
    start=pd.Timestamp("2020-01-01")
    dates=[start+pd.Timedelta(days=365),start+pd.Timedelta(days=730)]
    nav1=1.1*.96;nav2=nav1*1.1*.96
    p=pd.DataFrame({"spending":[1.1*.04,nav1*1.1*.04],"wealth":[nav1,nav2]},index=dates)
    assert money_weighted(p,start_date=start)==pytest.approx(.1)
    p=pd.DataFrame({"spending":[0.,0.],"wealth":[1.1,1.21]},index=dates)
    assert money_weighted(p,start_date=start)==pytest.approx(.1)


def test_all_adjustment_branches_have_order():
    good={f"C{i}":True for i in range(1,6)};bad=dict(good,C3=False)
    for winner in range(1,6):
        alternatives=[(f"A{j}",good if j==winner else bad) for j in range(1,6)]
        assert verdict(bad,alternatives)["alternative"]==f"A{winner}"
