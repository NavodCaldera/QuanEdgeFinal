"""EVT: GPD fit, POT formulas and threshold rule checked on data whose tail is known."""
import numpy as np
import pytest
from scipy import stats

from quanedge.risk import evt, settings as S
from quanedge.risk.validation import ModelFitError


def test_gpd_mle_recovers_parameters_and_matches_scipy():
    y = stats.genpareto.rvs(0.25, scale=1.0, size=20000, random_state=0)
    fit = evt.fit_gpd(y, 0.0)
    assert fit.xi == pytest.approx(0.25, abs=0.03)
    assert fit.sigma == pytest.approx(1.0, rel=0.03)
    c, _, scale = stats.genpareto.fit(y, floc=0)
    ll = lambda xi, s: stats.genpareto.logpdf(y, xi, scale=s).sum()
    assert ll(fit.xi, fit.sigma) >= ll(c, scale) - 1e-6


def test_cdf_and_ks_distance_match_scipy():
    y = stats.genpareto.rvs(0.3, scale=0.02, size=500, random_state=7)
    for xi in (-0.2, 0.0, 0.3):
        assert np.allclose(evt.gpd_cdf(y, xi, 0.02), stats.genpareto.cdf(y, xi, scale=0.02))
        p = np.linspace(0.01, 0.99, 50)
        assert np.allclose(evt.gpd_ppf(p, xi, 0.02), stats.genpareto.ppf(p, xi, scale=0.02))
        assert evt.ks_distance(y, xi, 0.02) == pytest.approx(
            stats.kstest(y, stats.genpareto(xi, scale=0.02).cdf).statistic, rel=1e-9)


def test_standard_errors_cover_truth():
    y = stats.genpareto.rvs(0.2, scale=0.01, size=2000, random_state=1)
    fit = evt.fit_gpd(y, 0.0)
    se_xi, se_sigma = fit.se
    assert abs(fit.xi - 0.2) < 3 * se_xi and abs(fit.sigma - 0.01) < 3 * se_sigma


def test_pot_formulas_on_exponential_tail():
    """xi = 0: P(L > x) = zeta exp(-(x - u)/sigma), so VaR = u + sigma ln(zeta/p) and ES = VaR + sigma."""
    losses = np.linspace(0, 1, 1000)
    model = evt.EVT(losses, evt.GPDFit(u=0.9, xi=0.0, sigma=0.05, n_exceed=100, n=1000))
    v = model.var(0.995)
    assert v == pytest.approx(0.9 + 0.05 * np.log(0.1 / 0.005))
    assert model.es(0.995) == pytest.approx(v + 0.05)


def test_model_is_continuous_at_the_threshold():
    losses = stats.t.rvs(4, size=10000, random_state=2)
    model = evt.fit_evt(losses, threshold_q=0.95)
    a = 1 - model.zeta
    assert model.var(a) == pytest.approx(model.fit.u, rel=1e-9)
    assert model.es(a - 1e-6) == pytest.approx(model.es(a + 1e-6), rel=1e-3)


def test_evt_beats_historical_far_in_the_tail():
    """
    5,000 draws of a t_3 leave about five beyond the 99.9% quantile.  Over
    repeated samples EVT should be less noisy than the empirical quantile
    (single samples are too noisy to judge either).  EVT runs a few percent
    low here because a t tail approaches its power law slowly, so xi-hat at
    practical thresholds sits below 1/nu: a known second-order bias.
    """
    true = stats.t.ppf(0.999, 3)
    e, h = [], []
    for seed in range(20):
        losses = stats.t.rvs(3, size=5000, random_state=seed)
        e.append(evt.fit_evt(losses).var(0.999) / true)
        h.append(np.quantile(losses, 0.999) / true)
    rmse = lambda x: np.sqrt(np.mean((np.array(x) - 1) ** 2))
    assert np.median(e) == pytest.approx(1, abs=0.10)
    assert rmse(e) < rmse(h)


