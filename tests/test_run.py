"""The one-command run: provided inputs, a complete manifest, and all-or-nothing publication."""
import json

import numpy as np
import pandas as pd
import pytest

from quanedge.risk import run


@pytest.fixture
def inputs(tmp_path):
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2015-01-01", periods=1200)
    x = pd.DataFrame(0.01 * rng.standard_t(5, (1200, 3)) / np.sqrt(5 / 3), index=idx, columns=["SPY", "AGG", "GLD"])
    x.to_csv(tmp_path / "returns.csv")
    (tmp_path / "weights.json").write_text(json.dumps({"SPY": 0.5, "AGG": 0.3, "GLD": 0.2}))
    return tmp_path


def args(folder, out, weights="weights.json"):
    return ["--quick", "--returns", str(folder / "returns.csv"), "--weights", str(folder / weights), "--out", str(out)]


def test_quick_run_with_provided_inputs_writes_a_complete_record(inputs):
    out = inputs / "run"
    run.main(args(inputs, out))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "quick" and manifest["inputs"]["development"] is False
    assert manifest["inputs"]["weights"] == {"SPY": 0.5, "AGG": 0.3, "GLD": 0.2}
    assert len(manifest["inputs"]["source_sha256"]) == 64 and manifest["rolling"] is None
    assert set(manifest["models"]) == set(run.LABEL)
    assert {"summary.md", "manifest.json", "tables/risk_table.csv", "tables/mc_convergence.csv"} <= set(manifest["files"])
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert "Development inputs" not in text and "tomorrow" not in text.lower()
    assert not list(inputs.glob(".run.*"))                     # no partial or replaced folders left behind


def test_a_run_that_fails_midway_leaves_the_previous_output_untouched(inputs, monkeypatch):
    out = inputs / "run"
    out.mkdir()
    (out / "marker.txt").write_text("previous run")

    def boom(*a, **k):
        raise RuntimeError("simulated failure after the run folder was created")

    monkeypatch.setattr(run, "bootstrap_intervals", boom)
    with pytest.raises(RuntimeError):
        run.main(args(inputs, out))
    assert (out / "marker.txt").read_text() == "previous run"
    assert not list(inputs.glob(".run.*"))


def test_inputs_outside_the_permitted_universe_are_rejected(inputs):
    pd.read_csv(inputs / "returns.csv", index_col=0).rename(columns={"GLD": "BTC"}).to_csv(inputs / "returns.csv")
    with pytest.raises(ValueError, match="permitted universe"):
        run.main(args(inputs, inputs / "run"))


def test_pipeline_weight_artifact_is_accepted_and_verified(inputs):
    from quanedge.portfolio import weight_hash
    weights={"SPY":.5,"AGG":.3,"GLD":.2}
    artifact={"weights":weights,"weight_hash":weight_hash(weights),"effective_date":"2026-09-30"}
    path=inputs/"canonical.json";path.write_text(json.dumps(artifact))
    _,loaded,meta=run.load_inputs(inputs/"returns.csv",path)
    assert loaded==weights and meta["weights_sha256"]==artifact["weight_hash"]
    artifact["weight_hash"]="wrong";path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError,match="hash mismatch"):run.load_inputs(inputs/"returns.csv",path)
