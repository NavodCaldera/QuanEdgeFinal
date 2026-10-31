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
    shutil.copytree(ROOT/"results"/F.RUN_V6, root/"results"/F.RUN_V6)
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
    fc = tmp_path/"results"/F.RUN_V6/"forecasts.csv"
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


def test_with_cost_matches_replay_at_that_cost(market):
    returns = market[1].loc["2010":"2014", ["SPY", "AGG"]]
    w = {"SPY": .4, "AGG": .6}
    free = F.replay(returns, w, cost=0., drift=.05)
    paid = F.replay(returns, w, cost=.001, drift=.05)
    assert np.allclose(F.with_cost(free["return"], free.turnover, .001), paid["return"], atol=1e-12)


def test_reserve_ledger_marks_partial_and_unfunded_payments():
    days = pd.bdate_range("2006-11-14", "2010-12-31")
    r = pd.Series(0., index=days)
    cfg = {"fund_value": 1_000_000, "reserve_initial": 400_000, "reserve_growth": .1}
    ledger = F.reserve_ledger(r, cfg)
    paid = ledger[ledger.required_payment > 0]
    assert list(paid.index.year) == [2007, 2008, 2009, 2010]
    assert paid.required_payment.to_numpy() == pytest.approx([400000, 440000, 484000, 532400])
    assert paid.paid_payment.to_numpy() == pytest.approx([400000, 440000, 160000, 0])
    assert paid.shortfall.to_numpy() == pytest.approx([0, 0, 324000, 532400])
    assert (ledger.loc["2009":].balance == 0).all()
    view = F.reserve_window(ledger, "2009-01-01", "2010-06-01")
    assert view.loc[paid.index[2], "required_payment"] == pytest.approx(484000)
    assert view.loc[paid.index[2], "shortfall"] == pytest.approx(324000)


def test_reserve_ledger_matches_existing_spending_history(evidence, market):
    cfg = F.policy(); cpi = market[3]
    ledger = F.reserve_ledger(evidence["path"]["return"], cfg)
    history = F.reserve_history(evidence["path"], cpi, cfg)
    assert ledger.balance.iloc[-1] == pytest.approx(history["end_usd"], rel=1e-12)
    assert ledger.paid_payment.sum() == pytest.approx(history["paid_usd"], rel=1e-12)
    assert (ledger.required_payment > 0).sum() == history["payments"]
    view = F.reserve_window(ledger, "2020-01-01", "2021-12-31")
    pd.testing.assert_frame_equal(view.loc["2020":"2021"], ledger.loc["2020":"2021"])


def test_relative_and_takeaway():
    days = pd.bdate_range("2010-01-01", "2019-12-31")
    rng = np.random.default_rng(0)
    b = pd.Series(rng.normal(.0002, .01, len(days)), index=days)
    active = pd.Series(rng.normal(.0001, .002, len(days)), index=days)
    rel = F.relative(b+active, b)
    assert np.isclose(rel["mean_diff"], active.mean()*252)
    assert np.isclose(rel["tracking_error"], active.std()*np.sqrt(252))
    assert "ir_t" not in rel
    assert F.relative(b+.0001, b)["information_ratio"] is None
    t = F.takeaway({"maximum_drawdown": -.1}, {"x": {"maximum_drawdown": -.2}}, {"x": {"cagr_diff": .01}})
    assert t == {"ahead": "x (+1.00 pp)", "behind": "none", "shallower": "x (20.0%)", "deeper": "none"}


def test_benchmark_window_preserves_history_and_trade_dates(market, evidence):
    returns = market[1]; p = evidence["path"]; w = {"SPY": .4, "AGG": .6}
    full = F.benchmark_frame(w, returns, p.index[0], p.index[-1])
    view = F.benchmark_window(full, "2020-02-03", "2020-03-10")
    pd.testing.assert_frame_equal(view, full.loc["2020-02-03":"2020-03-10"])
    restarted = F.benchmark_frame(w, returns, "2020-02-03", "2020-03-10")
    assert not np.allclose(view["return"], restarted["return"], rtol=0, atol=1e-8)
    assert view.turnover.iloc[-1] == 0 and restarted.turnover.iloc[-1] > 0


def test_failed_static_parity_preserves_other_benchmarks(monkeypatch, cfg):
    from quanedge import portfolio
    idx = pd.bdate_range("2010-01-01", periods=40)
    returns = pd.DataFrame(np.random.default_rng(9).normal(0, .005, (40, 7)), index=idx, columns=F.TICKERS)
    path = pd.DataFrame({"return": returns.AGG}, index=idx)
    monkeypatch.setattr(portfolio, "construct", lambda *a, **k: {"weights": None, "reason": "synthetic solver failure"})
    catalog = F.benchmarks(path, returns, cfg)
    assert catalog["Static risk parity"][0] is None and "synthetic solver failure" in catalog["Static risk parity"][1]
    assert catalog["40/60 SPY/AGG"][0] == {"SPY": .4, "AGG": .6}
    assert catalog["Permanent 25/50/25"][0] == {"SPY": .25, "AGG": .5, "GLD": .25}


