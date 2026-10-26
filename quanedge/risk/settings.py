"""
Every modelling choice of the risk workstream (VaR, ES, EVT) lives here, so it
can be changed in one place and defended in the report.
"""
import numpy as np
from ..config import END_DATE, START_DATE, TICKERS

# ---------------- Development inputs (replace when Persons 1 and 2 deliver) ----------------
DEV_START = START_DATE        # single source of truth: quanedge.config (first full year with all seven ETFs)
DEV_END = END_DATE            # fixed end date -> identical data on every run (yfinance end is exclusive)
DEV_WEIGHTS = {t: 1 / len(TICKERS) for t in TICKERS}   # neutral placeholder, NOT a recommendation

# ---------------- VaR / ES ----------------
HEADLINE_LEVELS = (0.95, 0.99)        # the brief's mandatory comparison
QUANTILE_METHOD = "linear"            # numpy default (Hyndman-Fan type 7) for empirical quantiles
N_SIM = 100_000                       # Monte Carlo scenarios per estimate
MC_T_NU_BOUNDS = (2.1, 100.0)         # nu > 2 so the covariance exists
SEED = 20261026

# ---------------- EVT (peaks over threshold) ----------------
EVT_THRESHOLD_GRID = np.round(np.arange(0.800, 0.9851, 0.005), 3)   # candidate u, as loss percentiles
EVT_MIN_EXCEED = 50                   # below this the GPD fit is too noisy to trust
EVT_STABILITY_Z = 1.96                # xi-hat(u) must sit inside the 95% CI of every higher threshold

# ---------------- Regime-conditioned models ----------------
GARCH_EVT_THRESHOLD_Q = 0.90          # McNeil & Frey (2000): top 10% of standardised losses

# ---------------- Estimation uncertainty ----------------
BOOT_REPS = 500
BOOT_BLOCK = 20                       # ~1 trading month: keeps volatility clusters intact
BOOT_N_SIM = 20_000                   # Monte Carlo scenarios inside each bootstrap resample
CI_LEVEL = 0.95

# ---------------- Rolling one-day-ahead forecasts (input to Person 4's backtest) ----------------
ROLL_WINDOW = 750                     # ~3 years: first forecast 27 Dec 2007, so the GFC is out-of-sample
ROLL_REFIT = 21                       # refit optimiser-based models monthly; GARCH volatility updates daily
