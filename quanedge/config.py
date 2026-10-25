"""
Constants shared by every workstream.  Change them only by team agreement:
the app, report and tear sheet must quote one consistent set of numbers.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

TICKERS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]   # the permitted universe, nothing else
PORTFOLIO_VALUE = 10_000_000          # USD mandate size
TRADING_DAYS = 252
CONF_LEVELS = (0.90, 0.95, 0.99)      # the Streamlit sidebar choices
