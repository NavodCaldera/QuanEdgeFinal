"""
Risk measurement (Person 3): VaR, Expected Shortfall and EVT for one portfolio.
See docs/person-3/AGENTS.md for conventions and the interface contract.
Figures live in quanedge.risk.plots (imported separately: it loads matplotlib).
"""
from .portfolio import portfolio_log_returns, loss_fraction, loss_usd
from .models import fit_models, risk_table, ALL_METHODS, UNCONDITIONAL, CONDITIONAL, LABEL
from .evt import fit_evt, threshold_scan, select_threshold
from .diagnostics import describe, assumption_checks, worst_days
from .uncertainty import bootstrap_intervals, with_intervals
from .rolling import rolling_forecasts, breach_summary
