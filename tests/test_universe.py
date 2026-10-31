"""Why-these-four evidence: independent-bet arithmetic, spanning regression, saved-evidence identity and the seven-ETF runs."""
import hashlib
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from quanedge import universe as U
from quanedge.config import TICKERS

ROOT = Path(__file__).resolve().parents[1]


def synthetic(n=3000, seed=1):
    """Fictitious daily log returns: EFA, EEM, XLK are SPY plus noise; the held four are independent."""
    rng = np.random.default_rng(seed)
    r = pd.DataFrame(rng.normal(0, .01, (n, 4)), columns=U.KEEP,
                     index=pd.bdate_range("2010-01-01", periods=n))
    for t in U.DROP:
        r[t] = r.SPY + rng.normal(0, .003, n)
    return r[TICKERS]


def test_effective_bets_limits():
    assert U.effective_bets(np.eye(5))[0] == pytest.approx(5)
    one_factor = np.full((4, 4), 1.) + np.eye(4)*1e-9
    assert U.effective_bets(one_factor)[0] == pytest.approx(1, abs=1e-6)


def test_copies_of_spy_add_almost_no_bets():
    b = U.bets_table(synthetic()).set_index("set")
    four, seven = b.loc["Four (SPY, AGG, GLD, XLE)", "effective_bets"], b.loc["All seven", "effective_bets"]
    assert four == pytest.approx(4, abs=.05) and seven < four + .5


def test_spanning_recovers_known_structure():
    s = U.spanning(synthetic()).set_index("etf")
    expected = .01**2/(.01**2+.003**2)
    assert np.allclose(s.r2_on_four, expected, atol=.02)
    assert np.allclose(s.beta_spy, 1, atol=.03)
    assert (s.alpha_t.abs() < 4).all()


def test_monthly_negative_counts_match_direct_calculation():
    r = synthetic(400)
    m = U.monthly_negative(r).set_index("pair")
    g = r.groupby(r.index.to_period("M"))
    direct = (g.apply(lambda d: d.SPY.corr(d.AGG)) < 0).sum()
    assert m.loc["SPY-AGG", "negative_months"] == direct and m.loc["SPY-AGG", "both_held"]
    assert not m.loc["SPY-XLK", "both_held"]


def test_seven_etf_risk_parity_puts_five_sevenths_of_risk_in_equity():
    rng = np.random.default_rng(2)
    simple = pd.DataFrame(rng.normal(0, .01, (700, 7))*np.linspace(.5, 2, 7), columns=TICKERS,
                          index=pd.bdate_range("2010-01-01", periods=700))
    static = pd.DataFrame(U.parity_comparison(simple)[0]).set_index("universe")
    assert static.loc["Four ETFs", "equity_risk_share"] == pytest.approx(.5, abs=1e-4)
    assert static.loc["All seven ETFs", "equity_risk_share"] == pytest.approx(5/7, abs=1e-4)


def test_seven_etf_optimisers_never_bought_efa_or_eem():
    o = U.optimiser_choices()
    assert len(o) == 8
    risk_min = o[o.allocation.isin(["min_cvar", "min_variance"])]
    assert (risk_min[U.DROP].abs() < 1e-6).all().all()
    v2 = o[(o.run.str.startswith("v2")) & (o.allocation == "selected")].iloc[0]
    assert v2[["EFA", "EEM", "XLK"]].abs().max() < 1e-6 and v2.weight_hash == "bd13d897"


def test_saved_evidence_is_refused_when_prices_or_tables_change(tmp_path):
    folder = tmp_path/U.OUT
    shutil.copytree(ROOT/"results"/U.OUT, folder)
    price_hash = hashlib.sha256((ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest()
    ev = U.load_saved(price_hash, folder)
    assert ev is not None and list(ev["correlation"].index) == TICKERS
    assert U.load_saved("0"*64, folder) is None
    (folder/"bets.csv").write_text("set,etfs\nx,1\n")
    assert U.load_saved(price_hash, folder) is None


def test_saved_evidence_matches_a_fresh_calculation():
    prices, macro = U.load()
    fresh = U.evidence(prices, macro)
    saved = U.load_saved(hashlib.sha256((ROOT/"data/clean/prices_clean.csv").read_bytes()).hexdigest())
    assert saved is not None
    for k in ["bets", "spanning", "crises", "parity_dynamic"]:
        pd.testing.assert_frame_equal(fresh[k].reset_index(drop=True), saved[k], check_dtype=False, atol=1e-9)