def test_cost_sensitivity_refuses_missing_turnover():
    dates = pd.bdate_range("2020-01-01", periods=3)
    returns = pd.Series(.01, index=dates)
    with pytest.raises(ValueError, match="complete turnover"):
        F.with_cost(returns, pd.Series(0., index=dates[:-1]), .001)


def test_page_kpis_real_returns_and_sortino(market):
    _, returns, rf, cpi = market
    r = returns.SPY.loc["2010":"2019"]
    q = F.page_kpis(r, rf, returns.SPY, cpi)
    assert np.isclose(q["real_cagr_cpi"], F.cpi_real(r, cpi)[2])
    assert np.isclose(q["real_cagr_policy"], F.policy_real(q["cagr"]))
    assert q["sortino_excess"] < q["sortino"]           # positive T-bill hurdle lowers the ratio


def portfolio_app(tmp_path):
    from streamlit.testing.v1 import AppTest
    src = (ROOT/"dashboard.py").read_text(encoding="utf-8")
    src = src.replace('title="Decision", default=True', 'title="Decision"').replace('title="Portfolio",', 'title="Portfolio", default=True,')
    page = tmp_path/"portfolio_page.py"
    page.write_text(f"import os, sys\nsys.path.insert(0, {str(ROOT)!r})\nos.chdir({str(ROOT)!r})\n" + src, encoding="utf-8")
    return AppTest.from_file(str(page)).run(timeout=180)


def test_portfolio_page_ranges_and_picker(tmp_path):
    app = portfolio_app(tmp_path)
    assert [t.value for t in app.title] == ["Portfolio"] and not app.exception and not app.error
    assert len(app.multiselect[0].value) == 4 and "Permanent 25/50/25" in app.multiselect[0].value
    import json
    charts = app.get("plotly_chart")
    assert len(charts) == 5
    assert all(t["line"]["shape"] == "hv" for t in json.loads(charts[1].proto.spec)["data"])
    assert all(len(json.loads(charts[i].proto.spec)["data"]) == 5 for i in (2, 3, 4))
    assert any("Fund balance after university payments" == x.value for x in app.subheader)
    assert any("After paying the reserves" in c.value for c in app.caption)
    assert not any("noise" in x.value or "|t|" in x.value for x in app.info)
    app.multiselect[0].set_value(["40/60 SPY/AGG"]).run(timeout=180)
    assert not app.exception
    main = next(d.value for d in app.dataframe if "KPI" in d.value and "CAGR" in d.value.KPI.to_list())
    assert list(main.columns) == ["KPI", "Final portfolio", "40/60 SPY/AGG", "Definition"]
    assert "Real CAGR (actual CPI)" in main.KPI.to_list()
    next(x for x in app.radio if x.label == "Period").set_value("Backtest date range from the sidebar").run(timeout=180)
    assert not app.exception and not app.error
    assert any("Opening holdings before" in c.value for c in app.caption)
    next(x for x in app.radio if x.label == "Allocation series").set_value("Actual holdings after each close").run(timeout=180)
    assert not app.exception
    app.multiselect[0].set_value([]).run(timeout=180)
    assert not app.exception and any("Only the final portfolio" in x.value for x in app.info)


def test_portfolio_short_range_hides_unstable_annualised_statistics(tmp_path):
    from datetime import date
    app = portfolio_app(tmp_path)
    app.sidebar.date_input[0].set_value((date(2026, 9, 1), date(2026, 9, 30)))
    next(x for x in app.radio if x.label == "Period").set_value("Backtest date range from the sidebar").run(timeout=180)
    assert not app.exception and not app.error
    main = next(d.value for d in app.dataframe if "KPI" in d.value and "CAGR" in d.value.KPI.to_list())
    assert main.set_index("KPI").loc["CAGR", "Final portfolio"] == "n/a (under 3 months)"
    assert main.set_index("KPI").loc["Volatility", "Final portfolio"] != "n/a (under 3 months)"
    assert any("less" in c.value or "Only" in c.value for c in app.caption)
    assert any("balances and payment years do not restart" in c.value for c in app.caption)

def test_strategy_risk_matches_saved_path(evidence):
    t = F.strategy_risk(evidence['path'], 9.6e6)
    row = t[np.isclose(t.alpha, .99)].iloc[0]
    assert np.isclose(row.es_fraction, evidence['summary']['es99']['path'], atol=1e-12)
    assert np.isclose(row.es_usd, row.es_fraction*9.6e6)
    assert np.all(np.diff(t['var']) >= 0)


