"""Executive tear sheet for the final model (v6): one page, numbers from the dashboard's own evidence."""
import json
import pytest
from pypdf import PdfReader
from quanedge import final_portfolio as F
from quanedge.final_report import num
from quanedge.tear_sheet import build, periods


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    folder, pages = build(tmp_path_factory.mktemp("tear"))
    text = PdfReader(folder/"executive_tear_sheet.pdf").pages[0].extract_text()
    return folder, pages, text, json.loads((folder/"numbers.json").read_text(encoding="utf-8"))


def test_exactly_one_page_with_required_blocks(sheet):
    folder, pages, text, _ = sheet
    assert pages == 1
    for block in ("Recommendation", "Allocation to hold now", "Performance", "Risk: one day", "Validation", "Stress tests",
                  "What can go wrong?", "How bad can losses get?", "How confident are we?", "evaluation incomplete",
                  "retrospective portfolio evaluation", "Human reviewer and date: pending"):
        assert block in text
    manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["model"] == "v6" and all((folder/f).exists() for f in manifest["outputs"])


def test_quotes_the_v6_evidence(sheet):
    _, _, text, q = sheet
    ev = F.load_evidence(model="v6"); s = ev["summary"]
    assert q["strategy_hash"] == ev["strategy_hash"] and q["weights"] == F.current_target(ev["path"])
    assert q["performance"]["v6"]["cagr"] == pytest.approx(s["realised"]["cagr"], abs=1e-9)
    assert -q["performance"]["v6"]["maximum_drawdown"] == pytest.approx(s["realised"]["maximum_decline"], abs=1e-9)
    ge = next(v for v in s["validation"] if v["method"] == "garch_evt" and v["alpha"] == .99)
    assert q["backtest"]["garch_evt"]["breaches"] == ge["breaches"]
    gfc = next(x for x in s["stress"] if x["scenario"] == "GFC")
    assert q["stress"]["GFC"]["return"] == pytest.approx(gfc["return"], abs=1e-9)
    assert q["overlay_months"] == len(s["overlay_months_on"]) and q["overlay_on_now"] == s["latest_overlay_on"]
    for x in (q["models_99"]["Historical simulation"]["es_usd"], q["hypothetical"]["loss_usd"], q["stress"]["Rates 2022"]["loss_usd"]):
        assert num(x) in text


def test_periods_groups_consecutive_months():
    runs = periods(["2008-11", "2008-12", "2009-01", "2019-05", "2020-02", "2020-03"])
    assert [[str(a), str(b)] for a, b in runs] == [["2008-11", "2009-01"], ["2019-05", "2019-05"], ["2020-02", "2020-03"]]
