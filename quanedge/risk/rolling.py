"""
One-day-ahead VaR/ES forecasts on a rolling window: the input to Validation's
out-of-sample backtest (Kupiec, Christoffersen, Basel traffic light).

No look-ahead: the forecast for day t uses only returns up to day t-1.
Cheap models (historical, normal) are re-estimated every day.  Models that
need an optimiser (student_t, evt, the GARCH filter and its residual tails)
are refitted every ROLL_REFIT days, while the GARCH volatility is updated
daily with the fitted recursion, so the conditional models react at once.
The EVT threshold is re-chosen by the scan rule inside each window, so even
that choice uses no future data.  Only the requested models are fitted.
Monte Carlo is not available here: mc_normal repeats normal up to
simulation noise, and rolling simulation would add minutes.

Columns: "return" (realised log return of day t); "train_start" and
"train_end" (the window behind day t's forecast, train_end = day t-1);
"refit_train_end" (the data cutoff of the slow-model parameters in use);
then, for every method m and level a, "var_{m}_{a}" / "es_{m}_{a}" in
log-loss units, e.g. var_evt_99.  A breach is a day with -return > VaR.
A model that fails at a refit leaves NaN until its next successful refit
(details in fc.attrs["fit_failures"]); NaN days are excluded from breach
counts, never counted as non-breaches.  Save with save_forecasts and read
with load_forecasts: pandas' default CSV round trip can move a value by one
unit in the last place, enough to flip a borderline breach.
"""
import numpy as np
import pandas as pd
from ..config import CONF_LEVELS
from . import conditional, evt, settings as S, var_es
from .validation import ModelFitError, check_alpha, check_sample

ROLL_METHODS = ["historical", "normal", "student_t", "evt", "fhs", "garch_evt"]
SLOW = ("student_t", "evt")
CONDITIONAL = ("fhs", "garch_evt")
FIT_ERRORS = (ModelFitError, np.linalg.LinAlgError)


def column(measure: str, method: str, alpha: float) -> str:
    return f"{measure}_{method}_{alpha * 100:g}"


def _residual_model(method: str, filt):
    return var_es.Empirical(-filt.z, "fhs_z") if method == "fhs" else \
        evt.fit_evt(-filt.z, threshold_q=S.GARCH_EVT_THRESHOLD_Q)


