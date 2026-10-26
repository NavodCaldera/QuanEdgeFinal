"""
Data access for the risk workstream. Uses Person 1's cleaned dataset
(data/clean/prices_clean.csv) when present, with fallback to dev cache.
"""
import numpy as np
import pandas as pd
from ..config import DATA_DIR, TICKERS
from . import settings as S

PRICE_FILE = DATA_DIR / "cache" / "prices_dev.csv"
CLEAN_PRICE_FILE = DATA_DIR / "clean" / "prices_clean.csv"


def download_prices() -> pd.DataFrame:
    import yfinance as yf
    raw = yf.download(TICKERS, start=S.DEV_START, end=S.DEV_END,
                      auto_adjust=True, progress=False)
    px = raw["Close"][TICKERS]
    if px.dropna().shape[0] < 5000:
        raise RuntimeError("Download failed or too short; check internet / Yahoo.")
    return px


def load_prices(refresh: bool = False) -> pd.DataFrame:
    """
    Load adjusted closes. Uses Person 1's approved clean dataset (data/clean/prices_clean.csv)
    when present, with seamless fallback to development cache.
    """
    if CLEAN_PRICE_FILE.exists() and not refresh:
        px = pd.read_csv(CLEAN_PRICE_FILE, index_col=0, parse_dates=True)
    elif PRICE_FILE.exists() and not refresh:
        px = pd.read_csv(PRICE_FILE, index_col=0, parse_dates=True)
    else:
        px = download_prices()
        PRICE_FILE.parent.mkdir(parents=True, exist_ok=True)
        px.to_csv(PRICE_FILE)
    px = px[TICKERS].dropna()          # keep only days on which every ETF traded
    assert (px > 0).all().all()
    return px


def load_log_returns(refresh: bool = False) -> pd.DataFrame:
    return np.log(load_prices(refresh)).diff().dropna()
