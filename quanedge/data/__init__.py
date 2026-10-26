"""
QuanEdge Data Engineering Package (Person 1 Workstream).

Provides the common clean, reproducible dataset, macroeconomic series,
provenance tracking, and statistical validation for Team Ghosted's endowment analysis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
import pandas as pd

from ..config import CLEAN_DATA_DIR, TICKERS
from .sources import download_etf_prices


def load_clean_prices(refresh: bool = False) -> pd.DataFrame:
    """
    Load clean, adjusted close prices for the 7 permitted ETFs.

    If clean file does not exist, triggers pipeline download and returns prices.
    Index is DatetimeIndex, columns are [SPY, EFA, EEM, AGG, GLD, XLE, XLK].
    """
    clean_file = CLEAN_DATA_DIR / "prices_clean.csv"
    if clean_file.exists() and not refresh:
        df = pd.read_csv(clean_file, index_col=0, parse_dates=True)
        return df[TICKERS]

    from .run import run_pipeline
    run_pipeline(refresh=refresh)
    return pd.read_csv(clean_file, index_col=0, parse_dates=True)[TICKERS]


def load_clean_returns(kind: str = "log", refresh: bool = False) -> pd.DataFrame:
    """
    Load clean daily returns for the permitted universe.

    Parameters:
        kind: 'log' for daily log returns (ln(P_t / P_{t-1})),
              'simple' for daily simple returns (P_t / P_{t-1} - 1).
    """
    kind = kind.lower().strip()
    if kind not in ("log", "simple"):
        raise ValueError(f"Invalid return kind '{kind}'; must be 'log' or 'simple'.")

    clean_file = CLEAN_DATA_DIR / f"{kind}_returns.csv"
    if clean_file.exists() and not refresh:
        return pd.read_csv(clean_file, index_col=0, parse_dates=True)[TICKERS]

    prices = load_clean_prices(refresh=refresh)
    if kind == "log":
        return np.log(prices).diff().dropna()
    else:
        return prices.pct_change().dropna()


def load_log_returns(refresh: bool = False) -> pd.DataFrame:
    """Convenience alias for load_clean_returns(kind='log')."""
    return load_clean_returns(kind="log", refresh=refresh)


def load_simple_returns(refresh: bool = False) -> pd.DataFrame:
    """Convenience alias for load_clean_returns(kind='simple')."""
    return load_clean_returns(kind="simple", refresh=refresh)


def load_macro_data(refresh: bool = False) -> pd.DataFrame:
    """
    Load clean aligned macroeconomic series from FRED (DTB3, DGS10, CPI, FEDFUNDS, VIX, etc.).
    """
    macro_file = CLEAN_DATA_DIR / "macro_clean.csv"
    if macro_file.exists() and not refresh:
        return pd.read_csv(macro_file, index_col=0, parse_dates=True)

    load_clean_prices(refresh=refresh)
    return pd.read_csv(macro_file, index_col=0, parse_dates=True)


def load_risk_free_rate(frequency: str = "daily", kind: str = "effective", refresh: bool = False) -> pd.Series:
    """
    Load risk-free rate proxy (3-Month US Treasury Bill DTB3, converted from its discount basis
    to a bond-equivalent yield `DTB3_bey`).

    Parameters:
        frequency: 'daily' or 'annualized'
        kind: 'effective' (compounded daily) or 'simple' or 'log'
    """
    macro = load_macro_data(refresh=refresh)
    if frequency == "annualized":
        return macro["DTB3_bey"] / 100.0      # bond-equivalent yield, decimal (DTB3 itself is a discount rate)

    if kind == "effective":
        return macro["rf_daily_effective"]
    elif kind == "simple":
        return macro["rf_daily_simple"]
    elif kind == "log":
        return macro["rf_daily_log"]
    else:
        raise ValueError(f"Unknown kind '{kind}'; must be 'effective', 'simple', or 'log'.")


def load_worldbank_data(refresh: bool = False) -> pd.DataFrame:
    """
    Load annual macroeconomic context from World Bank open data.
    """
    wb_file = CLEAN_DATA_DIR / "worldbank_macro.csv"
    if wb_file.exists() and not refresh:
        return pd.read_csv(wb_file, index_col=0, parse_dates=True)

    load_clean_prices(refresh=refresh)
    return pd.read_csv(wb_file, index_col=0, parse_dates=True)


def get_data_manifest() -> Dict[str, object]:
    """Load the JSON provenance and cryptographic SHA-256 manifest."""
    manifest_file = CLEAN_DATA_DIR / "data_manifest.json"
    if not manifest_file.exists():
        from .run import run_pipeline
        run_pipeline()
    with open(manifest_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_anomaly_log() -> pd.DataFrame:
    """Load the complete flagged anomaly and historical crisis cross-reference audit table."""
    anomaly_file = CLEAN_DATA_DIR / "anomaly_log.csv"
    if not anomaly_file.exists():
        from .run import run_pipeline
        run_pipeline()
    return pd.read_csv(anomaly_file)


def get_stationarity_report() -> pd.DataFrame:
    """Load the ADF and KPSS stationarity test diagnostic results."""
    stat_file = CLEAN_DATA_DIR / "stationarity_tests.csv"
    if not stat_file.exists():
        from .run import run_pipeline
        run_pipeline()
    return pd.read_csv(stat_file)


__all__ = [
    "load_clean_prices",
    "load_clean_returns",
    "load_log_returns",
    "load_simple_returns",
    "load_macro_data",
    "load_risk_free_rate",
    "load_worldbank_data",
    "get_data_manifest",
    "get_anomaly_log",
    "get_stationarity_report",
]
