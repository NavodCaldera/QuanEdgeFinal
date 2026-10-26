"""
Tests for the Person 1 audit fixes: as-of macro alignment, the forward-fill log, the
holiday-calendar audit, honest anomaly dispositions, persisted quality checks, and report
tables that must match the data.
"""
import re

import numpy as np
import pandas as pd
import pytest

from quanedge.config import CLEAN_DATA_DIR, DATA_DIR, ROOT
from quanedge.data import load_clean_prices, load_log_returns, load_macro_data
from quanedge.data.anomalies import (
    HISTORICAL_CRISIS_EVENTS,
    NO_LABEL,
    build_data_quality_log,
    detect_sharp_reversals,
    detect_volatility_regime_shifts,
    render_top_tail_events_markdown,
    scan_stale_prices,
)
from quanedge.data.cleaning import (
    MONTHLY_RELEASE_LAGS,
    NON_STANDARD_MARKET_CLOSURES,
    align_macro_series,
    audit_trading_calendar,
    nyse_standard_holidays,
)

RAW = DATA_DIR / "raw"


def _raw(series_id: str) -> pd.Series:
    df = pd.read_csv(RAW / f"fred_{series_id}.csv", index_col=0, parse_dates=True)
    return pd.to_numeric(df[series_id], errors="coerce").dropna()


def _expected_as_of(series_id: str, days: pd.DatetimeIndex) -> pd.Series:
    """Independent as-of reference: latest observation usable on each day."""
    s = _raw(series_id)
    lag = MONTHLY_RELEASE_LAGS.get(series_id)
    if lag is not None:
        s.index = s.index + lag
    ref = pd.merge_asof(
        pd.DataFrame({"day": days}),
        pd.DataFrame({"day": s.index, "value": s.values}),
        on="day",
    )
    return pd.Series(ref["value"].values, index=days)


# ---------------- Macro alignment (item 1) ----------------

@pytest.mark.parametrize("series_id", ["CPIAUCSL", "FEDFUNDS", "DTB3", "DGS10", "VIXCLS"])
def test_macro_matches_independent_as_of_alignment(series_id):
    macro = load_macro_data()
    expected = _expected_as_of(series_id, macro.index)
    assert expected.notnull().all()
    assert np.allclose(macro[series_id].values, expected.values)


@pytest.mark.parametrize("series_id", ["CPIAUCSL", "FEDFUNDS"])
def test_no_monthly_observation_is_dropped(series_id):
    macro = load_macro_data()
    s = _raw(series_id)
    s.index = s.index + MONTHLY_RELEASE_LAGS[series_id]
    usable = s[(s.index > macro.index[0]) & (s.index <= macro.index[-1])]
    used = set(np.round(macro[series_id].values, 6))
    # every observation that became available inside the sample was used on at least one day
    assert len(usable) > 200
    assert all(round(v, 6) in used for v in usable.values)


def test_monthly_values_are_not_used_before_publication():
    macro = load_macro_data()
    raw = _raw("CPIAUCSL")
    release = raw.index + MONTHLY_RELEASE_LAGS["CPIAUCSL"]
    for obs_date, rel_date, value in zip(raw.index, release, raw.values):
        if not (macro.index[0] < rel_date <= macro.index[-1]):
            continue
        before = macro.loc[macro.index < rel_date, "CPIAUCSL"]
        # on the last trading day before release the series must not yet equal this month's value
        # unless the previous month happened to print the same number
        previous = raw[raw.index < obs_date]
        if len(previous) and previous.iloc[-1] != value:
            assert before.iloc[-1] != value


def test_align_macro_series_synthetic_cases():
    days = pd.bdate_range("2020-03-02", "2020-06-30")
    monthly = pd.Series(
        [98.0, 99.0, 100.0, 101.0],   # Jan and Feb are history; Mar is dated a Sunday
        index=pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01"]),
    )
    fred = pd.DataFrame({"CPIAUCSL": monthly, "DTB3": pd.Series(1.0, index=pd.bdate_range("2020-01-01", "2020-06-30"))})
    aligned, log = align_macro_series(
        days, fred.sort_index(), release_lags={"CPIAUCSL": pd.DateOffset(months=1, days=20)}
    )

    # history seeds the start: Jan (released 2020-02-21) is in use on the first day, Feb is not yet
    assert aligned.loc["2020-03-02", "CPIAUCSL"] == 98.0
    assert aligned.loc["2020-03-20", "CPIAUCSL"] == 98.0
    assert aligned.loc["2020-03-23", "CPIAUCSL"] == 99.0       # Feb released Saturday 2020-03-21
    # the Sunday-dated March value is not dropped; it is released 2020-04-21
    assert aligned.loc["2020-04-20", "CPIAUCSL"] == 99.0
    assert aligned.loc["2020-04-22", "CPIAUCSL"] == 100.0
    assert aligned.loc["2020-05-20", "CPIAUCSL"] == 100.0
    assert aligned.loc["2020-05-21", "CPIAUCSL"] == 101.0
    # monthly carries are not logged; DTB3 has no gaps here
    assert log == []


