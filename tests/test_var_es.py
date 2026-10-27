"""VaR/ES formulas checked against independent calculations (closed forms, integration, simulation)."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quanedge.risk import var_es
from quanedge.risk.models import fit_models, risk_table
from quanedge.risk.portfolio import loss_fraction, loss_usd, portfolio_log_returns

ALPHAS = (0.90, 0.95, 0.99)


def fat_tailed_assets(n=4000, d=3, nu=4, seed=0):
    rng = np.random.default_rng(seed)
    cov = 1e-4 * np.array([[1.0, 0.6, 0.2], [0.6, 1.0, 0.3], [0.2, 0.3, 1.0]])[:d, :d]
    z = rng.multivariate_normal(np.zeros(d), cov, n) * np.sqrt((nu - 2) / rng.chisquare(nu, (n, 1)))
    return pd.DataFrame(z + 3e-4, columns=list("ABC")[:d])


# ---------------- portfolio conventions ----------------
def test_portfolio_aggregates_in_simple_returns():
    x = pd.DataFrame({"A": [0.10, -0.05], "B": [-0.02, 0.03]})
    rp = portfolio_log_returns(x, {"A": 0.6, "B": 0.4})
    assert np.allclose(rp, np.log(0.6 * np.exp(x["A"]) + 0.4 * np.exp(x["B"])))


def test_weights_are_validated():
    x = pd.DataFrame({"A": [0.01], "B": [0.02]})
    with pytest.raises(ValueError):
        portfolio_log_returns(x, {"A": 0.5, "B": 0.4})          # does not sum to 1
    with pytest.raises(ValueError):
        portfolio_log_returns(x, {"A": 0.5, "Z": 0.5})          # unknown ticker
    assert np.allclose(portfolio_log_returns(x, {"B": 1.0}), 0.02)   # missing ticker = zero weight


def test_loss_conversion_to_money():
    assert loss_fraction(0.01) == pytest.approx(1 - np.exp(-0.01))
    assert loss_usd(np.log(2)) == pytest.approx(5_000_000)    # a log loss of ln 2 halves USD 10m


# ---------------- historical ----------------
def test_historical_quantile_and_tail_mean():
    m = var_es.Empirical(np.arange(1, 1001, dtype=float))
    assert m.var(0.99) == pytest.approx(990.01)             # linear interpolation, Hyndman-Fan type 7
    assert m.es(0.99) == pytest.approx(995.5)               # mean of 991..1000


# ---------------- parametric ----------------
def test_normal_matches_conditional_expectation():
    m = var_es.Normal(np.random.default_rng(1).normal(5e-4, 0.01, 2000))
    loss = stats.norm(-m.mu, m.sigma)
    for a in ALPHAS:
        assert loss.cdf(m.var(a)) == pytest.approx(a, abs=1e-12)
        assert m.es(a) == pytest.approx(loss.expect(lambda x: x, lb=m.var(a), conditional=True), rel=1e-7)


def test_t_mle_is_at_least_as_good_as_scipy():
    r = stats.t.rvs(3, loc=7e-4, scale=6e-3, size=5000, random_state=6)
    ll = lambda p: stats.t.logpdf(r, *p).sum()
    assert ll(var_es.fit_t(r)) >= ll(stats.t.fit(r)) - 1e-6


def test_student_t_fit_and_es_formula():
    r = stats.t.rvs(4, loc=3e-4, scale=7e-3, size=20000, random_state=2)
    m = var_es.StudentT(r)
    assert m.nu == pytest.approx(4, abs=0.5)
    loss = stats.t(m.nu, loc=-m.loc, scale=m.scale)
    for a in ALPHAS:
        assert loss.cdf(m.var(a)) == pytest.approx(a, abs=1e-9)
        assert m.es(a) == pytest.approx(loss.expect(lambda x: x, lb=m.var(a), conditional=True), rel=1e-6)


# ---------------- Monte Carlo ----------------
def test_mc_normal_converges_to_parametric_normal():
    x = pd.DataFrame({"A": np.random.default_rng(3).normal(4e-4, 0.012, 3000)})   # one asset: aggregation is exact
    mc = var_es.monte_carlo(x, {"A": 1.0}, "normal", n_sim=400_000, seed=4)
    nm = var_es.Normal(x["A"])
    for a in ALPHAS:
        assert mc.var(a) == pytest.approx(nm.var(a), rel=0.01)
        assert mc.es(a) == pytest.approx(nm.es(a), rel=0.01)


def test_mvt_tail_index_is_recovered():
    assert var_es.mvt_nu(fat_tailed_assets(n=20000, nu=5, seed=5)) == pytest.approx(5, abs=0.5)


def test_mc_t_tail_is_heavier_than_mc_normal_on_fat_tailed_data():
    x = fat_tailed_assets()
    w = {"A": 0.5, "B": 0.3, "C": 0.2}
    mcn, mct = (var_es.monte_carlo(x, w, d, n_sim=200_000) for d in ("normal", "t"))
    assert mct.es(0.99) > mcn.es(0.99)


def test_batch_se_is_small_for_large_simulations():
    mc = var_es.monte_carlo(fat_tailed_assets(), {"A": 1.0}, "normal", n_sim=200_000)
    se_var, se_es = var_es.batch_se(mc, 0.99)
    assert 0 < se_var < 0.01 * mc.var(0.99) and 0 < se_es < 0.01 * mc.es(0.99)


# ---------------- properties every model must satisfy ----------------
def test_es_exceeds_var_and_both_rise_with_confidence():
    x = fat_tailed_assets()
    table = risk_table(fit_models(x, {"A": 0.5, "B": 0.3, "C": 0.2}, n_sim=50_000), alphas=ALPHAS)
    assert (table["es"] >= table["var"]).all()
    for _, g in table.groupby("method"):
        assert g.sort_values("alpha")["var"].is_monotonic_increasing
        assert g.sort_values("alpha")["es"].is_monotonic_increasing
