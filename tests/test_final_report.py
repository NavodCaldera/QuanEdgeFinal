"""Technical report for the final portfolio: built from the dashboard's evidence, 7-15 pages, numbers traceable."""
import json
import numpy as np
import pandas as pd
import pytest
from pypdf import PdfReader
from quanedge import config, final_portfolio as F
from quanedge.final_report import Doc, build, data_facts, num, to_markdown


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    out = tmp_path_factory.mktemp("report")
    folder, pages = build(out, model="v5")
    text = "\n".join(p.extract_text() for p in PdfReader(folder/"technical_report.pdf").pages)
    return folder, pages, text, json.loads((folder/"numbers.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report_v6(tmp_path_factory):
    out = tmp_path_factory.mktemp("report_v6")
    folder, pages = build(out, model="v6")
    text = "\n".join(p.extract_text() for p in PdfReader(folder/"technical_report.pdf").pages)
    return folder, pages, text, json.loads((folder/"numbers.json").read_text(encoding="utf-8"))


def test_v6_report_length_sections_and_disclosure(report_v6):
    folder, pages, text, numbers = report_v6
    assert 7 <= pages <= 15 and numbers["model"] == "v6"
    for heading in ("3.4 The recession overlay", "Assumptions and limitations", "Recommendation and monitoring",
                    "evaluation incomplete", "higher of"):
        assert heading in text
    assert json.loads((folder/"manifest.json").read_text(encoding="utf-8"))["model"] == "v6"


def test_v6_report_quotes_the_v6_evidence(report_v6):
    _, _, text, numbers = report_v6
    ev = F.load_evidence(model="v6"); s = ev["summary"]; _, returns, rf, cpi = F.load_market()
    assert numbers["strategy_hash"] == ev["strategy_hash"] and numbers["weights"] == F.current_target(ev["path"])
    perf = F.performance(ev["path"], returns, rf, cpi)
    assert numbers["performance"]["cagr"] == pytest.approx(s["realised"]["cagr"], abs=1e-9)
    assert f"{100*perf['cagr']:.2f}%" in text and f"{-100*perf['maximum_drawdown']:.1f}%" in text
    ge = next(v for v in s["validation"] if v["method"] == "garch_evt" and v["alpha"] == .99)
    assert numbers["backtest_challenger_99"]["breaches"] == ge["breaches"] and f"GARCH-EVT {ge['breaches']} breaches" in text
    assert numbers["overlay"]["months_on"] == len(s["overlay_months_on"])


def test_report_length_and_required_sections(report):
    folder, pages, text, _ = report
    assert 7 <= pages <= 15
    for heading in ("Data sources and cleaning", "Portfolio construction", "Risk measurement and validation methods", "Results",
                    "Assumptions and limitations", "Recommendation and monitoring", "Reproducibility, provenance and AI use"):
        assert heading in text
    md = (folder/"technical_report.md").read_text(encoding="utf-8")
    assert "@T:" not in md and "@F:" not in md and "&lt;" not in md
    for f in json.loads((folder/"manifest.json").read_text(encoding="utf-8"))["outputs"]:
        assert (folder/f).exists()


def test_report_quotes_the_dashboard_numbers(report):
    _, _, text, numbers = report
    ev = F.load_evidence(model="v5"); prices, returns, rf, cpi = F.load_market(); V = float(F.policy()["value"])
    w = F.current_target(ev["path"])
    assert numbers["weights"] == w
    perf = F.performance(ev["path"], returns, rf, cpi)
    assert numbers["performance"]["cagr"] == pytest.approx(perf["cagr"], abs=1e-12)
    _, table = F.risk_now(returns, w, V)
    hist = table[(table.method == "historical") & np.isclose(table.alpha, .99)].iloc[0]
    assert num(hist.var_usd) in text and num(hist.es_usd) in text
    assert f"{100*perf['cagr']:.2f}%" in text and f"{100*w['XLE']:.1f}%" in text
    ge = next(v for v in ev["summary"]["validation"] if v["method"] == "garch_evt" and v["alpha"] == .99)
    assert f"GARCH-EVT {ge['breaches']} breaches" in text


def test_no_double_negatives_or_negative_zero(report):
    import re
    _, _, text, _ = report
    for phrase in ("cost USD −", "costs USD −", "loss USD −", "loss of USD −", "lost USD −"):
        assert phrase not in text
    assert not re.search(r"−0(?![.,\d])", text)


def test_cross_references_resolve_forward():
    doc = Doc()
    doc.p("See Table @T:later@ and Figure @F:pic@.")
    doc.table(["a"], [["1"]], [1.], caption="first")
    doc.table(["a"], [["1"]], [1.], caption="second", label="later")
    doc.figure("x.png", "a figure", label="pic")
    assert doc.resolved()[0][1][0] == "See Table 2 and Figure 1."


def test_markdown_renders_markup(tmp_path):
    doc = Doc(); doc.p("<b>Bold</b> w<sub>i</sub> p &lt;0.001")
    to_markdown(doc, tmp_path/"x.md", "figures")
    assert (tmp_path/"x.md").read_text(encoding="utf-8").strip() == "**Bold** w_i p <0.001"


def test_data_facts_are_internally_consistent():
    d = data_facts(config.ROOT)
    assert d["weekdays"]-d["dates"] == sum(d["calendar"].values())
    assert d["flags_corroborated"]+d["flags_review"] == d["flags"]
    assert sum(d["ffill_by_series"].values()) == d["ffill_rows"]
    for g in d["cpi_gaps"]:                       # a missing CPI month is carried longer than a normal release interval
        assert g["sessions"] > g["typical"]


def test_reserve_history_matches_the_v5_reserve_accounting():
    from quanedge.strategy import reserve_path
    ev = F.load_evidence(model="v5"); _, _, _, cpi = F.load_market(); cfg = F.policy()
    h = F.reserve_history(ev["path"], cpi, cfg)
    p = reserve_path(ev["path"]["return"], cfg)
    assert h["end_usd"] == pytest.approx(cfg["fund_value"]*p.wealth.iloc[-1], rel=1e-12)
    assert h["payments"] == int((p.spending > 0).sum()) == p.index.year.nunique()


def test_bootstrap_reproduces_the_mandate_v5_run():
    saved = config.RESULTS_DIR/"final-v5-20261031"/"selected"/"uncertainty.csv"
    if not saved.exists():
        pytest.skip("mandate v5 run not present")
    ev = F.load_evidence(model="v5"); _, returns, _, _ = F.load_market()
    mine = F.bootstrap(returns, F.current_target(ev["path"]), float(F.policy()["value"]))
    theirs = pd.read_csv(saved)
    cols = [c for c in theirs if c != "method"]
    assert (mine.method == theirs.method).all()
    assert np.allclose(mine[cols].to_numpy(float), theirs[cols].to_numpy(float), rtol=1e-12, atol=1e-15)


def test_comparison_weights_are_feasible():
    ev = F.load_evidence(model="v5"); _, returns, rf, cpi = F.load_market()
    c = F.comparison(ev["path"], returns, rf, cpi)
    assert c.weights.iloc[0] is None and c.portfolio.iloc[0].startswith("Final portfolio")
    for w in c.weights.iloc[1:]:
        assert set(w) == set(F.UNIVERSE) and abs(sum(w.values())-1) < 1e-6 and min(w.values()) >= 0
