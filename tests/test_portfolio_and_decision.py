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
    r=construct(x,cfg,"max_return")
    assert r["status"]=="ok" and feasible(r["weights"],cfg)
    assert r["es99"]<=cfg["es_budget"]+1e-6
    bad=dict(cfg,agg_min=.9,agg_max=.7)
    assert construct(x,bad,"max_return")["status"]=="infeasible"
    assert construct(x,bad)["status"]=="infeasible"


def test_mandate_v2_policy_values(cfg):
    from quanedge.portfolio import nominal_target,real_return,reserve_schedule
    assert cfg["cost"]==0 and cfg["value"]==cfg["fund_value"]-cfg["reserve_initial"]
    assert all(cfg[k]==1 for k in ("gold_cap","equity_cap","agg_max","single_cap","sector_cap")) and cfg["agg_min"]==0
    assert reserve_schedule(cfg,2)==pytest.approx([400000,414560])
    assert nominal_target(.0364,.03)==pytest.approx(.067492)
    assert real_return(nominal_target(.0364,.01),.0364)==pytest.approx(.01)
    with pytest.raises(ValueError):nominal_target(300,.01)


def test_target_selection_binding_and_nonbinding(cfg):
    from quanedge.portfolio import nominal_target
    cfg=dict(cfg,mean_shrinkage=0.)          # raw means, so the low-risk allocation misses the target
    rng=np.random.default_rng(7);n=1500
    means=np.array([.0006,.0004,.0005,.0001,.0003,.0005,.0008])
    x=pd.DataFrame(rng.normal(means,[.012,.012,.016,.003,.01,.016,.018],(n,7)),columns=TICKERS)
    minimum=construct(x,cfg,"min_cvar")
    loose=construct(x,dict(cfg,real_return_target=-.5))
    assert loose["target_binding"] is False and loose["weights"]==minimum["weights"]
    tight=construct(x,cfg)
    assert tight["status"]=="ok" and tight["target_binding"]
    assert tight["expected_geometric"]>=nominal_target(cfg["inflation"],cfg["real_return_target"])-1e-5
    assert tight["es99"]>=minimum["es99"]-1e-9
    lower=construct(x,dict(cfg,real_return_target=cfg["real_return_target"]-.01))
    assert lower["es99"]<=tight["es99"]+1e-6
    assert construct(x,dict(cfg,real_return_target=5.))["status"]=="infeasible"


def test_reserve_replay_depletes_exactly_on_the_25th_payment():
    # Invested returns equal reserve growth: real balance falls by the year-1 reserve each year.
    idx=pd.bdate_range("2000-01-03","2025-12-31");year=pd.Series(idx.year,index=idx)
    daily=1.0364**(1/year.groupby(year).transform("count"))-1
    p=replay(pd.DataFrame({"SPY":daily,"AGG":daily}),{"SPY":.5,"AGG":.5},0,.05,reserve=(.04,.0364))
    for t in (1,10,24):
        assert p.wealth.loc[str(1999+t)].iloc[-1]/1.0364**t==pytest.approx(1-.04*t)
    assert p.spending.loc["2024"].iloc[0]==pytest.approx(.04*1.0364**24)
    assert p.wealth.loc["2024":].max()==pytest.approx(0,abs=1e-12)
    assert p.spending.sum()==pytest.approx(sum(.04*1.0364**t for t in range(25)))


def test_reserve_survival_and_return_check(cfg):
    from quanedge.stress import reserve_survival
    from quanedge.portfolio import return_check
    months=pd.date_range("2000-01-31",periods=60,freq="ME")
    rich=pd.DataFrame(.02,index=months,columns=TICKERS);poor=pd.DataFrame(-.02,index=months,columns=TICKERS)
    small=dict(cfg,survival_paths=200)
    assert reserve_survival(rich,{"AGG":1,**{t:0 for t in TICKERS if t!="AGG"}},small)["results"][-1]["all_payments_funded"]==1
    bad=reserve_survival(poor,{"AGG":1,**{t:0 for t in TICKERS if t!="AGG"}},small)["results"][-1]
    assert bad["all_payments_funded"]==0 and bad["median_depletion_year"]<25
    assert return_check(.0469,cfg) and not return_check(.0467,cfg)
    v1=dict({k:v for k,v in cfg.items() if k!="real_return_floor"},inflation=.025,spending=.04)
    assert return_check(.0678,v1) and not return_check(.0677,v1)


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