def test_align_macro_series_refuses_to_backfill():
    days = pd.bdate_range("2020-03-02", "2020-03-10")
    fred = pd.DataFrame({"DTB3": pd.Series([1.0], index=pd.to_datetime(["2020-03-05"]))})
    with pytest.raises(ValueError):
        align_macro_series(days, fred)


# ---------------- Forward-fill log (item 2) ----------------

def test_ffill_log_is_persisted_and_only_covers_daily_series():
    log = pd.read_csv(CLEAN_DATA_DIR / "macro_ffill_log.csv", parse_dates=["date", "filled_from_date"])
    prices = load_clean_prices()
    assert set(log["series"]) <= {"DTB3", "DGS10", "VIXCLS"}
    assert (log["filled_from_date"] < log["date"]).all()

    expected = sum(len(prices.index.difference(_raw(s).index)) for s in ("DTB3", "DGS10", "VIXCLS"))
    assert len(log) == expected
    # the documented cause: bond-market holidays, mainly Columbus Day and Veterans Day
    assert 60 <= len(log) <= 120


def test_ffill_log_lists_columbus_and_veterans_day():
    log = pd.read_csv(CLEAN_DATA_DIR / "macro_ffill_log.csv", parse_dates=["date"])
    assert ((log["date"].dt.month == 11) & (log["date"].dt.day.isin([11, 12, 10]))).any()
    assert (log["date"].dt.month == 10).any()


# ---------------- Calendar audit (item 5) ----------------

def test_standard_holiday_rules():
    h = nyse_standard_holidays(pd.Timestamp("2005-01-01"), pd.Timestamp("2026-12-31"))
    assert pd.Timestamp("2022-06-20") in h        # Juneteenth observed on Monday (Sunday holiday)
    assert pd.Timestamp("2022-12-26") in h        # Christmas on Sunday observed Monday
    assert pd.Timestamp("2015-07-03") in h        # July 4 on Saturday observed Friday
    assert pd.Timestamp("2009-04-10") in h        # Good Friday
    assert pd.Timestamp("2021-12-31") not in h    # NYSE stays open when Jan 1 is a Saturday
    assert pd.Timestamp("2021-06-18") not in h    # Juneteenth not observed before 2022
    assert pd.Timestamp("2011-11-24") in h        # Thanksgiving


def test_real_calendar_has_no_unexplained_days():
    audit = audit_trading_calendar(load_clean_prices())
    assert audit["unexplained_missing_days"] == []
    assert audit["unexpected_trading_days"] == []
    closed = {r["date"] for r in audit["non_standard_closures"]}
    assert closed == set(NON_STANDARD_MARKET_CLOSURES)
    assert {"2018-12-05", "2025-01-09"} <= closed


def test_calendar_audit_file_matches_audit():
    cal = pd.read_csv(CLEAN_DATA_DIR / "calendar_audit.csv")
    assert (cal["classification"] != "UNEXPLAINED").all()
    assert len(cal) == 203
    assert (cal["classification"] == "NON_STANDARD_CLOSURE").sum() == 5


def test_calendar_audit_flags_synthetic_problems():
    idx = pd.bdate_range("2021-03-01", "2021-03-31").drop(pd.Timestamp("2021-03-17"))   # random Wednesday
    prices = pd.DataFrame({"SPY": 1.0}, index=idx)
    audit = audit_trading_calendar(prices)
    assert audit["unexplained_missing_days"] == ["2021-03-17"]

    with_holiday = pd.DataFrame({"SPY": 1.0}, index=pd.bdate_range("2021-03-29", "2021-04-05"))  # includes Good Friday
    audit = audit_trading_calendar(with_holiday)
    assert any("Good Friday" in u["reason"] for u in audit["unexpected_trading_days"])


# ---------------- Anomaly log honesty (items 3 and 4) ----------------

@pytest.fixture(scope="module")
def anomaly_log():
    return pd.read_csv(CLEAN_DATA_DIR / "anomaly_log.csv")


def test_anomaly_returns_match_clean_returns(anomaly_log):
    log_ret = load_log_returns()
    for _, r in anomaly_log.sample(60, random_state=0).iterrows():
        actual = log_ret.loc[r["date"], r["ticker"]]
        assert abs(actual - r["log_return"]) < 1e-6
        assert abs((np.exp(actual) - 1) * 100 - r["simple_return_pct"]) < 1e-3


def test_event_labels_contain_no_hand_typed_return_figures():
    for date, label in HISTORICAL_CRISIS_EVENTS.items():
        assert not re.search(r"\d\s*%", label), f"{date}: label embeds a return figure: {label}"


def test_dispositions_claim_only_what_was_checked(anomaly_log):
    text = " ".join(anomaly_log["disposition"]).lower()
    for banned in ("verified against", "exchange print", "exchange volume", "news archive"):
        assert banned not in text
    assert (anomaly_log["disposition"].str.startswith("RETAIN")).all()
    assert anomaly_log["historical_context"].isin(set(HISTORICAL_CRISIS_EVENTS.values()) | {NO_LABEL}).all()
    labelled = anomaly_log["historical_context"] != NO_LABEL
    assert anomaly_log.loc[labelled, "label_source"].str.contains("not verified per ticker").all()
    assert (anomaly_log.loc[~labelled, "label_source"] == "none").all()