def test_threshold_rule_does_not_go_below_where_the_gpd_starts():
    """Uniform body below 1, exact GPD(0.25) tail above it (the top 15%): the rule should find the tail."""
    chosen_q, xi = [], []
    for seed in range(6):
        rng = np.random.default_rng(seed)
        tail = rng.random(10000) < 0.15
        losses = np.where(tail, 1 + stats.genpareto.rvs(0.25, scale=0.5, size=10000, random_state=rng),
                          rng.random(10000))
        c = evt.select_threshold(evt.threshold_scan(losses))
        assert c["stable"] and c["n_exceed"] >= 50
        chosen_q.append(c["q"])
        xi.append(c["xi"])
    assert min(chosen_q) >= 0.84
    assert np.median(xi) == pytest.approx(0.25, abs=0.05)


def test_es_exceeds_var_at_every_sidebar_level():
    model = evt.fit_evt(stats.t.rvs(3, size=5000, random_state=5))
    for a in (0.90, 0.95, 0.99, 0.999):
        assert np.isfinite(model.es(a)) and model.es(a) >= model.var(a)


# ---------------- failure states and the threshold rule's edges ----------------
def test_gpd_fit_failures_are_explicit():
    with pytest.raises(ModelFitError):
        evt.fit_gpd(np.r_[np.zeros(100), np.ones(5)], 0.5)            # 5 exceedances: too few
    with pytest.raises(ModelFitError):
        evt.fit_gpd(np.r_[np.zeros(100), np.full(30, 2.0)], 0.5)       # constant excesses


def test_empty_scan_keeps_its_columns_and_selection_fails_clearly():
    scan = evt.threshold_scan(np.random.default_rng(0).standard_t(4, 100))   # no candidate reaches 50 exceedances
    assert scan.empty and {"q", "u", "xi", "ks", "stable", "fit_ok"} <= set(scan.columns)
    with pytest.raises(ModelFitError):
        evt.select_threshold(scan)


def test_top_thresholds_cannot_pass_stability_by_comparing_with_themselves():
    scan = evt.threshold_scan(stats.t.rvs(4, size=20000, random_state=8))
    assert not scan[scan["fit_ok"]]["stable"].iloc[-S.EVT_STABILITY_MIN_HIGHER:].any()


def test_fallback_is_flagged_when_no_threshold_is_stable():
    scan = evt.threshold_scan(stats.t.rvs(4, size=20000, random_state=9))
    scan["stable"] = False
    assert evt.select_threshold(scan)["rule"].startswith("FALLBACK")


def _worst_mass_mean(values, weights, mass):
    """Brute force: average of the largest values carrying total probability 'mass'."""
    order = np.argsort(values)[::-1]
    v, w = values[order], weights[order]
    cum = np.cumsum(w)
    k = int(np.searchsorted(cum, mass))
    taken = cum[k - 1] if k else 0.0
    return (np.dot(v[:k], w[:k]) + (mass - taken) * v[k]) / mass


def test_hybrid_es_matches_a_brute_force_mixture():
    """Body: each observed loss below u with mass 1/n; tail: the GPD discretised into 400,000 equal-mass points."""
    losses = stats.t.rvs(4, size=4000, random_state=11)
    m = evt.fit_evt(losses, threshold_q=0.9)
    f, n, M = m.fit, len(losses), 400_000
    values = np.r_[losses[losses <= f.u], f.u + evt.gpd_ppf((np.arange(M) + 0.5) / M, f.xi, f.sigma)]
    weights = np.r_[np.full((losses <= f.u).sum(), 1 / n), np.full(M, m.zeta / M)]
    assert weights.sum() == pytest.approx(1)
    for a in (0.80, 0.85, 0.95, 0.99):                    # two levels in the body, two in the tail
        assert m.es(a) == pytest.approx(_worst_mass_mean(values, weights, 1 - a), rel=2e-3)
        assert m.es_fraction(a) == pytest.approx(_worst_mass_mean(-np.expm1(-values), weights, 1 - a), rel=2e-3)
