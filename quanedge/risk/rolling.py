"""
One-day-ahead VaR/ES forecasts on a rolling window: the input to Person 4's
out-of-sample backtest (Kupiec, Christoffersen, Basel traffic light).

No look-ahead: the forecast for day t uses only returns up to day t-1.
Cheap models (historical, normal) are re-estimated every day.  Models that
need an optimiser (student_t, evt, the GARCH filter and its residual tails)
are refitted every ROLL_REFIT days, while the GARCH volatility is updated
daily with the fitted recursion, so the conditional models react at once.
The EVT threshold is re-chosen by the scan rule inside each window, so even
that choice uses no future data.  Monte Carlo is left out: mc_normal repeats
normal up to simulation noise, and rolling simulation would add minutes.

Columns: "return" (realised log return of day t) and, for every method m and
level a, "var_{m}_{a}" / "es_{m}_{a}" in log-loss units, e.g. var_evt_99.
A breach is a day with -return > VaR.
"""
import numpy as np
import pandas as pd
from ..config import CONF_LEVELS
from . import conditional, evt, settings as S, var_es

ROLL_METHODS = ["historical", "normal", "student_t", "evt", "fhs", "garch_evt"]


def column(measure: str, method: str, alpha: float) -> str:
    return f"{measure}_{method}_{alpha * 100:g}"


def rolling_forecasts(r: pd.Series, alphas=CONF_LEVELS, methods=ROLL_METHODS,
                      window: int = S.ROLL_WINDOW, refit: int = S.ROLL_REFIT) -> pd.DataFrame:
    x = r.to_numpy(dtype=float)
    n_out = len(x) - window
    cond = [m for m in methods if m in ("fhs", "garch_evt")]
    out = {column(q, m, a): np.full(n_out, np.nan) for m in methods for a in alphas for q in ("var", "es")}

    def put(i, m, a, v, e):
        out[column("var", m, a)][i], out[column("es", m, a)][i] = v, e

    for i, t in enumerate(range(window, len(x))):
        hist = x[t - window:t]
        if i % refit == 0:                       # refit the slow models on data up to t-1
            slow = {}
            if "student_t" in methods:
                slow["student_t"] = var_es.StudentT(hist)
            if "evt" in methods:
                slow["evt"] = evt.fit_evt(-hist)
            frozen = {(m, a): (mod.var(a), mod.es(a)) for m, mod in slow.items() for a in alphas}
            if cond:
                filt = conditional.fit_filter(hist)
                sigma = filt.sigma_next
                base = {"fhs": var_es.Empirical(-filt.z),
                        "garch_evt": evt.fit_evt(-filt.z, threshold_q=S.GARCH_EVT_THRESHOLD_Q)}
                zq = {(m, a): (base[m].var(a), base[m].es(a)) for m in cond for a in alphas}
        elif cond:
            sigma = filt.next_sigma(sigma, x[t - 1])   # yesterday's volatility and return -> today's
        daily = {}
        if "historical" in methods:
            daily["historical"] = var_es.historical(hist)
        if "normal" in methods:
            daily["normal"] = var_es.Normal(hist)
        for a in alphas:
            for m, mod in daily.items():
                put(i, m, a, mod.var(a), mod.es(a))
            for m in slow:
                put(i, m, a, *frozen[(m, a)])
            for m in cond:
                zv, ze = zq[(m, a)]
                put(i, m, a, -filt.mu + sigma * zv, -filt.mu + sigma * ze)

    fc = pd.DataFrame(out, index=r.index[window:])
    fc.insert(0, "return", x[window:])
    return fc


def breach_summary(fc: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    """
    Raw breach counts per method and level over [start, end] (the dashboard's
    backtest date range).  Formal tests (Kupiec, Christoffersen, traffic
    light) are Person 4's; this is only the count they start from.
    """
    fc = fc.loc[start:end]
    losses = -fc["return"]
    rows = []
    for col in (c for c in fc.columns if c.startswith("var_")):
        method, level = col[len("var_"):].rsplit("_", 1)
        alpha = float(level) / 100
        hits = losses > fc[col]
        rows.append({"method": method, "alpha": alpha, "days": len(fc), "breaches": int(hits.sum()),
                     "breach_pct": 100 * hits.mean(), "expected_pct": 100 * (1 - alpha),
                     "expected_breaches": len(fc) * (1 - alpha)})
    return pd.DataFrame(rows)
