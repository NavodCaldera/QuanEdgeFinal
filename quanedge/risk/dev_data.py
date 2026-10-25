"""
TEMPORARY data access for the risk workstream, used until Person 1's cleaned
dataset lands.  It follows the brief's discipline: adjusted closes, only the
days on which all seven ETFs trade, log returns, no manual edits.  The raw
download is cached so every run (and every teammate) sees identical prices.
"""
import numpy as np
import pandas as pd
from ..config import DATA_DIR, TICKERS
from . import settings as S

PRICE_FILE = DATA_DIR / "cache" / "prices_dev.csv"


def download_prices() -> pd.DataFrame:
    import yfinance as yf
    raw = yf.download(TICKERS, start=S.DEV_START, end=S.DEV_END,
                      auto_adjust=True, progress=False)
    px = raw["Close"][TICKERS]
    if px.dropna().shape[0] < 5000:
        raise RuntimeError("Download failed or too short; check internet / Yahoo.")
    return px


def load_prices(refresh: bool = False) -> pd.DataFrame:
    """Cached adjusted closes; downloads only if the cache is missing (or refresh=True)."""
    if PRICE_FILE.exists() and not refresh:
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
