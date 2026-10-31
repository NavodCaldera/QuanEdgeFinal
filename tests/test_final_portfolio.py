"""Final portfolio (monthly dynamic EWMA risk parity): evidence identity, accounting and dashboard smoke test."""
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from quanedge import final_portfolio as F

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence():
    return F.load_evidence()


@pytest.fixture(scope="module")
def market():
    return F.load_market()


def copy_evidence(root):
    shutil.copytree(ROOT/"results"/F.RUN, root/"results"/F.RUN)
    (root/"data/clean").mkdir(parents=True)
    shutil.copy(ROOT/"data/clean/prices_clean.csv", root/"data/clean/prices_clean.csv")


def test_current_target_is_last_decision(evidence):
    path = evidence["path"]; w = F.current_target(path)
    assert set(w) == set(F.UNIVERSE) and abs(sum(w.values())-1) < 1e-9
    assert all(abs(w[t]-path[f"target_{t}"].iloc[-1]) < 1e-6 for t in F.UNIVERSE)
    assert F.target_history(path).index[0] == path.index[0]


def test_changed_forecast_hash_is_refused(tmp_path, evidence):
    copy_evidence(tmp_path)
    assert F.load_evidence(tmp_path)["strategy_hash"] == evidence["strategy_hash"]
    fc = tmp_path/"results"/F.RUN/f"{F.NAME}_forecasts.csv"
    fc.write_text(fc.read_text().replace(evidence["strategy_hash"], "0"*64, 1))
    with pytest.raises(F.EvidenceError):
        F.load_evidence(tmp_path)


def test_changed_prices_are_refused(tmp_path):
    copy_evidence(tmp_path)
    with open(tmp_path/"data/clean/prices_clean.csv", "ab") as f:
        f.write(b"\n")
    with pytest.raises(F.EvidenceError):
        F.load_evidence(tmp_path)


def test_backtest_refuses_other_hash(evidence):
    with pytest.raises(ValueError):
        F.backtest(evidence["forecasts"], "0"*64, "fhs", .99, "2017-01-01", "2026-09-30")


def test_backtest_matches_saved_reference(evidence):
    saved = {(v["method"], v["alpha"]): v for v in evidence["summary"]["validation"]}
    for method in ("fhs", "garch_evt"):
        res, frame = F.backtest(evidence["forecasts"], evidence["strategy_hash"], method, .99, "2017-01-01", "2026-09-30")
        assert res["breaches"] == saved[(method, .99)]["breaches"] == int(frame.breach.sum())
        assert np.isclose(res["kupiec_p"], saved[(method, .99)]["kupiec_p"])


def test_cpi_real_return_uses_index_ratio():
    days = pd.bdate_range("2010-01-01", "2019-12-31")
    r = pd.Series(.0002, index=days)
    cpi = pd.Series(np.linspace(100, 125, len(days)+1), index=days.insert(0, pd.Timestamp("2009-12-31")))
    cagr, inflation, real = F.cpi_real(r, cpi)
    years = (days[-1]-days[0]).days/365.25
    assert np.isclose(inflation, 1.25**(1/years)-1)
    assert np.isclose(cagr, (1.0002**len(days))**(1/years)-1)
    assert np.isclose(real, (1+cagr)/(1+inflation)-1)


def test_scenario_pnl_reconciles_and_matches_saved(evidence, market):
    returns = market[1]
    saved = {s["scenario"]: s for s in evidence["summary"]["stress"]}
    for name, (start, end) in F.SCENARIOS.items():
        x = F.scenario_pnl(evidence["path"], returns, start, end, 1e7)
        assert abs(sum(x["pnl_usd"].values())+x["loss_usd"]) < 1.     # parts add to the total (CSV rounding only)
        assert np.isclose(x["return"], saved[name]["return"], atol=1e-9)
        assert np.isclose(x["max_fall"], -saved[name]["drawdown"], atol=1e-9)


def test_es_contributions_reconcile(evidence, market):
    rows, total = F.risk_contributions(market[1], F.current_target(evidence["path"]), .99, 9.6e6)
    assert abs(rows.es_usd.sum()-total["es_usd"]) < 1e-6
    assert np.isclose(rows.vol_contribution.sum(), 1)


def test_dashboard_runs_without_errors():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT/"dashboard.py")).run(timeout=180)
    assert not app.exception and not app.error
    assert any(m.label == "1-day 99% ES" for m in app.metric)
    assert "Why these four ETFs" in [s.value for s in app.subheader] and len(app.tabs) == 5
