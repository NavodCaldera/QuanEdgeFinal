"""
Constants shared by every workstream. Change them only by owner approval:
the app, report and tear sheet must quote one consistent set of numbers.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
CLEAN_DATA_DIR = DATA_DIR / "clean"
CACHE_DATA_DIR = DATA_DIR / "cache"

TICKERS = ["SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK"]   # the permitted universe, nothing else
START_DATE = "2005-01-01"      # first full calendar year in which all 7 ETFs traded (GLD listed Nov 2004)
END_DATE = "2026-10-01"        # fixed end date -> identical, reproducible data across all workstreams
PORTFOLIO_VALUE = 10_000_000   # USD mandate size
TRADING_DAYS = 252
CONF_LEVELS = (0.90, 0.95, 0.99)      # the Streamlit sidebar choices


def frozen_policy(tag="prereg-v1"):
    """Investment policy exactly as frozen at a Git tag. Mandate v1 comparisons
    (dynamic, hedging, overlay) use prereg-v1 even after config/final.yaml moves on."""
    import subprocess
    import yaml
    text = subprocess.check_output(["git", "show", f"{tag}:config/final.yaml"], cwd=ROOT, text=True)
    return yaml.safe_load(text)
