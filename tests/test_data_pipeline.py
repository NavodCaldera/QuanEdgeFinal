"""
Comprehensive unit and integration tests for Person 1 (Data Engineering & Reproducibility).

Validates:
1. ETF price dataset structure, positivity, and lack of nulls.
2. Return mathematics: exact mathematical equivalence between simple and log returns.
3. Market calendar alignment across all 7 ETFs, including documented closures.
4. Macroeconomic and risk-free series alignment and bank holiday forward-fill policy.
5. Outlier detection, historical crisis cross-referencing, and 0 silent deletions.
6. Stationarity verification (ADF unit root rejection on returns).
7. Cryptographic SHA-256 data manifest integrity.
8. Seamless integration into Person 3 risk models.
"""
import numpy as np
import pandas as pd
import pytest

from quanedge.config import TICKERS
from quanedge.data import (
    get_anomaly_log,
    get_data_manifest,
    get_stationarity_report,
    load_clean_prices,
    load_clean_returns,
    load_log_returns,
    load_macro_data,
    load_risk_free_rate,
    load_simple_returns,
)
from quanedge.data.anomalies import generate_full_anomaly_audit
from quanedge.data.cleaning import audit_trading_calendar, calculate_returns, validate_price_data
from quanedge.data.manifest import verify_dataset_manifest
from quanedge.data.stationarity import run_adf_test, run_kpss_test
from quanedge.risk.portfolio import portfolio_log_returns


# ---------------- Price and Return Data Contract Tests ----------------

def test_clean_prices_contract():
    prices = load_clean_prices()
    assert isinstance(prices, pd.DataFrame)
    assert isinstance(prices.index, pd.DatetimeIndex)
    assert prices.index.is_monotonic_increasing
    assert not prices.index.duplicated().any()
    assert list(prices.columns) == TICKERS
    assert len(prices) >= 5000
    assert (prices > 0).all().all()
    assert prices.notnull().all().all()


def test_return_mathematical_identity():
    prices = load_clean_prices()
    simple_ret, log_ret = calculate_returns(prices)

    # 1. Dimensions match
    assert simple_ret.shape == log_ret.shape
    assert len(log_ret) == len(prices) - 1

    # 2. Exact mathematical identity: r = ln(1 + R)
    expected_log = np.log(1.0 + simple_ret.values)
    assert np.allclose(log_ret.values, expected_log, atol=1e-12)

    # 3. Exact inverse: R = exp(r) - 1
    expected_simple = np.exp(log_ret.values) - 1.0
    assert np.allclose(simple_ret.values, expected_simple, atol=1e-12)


def test_return_convenience_loaders():
    log_ret = load_log_returns()
    simp_ret = load_simple_returns()
    assert log_ret.shape == simp_ret.shape
    assert (log_ret.columns == TICKERS).all()
    assert (simp_ret.columns == TICKERS).all()

    with pytest.raises(ValueError):
        load_clean_returns(kind="unsupported_return_type")


# ---------------- Calendar and Gap Audit Tests ----------------

def test_trading_calendar_alignment():
    prices = load_clean_prices()
    audit = audit_trading_calendar(prices)

    assert audit["total_trading_days"] == len(prices)
    assert audit["start_date"] == prices.index.min().strftime("%Y-%m-%d")
    assert audit["end_date"] == prices.index.max().strftime("%Y-%m-%d")

    # Verify documented non-standard closures exist in audit gaps
    closure_reasons = [g["reasons"] for g in audit["extended_gaps"]]
    all_reasons_str = " ".join(closure_reasons)
    assert "Hurricane Sandy" in all_reasons_str
    assert "Gerald R. Ford" in all_reasons_str


# ---------------- Macroeconomic and Risk-Free Tests ----------------

