"""
Tests for price provenance, the risk-free basis, failure behaviour, stationarity reporting,
deterministic offline re-runs, and repository housekeeping.
"""
import hashlib
import inspect
import json
import re
import shutil
import urllib.request

import numpy as np
import pandas as pd
import pytest

import quanedge.config as config
import quanedge.data.run as run_module
import quanedge.data.sources as sources
from quanedge.config import CLEAN_DATA_DIR, DATA_DIR, ROOT, TICKERS
from quanedge.data import load_macro_data, load_risk_free_rate
from quanedge.data.cleaning import discount_to_bond_equivalent_yield
from quanedge.data.sources import audit_price_snapshot, download_etf_prices
from quanedge.data.stationarity import (
    generate_stationarity_summary_markdown,
    run_adf_test,
    run_arch_lm_test,
    test_portfolio_return_series as portfolio_stationarity,
)


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------- Risk-free basis ----------------

def test_discount_to_bond_equivalent_yield_formula():
    assert discount_to_bond_equivalent_yield(4.0) == pytest.approx(100 * 365 * 0.04 / (360 - 91 * 0.04))
    assert discount_to_bond_equivalent_yield(0.0) == 0.0
    series = pd.Series([1.0, 4.0, 5.0], index=pd.date_range("2020-01-01", periods=3))
    out = discount_to_bond_equivalent_yield(series)
    assert isinstance(out, pd.Series) and out.index.equals(series.index)
    assert (out > series).all()                       # yield is always above the discount rate
    assert (out - series).iloc[-1] > (out - series).iloc[0]


def test_risk_free_columns_are_built_from_bond_equivalent_yield():
    macro = load_macro_data()
    bey = discount_to_bond_equivalent_yield(macro["DTB3"])
    assert np.allclose(macro["DTB3_bey"], bey)
    assert np.allclose(macro["rf_daily_effective"], (1 + bey / 100) ** (1 / 252) - 1)
    assert np.allclose(macro["rf_daily_simple"], bey / 100 / 252)
    assert np.allclose(macro["term_spread_10y_3m"], macro["DGS10"] - bey)
    annual = load_risk_free_rate(frequency="annualized")
    assert np.allclose(annual, bey / 100)
    positive = macro["DTB3"] > 0.5
    assert (annual[positive] > macro.loc[positive, "DTB3"] / 100).all()


# ---------------- Price provenance ----------------

def test_price_provenance_file_describes_the_snapshot():
    prov = json.loads((CLEAN_DATA_DIR / "price_provenance.json").read_text(encoding="utf-8"))
    snap = DATA_DIR / "cache" / prov["snapshot"]["file"]
    assert prov["snapshot"]["sha256"] == _sha(snap)
    assert prov["snapshot"]["rows_in_file"] == 5470
    assert prov["snapshot"]["rows_dropped_by_common_calendar_filter"] == 0
    assert prov["clean_rows"] == 5470 and prov["refreshed_in_this_run"] is False
    assert "auto_adjust=True" in prov["source"]
    assert "will not match" in prov["reproducibility_warning"]
    meta = prov["download_metadata"]
    # either a real retrieval time, or an explicit statement that it is unknown
    assert ("yfinance_version" in meta) or (meta["retrieved_at_utc"] == "unknown" and "pre-dates" in meta["note"])
    assert set(prov["installed_versions"]) == {"yfinance", "pandas", "numpy", "statsmodels"}


def test_price_snapshot_audit_counts_dropped_dates_and_ingest_warns(tmp_path, caplog):
    idx = pd.bdate_range("2020-01-01", periods=10)
    px = pd.DataFrame(np.arange(1, 71, dtype=float).reshape(10, 7), index=idx, columns=TICKERS)
    px.iloc[3, 2] = np.nan
    px.iloc[7, 5] = np.nan
    snap = tmp_path / "snap.csv"
    px.to_csv(snap)

    audit = audit_price_snapshot(snap)
    assert audit["rows_in_file"] == 10
    assert audit["rows_with_missing_price"] == 2
    assert audit["rows_dropped_by_common_calendar_filter"] == 2
    assert audit["sha256"] == _sha(snap)

    with caplog.at_level("WARNING"):
        common = download_etf_prices(cache_path=snap)
    assert len(common) == 8
    assert "2 of 10 dates dropped" in caplog.text


# ---------------- Failure behaviour: no invented data ----------------

@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """A private copy of the cached inputs with every output directory redirected to tmp_path."""
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR / "raw", data / "raw")
    shutil.copytree(DATA_DIR / "cache", data / "cache")
    for name, value in {
        "DATA_DIR": data,
        "CLEAN_DATA_DIR": data / "clean",
        "RESULTS_DATA_DIR": tmp_path / "results" / "data",
    }.items():
        monkeypatch.setattr(run_module, name, value)
    monkeypatch.setattr(sources, "RAW_DATA_DIR", data / "raw")
    monkeypatch.setattr(sources, "CACHE_DATA_DIR", data / "cache")
    return tmp_path


