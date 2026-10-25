"""Every figure builds from model output without touching pyplot (smoke test on synthetic data)."""
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from quanedge.risk import plots
from quanedge.risk.models import fit_models, risk_table
from quanedge.risk.portfolio import portfolio_log_returns
from quanedge.risk.rolling import rolling_forecasts
from quanedge.risk.uncertainty import bootstrap_intervals, with_intervals


def test_all_figures_render():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2019-01-01", periods=1500)
    x = pd.DataFrame(0.01 * rng.standard_t(4, (1500, 2)), index=idx, columns=["A", "B"])
    w = {"A": 0.6, "B": 0.4}
    r = portfolio_log_returns(x, w)
    models = fit_models(x, w, n_sim=20_000)
    table = with_intervals(risk_table(models), bootstrap_intervals(x, w, methods=["historical", "normal"],
                                                                   reps=20))
    fc = rolling_forecasts(r, alphas=(0.99,), methods=["historical", "garch_evt"], window=750, refit=250)
    figs = [plots.fig_distribution(r, models),
            plots.fig_threshold(models["evt"].scan, 0.9),
            plots.fig_evt_fit(models["evt"], models["normal"]),
            plots.fig_comparison(table),
            plots.fig_tail_curve(models),
            plots.fig_uncertainty(table),
            plots.fig_rolling(fc, zoom=("2021-06-01", "2021-12-31"))]
    for fig in figs:
        assert isinstance(fig, Figure)
        fig.canvas.draw()          # forces layout and text rendering, where most plotting errors surface
