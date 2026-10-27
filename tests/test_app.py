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
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run()
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
    meta={"run_id":"test","data_hash":dh,"config_hash":"config","code_rev":"revision"}
    selected={"weights":w,"weight_hash":wh,"checks":{f"C{i}":True for i in range(1,6)},"validation":[],"stress":[]}
    bundle={"metadata":meta,"policy":cfg,"portfolios":{"selected":selected},"decision":{"outcome":"Accept","action":"Synthetic test only"}}
    (folder.parent/"submission.json").write_text(json.dumps(bundle))
    key=artifact_key(wh,"fhs",dh,"config","revision")
    (folder.parent/"index.json").write_text(json.dumps({key:{"portfolio":"selected","path":"selected"}}))
    (tmp_path/"results/latest.txt").write_text("test")
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run(timeout=30)
    assert not app.exception
    assert any("MATCHED" in c.value for c in app.caption)
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
