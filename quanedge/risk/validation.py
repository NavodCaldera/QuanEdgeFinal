"""
Input checks shared by the risk models, and the error a model raises when it
cannot be estimated.  fit_models turns a ModelFitError into a visible
"unavailable" result instead of a number; any other exception is a bad input
or a bug, and propagates.
"""
import numpy as np
import pandas as pd
from ..config import TICKERS


class ModelFitError(RuntimeError):
    """A model could not be estimated on this sample (too little data, failed optimiser, invalid fit)."""


def check_alpha(alpha) -> float:
    a = float(alpha)
    if not 0 < a < 1:
        raise ValueError(f"confidence level must lie strictly between 0 and 1 (0.99, not 99), got {alpha!r}")
    return a


def check_sample(x, name: str = "sample", min_n: int = 1) -> np.ndarray:
    """1-D float array of at least min_n values, all finite."""
    x = np.asarray(x, dtype=float).ravel()
    if len(x) < min_n:
        raise ValueError(f"{name} has {len(x)} observations; at least {min_n} are needed")
    if not np.isfinite(x).all():
        raise ValueError(f"{name} contains NaN or infinite values")
    return x


def require_n(n: int, needed: int, model: str) -> None:
    """A sample too short for one particular model is a fit failure, not an input error."""
    if n < needed:
        raise ModelFitError(f"{model} needs at least {needed} observations, got {n}")


def check_returns(df: pd.DataFrame, min_rows: int = 1) -> pd.DataFrame:
    """Numeric, finite asset returns with unique column names (nothing assumed about the index)."""
    if not isinstance(df, pd.DataFrame) or df.shape[1] == 0:
        raise ValueError("asset returns must be a DataFrame with at least one asset column")
    if df.columns.has_duplicates:
        raise ValueError(f"duplicate asset columns: {sorted(map(str, df.columns[df.columns.duplicated()]))}")
    if len(df) < min_rows:
        raise ValueError(f"asset returns have {len(df)} rows; at least {min_rows} are needed")
    if not np.isfinite(df.to_numpy(dtype=float)).all():
        raise ValueError("asset returns contain NaN or infinite values")
    return df


def check_dated_history(df: pd.DataFrame, eligible=TICKERS) -> pd.DataFrame:
    """
    The production boundary, where approved data enter: permitted tickers
    only, unique increasing dates.  Kept out of fit_models on purpose: the
    bootstrap legitimately refits on resampled, undated rows.
    """
    check_returns(df)
    extra = sorted(set(map(str, df.columns)) - set(eligible))
    if extra:
        raise ValueError(f"assets outside the permitted universe: {extra}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("dated history needs a DatetimeIndex")
    if df.index.has_duplicates or not df.index.is_monotonic_increasing:
        raise ValueError("dates must be unique and increasing")
    return df