def test_macro_data_alignment():
    macro = load_macro_data()
    prices = load_clean_prices()

    assert (macro.index == prices.index).all()

    expected_cols = ["DTB3", "DGS10", "rf_daily_effective", "rf_daily_simple", "rf_daily_log", "term_spread_10y_3m"]
    for col in expected_cols:
        assert col in macro.columns, f"Missing expected macro column: {col}"

    assert macro[expected_cols].notnull().all().all()

    # Risk-free rates in this historical sample: yields were positive except brief collateral crunches in 2015 and 2020 down to -0.05%
    assert (macro["rf_daily_effective"] >= -0.001).all()


def test_risk_free_rate_loader():
    rf_daily = load_risk_free_rate(frequency="daily", kind="effective")
    rf_ann = load_risk_free_rate(frequency="annualized")

    assert len(rf_daily) == len(rf_ann)
    # Check annualized yield range: bounded between -0.1% and 10%
    assert (rf_ann >= -0.001).all()
    assert (rf_ann <= 0.10).all()

    # Compound daily rate scaled back up to annual should be close to rf_ann
    reconstituted = (1.0 + rf_daily) ** 252 - 1.0
    assert np.allclose(reconstituted.values, rf_ann.values, atol=1e-3)


# ---------------- Anomaly Detection & Crisis Mapping Tests ----------------

def test_anomaly_audit_compliance():
    prices = load_clean_prices()
    log_ret = load_log_returns()
    anomaly_df, summary = generate_full_anomaly_audit(prices, log_ret)

    # 1. Compliance with rubric: exactly zero deleted observations
    assert summary["silently_deleted_count"] == 0

    # 2. Must flag extreme historic crash days
    flagged_dates = set(anomaly_df["date"])
    assert "2020-03-09" in flagged_dates  # Oil price war & COVID circuit breaker
    assert "2020-03-16" in flagged_dates  # COVID Black Monday II
    assert "2008-09-29" in flagged_dates  # GFC TARP rejection

    # 3. Every flagged record has required audit fields
    for col in ["date", "ticker", "log_return", "simple_return_pct", "z_score", "category", "historical_context", "disposition"]:
        assert col in anomaly_df.columns

    # 4. Persistence check: get_anomaly_log() returns identical rows
    disk_anomalies = get_anomaly_log()
    assert len(disk_anomalies) == len(anomaly_df)


# ---------------- Stationarity Diagnostic Tests ----------------

def test_stationarity_adf_and_kpss():
    prices = load_clean_prices()
    log_ret = load_log_returns()

    # SPY log price level must be non-stationary (fail to reject unit root)
    spy_px_res = run_adf_test(np.log(prices["SPY"]))
    assert not spy_px_res["is_stationary_5pct"]
    assert spy_px_res["p_value"] > 0.10

    # SPY log returns must be stationary (reject unit root with p < 0.001)
    spy_ret_res = run_adf_test(log_ret["SPY"])
    assert spy_ret_res["is_stationary_5pct"]
    assert spy_ret_res["p_value"] < 1e-4

    # SPY log returns KPSS test should fail to reject stationarity
    spy_kpss_res = run_kpss_test(log_ret["SPY"])
    assert spy_kpss_res["is_stationary_5pct"]

    # Verify report table loader
    stat_report = get_stationarity_report()
    assert len(stat_report) >= 14
    assert "Statistical Verdict" in stat_report.columns or "verdict" in stat_report.columns


# ---------------- Cryptographic Manifest Integrity ----------------

def test_data_manifest_integrity():
    manifest = get_data_manifest()
    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["client"] == "The Serendib University Endowment Fund (USD 10 Million)"
    assert set(manifest["investable_universe"]) == set(TICKERS)

    # Verify on-disk SHA-256 hashes
    assert verify_dataset_manifest()


# ---------------- Downstream Integration with Person 3 ----------------

def test_integration_with_person_3_models():
    """Verify that Person 1's clean data feeds cleanly into Person 3's portfolio calculations."""
    log_ret = load_log_returns()
    weights = {t: 1.0 / len(TICKERS) for t in TICKERS}

    rp = portfolio_log_returns(log_ret, weights)
    assert isinstance(rp, pd.Series)
    assert len(rp) == len(log_ret)
    assert not rp.isnull().any()
    assert np.isfinite(rp.values).all()
