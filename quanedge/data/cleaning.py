"""
Data cleaning, calendar alignment, and return calculation module.

Mandatory data discipline (Competition Brief Section 9.2):
1. Adjusted close prices: Dividends and splits incorporated into total return.
2. Market calendar alignment: Aligns trading calendars across all permitted ETFs
   and documents exchange holidays, emergency weather closures, and mourning days.
3. Simple vs log returns: Calculates both simple and log returns, mathematically
   validates the exact identity r = ln(1 + R), and documents their distinct roles
   (simple for cross-sectional portfolio aggregation; log for time-series modeling).
4. Macro series alignment: Aligns FRED series to the trading calendar "as of" each
   trading day. Daily series are forward-filled on bond-market holidays (Columbus Day,
   Veterans Day) and every fill is logged. Monthly series are made available only after
   an approximate publication lag, so no future information leaks into earlier days.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from dateutil.easter import easter

import numpy as np
import pandas as pd

from ..config import TICKERS, TRADING_DAYS

logger = logging.getLogger(__name__)

# Known historical unscheduled US equity market closures
NON_STANDARD_MARKET_CLOSURES = {
    "2007-01-02": "National Day of Mourning for President Gerald R. Ford",
    "2012-10-29": "Hurricane Sandy: Emergency weather closure of NYSE and Nasdaq",
    "2012-10-30": "Hurricane Sandy: Day 2 weather closure (first consecutive 2-day storm closure since 1888)",
    "2018-12-05": "National Day of Mourning for President George H.W. Bush",
    "2025-01-09": "National Day of Mourning for President Jimmy Carter",
}


def validate_price_data(prices: pd.DataFrame, expected_tickers: Optional[List[str]] = None) -> None:
    """
    Validate that price data conforms to production contracts.

    Checks:
    - Index is a strictly increasing DatetimeIndex without duplicates.
    - Expected tickers are present as columns.
    - All prices are strictly positive finite numbers.
    """
    expected_tickers = expected_tickers or TICKERS

    if not isinstance(prices.index, pd.DatetimeIndex):
        raise TypeError("Price DataFrame index must be a DatetimeIndex.")

    if not prices.index.is_monotonic_increasing:
        raise ValueError("Price DatetimeIndex must be strictly increasing.")

    if prices.index.duplicated().any():
        dup_count = prices.index.duplicated().sum()
        raise ValueError(f"Price DatetimeIndex contains {dup_count} duplicate dates.")

    missing_cols = [t for t in expected_tickers if t not in prices.columns]
    if missing_cols:
        raise ValueError(f"Price DataFrame missing expected tickers: {missing_cols}")

    for t in expected_tickers:
        series = prices[t]
        if series.isnull().any():
            nan_count = series.isnull().sum()
            raise ValueError(f"Ticker {t} contains {nan_count} NaN values.")
        if np.isinf(series).any():
            raise ValueError(f"Ticker {t} contains infinite values.")
        if (series <= 0).any():
            non_pos = (series <= 0).sum()
            raise ValueError(f"Ticker {t} contains {non_pos} non-positive prices.")


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> pd.Timestamp:
    """n-th (1-based) given weekday (Mon=0) of a month; n=-1 gives the last one."""
    if n > 0:
        first = pd.Timestamp(year=year, month=month, day=1)
        offset = (weekday - first.dayofweek) % 7
        return first + pd.Timedelta(days=offset + 7 * (n - 1))
    last = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
    return last - pd.Timedelta(days=(last.dayofweek - weekday) % 7)


def nyse_standard_holidays(start: pd.Timestamp, end: pd.Timestamp) -> Dict[pd.Timestamp, str]:
    """
    Scheduled NYSE full-day holidays between start and end (inclusive).

    Weekend rule: a holiday on Saturday closes the market the Friday before and one on
    Sunday closes it the Monday after, except New Year's Day on a Saturday, where the
    NYSE stays open on the preceding Friday. Juneteenth is observed from 2022.
    """
    holidays: Dict[pd.Timestamp, str] = {}

    def add(day: pd.Timestamp, name: str, saturday_to_friday: bool = True) -> None:
        if day.dayofweek == 5:
            if not saturday_to_friday:
                return
            day = day - pd.Timedelta(days=1)
        elif day.dayofweek == 6:
            day = day + pd.Timedelta(days=1)
        holidays[day] = name

    for year in range(start.year, end.year + 1):
        add(pd.Timestamp(year=year, month=1, day=1), "New Year's Day", saturday_to_friday=False)
        holidays[_nth_weekday(year, 1, 0, 3)] = "Martin Luther King Jr. Day"
        holidays[_nth_weekday(year, 2, 0, 3)] = "Washington's Birthday"
        holidays[pd.Timestamp(easter(year)) - pd.Timedelta(days=2)] = "Good Friday"
        holidays[_nth_weekday(year, 5, 0, -1)] = "Memorial Day"
        if year >= 2022:
            add(pd.Timestamp(year=year, month=6, day=19), "Juneteenth National Independence Day")
        add(pd.Timestamp(year=year, month=7, day=4), "Independence Day")
        holidays[_nth_weekday(year, 9, 0, 1)] = "Labor Day"
        holidays[_nth_weekday(year, 11, 3, 4)] = "Thanksgiving Day"
        add(pd.Timestamp(year=year, month=12, day=25), "Christmas Day")

    return {d: n for d, n in sorted(holidays.items()) if start <= d <= end}


def audit_trading_calendar(prices: pd.DataFrame) -> Dict[str, object]:
    """
    Audit the trading calendar against the scheduled NYSE holiday calendar.

    Every weekday between the first and last date that is absent from the price index is
    classified as one of:
      - STANDARD_HOLIDAY      : a scheduled NYSE holiday
      - NON_STANDARD_CLOSURE  : listed in NON_STANDARD_MARKET_CLOSURES (mourning days, storms)
      - UNEXPLAINED           : neither; this means missing data or an undocumented closure
    Scheduled holidays or documented closures that DO appear in the index are reported too
    (`unexpected_trading_days`), because they would indicate bad dates in the price file.
    The older "extended gap" view (gaps longer than 4 calendar days) is kept for the report.
    """
    idx = prices.index
    gaps = (idx[1:] - idx[:-1]).days
    gap_series = pd.Series(gaps, index=idx[1:])

    extended_gaps = []
    for dt, gap_len in gap_series[gap_series > 4].items():
        prev_dt = idx[idx.get_loc(dt) - 1]
        closure_reasons = []
        cur = prev_dt + pd.Timedelta(days=1)
        while cur < dt:
            cur_str = cur.strftime("%Y-%m-%d")
            if cur_str in NON_STANDARD_MARKET_CLOSURES:
                closure_reasons.append(NON_STANDARD_MARKET_CLOSURES[cur_str])
            cur += pd.Timedelta(days=1)

        extended_gaps.append({
            "from_date": prev_dt.strftime("%Y-%m-%d"),
            "to_date": dt.strftime("%Y-%m-%d"),
            "gap_calendar_days": int(gap_len),
            "reasons": "; ".join(closure_reasons) if closure_reasons else "Holiday / Extended weekend",
        })

    standard = nyse_standard_holidays(idx.min(), idx.max())
    missing_weekdays = pd.bdate_range(idx.min(), idx.max()).difference(idx)

    records: List[Dict[str, str]] = []
    for day in missing_weekdays:
        day_str = day.strftime("%Y-%m-%d")
        if day in standard:
            cls, reason = "STANDARD_HOLIDAY", standard[day]
        elif day_str in NON_STANDARD_MARKET_CLOSURES:
            cls, reason = "NON_STANDARD_CLOSURE", NON_STANDARD_MARKET_CLOSURES[day_str]
        else:
            cls, reason = "UNEXPLAINED", "Weekday missing from price file with no scheduled holiday or documented closure"
        records.append({"date": day_str, "weekday": day.day_name(), "classification": cls, "reason": reason})

    unexpected = [
        {"date": d.strftime("%Y-%m-%d"), "reason": f"Present in price file but is {name}"}
        for d, name in standard.items() if d in idx
    ] + [
        {"date": d, "reason": f"Present in price file but documented as closed: {why}"}
        for d, why in NON_STANDARD_MARKET_CLOSURES.items()
        if pd.Timestamp(d) in idx
    ]

    return {
        "start_date": idx.min().strftime("%Y-%m-%d"),
        "end_date": idx.max().strftime("%Y-%m-%d"),
        "total_trading_days": len(idx),
        "extended_gaps": extended_gaps,
        "calendar_records": records,
        "unexplained_missing_days": [r["date"] for r in records if r["classification"] == "UNEXPLAINED"],
        "non_standard_closures": [r for r in records if r["classification"] == "NON_STANDARD_CLOSURE"],
        "unexpected_trading_days": unexpected,
    }


def calculate_returns(prices: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute daily simple returns and daily log returns from adjusted close prices.

    Formulas:
        Simple return:  R_{i,t} = P_{i,t} / P_{i,t-1} - 1
        Log return:     r_{i,t} = ln(P_{i,t} / P_{i,t-1})

    Verifies the mathematical identity:
        r_{i,t} = ln(1 + R_{i,t})
        R_{i,t} = exp(r_{i,t}) - 1

    Returns:
        (simple_returns, log_returns) as a tuple of DataFrames.
    """
    validate_price_data(prices)

    simple_ret = prices.pct_change().dropna()
    log_ret = np.log(prices).diff().dropna()

    max_discrepancy = np.max(np.abs(log_ret.values - np.log(1.0 + simple_ret.values)))
    if max_discrepancy > 1e-12:
        raise ValueError(f"Return identity mismatch: max discrepancy {max_discrepancy:.2e} exceeds tolerance 1e-12.")

    return simple_ret, log_ret