def test_corroboration_count_is_correct(anomaly_log):
    log_ret = load_log_returns()
    z = (log_ret - log_ret.mean()) / log_ret.std()
    for _, r in anomaly_log.sample(40, random_state=1).iterrows():
        others = [t for t in log_ret.columns if t != r["ticker"]]
        sign = np.sign(log_ret.loc[r["date"], r["ticker"]])
        expected = int(((z.loc[r["date"], others] * sign) >= 2.0).sum())
        assert r["corroborating_assets"] == expected
        if expected == 0:
            assert "no cross-asset corroboration" in r["disposition"]


def test_known_unlabelled_events_are_now_labelled(anomaly_log):
    rows = anomaly_log.set_index(["date", "ticker"])
    assert "Brexit" in rows.loc[("2016-06-24", "EFA"), "historical_context"]
    assert "Gold price crash" in rows.loc[("2013-04-15", "GLD"), "historical_context"]


# ---------------- Persisted quality checks (item 6) ----------------

def test_quality_log_persists_all_checks():
    prices, log_ret = load_clean_prices(), load_log_returns()
    findings = pd.read_csv(CLEAN_DATA_DIR / "data_quality_log.csv")
    checks = pd.read_csv(CLEAN_DATA_DIR / "data_quality_checks.csv").set_index("check")

    assert checks.loc["SHARP_TWO_DAY_REVERSAL", "findings"] == len(detect_sharp_reversals(log_ret, 0.06))
    assert checks.loc["STALE_PRICE_STREAK", "findings"] == len(scan_stale_prices(prices, 3))
    assert checks.loc["VOLATILITY_REGIME_SHIFT", "findings"] == log_ret.shape[1]
    assert (findings["check"].value_counts().to_dict().get("SHARP_TWO_DAY_REVERSAL", 0)
            == checks.loc["SHARP_TWO_DAY_REVERSAL", "findings"])
    assert findings["disposition"].notnull().all()


def test_stale_price_detection_on_synthetic_series():
    idx = pd.bdate_range("2021-01-04", periods=20)
    px = pd.DataFrame({"AAA": np.linspace(10, 12, 20)}, index=idx)
    px.iloc[8:12, 0] = px.iloc[7, 0]            # four flat days after day 7 -> 4 zero returns
    records = scan_stale_prices(px, min_consecutive_days=3)
    assert len(records) == 1 and records[0]["consecutive_days"] >= 3


def test_sharp_reversal_detection_on_synthetic_series():
    idx = pd.bdate_range("2021-01-04", periods=10)
    r = pd.DataFrame({"AAA": [0.0, 0.0, -0.08, 0.07, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0]}, index=idx)
    found = detect_sharp_reversals(r, threshold=0.06)
    assert len(found) == 1 and found[0]["date_day1"] == "2021-01-06"


def test_regime_shift_detection_on_synthetic_series():
    rng = np.random.default_rng(0)
    calm, wild = rng.normal(0, 0.005, 1500), rng.normal(0, 0.02, 1500)
    r = pd.DataFrame({"AAA": np.concatenate([calm, wild])}, index=pd.bdate_range("2010-01-04", periods=3000))
    rec = detect_volatility_regime_shifts(r)[0]
    assert rec["value"] > 1.358
    assert "2015" in rec["metric"] or "2016" in rec["metric"]      # break near the middle of the sample

    flat = pd.DataFrame({"AAA": rng.normal(0, 0.01, 3000)}, index=r.index)
    assert detect_volatility_regime_shifts(flat)[0]["value"] < 3.0   # no pronounced break


def test_build_data_quality_log_shapes():
    prices, log_ret = load_clean_prices(), load_log_returns()
    findings, checks = build_data_quality_log(prices, log_ret)
    assert set(checks["check"]) == {"STALE_PRICE_STREAK", "SHARP_TWO_DAY_REVERSAL", "VOLATILITY_REGIME_SHIFT"}
    assert len(findings) == checks["findings"].sum()


# ---------------- Report tables must match the data (item 3) ----------------

def _block(path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<!-- BEGIN top-tail-events -->\n(.*?)\n<!-- END top-tail-events -->", text, re.S)
    assert m, f"{path} has no generated tail-event block"
    return m.group(1).strip()


@pytest.mark.parametrize("doc", ["docs/person-1/01-data-pipeline.md", "data/data_dictionary.md"])
def test_documented_tail_table_matches_data(doc):
    anomaly = pd.read_csv(CLEAN_DATA_DIR / "anomaly_log.csv")
    assert _block(ROOT / doc) == render_top_tail_events_markdown(anomaly).strip()


def test_results_file_matches_data():
    anomaly = pd.read_csv(CLEAN_DATA_DIR / "anomaly_log.csv")
    written = (ROOT / "results" / "data" / "top_tail_events.md").read_text(encoding="utf-8").strip()
    assert written == render_top_tail_events_markdown(anomaly).strip()
