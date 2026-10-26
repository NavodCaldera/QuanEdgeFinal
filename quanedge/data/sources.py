"""
Approved data sources module for QuanEdge.

Implements robust downloading and caching pipelines for:
1. Yahoo Finance (via yfinance): 7 permitted ETFs (SPY, EFA, EEM, AGG, GLD, XLE, XLK)
   using auto-adjusted prices to prevent dividend/split distortions.
2. Federal Reserve Economic Data (FRED): Risk-free proxy (3-month T-bill DTB3),
   10-Year Treasury (DGS10), CPI (CPIAUCSL), Fed Funds (FEDFUNDS), and VIX (VIXCLS).
3. World Bank Open Data: Macroeconomic context (annual GDP growth, CPI inflation).

All downloads are cached locally; the SHA-256 manifest (manifest.py) pins the exact files.
If network is unavailable, cached files are used automatically.

Reproducibility caveat for prices: Yahoo's auto-adjusted history is re-scaled every time an ETF
pays a dividend, so a fresh download made later will NOT match the committed snapshot exactly.
The committed snapshot (data/cache/prices_dev.csv) is the canonical dataset for the report.
Use --refresh only deliberately, and treat every figure as changed afterwards.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..config import CACHE_DATA_DIR, DATA_DIR, END_DATE, START_DATE, TICKERS

logger = logging.getLogger(__name__)

RAW_DATA_DIR = DATA_DIR / "raw"
PRICE_SNAPSHOT_NAME = "prices_dev.csv"     # name kept: docs/person-3 asks for this file to be preserved

# Approved FRED series
FRED_SERIES = {
    "DTB3": "3-Month Treasury Bill Secondary Market Rate (Discount Basis, %)",
    "DGS10": "10-Year Treasury Constant Maturity Rate (% annualized)",
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers: All Items (Index 1982-1984=100)",
    "FEDFUNDS": "Effective Federal Funds Rate (% annualized)",
    "VIXCLS": "CBOE Volatility Index (VIX Closing Value)",
}

# Approved World Bank indicators
WORLDBANK_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
}


def _urlopen(request: urllib.request.Request, timeout: int = 15):
    """
    urlopen with the certifi CA bundle. python.org builds of Python on macOS ship without a
    usable system CA store, which makes every FRED / World Bank download fail with
    CERTIFICATE_VERIFY_FAILED unless "Install Certificates.command" was run.
    """
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:                      # fall back to the platform default
        context = ssl.create_default_context()
    return urllib.request.urlopen(request, timeout=timeout, context=context)


def audit_price_snapshot(cache_path: Optional[Path] = None, tickers: Optional[List[str]] = None) -> Dict[str, object]:
    """
    Describe the raw price snapshot BEFORE any row is dropped: how many dates it holds, how many
    contain a missing price for at least one ticker, and its SHA-256. The ingestion step keeps
    only dates on which every ETF has a price, so this makes the number of dropped dates visible.
    """
    tickers = tickers or TICKERS
    cache_path = cache_path or (CACHE_DATA_DIR / PRICE_SNAPSHOT_NAME)
    raw = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    incomplete = raw[tickers].isnull().any(axis=1)
    return {
        "file": cache_path.name,
        "sha256": hashlib.sha256(cache_path.read_bytes()).hexdigest(),
        "rows_in_file": int(len(raw)),
        "rows_with_missing_price": int(incomplete.sum()),
        "rows_dropped_by_common_calendar_filter": int(incomplete.sum()),
        "first_date": raw.index.min().strftime("%Y-%m-%d"),
        "last_date": raw.index.max().strftime("%Y-%m-%d"),
        "columns": list(raw.columns),
    }


def _snapshot_meta_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(".meta.json")


def read_snapshot_meta(cache_path: Optional[Path] = None) -> Optional[Dict[str, object]]:
    """Metadata written when the snapshot was downloaded by this pipeline (None if it pre-dates it)."""
    cache_path = cache_path or (CACHE_DATA_DIR / PRICE_SNAPSHOT_NAME)
    meta_path = _snapshot_meta_path(cache_path)
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return None


def download_etf_prices(
    tickers: Optional[List[str]] = None,
    start: str = START_DATE,
    end: str = END_DATE,
    cache_path: Optional[Path] = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Download or load cached adjusted close prices for the permitted ETF universe.

    Uses yfinance with auto_adjust=True so dividend distributions and stock
    splits are factored into total return prices, matching CFA Institute
    and competition brief standards.

    Only dates on which every ETF has a price are kept (common calendar). The number of dates
    removed by that filter is logged as a warning and recorded in the provenance file; a fresh
    download also writes a `.meta.json` sidecar with the retrieval time and library version.
    """
    tickers = tickers or TICKERS
    cache_path = cache_path or (CACHE_DATA_DIR / PRICE_SNAPSHOT_NAME)

    def keep_common(px: pd.DataFrame, origin: str) -> pd.DataFrame:
        px = px[tickers]
        common = px.dropna()
        dropped = len(px) - len(common)
        if dropped:
            logger.warning("%s: %d of %d dates dropped because at least one ETF had no price.", origin, dropped, len(px))
        return common

    if cache_path.exists() and not refresh:
        px = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        if all(t in px.columns for t in tickers):
            return keep_common(px, "cached snapshot")

    logger.info("Downloading ETF prices via yfinance for %s from %s to %s", tickers, start, end)
    try:
        import yfinance as yf
        raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            px = raw["Close"][tickers]
        else:
            px = raw[tickers]

        if px.dropna().shape[0] < 500:
            raise RuntimeError(f"Downloaded ETF price dataset has only {len(px)} rows; download incomplete.")

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        px.to_csv(cache_path)
        _snapshot_meta_path(cache_path).write_text(json.dumps({
            "source": "Yahoo Finance via yfinance",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "yfinance_version": getattr(yf, "__version__", "unknown"),
            "tickers": tickers,
            "requested_start": start,
            "requested_end_exclusive": end,
            "auto_adjust": True,
            "rows_downloaded": int(len(px)),
        }, indent=2), encoding="utf-8")
        return keep_common(px, "fresh download")
    except Exception as exc:
        if cache_path.exists():
            logger.warning("Download failed (%s); falling back to existing cache at %s", exc, cache_path)
            px = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return keep_common(px, "cached snapshot (fallback)")
        raise RuntimeError(f"Failed to download or load ETF prices: {exc}") from exc