# Monthly FRED series carry the first day of their reference month as the observation date,
# but the value is only known later. An observation becomes usable on
# (observation date + lag). Lags are conservative approximations; ALFRED vintages would
# give exact release dates.
TBILL_DAYS_TO_MATURITY = 91   # 13-week bill


def discount_to_bond_equivalent_yield(discount_pct, days: int = TBILL_DAYS_TO_MATURITY):
    """
    Convert a T-bill discount rate d (percent, 360-day year) to the bond-equivalent yield
    (percent, 365-day year):  y = 365 * d / (360 - days * d).

    FRED's DTB3 is quoted on a discount basis, which understates the return an investor earns
    (about 0.1-0.2 percentage points at 4-5% rates), so Sharpe-type excess returns must use the
    yield, not the discount rate.
    """
    d = np.asarray(discount_pct, dtype=float) / 100.0
    result = 100.0 * 365.0 * d / (360.0 - days * d)
    return pd.Series(result, index=discount_pct.index) if isinstance(discount_pct, pd.Series) else result


MONTHLY_RELEASE_LAGS: Dict[str, pd.DateOffset] = {
    "CPIAUCSL": pd.DateOffset(months=1, days=20),   # BLS releases month M around the 10th-20th of M+1
    "FEDFUNDS": pd.DateOffset(months=1),            # monthly average, published at the start of M+1
}