def test_disagreement_notes_guards():
    from types import SimpleNamespace
    rows = [dict(method=m, alpha=a, es_usd=v, status='ok', basis='GPD tail')
            for a, ratio in [(.90, 1.1), (.95, 1.2), (.99, 1.4)]
            for m, v in [('normal', 100.), ('historical', 100*ratio), ('mc_normal', 101.), ('evt', 130.)]]
    table = pd.DataFrame(rows)
    models = {'evt': SimpleNamespace(params={'xi': .1, 'xi_se': .02})}
    assert any('widens' in x for x in F.disagreement_notes(table, models, .99))
    table.loc[table.method == 'evt', 'status'] = 'Unavailable: failed fit'
    table.loc[(table.method == 'historical') & (table.alpha == .95), 'es_usd'] = 200
    notes = F.disagreement_notes(table, {}, .99)
    assert any('Unavailable:' in x for x in notes)
    assert not any('xi' in x or 'widens' in x for x in notes)
    for v in (0., np.nan):
        table.loc[table.method == 'normal', 'es_usd'] = v
        assert not any('historical ES is' in x for x in F.disagreement_notes(table, {}, .99))


def test_risk_page_windows_and_confidence(tmp_path):
    from streamlit.testing.v1 import AppTest
    src = (ROOT/'dashboard.py').read_text(encoding='utf-8')
    src = src.replace('title="Decision", default=True', 'title="Decision"').replace('title="Risk: VaR, ES, EVT",', 'title="Risk: VaR, ES, EVT", default=True,')
    page = tmp_path/'risk_page.py'
    page.write_text(f'import os, sys\nsys.path.insert(0, {str(ROOT)!r})\nos.chdir({str(ROOT)!r})\n'+src, encoding='utf-8')
    app = AppTest.from_file(str(page)).run(timeout=240)
    for alpha in (.90, .95, .99):
        app.sidebar.selectbox[0].set_value(alpha)
        for window in app.radio[0].options:
            app.radio[0].set_value(window).run(timeout=240)
            assert not app.exception and not app.error
            headers = [x.value for x in app.subheader]
            assert 'Unconditional: whole estimation window' in headers
            assert any(x.startswith('Conditional: next day') for x in headers)
            assert ('Full-sample bootstrap intervals' in headers) == window.startswith('Full sample')
            assert any('Neither is a maximum' in x.value for x in app.markdown)

def test_all_dashboard_pages(tmp_path):
    from streamlit.testing.v1 import AppTest
    source = (ROOT/'dashboard.py').read_text(encoding='utf-8')
    import re
    titles = re.findall(r'st.Page\(page_\w+, title="([^"]+)"', source)
    assert len(titles) == 10
    for i, title in enumerate(titles):
        src = source.replace('title="Decision", default=True', 'title="Decision"')
        src = src.replace(f'title="{title}",', f'title="{title}", default=True,')
        page = tmp_path/f'dashboard_page_{i}.py'
        page.write_text(f'import os, sys\nsys.path.insert(0, {str(ROOT)!r})\nos.chdir({str(ROOT)!r})\n'+src, encoding='utf-8')
        app = AppTest.from_file(str(page)).run(timeout=240)
        assert not app.exception and not app.error, title

# APP-018: EVT diagnostics and page verification.
def test_gpd_tail_probability_limits():
    from quanedge.risk.evt import EVT, GPDFit
    for xi in (.3, 0., -.3):
        fit = GPDFit(.01, xi, .02, 100, 1000)
        model = EVT(np.linspace(-.02, .1, 1000), fit)
        assert F.gpd_tail_prob(model.var(.99), fit, .1) == pytest.approx(.01)
        if xi == 0:
            assert F.gpd_tail_prob(.03, fit, .1) == pytest.approx(.1*np.exp(-1))
        if xi < 0:
            p = F.gpd_tail_prob(np.array([fit.u-fit.sigma/xi, 1.]), fit, .1)
            assert np.isfinite(p).all() and np.allclose(p, 0)


def test_evt_scan_matches_selected_model():
    from quanedge.risk.evt import fit_evt
    losses = np.random.default_rng(11).standard_t(4, 1200)*.01
    m = fit_evt(losses); scan = F.evt_scan(losses, 9.6e6, .99)
    row = scan.iloc[(scan.u-m.fit.u).abs().argmin()]
    assert row.es_usd == pytest.approx(9.6e6*m.es_fraction(.99))