def test_missing_fred_data_stops_the_pipeline_instead_of_inventing_a_rate(sandbox, monkeypatch):
    def fail(refresh=False):
        raise RuntimeError("FRED unreachable")

    monkeypatch.setattr(run_module, "download_all_fred_series", fail)
    with pytest.raises(RuntimeError, match="FRED unreachable"):
        run_module.run_pipeline()
    assert list((sandbox / "data" / "clean").glob("*.csv")) == []      # nothing half-written


def test_partial_fred_failure_is_not_swallowed(tmp_path, monkeypatch):
    real = sources.download_fred_series

    def flaky(series_id, cache_dir=None, refresh=False):
        if series_id == "DTB3":
            raise RuntimeError("no DTB3")
        return real(series_id, cache_dir=sources.RAW_DATA_DIR, refresh=False)

    monkeypatch.setattr(sources, "download_fred_series", flaky)
    with pytest.raises(RuntimeError, match="no DTB3"):
        sources.download_all_fred_series()


def test_worldbank_failure_without_cache_raises(tmp_path, monkeypatch):
    def offline(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", offline)
    with pytest.raises(RuntimeError):
        sources.download_worldbank_indicators(cache_dir=tmp_path, refresh=True)


def test_no_synthetic_risk_free_fallback_in_code():
    assert "synthetic" not in inspect.getsource(run_module).lower()
    assert "0.04 / 252" not in inspect.getsource(run_module)


# ---------------- Deterministic, offline re-run ----------------

def test_rerun_is_offline_and_reproduces_committed_files(sandbox, monkeypatch, capsys):
    def no_network(*args, **kwargs):
        raise AssertionError("pipeline tried to use the network although every input is cached")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    run_module.run_pipeline()
    capsys.readouterr()

    rebuilt = sandbox / "data" / "clean"
    for committed in sorted(CLEAN_DATA_DIR.glob("*.csv")):
        # Recomputed floats differ at ~1e-15 between CPUs/platforms, so compare values, not bytes.
        pd.testing.assert_frame_equal(pd.read_csv(rebuilt / committed.name), pd.read_csv(committed),
                                      check_exact=False, rtol=1e-9, atol=1e-12,
                                      obj=f"{committed.name} after re-run")
    assert (rebuilt / "price_provenance.json").read_text() == (CLEAN_DATA_DIR / "price_provenance.json").read_text()

    # Raw inputs are never recomputed, so their hashes must be identical.
    manifest = json.loads((rebuilt / "data_manifest.json").read_text())["files"]
    committed_manifest = json.loads((CLEAN_DATA_DIR / "data_manifest.json").read_text())["files"]
    raw = [k for k in committed_manifest if k.startswith("raw")]
    assert {k: manifest[k]["sha256"] for k in raw} == {k: committed_manifest[k]["sha256"] for k in raw}


def test_refresh_prints_a_warning_banner(sandbox, monkeypatch, capsys):
    # stand-ins that ignore refresh so no download happens
    for name in ("download_etf_prices", "download_all_fred_series", "download_worldbank_indicators"):
        original = getattr(sources, name)
        monkeypatch.setattr(run_module, name, lambda refresh=False, _f=original: _f(refresh=False))
    run_module.run_pipeline(refresh=True)
    out = capsys.readouterr().out
    assert "REFRESH REQUESTED" in out and "re-scaled after every dividend" in out
    prov = json.loads((sandbox / "data" / "clean" / "price_provenance.json").read_text())
    assert prov["refreshed_in_this_run"] is True


# ---------------- Stationarity reporting ----------------

@pytest.fixture(scope="module")
def stat():
    return pd.read_csv(CLEAN_DATA_DIR / "stationarity_tests.csv")


def test_stationarity_table_has_fixed_lag_kpss_flag_and_arch_columns(stat):
    for col in ("adf_stat_lag5", "adf_p_value_lag5", "kpss_p_capped", "arch_lm_p_value"):
        assert col in stat.columns
    returns = stat[stat["series_type"] == "Daily Log Returns r_t"]
    assert len(returns) == 7
    # KPSS p-values are capped at 0.10: flag exactly those
    assert (returns["kpss_p_capped"] == (returns["kpss_p_value"] >= 0.1 - 1e-9)).all()
    # volatility clusters: ARCH effects are overwhelming for every ETF
    assert (returns["arch_lm_p_value"] < 1e-10).all()


def test_gld_adf_extreme_value_is_a_lag_selection_artefact(stat):
    returns = stat[stat["series_type"] == "Daily Log Returns r_t"].set_index("asset")
    assert returns.loc["GLD", "adf_lags"] == 0
    assert returns.loc["GLD", "adf_stat"] < -60
    # at a common fixed lag the assets are comparable
    assert returns["adf_stat_lag5"].between(-40, -25).all()


def test_equal_weight_placeholder_row_is_labelled(stat):
    row = stat[stat["asset"] == "EW-PLACEHOLDER"]
    assert len(row) == 1 and "placeholder" in row.iloc[0]["series_type"]


def test_run_adf_test_fixed_lag_and_arch_lm_on_synthetic_data():
    rng = np.random.default_rng(1)
    noise = pd.Series(rng.normal(size=3000))
    assert run_adf_test(noise, autolag=None, maxlag=5)["used_lag"] == 5

    walk = pd.Series(np.cumsum(rng.normal(size=3000)))
    assert run_adf_test(walk)["p_value"] > 0.05            # unit root not rejected

    assert run_arch_lm_test(noise)["p_value"] > 0.01       # no ARCH effects in iid noise
    vol = np.ones(3000)
    shocks = rng.normal(size=3000)
    r = np.zeros(3000)
    for t in range(1, 3000):
        vol[t] = np.sqrt(0.2 + 0.7 * r[t - 1] ** 2)
        r[t] = vol[t] * shocks[t]
    assert run_arch_lm_test(pd.Series(r))["p_value"] < 1e-6


def test_portfolio_stationarity_helper():
    rng = np.random.default_rng(2)
    series = pd.Series(rng.normal(0, 0.01, 2000), index=pd.bdate_range("2015-01-01", periods=2000))
    out = portfolio_stationarity(series, name="My portfolio")
    assert out.iloc[0]["asset"] == "My portfolio"
    assert out.iloc[0]["verdict"] == "Stationary I(0)"
    assert {"adf_stat", "adf_stat_lag5", "kpss_stat", "arch_lm_p_value"} <= set(out.columns)


def _marked_block(path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<!-- BEGIN stationarity -->\n(.*?)\n<!-- END stationarity -->", text, re.S)
    assert m, f"{path} has no generated stationarity block"
    return m.group(1).strip()


@pytest.mark.parametrize("doc", ["README.md", "docs/person-1/01-data-pipeline.md"])
def test_documented_stationarity_text_matches_data(doc):
    md = generate_stationarity_summary_markdown(pd.read_csv(CLEAN_DATA_DIR / "stationarity_tests.csv"))
    expected = ("### Test Results Across Investable Universe" + md.split("### Test Results Across Investable Universe", 1)[1]).strip()
    assert _marked_block(ROOT / doc) == expected


def test_stationarity_text_does_not_overclaim():
    text = generate_stationarity_summary_markdown(pd.read_csv(CLEAN_DATA_DIR / "stationarity_tests.csv"))
    assert "Strictly Stationary" not in text and "validates the mathematical assumptions" not in text
    assert "lag-selection artefact" in text and "PLACEHOLDER" in text


# ---------------- Housekeeping ----------------

def test_no_machine_specific_pytest_options():
    assert "fugue" not in (ROOT / "pytest.ini").read_text()


def test_date_range_has_a_single_source_of_truth():
    from quanedge.risk import settings

    assert settings.DEV_START == config.START_DATE
    assert settings.DEV_END == config.END_DATE


def test_unused_quick_flag_removed_and_https_used():
    assert "--quick" not in inspect.getsource(run_module)
    assert "quick" not in inspect.signature(run_module.run_pipeline).parameters
    assert "http://api.worldbank.org" not in inspect.getsource(sources)


def test_readme_does_not_claim_unreviewed_validation():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Completed & Validated" not in readme


def test_downloads_use_a_certifi_ca_bundle(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout=None, context=None):
        seen["context"] = context
        raise OSError("stop")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(OSError):
        sources._urlopen(urllib.request.Request("https://example.invalid"))
    assert seen["context"] is not None and seen["context"].verify_mode.name == "CERT_REQUIRED"
    assert "certifi" in (ROOT / "requirements.txt").read_text()


def test_documented_row_counts_match_files():
    dictionary = (ROOT / "data" / "data_dictionary.md").read_text(encoding="utf-8")
    for name in ("worldbank_macro", "stationarity_tests", "anomaly_log", "data_quality_log", "calendar_audit", "macro_ffill_log", "prices_clean"):
        rows = len(pd.read_csv(CLEAN_DATA_DIR / f"{name}.csv"))
        line = next(l for l in dictionary.splitlines() if l.startswith(f"| `{name}.csv`"))
        assert f"| {rows:,} |" in line or f"| {rows} |" in line, f"{name}: dictionary row count != {rows}"
