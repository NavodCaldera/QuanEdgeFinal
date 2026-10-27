"""Rolling forecasts: alignment, no look-ahead, audit metadata, input checks and faithful saving."""
import numpy as np
import pandas as pd
import pytest

from quanedge.risk import rolling, var_es
from quanedge.risk.rolling import breach_summary, rolling_forecasts


def returns(n=800, seed=0):
    rng = np.random.default_rng(seed)
    vol = 0.01 * np.exp(np.cumsum(rng.normal(0, 0.05, n)) * 0.3)      # slowly drifting volatility
    return pd.Series(vol * rng.standard_t(4, n), index=pd.bdate_range("2015-01-01", periods=n))


def forecast_columns(fc):
    return [c for c in fc.columns if c.startswith(("var_", "es_"))]


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
    kw = dict(alphas=(0.99,), window=500, refit=50)
    a = rolling_forecasts(r, **kw)
    cols = forecast_columns(a)
    for cut in (700, 723):                     # a refit day (i = 200) and a day between refits
        shocked = r.copy()
        shocked.iloc[cut:] *= 5
        b = rolling_forecasts(shocked, **kw)
        pd.testing.assert_frame_equal(a.loc[:r.index[cut], cols], b.loc[:r.index[cut], cols])
        assert not np.allclose(a[cols].iloc[-1], b[cols].iloc[-1])


def test_forecasts_carry_their_training_and_refit_dates():
    r = returns()
    fc = rolling_forecasts(r, alphas=(0.99,), methods=["historical", "student_t"], window=500, refit=50)
    row = fc.loc[r.index[670]]                 # i = 170: the parameters in use were refitted at i = 150
    assert row["train_start"] == r.index[170] and row["train_end"] == r.index[669]
    assert row["refit_train_end"] == r.index[649]
    assert (fc["refit_train_end"] <= fc["train_end"]).all()


def test_invalid_requests_are_rejected():
    r = returns()
    with pytest.raises(ValueError, match="no rolling forecast"):
        rolling_forecasts(r, methods=["mc_normal"])
    with pytest.raises(ValueError):
        rolling_forecasts(r, window=100)
    with pytest.raises(ValueError):
        rolling_forecasts(r, window=500, refit=0)
    with pytest.raises(ValueError):
        rolling_forecasts(r.iloc[:400], window=500)
    with pytest.raises(ValueError):
        rolling_forecasts(r, alphas=(99,), window=500)
    with pytest.raises(ValueError):
        rolling_forecasts(r.iloc[::-1], window=500)            # dates must increase


def test_only_requested_models_are_fitted(monkeypatch):
    calls = []
    real = rolling.evt.fit_evt
    monkeypatch.setattr(rolling.evt, "fit_evt", lambda *a, **k: calls.append(k) or real(*a, **k))
    fc = rolling_forecasts(returns(), alphas=(0.99,), methods=["fhs"], window=500, refit=100)
    assert not calls                                           # FHS alone fits no residual EVT
    assert forecast_columns(fc) == ["var_fhs_99", "es_fhs_99"]


def test_saved_forecasts_reload_to_identical_breach_counts(tmp_path):
    fc = rolling_forecasts(returns(), alphas=(0.95, 0.99), methods=["historical", "normal", "garch_evt"],
                           window=500, refit=50)
    assert not fc.attrs["fit_failures"]                        # boundary GARCH solutions are accepted, not dropped
    rolling.save_forecasts(fc, tmp_path / "fc.csv")
    back = rolling.load_forecasts(tmp_path / "fc.csv")
    cols = ["return"] + forecast_columns(fc)
    assert np.array_equal(back[cols].to_numpy(), fc[cols].to_numpy(), equal_nan=True)
    assert (back["refit_train_end"] == fc["refit_train_end"]).all()
    pd.testing.assert_frame_equal(breach_summary(back), breach_summary(fc))


def test_breach_summary_counts_losses_beyond_var():
    fc = pd.DataFrame({"return": [-0.03, 0.01, -0.02, -0.001], "var_normal_99": [0.02, 0.02, 0.02, 0.02],
                       "es_normal_99": [0.03] * 4}, index=pd.bdate_range("2020-01-01", periods=4))
    row = breach_summary(fc).iloc[0]
    assert (row["method"], row["alpha"], row["breaches"], row["days"]) == ("normal", 0.99, 1, 4)


def test_days_without_a_forecast_are_not_counted_as_passes():
    fc = pd.DataFrame({"return": [-0.03, 0.01, -0.05, -0.001], "var_normal_99": [0.02, np.nan, np.nan, 0.02],
                       "es_normal_99": [0.03, np.nan, np.nan, 0.03]}, index=pd.bdate_range("2020-01-01", periods=4))
    row = breach_summary(fc).iloc[0]
    assert (row["days"], row["missing_days"], row["breaches"]) == (2, 2, 1)
    assert row["expected_breaches"] == pytest.approx(0.02)
