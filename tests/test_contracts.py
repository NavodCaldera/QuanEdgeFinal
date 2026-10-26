"""Contracts from docs/person-3: exact ES (empirical and in dollars), input validation, visible failure states."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quanedge.risk import diagnostics, evt, uncertainty, var_es
from quanedge.risk.models import Unavailable, fit_models, risk_table
from quanedge.risk.portfolio import loss_fraction, portfolio_log_returns
from quanedge.risk.validation import ModelFitError, check_alpha

ALPHAS = (0.90, 0.95, 0.99)


def assets(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    z = rng.standard_t(4, (n, 2)) * 0.01 / np.sqrt(2)
    return pd.DataFrame({"A": z[:, 0], "B": 0.5 * z[:, 0] + z[:, 1]})


# ---------------- exact empirical ES ----------------
def test_empirical_es_weights_the_boundary_observation():
    m = var_es.Empirical([1.0, 2.0, 3.0, 4.0, 5.0])
    # worst 30% of five equally likely days: all of the 5 (mass 0.2) and half of the 4 (mass 0.1)
    assert m.es(0.70) == pytest.approx((0.2 * 5 + 0.1 * 4) / 0.3)


def test_empirical_es_with_ties_and_a_tail_smaller_than_one_observation():
    m = var_es.Empirical([0, 1, 1, 1, 7, 7])
    assert m.es(0.75) == pytest.approx(7)                 # worst 25% = 1.5 observations, both 7s
    assert m.es(0.95) == pytest.approx(7)                 # a tail of 0.3 observations: the worst value
    assert m.es(0.50) == pytest.approx((7 + 7 + 1) / 3)


def test_dollar_es_averages_dollar_losses_not_log_es():
    m = var_es.Empirical([0.5, 0.1, 0.05, 0.02, 0.01])    # a dispersed tail
    exact = (loss_fraction(0.5) + loss_fraction(0.1)) / 2
    assert m.es_fraction(0.6) == pytest.approx(exact)
    assert loss_fraction(m.es(0.6)) > exact + 0.01        # the shortcut overstates, because g is concave


def test_normal_dollar_es_closed_form_matches_integration():
    m = var_es.Normal(np.random.default_rng(1).normal(4e-4, 0.012, 3000))
    loss = stats.norm(-m.mu, m.sigma)
    for a in ALPHAS + (0.999,):
        target = loss.expect(lambda x: -np.expm1(-x), lb=m.var(a), conditional=True)
        assert m.es_fraction(a) == pytest.approx(target, rel=1e-6)
        assert var_es.LossModel.tail_mean(m, a, loss_fraction) == pytest.approx(target, rel=1e-6)


def test_student_t_dollar_es_matches_conditional_expectation():
    m = var_es.StudentT(stats.t.rvs(3, loc=5e-4, scale=6e-3, size=5000, random_state=2))
    loss = stats.t(m.nu, loc=-m.loc, scale=m.scale)
    for a in ALPHAS:
        target = loss.expect(lambda x: -np.expm1(-x), lb=m.var(a), conditional=True)
        assert m.es_fraction(a) == pytest.approx(target, rel=1e-5)


def test_risk_table_reports_exact_dollar_es():
    models = fit_models(assets(), {"A": 0.6, "B": 0.4}, methods=["historical", "normal", "evt"])
    for _, row in risk_table(models, value=1e7).iterrows():
        assert row["es_usd"] == pytest.approx(1e7 * models[row["method"]].es_fraction(row["alpha"]))
        assert row["es_usd"] <= 1e7 * loss_fraction(row["es"]) + 1e-6


def test_scaling_nav_scales_money_only():
    models = fit_models(assets(), {"A": 1.0}, methods=["historical", "normal"])
    a, b = risk_table(models, value=1e7), risk_table(models, value=2e7)
    assert np.allclose(b["var_usd"], 2 * a["var_usd"]) and np.allclose(b["es_usd"], 2 * a["es_usd"])
    assert np.allclose(a["var_pct"], b["var_pct"]) and np.allclose(a["es"], b["es"])


# ---------------- validation ----------------
def test_bad_inputs_raise():
    x = assets(200)
    with pytest.raises(ValueError):
        fit_models(x.assign(A=np.r_[np.nan, x["A"].to_numpy()[1:]]), {"A": 1.0})     # NaN return
    with pytest.raises(ValueError):
        fit_models(pd.concat([x, x["A"]], axis=1), {"A": 1.0})                        # duplicate column
    with pytest.raises(ValueError):
        fit_models(x.iloc[:10], {"A": 1.0})                                            # too short for any model
    with pytest.raises(ValueError):
        portfolio_log_returns(x, {"A": np.nan, "B": 1.0})                              # NaN weight
    with pytest.raises(ValueError):
        risk_table(fit_models(x, {"A": 1.0}, methods=["normal"]), alphas=(99,))        # 99 is not 0.99
    with pytest.raises(ValueError):
        check_alpha(1.0)


def test_portfolio_value_must_stay_positive():
    x = pd.DataFrame({"A": [0.5, 0.0], "B": [-0.1, 0.0]})
    with pytest.raises(ValueError, match="falls to zero"):
        portfolio_log_returns(x, {"A": -2.0, "B": 3.0})


# ---------------- visible failure states ----------------
def test_a_model_that_cannot_be_fitted_is_unavailable_not_zero():
    models = fit_models(assets().assign(C=0.0), {"A": 0.5, "B": 0.3, "C": 0.2})   # a constant asset
    assert isinstance(models["mc_normal"], Unavailable) and isinstance(models["mc_t"], Unavailable)
    assert models["mc_normal"].status.startswith("failed: sample covariance")
    table = risk_table(models)
    is_mc = table["method"].str.startswith("mc_")
    assert table.loc[is_mc, ["var_usd", "es_usd"]].isna().all().all()
    assert table.loc[~is_mc, ["var_usd", "es_usd"]].notna().all().all()


def test_short_samples_make_the_demanding_models_unavailable():
    models = fit_models(assets(120), {"A": 1.0})
    assert isinstance(models["fhs"], Unavailable) and "at least 250" in models["fhs"].status
    assert isinstance(models["evt"], Unavailable)
    assert not isinstance(models["historical"], Unavailable)


def test_infinite_log_es_is_flagged_and_dollar_es_stays_finite():
    model = evt.EVT(np.linspace(0, 1, 1000), evt.GPDFit(u=0.9, xi=1.2, sigma=0.05, n_exceed=100, n=1000))
    assert model.es(0.99) == np.inf and 0 < model.es_fraction(0.99) < 1
    row = risk_table({"evt": model}, alphas=(0.99,)).iloc[0]
    assert row["status"].startswith("warning") and np.isfinite(row["es_usd"]) and row["es_over_var"] == np.inf


# ---------------- Monte Carlo and Student-t edge cases ----------------
def test_monte_carlo_overflow_is_an_error_not_a_clip():
    x = pd.DataFrame({"A": np.random.default_rng(3).normal(0, 1000, 500)})
    with pytest.raises(ModelFitError, match="not clipped"):
        var_es.monte_carlo(x, {"A": 1.0}, n_sim=10_000)


def test_monte_carlo_keeps_asset_scenarios_for_attribution():
    m = var_es.monte_carlo(assets(), {"A": 0.6, "B": 0.4}, n_sim=5_000)
    assert m.scenarios.shape == (5_000, 2) and m.assets == ["A", "B"]
    assert np.allclose(-np.log1p(np.expm1(m.scenarios) @ np.array([0.6, 0.4])), m.losses)


def test_student_t_zero_mad_gives_a_fit_or_a_clear_failure():
    rng = np.random.default_rng(4)
    r = np.where(rng.random(3000) < 0.6, 0.0, rng.standard_t(4, 3000) * 0.01)   # over half the days flat
    assert stats.median_abs_deviation(r) == 0
    try:
        m = var_es.StudentT(r)
    except ModelFitError as err:
        assert "point mass" in str(err) or "converge" in str(err)
    else:
        assert np.isfinite(m.var(0.99)) and m.scale > 0
    with pytest.raises(ModelFitError, match="constant"):
        var_es.StudentT(np.zeros(100))


def test_batch_se_refuses_batches_with_too_few_tail_points():
    m = var_es.monte_carlo(assets(), {"A": 1.0}, n_sim=2_000)
    with pytest.raises(ValueError):
        var_es.batch_se(m, 0.99, n_batches=20)          # 100 scenarios per batch: one tail point each


def test_mc_convergence_table_covers_every_size_seed_and_level():
    conv = var_es.mc_convergence(assets(), {"A": 0.6, "B": 0.4}, sizes=(5_000, 10_000), n_seeds=2)
    assert len(conv) == 2 * 2 * 2 * 2 and set(conv["method"]) == {"mc_normal", "mc_t"}


# ---------------- bootstrap ----------------
def test_bootstrap_dollar_es_bounds_come_from_dollar_draws():
    x = assets(1500)
    kw = dict(methods=["historical"], alphas=(0.99,), reps=40)
    ci = uncertainty.bootstrap_intervals(x, {"A": 1.0}, **kw)
    row = ci.iloc[0]
    assert row["reps_ok"] == 40 and row["reps_failed"] == 0
    assert row["es_frac_lo"] <= loss_fraction(row["es_lo"]) + 1e-9
    table = uncertainty.with_intervals(risk_table(fit_models(x, {"A": 1.0}, methods=["historical"]),
                                                  alphas=(0.99,)), ci)
    assert table["es_lo_usd"].iloc[0] == pytest.approx(1e7 * row["es_frac_lo"])
    pd.testing.assert_frame_equal(ci, uncertainty.bootstrap_intervals(x, {"A": 1.0}, **kw))   # same seed, same answer


def test_bootstrap_counts_resamples_where_a_model_fails():
    ci = uncertainty.bootstrap_intervals(assets(1500).assign(C=0.0), {"A": 0.5, "B": 0.3, "C": 0.2},
                                         methods=["historical", "mc_normal"], alphas=(0.99,), reps=10)
    mc = ci.set_index("method").loc["mc_normal"]
    assert mc["reps_ok"] == 0 and mc["reps_failed"] == 10 and np.isnan(mc["var_lo"])


# ---------------- diagnostics ----------------
def test_worst_days_separates_lowest_return_from_largest_contribution():
    x = pd.DataFrame({"A": [-0.10, 0.0, 0.01], "B": [-0.05, 0.0, 0.01]}, index=pd.bdate_range("2020-01-01", periods=3))
    w = {"A": 0.1, "B": 0.9}
    day = diagnostics.worst_days(portfolio_log_returns(x, w), x, w, n=1).iloc[0]
    assert day["lowest_return_asset"] == "A" and day["top_loss_contributor"] == "B"