def download_fred_series(
    series_id: str,
    cache_dir: Optional[Path] = None,
    refresh: bool = False,
) -> pd.Series:
    """
    Download a single macroeconomic or risk-free series from FRED.

    Directly queries the St. Louis Fed CSV export without requiring a proprietary API key.
    Replaces missing character markers ('.') with NaN and parses dates.
    """
    cache_dir = cache_dir or RAW_DATA_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"fred_{series_id}.csv"

    if cache_file.exists() and not refresh:
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        s = pd.to_numeric(df[series_id], errors="coerce").dropna()
        return s

    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (QuanEdge Research Data Pipeline)"})

    try:
        with _urlopen(req) as resp:
            content = resp.read()
        df = pd.read_csv(io.BytesIO(content))
        date_col = "observation_date" if "observation_date" in df.columns else df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col])
        df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
        df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()

        df.to_csv(cache_file)
        return df[series_id].dropna()
    except Exception as exc:
        if cache_file.exists():
            logger.warning("FRED download failed for %s (%s); using existing cache.", series_id, exc)
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return pd.to_numeric(df[series_id], errors="coerce").dropna()
        raise RuntimeError(f"Could not download or load FRED series {series_id}: {exc}") from exc


def download_all_fred_series(refresh: bool = False) -> pd.DataFrame:
    """
    Download and combine all approved FRED macroeconomic and interest rate series.

    Every series is required downstream, so a failure raises instead of silently returning a
    partial table.
    """
    series_dict = {sid: download_fred_series(sid, refresh=refresh) for sid in FRED_SERIES}
    return pd.DataFrame(series_dict)


def download_worldbank_indicators(
    country: str = "USA",
    indicators: Optional[Dict[str, str]] = None,
    cache_dir: Optional[Path] = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Download macroeconomic indicators from World Bank Open Data API for country context.
    """
    indicators = indicators or WORLDBANK_INDICATORS
    cache_dir = cache_dir or RAW_DATA_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"worldbank_{country.lower()}.csv"

    if cache_file.exists() and not refresh:
        return pd.read_csv(cache_file, index_col=0, parse_dates=True)

    records = []
    for ind_code, ind_name in indicators.items():
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{ind_code}?format=json&per_page=100"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (QuanEdge Research)"})
        try:
            with _urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if len(data) > 1 and isinstance(data[1], list):
                for row in data[1]:
                    if row.get("value") is not None:
                        records.append({
                            "year": pd.to_datetime(row["date"], format="%Y"),
                            "indicator_code": ind_code,
                            "indicator_name": ind_name,
                            "value": float(row["value"]),
                        })
        except Exception as e:
            logger.warning("World Bank download failed for %s: %s", ind_code, e)

    if not records:
        if cache_file.exists():
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        raise RuntimeError("World Bank download returned no data and no cached copy exists.")

    raw_df = pd.DataFrame(records)
    pivot_df = raw_df.pivot(index="year", columns="indicator_code", values="value").sort_index()
    pivot_df.to_csv(cache_file)
    return pivot_df