def rolling_forecasts(r: pd.Series, alphas=CONF_LEVELS, methods=ROLL_METHODS,
                      window: int = S.ROLL_WINDOW, refit: int = S.ROLL_REFIT) -> pd.DataFrame:
    methods = list(methods)
    unsupported = sorted(set(methods) - set(ROLL_METHODS))
    if unsupported or not methods:
        raise ValueError(f"no rolling forecast for {unsupported or 'an empty method list'}; "
                         f"available: {ROLL_METHODS}")
    alphas = [check_alpha(a) for a in alphas]
    if not isinstance(r, pd.Series):
        raise ValueError("r must be a pandas Series of portfolio log returns")
    if r.index.has_duplicates or not r.index.is_monotonic_increasing:
        raise ValueError("forecast dates must be unique and increasing")
    if int(window) != window or window < S.ROLL_MIN_WINDOW:
        raise ValueError(f"window must be a whole number of at least {S.ROLL_MIN_WINDOW} days, got {window}")
    if int(refit) != refit or refit < 1:
        raise ValueError(f"refit must be a positive whole number of days, got {refit}")
    window, refit = int(window), int(refit)
    x = check_sample(r.to_numpy(dtype=float), "returns", min_n=window + 1)
    dates, n_out = r.index, len(x) - window
    slow = [m for m in methods if m in SLOW]
    cond = [m for m in methods if m in CONDITIONAL]
    out = {column(q, m, a): np.full(n_out, np.nan) for m in methods for a in alphas for q in ("var", "es")}
    refit_end, failures = [], []

    def put(i, m, a, v, e):
        out[column("var", m, a)][i], out[column("es", m, a)][i] = v, e

    def failed(method, err):
        failures.append({"refit_train_end": last_refit, "method": method, "reason": str(err)})

    for i, t in enumerate(range(window, len(x))):
        hist = x[t - window:t]
        if i % refit == 0:                       # refit the slow models on data up to t-1
            last_refit, frozen, zq, filt = dates[t - 1], {}, {}, None
            for m in slow:
                try:
                    mod = var_es.StudentT(hist) if m == "student_t" else evt.fit_evt(-hist)
                    frozen.update({(m, a): (mod.var(a), mod.es(a)) for a in alphas})
                except FIT_ERRORS as err:
                    failed(m, err)
            if cond:
                try:
                    filt = conditional.fit_filter(hist)
                    sigma = filt.sigma_next
                except FIT_ERRORS as err:
                    for m in cond:
                        failed(m, err)
            for m in cond if filt is not None else ():
                try:
                    base = _residual_model(m, filt)
                    zq.update({(m, a): (base.var(a), base.es(a)) for a in alphas})
                except FIT_ERRORS as err:
                    failed(m, err)
        elif filt is not None:
            sigma = filt.next_sigma(sigma, x[t - 1])   # yesterday's volatility and return -> today's
        refit_end.append(last_refit)
        daily = {}
        if "historical" in methods:
            daily["historical"] = var_es.historical(hist)
        if "normal" in methods:
            daily["normal"] = var_es.Normal(hist)
        for a in alphas:
            for m, mod in daily.items():
                put(i, m, a, mod.var(a), mod.es(a))
        for (m, a), (v, e) in frozen.items():
            put(i, m, a, v, e)
        for (m, a), (zv, ze) in zq.items():
            put(i, m, a, -filt.mu + sigma * zv, -filt.mu + sigma * ze)

    fc = pd.DataFrame(out, index=dates[window:])
    fc.insert(0, "return", x[window:])
    fc.insert(1, "train_start", dates[:n_out])
    fc.insert(2, "train_end", dates[window - 1:len(x) - 1])
    fc.insert(3, "refit_train_end", pd.Index(refit_end))
    fc.attrs["fit_failures"] = failures
    return fc


def save_forecasts(fc: pd.DataFrame, path) -> None:
    """Write forecasts with 17 significant digits: enough to reproduce every breach decision exactly."""
    fc.to_csv(path, float_format="%.17g")


def load_forecasts(path) -> pd.DataFrame:
    """Read forecasts written by save_forecasts bit for bit (round-trip float parsing, dates parsed)."""
    fc = pd.read_csv(path, index_col=0, parse_dates=True, float_precision="round_trip")
    for col in ("train_start", "train_end", "refit_train_end"):
        if col in fc:
            fc[col] = pd.to_datetime(fc[col])
    return fc


def breach_summary(fc: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    """
    Raw breach counts per method and level over [start, end] (the dashboard's
    backtest date range), on days with a forecast only.  Formal tests
    (Kupiec, Christoffersen, traffic light) are Validation's; this is only the
    count they start from.
    """
    fc = fc.loc[start:end]
    losses = -fc["return"]
    rows = []
    for col in (c for c in fc.columns if c.startswith("var_")):
        method, level = col[len("var_"):].rsplit("_", 1)
        alpha = float(level) / 100
        ok = fc[col].notna()
        hits = losses[ok] > fc.loc[ok, col]
        rows.append({"method": method, "alpha": alpha, "days": int(ok.sum()), "missing_days": int((~ok).sum()),
                     "breaches": int(hits.sum()), "breach_pct": 100 * hits.mean() if ok.any() else np.nan,
                     "expected_pct": 100 * (1 - alpha), "expected_breaches": ok.sum() * (1 - alpha)})
    return pd.DataFrame(rows, columns=["method", "alpha", "days", "missing_days", "breaches", "breach_pct",
                                       "expected_pct", "expected_breaches"])
