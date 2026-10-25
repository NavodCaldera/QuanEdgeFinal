"""GARCH filter, conditional VaR/ES, assumption tests and bootstrap intervals."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quanedge.risk import conditional, diagnostics, uncertainty, var_es
from quanedge.risk.models import CONDITIONAL, fit_models, risk_table

MU, OMEGA, ALPHA, GAMMA, BETA = 3e-4, 2e-6, 0.03, 0.10, 0.90


def gjr_series(n=5000, seed=0):
    """GJR-GARCH(1,1) returns with unit-variance t_5 shocks: clustered and fat-tailed, like the real data."""
    rng = np.random.default_rng(seed)
    z = rng.standard_t(5, n) / np.sqrt(5 / 3)
    r, s2 = np.empty(n), OMEGA / (1 - ALPHA - GAMMA / 2 - BETA)
    for t in range(n):
        r[t] = MU + np.sqrt(s2) * z[t]
        eps = r[t] - MU
        s2 = OMEGA + (ALPHA + GAMMA * (eps < 0)) * eps ** 2 + BETA * s2
    return r


def test_filter_recovers_dynamics_and_forecasts_with_the_recursion():
    r = gjr_series()
    f = conditional.fit_filter(r)
    assert f.beta == pytest.approx(BETA, abs=0.05)
    assert f.alpha + f.gamma / 2 + f.beta == pytest.approx(ALPHA + GAMMA / 2 + BETA, abs=0.02)   # persistence
    eps = r[-1] - f.mu
    manual = np.sqrt(f.omega + (f.alpha + f.gamma * (eps < 0)) * eps ** 2 + f.beta * f.sigma[-1] ** 2)
    assert f.sigma_next == pytest.approx(manual, rel=1e-12)


def test_filter_removes_clustering_but_not_fat_tails():
    r = gjr_series(seed=1)
    checks = diagnostics.assumption_checks(r, z=conditional.fit_filter(r).z).set_index("test")
    assert checks.loc["Ljung-Box Q(10) on r^2", "supported"] == "no"       # raw returns cluster
    assert checks.loc["Ljung-Box Q(10) on z^2", "supported"] == "yes"      # residuals do not
    assert checks.loc["Jarque-Bera on z", "supported"] == "no"             # but they are still fat-tailed


def test_conditional_var_scales_with_tomorrows_volatility():
    z = np.random.default_rng(2).standard_t(4, 4000)
    calm, storm = (conditional.GarchFilter(0.0, 0, 0, 0, 0, np.ones(4000), z, s) for s in (0.005, 0.02))
    for build in (conditional.fhs, conditional.garch_evt):
        assert build(storm).var(0.99) == pytest.approx(4 * build(calm).var(0.99))
        assert build(storm).es(0.99) == pytest.approx(4 * build(calm).es(0.99))


def test_all_models_fit_on_a_portfolio():
    r = gjr_series(seed=3)
    x = pd.DataFrame({"A": r, "B": 0.5 * r + 0.002 * np.random.default_rng(4).standard_normal(len(r))})
    models = fit_models(x, {"A": 0.6, "B": 0.4}, n_sim=20_000)
    table = risk_table(models)
    assert set(CONDITIONAL) <= set(models) and table[["var", "es"]].notna().all().all()
    assert (table["es"] >= table["var"]).all()


def test_assumption_checks_on_iid_normal_data_support_the_normal():
    r = np.random.default_rng(5).normal(0, 0.01, 3000)
    checks = diagnostics.assumption_checks(r).set_index("test")
    assert checks.loc["Jarque-Bera", "supported"] == "yes"
    assert checks.loc["ADF (H0: unit root)", "supported"] == "yes"


def test_block_bootstrap_keeps_blocks_contiguous():
    idx = uncertainty.block_bootstrap_index(103, 10, np.random.default_rng(6))
    assert len(idx) == 103 and idx.min() >= 0 and idx.max() < 103
    steps = np.diff(idx.reshape(-1)[:100].reshape(10, 10), axis=1) % 103
    assert (steps == 1).all()                                             # consecutive days inside each block


def test_bootstrap_interval_brackets_the_estimate_and_the_truth():
    x = pd.DataFrame({"A": np.random.default_rng(7).normal(0, 0.01, 2500)})
    ci = uncertainty.bootstrap_intervals(x, {"A": 1.0}, methods=["historical", "normal"], alphas=(0.99,), reps=200)
    point = var_es.Normal(x["A"]).var(0.99)
    row = ci.set_index("method").loc["normal"]
    assert row["var_lo"] < point < row["var_hi"]
    assert row["var_lo"] < stats.norm.ppf(0.99) * 0.01 < row["var_hi"]
