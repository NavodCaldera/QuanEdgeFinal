"""UI contract checks using an isolated synthetic frozen run, without network."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
from quanedge import config
from quanedge.portfolio import canonical_weights,weight_hash
from quanedge.results import artifact_key


def by_label(elements,label):return next(e for e in elements if e.label==label)


def test_missing_run_is_honest(tmp_path,monkeypatch):
    monkeypatch.setattr(config,"ROOT",tmp_path);st.cache_data.clear()
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=30)
    assert not app.exception
    assert any("No completed analytical run" in x.value for x in app.info)


def test_explore_invalidates_and_restores(tmp_path,monkeypatch,cfg):
    monkeypatch.setattr(config,"ROOT",tmp_path);st.cache_data.clear()
    folder=tmp_path/"results/test/selected";folder.mkdir(parents=True)
    data=tmp_path/"data/clean";data.mkdir(parents=True)
    prices=pd.DataFrame(np.exp(np.random.default_rng(42).normal(0,.005,(500,7)).cumsum(axis=0))*100,
                        index=pd.bdate_range("2015-01-01",periods=500),columns=config.TICKERS)
    prices.to_csv(data/"prices_clean.csv")
    dh=hashlib.sha256((data/"prices_clean.csv").read_bytes()).hexdigest()
    w=canonical_weights({"SPY":.35,"AGG":.5,"GLD":.15});wh=weight_hash(w)
    (tmp_path/"app.py").write_text("# Updated viewer interface\n")
    meta={"run_id":"test","data_hash":dh,"config_hash":"config","code_rev":"revision",
          "source_file_hashes":{"app.py":hashlib.sha256(b"# Frozen viewer interface\n").hexdigest()},
          "input_hashes":{"data/clean/prices_clean.csv":dh}}
    selected={"weights":w,"weight_hash":wh,"checks":{f"C{i}":True for i in range(1,6)},"validation":[],"stress":[]}
    bundle={"metadata":meta,"policy":cfg,"portfolios":{"selected":selected},"decision":{"outcome":"Accept","action":"Synthetic test only"}}
    (folder.parent/"submission.json").write_text(json.dumps(bundle))
    key=artifact_key(wh,"fhs",dh,"config","revision")
    (folder.parent/"index.json").write_text(json.dumps({key:{"portfolio":"selected","path":"selected"}}))
    (tmp_path/"results/latest.txt").write_text("test")
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=30)
    assert not app.exception
    assert any("MATCHED" in c.value for c in app.caption)
    assert any("Updated application interface" in c.value for c in app.caption)
    frozen_before=[c.value for c in app.expander[0].caption]
    by_label(app.sidebar.radio,"Mode").set_value("Explore").run()
    by_label(app.sidebar.number_input,"SPY").set_value(36.)
    by_label(app.sidebar.number_input,"AGG").set_value(49.).run()
    assert not app.exception
    assert any("Grey traffic light" in x.value for x in app.info)
    assert any("RERUN_REQUIRED" in c.value for c in app.caption)
    assert [c.value for c in app.expander[0].caption]==frozen_before
    by_label(app.sidebar.number_input,"SPY").set_value(35.)
    by_label(app.sidebar.number_input,"AGG").set_value(50.).run()
    assert not app.exception
    assert any("MATCHED" in c.value for c in app.caption)
    by_label(app.sidebar.radio,"Page").set_value("Portfolio comparison").run()
    assert not app.exception
    assert len(app.get("plotly_chart"))==2
    assert any("needs more than 500 days" in x.value for x in app.info)
    assert any("Computed in app, not part of frozen run" in c.value for c in app.caption)
    table=app.dataframe[0].value
    assert list(table.Portfolio)==["W_rec (selected)"] and table.iloc[0,1]=="35 / 50 / 15 / 0"
    assert len(app.get("download_button"))==1
    by_label(app.sidebar.checkbox,"Show comparison table").uncheck().run()
    assert not app.dataframe
    by_label(app.sidebar.multiselect,"Portfolios to compare").set_value([]).run()
    app.sidebar.checkbox[0].uncheck().run()
    assert any("Select at least one portfolio" in x.value for x in app.info)
    by_label(app.sidebar.radio,"Page").set_value("ETF charts").run()
    assert not app.exception
    assert len(app.get("plotly_chart"))==1
    assert any("full-history context is unavailable" in x.value for x in app.info)
    by_label(app.radio,"View").set_value("Adjusted prices (USD)").run()
    assert not app.exception
    by_label(app.multiselect,"ETFs to display").set_value([]).run()
    assert not app.exception
    assert any("Select at least one ETF" in x.value for x in app.info)
    with (data/"prices_clean.csv").open("a") as stream:stream.write("\n")
    app.run()
    assert any("Run input changed: data/clean/prices_clean.csv" in x.value for x in app.error)


def v1_policy(cfg):
    """Mandate v1 policy keys, so runs made before the v2 change remain viewable."""
    old={k:v for k,v in cfg.items() if k not in ("real_return_target","real_return_floor","reserve_initial","reserve_growth","reserve_rate","fund_value","mandate","prereg_tag")}
    return dict(old,inflation=.025,spending=.04,cost=.0005,expected_annual_turnover=1.)


def synthetic_run(root,cfg,sensitivity_hash=None):
    """Minimal frozen run whose reported allocation is an A1 adjustment."""
    folder=root/"results/test";(folder/"A1_min_cvar").mkdir(parents=True)
    data=root/"data/clean";data.mkdir(parents=True)
    prices=pd.DataFrame(np.exp(np.random.default_rng(1).normal(0,.005,(400,7)).cumsum(axis=0))*100,
                        index=pd.bdate_range("2015-01-01",periods=400),columns=config.TICKERS)
    prices.to_csv(data/"prices_clean.csv");dh=hashlib.sha256((data/"prices_clean.csv").read_bytes()).hexdigest()
    w=canonical_weights({"SPY":.15,"AGG":.7,"GLD":.15});wh=weight_hash(w)
    survival=([{"year":25,"all_payments_funded":.7,"mc_se":.005,"real_capital_preserved":0.,"median_real_balance_usd":1e6}]
              if "reserve_initial" in cfg else [{"year":5,"shortfall_probability":.6,"mc_se":.005,"median_real_surplus_usd":-1}])
    a1={"weights":w,"weight_hash":wh,"checks":{f"C{i}":True for i in range(1,6)},"validation":[],"stress":[],
        "real_capital_survival":{"results":survival}}
    bundle={"metadata":{"run_id":"test","data_hash":dh,"config_hash":"config","code_rev":"revision"},"policy":cfg,
            "portfolios":{"selected":dict(a1,checks={**a1["checks"],"C5":False}),"A1_min_cvar":a1},
            "decision":{"outcome":"Adjust","action":"Synthetic test only","alternative":"A1_min_cvar","reported_portfolio":"A1_min_cvar"}}
    (folder/"submission.json").write_text(json.dumps(bundle))
    (folder/"index.json").write_text(json.dumps({artifact_key(wh,"fhs",dh,"config","revision"):{"portfolio":"A1_min_cvar"}}))
    (root/"results/latest.txt").write_text("test")
    rows=[{"mean_shrinkage":f,"lookback_years":y,"expected_geometric":g,"weight_hash":sensitivity_hash or wh}
          for f,gs in [(0.,[.040,.044,.046]),(.5,[.092,.087,.080])] for y,g in zip([5,10,"all"],gs)]
    pd.DataFrame(rows).to_csv(folder/"estimator_sensitivity.csv",index=False)
    return prices


@pytest.mark.parametrize("mandate",["v2","v1"])
def test_estimator_disclosure_requires_matching_hash(tmp_path,monkeypatch,cfg,mandate):
    cfg=cfg if mandate=="v2" else v1_policy(cfg)
    monkeypatch.setattr(config,"ROOT",tmp_path);st.cache_data.clear()
    synthetic_run(tmp_path,cfg)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=30)
    assert not app.exception
    floor="1% real floor" if mandate=="v2" else "hurdle"
    assert any(f"below the {floor} in every displayed window" in x.value for x in app.warning)
    caption="Illustrative reserve sustainability" if mandate=="v2" else "does not mean the fund is exhausted"
    assert any(caption in c.value for c in app.caption)
    other=tmp_path/"other";other.mkdir()
    monkeypatch.setattr(config,"ROOT",other);st.cache_data.clear()
    synthetic_run(other,cfg,sensitivity_hash="0"*64)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=30)
    assert not app.exception
    assert any("does not match the reported allocation" in x.value for x in app.info)
    assert not any("in every displayed window" in x.value for x in app.warning)


def test_etf_charts_with_standalone_context(tmp_path,monkeypatch,cfg):
    monkeypatch.setattr(config,"ROOT",tmp_path);st.cache_data.clear()
    prices=synthetic_run(tmp_path,cfg)
    full=pd.concat([prices.iloc[:1]*np.nan,prices]);full.index=[pd.Timestamp("2014-06-02")]+list(prices.index)
    full.loc[:"2015-03-01",["GLD","EEM"]]=np.nan          # later launches stay missing, never filled
    raw=tmp_path/"context/raw";raw.mkdir(parents=True)
    full.to_csv(raw/"prices_full_history.csv",lineterminator="\n")
    digest=hashlib.sha256((raw/"prices_full_history.csv").read_bytes()).hexdigest()
    (raw/"manifest.json").write_text(json.dumps({"files":{"prices_full_history.csv":digest}}))
    from quanedge import context
    out=tmp_path/"context/results";out.mkdir()
    context.coverage(full).to_csv(out/"coverage.csv",index=False);context.drawdowns(full).to_csv(out/"drawdowns.csv",index=False)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=30)
    by_label(app.sidebar.radio,"Page").set_value("ETF charts").run()
    by_label(app.radio,"Data").set_value("Standalone full history (context)").run()
    assert not app.exception
    assert any("added after preregistration" in x.value for x in app.warning)
    assert len(app.dataframe)==2
    for view in ["Indexed comparison (start = 100)","Indexed from each ETF's own first date","Adjusted prices (USD)","Drawdown from running peak"]:
        by_label(app.radio,"View").set_value(view).run()
        assert not app.exception and len(app.get("plotly_chart"))==1
    assert not any("not a fair performance ranking" in c.value for c in app.caption)
    by_label(app.radio,"View").set_value("Indexed from each ETF's own first date").run()
    assert any("not a fair performance ranking" in c.value for c in app.caption)
