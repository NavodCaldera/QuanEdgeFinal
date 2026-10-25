"""Rolling forecasts: correct alignment and no look-ahead."""
import numpy as np
import pandas as pd

from quanedge.risk import var_es
from quanedge.risk.rolling import breach_summary, rolling_forecasts


def returns(n=800, seed=0):
    rng = np.random.default_rng(seed)
    vol = 0.01 * np.exp(np.cumsum(rng.normal(0, 0.05, n)) * 0.3)      # slowly drifting volatility
    return pd.Series(vol * rng.standard_t(4, n), index=pd.bdate_range("2015-01-01", periods=n))


def test_forecast_for_day_t_uses_the_window_ending_at_t_minus_1():
    r = returns()
    fc = rolling_forecasts(r, alphas=(0.99,), methods=["historical", "normal"], window=500)
    t = 650
    hist = r.iloc[t - 500:t]
    assert fc.loc[r.index[t], "var_historical_99"] == var_es.historical(hist).var(0.99)
    assert fc.loc[r.index[t], "es_normal_99"] == var_es.Normal(hist).es(0.99)
    assert fc.loc[r.index[t], "return"] == r.iloc[t]


def test_changing_the_future_does_not_change_past_forecasts():
    r = returns()
    shocked = r.copy()
    shocked.iloc[700:] *= 5
    kw = dict(alphas=(0.99,), window=500, refit=50)
    a, b = rolling_forecasts(r, **kw), rolling_forecasts(shocked, **kw)
    cols = [c for c in a.columns if c != "return"]
    pd.testing.assert_frame_equal(a.loc[:r.index[700], cols], b.loc[:r.index[700], cols])
    assert not np.allclose(a[cols].iloc[-1], b[cols].iloc[-1])


def test_breach_summary_counts_losses_beyond_var():
    fc = pd.DataFrame({"return": [-0.03, 0.01, -0.02, -0.001], "var_normal_99": [0.02, 0.02, 0.02, 0.02],
                       "es_normal_99": [0.03] * 4}, index=pd.bdate_range("2020-01-01", periods=4))
    row = breach_summary(fc).iloc[0]
    assert (row["method"], row["alpha"], row["breaches"], row["days"]) == ("normal", 0.99, 1, 4)
