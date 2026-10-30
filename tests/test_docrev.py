"""Documentation revision r1: parent identity, page limits and tamper detection, offline."""
import shutil
import pytest
from quanedge import docrev
from quanedge.config import ROOT

RUN = ROOT/"results/final-20261027"
OUT = ROOT/"results/docrev/final-20261027-r1"


def test_listed_joins_names_plainly():
    assert docrev.listed(["AGG"]) == "AGG"
    assert docrev.listed(["AGG", "GLD"]) == "AGG and GLD"
    assert docrev.listed(["SPY", "AGG", "GLD"]) == "SPY, AGG and GLD"


@pytest.mark.skipif(not (OUT/"revision.json").exists(), reason="revision not built")
def test_revision_verifies_and_detects_tampering(tmp_path):
    result = docrev.verify(OUT, RUN)
    assert result["status"] == "PASS" and result["page_counts"]["executive_tear_sheet.pdf"] == 1
    assert 7 <= result["page_counts"]["investment_memorandum.pdf"] <= 15
    copy = tmp_path/"rev"; shutil.copytree(OUT, copy)
    with (copy/"speaker_qa_notes.md").open("a", encoding="utf-8") as f:
        f.write("edited\n")
    with pytest.raises(ValueError, match="revision file hash"):
        docrev.verify(copy, RUN)
