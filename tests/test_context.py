"""Standalone long-history context (CTX-001): arithmetic, honesty and isolation, offline."""
import hashlib
import json
import numpy as np
import pandas as pd
import pytest
from quanedge import config, context
from quanedge.config import ROOT, TICKERS

RUN = ROOT/"results/final-20261027"


def staggered_prices():
    """Synthetic panel whose ETFs start on different dates; NaN before each start."""
    idx = pd.bdate_range("1999-01-04", "2006-12-29")
    rng = np.random.default_rng(7)
    px = pd.DataFrame(100*np.exp(rng.normal(0, .01, (len(idx), 7)).cumsum(axis=0)), index=idx, columns=TICKERS)
    for t, start in zip(TICKERS, ["1999-01-04", "2001-08-27", "2003-04-14", "2003-09-29", "2004-11-18", "1999-01-04", "2000-06-01"]):
        px.loc[:pd.Timestamp(start) - pd.Timedelta(days=1), t] = np.nan
    return px


def test_drawdown_peak_trough_recovery_and_under_water():
    s = pd.Series([100, 120, 90, 60, 100, 125, 110.], index=pd.bdate_range("2020-01-01", periods=7))
    d = context.drawdown(s)
    assert d["max_drawdown"] == pytest.approx(-.5)
    assert (str(d["peak"]), str(d["trough"]), str(d["recovery"])) == ("2020-01-02", "2020-01-06", "2020-01-08")
    assert d["recovered"] and d["under_water_trading_days"] == 4
    unrecovered = context.drawdown(s.iloc[:5])
    assert unrecovered["recovery"] is None and not unrecovered["recovered"]
    assert unrecovered["under_water_trading_days"] == 3


def test_coverage_uses_each_etfs_own_dates_without_filling():
    px = staggered_prices(); cov = context.coverage(px).set_index("ticker")
    assert str(cov.loc["GLD", "first_price_date"]) == "2004-11-18"
    assert str(cov.loc["GLD", "first_return_date"]) == "2004-11-19"
    assert cov.loc["GLD", "omitted_before_frozen_start"] == len(px.loc["2004-11-18":"2005-01-02"])
    assert cov.loc["SPY", "Dot-com bear market"] == "full"
    assert cov.loc["EFA", "Dot-com bear market"] == "partial"
    assert cov.loc["GLD", "Dot-com bear market"] == "none"
    r = context.own_returns(px.GLD)
    assert r.index[0] == pd.Timestamp("2004-11-19") and r.notna().all()
    assert len(r) == px.GLD.notna().sum() - 1        # no zero-filled or invented pre-launch returns


def test_drawdowns_since_2005_restart_the_peak():
    px = staggered_prices(); px.loc["2005-01-03":, "XLK"] = np.linspace(50, 60, len(px.loc["2005-01-03":]))
    d = context.drawdowns(px).set_index(["ticker", "sample"])
    assert d.loc[("XLK", "since 2005"), "max_drawdown"] == pytest.approx(0)
    assert d.loc[("XLK", "full history"), "max_drawdown"] < 0


def test_validate_rejects_unsafe_snapshots():
    px = staggered_prices()
    context.validate(px)
    with pytest.raises(ValueError, match="snapshot end"):
        context.validate(pd.concat([px, px.iloc[[-1]].set_axis([pd.Timestamp("2026-10-01")])]))
    with pytest.raises(ValueError, match="positive"):
        bad = px.copy(); bad.iloc[-1, 0] = -1; context.validate(bad)
    with pytest.raises(ValueError, match="fixed order"):
        context.validate(px[TICKERS[::-1]])


def test_load_refuses_missing_or_altered_snapshot(tmp_path):
    assert context.load(tmp_path) is None
    staggered_prices().to_csv(tmp_path/"prices_full_history.csv", lineterminator="\n")
    digest = hashlib.sha256((tmp_path/"prices_full_history.csv").read_bytes()).hexdigest()
    (tmp_path/"manifest.json").write_text(json.dumps({"files": {"prices_full_history.csv": digest}}))
    assert context.load(tmp_path) is not None
    with (tmp_path/"prices_full_history.csv").open("a") as f:
        f.write("\n")
    assert context.load(tmp_path) is None


def test_paths_follow_project_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    assert context.raw_dir() == tmp_path/"context/raw" and context.load() is None


def test_context_is_isolated_from_frozen_pipeline():
    # Kept outside data/, which the final pipeline hashes as its data identity.
    assert not (ROOT/"data/context").exists()
    # No module of the frozen analysis may read the context; documentation revisions may.
    frozen_sources = json.loads((RUN/"manifest.json").read_text(encoding="utf-8"))["source_file_hashes"] if (RUN/"manifest.json").exists() else {}
    for name in frozen_sources or [p.relative_to(ROOT).as_posix() for p in (ROOT/"quanedge").rglob("*.py") if p.stem not in ("context", "docrev")]:
        if name.endswith(".py") and name != "app.py":
            text = (ROOT/name).read_text(encoding="utf-8")
            assert "quanedge.context" not in text and "from .context" not in text and "from . import context" not in text, name
    clean = pd.read_csv(ROOT/"data/clean/prices_clean.csv", index_col=0, parse_dates=True)
    assert clean.index[0] == pd.Timestamp(context.FROZEN_START) and clean.notna().all().all()


@pytest.mark.skipif(not (RUN/"submission.json").exists(), reason="frozen run absent")
def test_estimator_sensitivity_reproduces_frozen_file_and_flags_hurdle():
    prices = pd.read_csv(ROOT/"data/clean/prices_clean.csv", index_col=0, parse_dates=True)
    table = context.estimator_sensitivity(RUN, prices)       # raises if the frozen rows are not reproduced
    a1 = table[(table.portfolio == "A1_min_cvar") & (table.mean_shrinkage == 0)]
    assert not a1.meets_hurdle.any()
    frozen = table[(table.portfolio == "A1_min_cvar") & table.frozen_setting]
    assert frozen.meets_hurdle.all()


@pytest.mark.skipif(not (RUN/"submission.json").exists(), reason="frozen run absent")
def test_dotcom_partial_never_estimates_unobserved_sleeves():
    table = context.dotcom_partial(RUN, staggered_prices())
    unseen = table[~table.observed]
    assert set(unseen.ticker) >= {"AGG", "GLD"}
    assert unseen.sleeve_return.isna().all() and unseen.sleeve_loss_usd.isna().all()
    seen = table[table.observed].iloc[0]
    assert seen.sleeve_loss_usd == pytest.approx(-1e7*seen.weight*seen.sleeve_return)