def align_macro_series(
    trading_index: pd.DatetimeIndex,
    fred_raw: pd.DataFrame,
    release_lags: Optional[Dict[str, pd.DateOffset]] = None,
) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    """
    Align FRED series to the equity trading calendar "as of" each trading day.

    Every series is forward-filled from its own full history (not just the sample window),
    so nothing is back-filled from the future and no observation dated on a weekend or
    holiday is lost.

    - Daily series (DTB3, DGS10, VIXCLS): on trading days with no published value
      (bond-market holidays such as Columbus Day and Veterans Day) the last published
      value is carried forward. Each such fill is returned in the log together with the
      date of the value that was used.
    - Monthly series (CPIAUCSL, FEDFUNDS): the observation becomes available only after
      `release_lags[series]`; until then the previous month's value is used. These routine
      monthly carries are NOT logged day by day; the policy is documented instead.

    Raises ValueError if any series has no value available on the first trading day.

    Calculates derived metrics (DTB3 is a discount rate, so the risk-free rate is built from its
    bond-equivalent yield, `DTB3_bey`, in percent):
    - DTB3_bey:           365 * d / (360 - 91 * d), with d = DTB3 / 100
    - rf_daily_effective: (1 + DTB3_bey / 100)**(1 / 252) - 1
    - rf_daily_simple:    (DTB3_bey / 100) / 252
    - rf_daily_log:       ln(1 + rf_daily_effective)
    - term_spread_10y_3m: DGS10 - DTB3_bey (percentage points; both are yields)
    """
    release_lags = MONTHLY_RELEASE_LAGS if release_lags is None else release_lags

    columns = {}
    forward_filled_log: List[Dict[str, str]] = []
    for col in fred_raw.columns:
        series = fred_raw[col].dropna().sort_index()
        lag = release_lags.get(col)
        if lag is not None:
            series = series.copy()
            series.index = series.index + lag

        union = series.index.union(trading_index)
        columns[col] = series.reindex(union).ffill().reindex(trading_index)

        if lag is None:
            available = series.index
            for dt in trading_index.difference(available):
                pos = available.searchsorted(dt, side="right") - 1
                if pos < 0:
                    continue
                forward_filled_log.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "series": col,
                    "day_of_week": dt.day_name(),
                    "filled_from_date": available[pos].strftime("%Y-%m-%d"),
                    "action": "Forward-filled from last published observation (bond market holiday)",
                })

    aligned_filled = pd.DataFrame(columns, index=trading_index)
    empty = [c for c in aligned_filled.columns if aligned_filled[c].isnull().any()]
    if empty:
        raise ValueError(f"No FRED value available on or before the first trading day for: {empty}")

    if "DTB3" in aligned_filled.columns:
        aligned_filled["DTB3_bey"] = discount_to_bond_equivalent_yield(aligned_filled["DTB3"])
        bey_decimal = aligned_filled["DTB3_bey"] / 100.0

        aligned_filled["rf_daily_effective"] = (1.0 + bey_decimal) ** (1.0 / TRADING_DAYS) - 1.0
        aligned_filled["rf_daily_simple"] = bey_decimal / TRADING_DAYS
        aligned_filled["rf_daily_log"] = np.log(1.0 + aligned_filled["rf_daily_effective"])

    if "DGS10" in aligned_filled.columns and "DTB3_bey" in aligned_filled.columns:
        aligned_filled["term_spread_10y_3m"] = aligned_filled["DGS10"] - aligned_filled["DTB3_bey"]

    return aligned_filled, forward_filled_log