def test_gpd_qq_refit_envelope_and_misspecification():
    from scipy.stats import genpareto
    from quanedge.risk.evt import fit_gpd
    n = 500
    losses = genpareto.rvs(.2, scale=.01, size=n, random_state=np.random.default_rng(23))
    fit = fit_gpd(losses, 0.)
    qq = F.gpd_qq(fit, losses, reps=100, seed=23)
    assert qq['status'] == 'ok' and qq['reps_ok']+qq['reps_failed'] == 100
    assert .90 < 1-qq['outside'].mean() < .995
    again = F.gpd_qq(fit, losses, reps=100, seed=23)
    assert np.array_equal(qq['lo'], again['lo'])
    other = genpareto.ppf((np.arange(n)+.5)/n, .8, scale=.01)
    bad = F.gpd_qq(fit, other, reps=100, seed=23)
    assert bad['outside'].mean() > qq['outside'].mean()+.2


def test_evt_notes_change_with_fit_and_failures():
    from quanedge.risk.evt import EVT, GPDFit
    losses = np.linspace(.001, .1, 100)
    scan = pd.DataFrame(dict(q=[.85, .95], fit_ok=[True, True], stable=[True, True], es_usd=[10., 12.], xi=[.2, .4],
                             u=[.01, .02], mean_excess=[.03, .04], sigma_star=[.002, -.001]))
    notes = []
    for xi in (.3, -.2):
        m = EVT(losses, GPDFit(.01, xi, .01, 90, 100))
        notes.append(F.evt_notes(m, scan, .99, 100., {'90th': {'status': 'failed'}}, None, {'status': 'unavailable'}))
    assert notes[0]['shape'] != notes[1]['shape']
    assert 'power-law' in notes[0]['shape'] and 'finite upper endpoint' in notes[1]['shape']
    assert 'unavailable' in notes[0]['conclusion']
    assert 'unavailable' in F.evt_notes({'status': 'failed'}, scan, .99, 100., {}, None, {})['conclusion']
    # sigma* crossing zero is reported in log-loss units, never as a share of its mean
    assert 'absolute mean' not in notes[0]['diagnostics'] and 'changing sign' in notes[0]['diagnostics']
    assert 'moves +0.20' in notes[0]['diagnostics']
    # at 90% the 95th-percentile row answers from the empirical body and is left out of the GPD-tail range
    at90 = F.evt_notes(m, scan, .90, 100., {}, None, {'status': 'unavailable'})['conclusion']
    assert 'USD 10 to USD 10.' in at90
    assert 'USD 10 to USD 12.' in notes[0]['conclusion']


def test_evt_qq_caption_gives_chance_rate():
    from quanedge.risk.evt import EVT, GPDFit
    m = EVT(np.linspace(.001, .1, 100), GPDFit(.01, .2, .01, 90, 100))
    scan = pd.DataFrame(dict(q=[.9], fit_ok=[True], stable=[False], es_usd=[1.], xi=[.2], u=[.01], mean_excess=[.03], sigma_star=[.01]))
    qq = {'status': 'ok', 'outside': np.r_[np.zeros(95, bool), np.ones(5, bool)], 'reps_ok': 10, 'reps_failed': 0}
    assert 'about 5% would by chance' in F.evt_notes(m, scan, .99, 1., {}, None, qq)['qq']


def test_strategy_evt_flags_grid_edge():
    from quanedge.risk import settings as S
    path = pd.DataFrame({'return': np.random.default_rng(5).standard_t(5, 3000)*.005})
    m = F.strategy_evt(path)
    q, grid = m.params['threshold_q'], S.EVT_THRESHOLD_GRID
    edge = abs(q-grid[0]) < 1e-3 or abs(q-grid[-1]) < 1e-3
    assert ('grid point' in m.status) == edge


def test_evt_page_all_confidence_levels(tmp_path):
    from streamlit.testing.v1 import AppTest
    source = (ROOT/'dashboard.py').read_text(encoding='utf-8')
    assert 'The GPD follows them' not in source
    src = source.replace('title="Decision", default=True', 'title="Decision"').replace('title="EVT tail",', 'title="EVT tail", default=True,')
    page = tmp_path/'evt_page.py'
    page.write_text(f'import os, sys\nsys.path.insert(0, {str(ROOT)!r})\nos.chdir({str(ROOT)!r})\n'+src, encoding='utf-8')
    app = AppTest.from_file(str(page)).run(timeout=240)
    for alpha in (.90, .95, .99):
        app.sidebar.selectbox[0].set_value(alpha).run(timeout=240)
        assert not app.exception and not app.error
        table = next(d.value for d in app.dataframe if 'Threshold / portfolio' in d.value)
        assert len(table) == 4 and f'ES {alpha:.0%}' in table
        assert any('In-sample diagnostic' in c.value for c in app.caption)
        assert len(app.get('plotly_chart')) == 7
        text = ' '.join(m.value for m in app.markdown)
        assert table.iloc[0][f'ES {alpha:.0%}'] in text
        assert 'Sequential evidence' in text and 'not this full-sample fit' in text
        assert 'absolute mean' not in ' '.join(c.value for c in app.caption)
