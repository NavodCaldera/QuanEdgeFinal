"""
From asset returns to the single portfolio return every risk model uses.

Log returns add up over time but not across assets; simple returns do the
opposite.  So the portfolio is aggregated in simple returns,
R_p = sum_i w_i (e^{r_i} - 1), and converted back, r_p = ln(1 + R_p), for the
statistical work.  Weights are held fixed (daily rebalanced): the numbers
describe the portfolio as it is held today, replayed over history.

Sign convention across the risk package: a loss is a positive number in
log-return units, L = -r_p.  Money is computed only at the end:
USD loss = V0 * (1 - e^{-L}).
"""
import numpy as np
import pandas as pd
from ..config import PORTFOLIO_VALUE


def weight_vector(weights, columns) -> np.ndarray:
    """{ticker: weight} -> array in the column order of the return data."""
    w = pd.Series(weights, dtype=float)
    unknown = sorted(set(w.index) - set(columns))
    if unknown:
        raise ValueError(f"weights given for assets not in the data: {unknown}")
    w = w.reindex(columns, fill_value=0.0).to_numpy()
    if not np.isclose(w.sum(), 1.0, atol=1e-6):
        raise ValueError(f"weights sum to {w.sum():.6f}, not 1")
    return w


def portfolio_log_returns(asset_log_returns: pd.DataFrame, weights) -> pd.Series:
    w = weight_vector(weights, asset_log_returns.columns)
    simple = np.expm1(asset_log_returns.to_numpy()) @ w
    return pd.Series(np.log1p(simple), index=asset_log_returns.index, name="portfolio")


def loss_fraction(log_loss):
    """Log-return loss -> fraction of portfolio value lost, 1 - e^{-L}."""
    out = -np.expm1(-np.asarray(log_loss, dtype=float))
    return float(out) if out.ndim == 0 else out


def loss_usd(log_loss, value: float = PORTFOLIO_VALUE):
    return value * loss_fraction(log_loss)
