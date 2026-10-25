"""
Figures for the report and the dashboard.  Every function returns a
matplotlib Figure, so Streamlit can show it with st.pyplot and the run script
can save it; nothing touches pyplot's global state.

One visual language across all figures, from a validated palette:
blue = what actually happened (data, historical simulation), orange = the
normal assumption, aqua = the EVT family, grey = other models as labelled
context.  Only the palette's first three hues ever appear together: that set
stays distinguishable for every pair under red-green colour blindness.  Aqua
is below 3:1 contrast on the light surface, so aqua lines always carry a
direct label.  VaR -> ES is one hue in two shades (light -> dark = deeper
into the tail).
"""
from functools import wraps
import matplotlib
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy import stats
from ..config import PORTFOLIO_VALUE
from .evt import gpd_cdf, gpd_ppf
from .models import LABEL
from .portfolio import loss_fraction

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE, GRID, AXIS = "#fcfcfb", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
VAR_SHADE, ES_SHADE = "#6da7ec", "#184f95"
COLOR = {"historical": BLUE, "normal": ORANGE, "evt": AQUA, "garch_evt": AQUA}

STYLE = {
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "savefig.dpi": 200, "savefig.bbox": "tight",
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.titlecolor": INK, "axes.labelcolor": INK2, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "xtick.color": AXIS, "ytick.color": AXIS, "xtick.labelcolor": MUTED, "ytick.labelcolor": MUTED,
    "lines.linewidth": 1.8, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
    "legend.frameon": False, "legend.fontsize": 8.5, "legend.labelcolor": INK2,
}


def _styled(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with matplotlib.rc_context(STYLE):
            return fn(*args, **kwargs)
    return wrapper


def _usd(x, _=None):
    return f"${x / 1e6:.1f}M" if abs(x) >= 1e6 else f"${x / 1e3:.0f}K"


def _pct(decimals=1):
    return mticker.PercentFormatter(xmax=100, decimals=decimals)


def _dot(ax, x, y, color, size=26, ring=True, **kw):
    """
    Data dot with a surface-coloured ring, so overlapping marks stay legible.
    Dense scatters (hundreds of overlapping points) skip the ring: there the
    rings would paint over each other's fill and wash the cloud out.
    """
    return ax.scatter(x, y, s=size, color=color, edgecolors=SURFACE if ring else "none",
                      linewidths=1.2 if ring else 0, zorder=3, **kw)


def _first_visible(grid, y, floor):
    """Index of the first grid point where curve y is clearly above the axis floor (to anchor a label)."""
    return int(np.argmax(np.asarray(y) >= floor))


def _line_label(ax, x, y, text, dx, dy):
    ax.annotate(text, xy=(x, y), xytext=(dx, dy), textcoords="offset points", color=INK2, fontsize=8,
                va="center", arrowprops=dict(arrowstyle="-", color=AXIS, lw=0.8, shrinkA=0, shrinkB=2))


def _subtitle(ax, text):
    ax.text(0, 1.0, text, transform=ax.transAxes, color=MUTED, fontsize=8, va="bottom")


def _end_labels(ax, ends, x_text, min_gap):
    """Label line ends at x_text, spreading labels at least min_gap apart (data units) with hairline leaders."""
    ends = sorted(ends)                                   # (y, text, x_end)
    placed = []
    for y, _, _ in ends:
        placed.append(y if not placed else max(y, placed[-1] + min_gap))
    shift = (np.mean(placed) - np.mean([e[0] for e in ends])) if placed else 0
    for (y, text, x_end), yp in zip(ends, placed):
        ax.annotate(text, xy=(x_end, y), xytext=(x_text, yp - shift), color=INK2, fontsize=8, va="center",
                    arrowprops=dict(arrowstyle="-", color=AXIS, lw=0.8, shrinkA=0, shrinkB=2))


@_styled
def fig_distribution(r: pd.Series, models: dict) -> Figure:
    """(a) density of daily returns on a log scale against normal and Student-t fits; (b) normal QQ plot."""
    x = 100 * r.to_numpy(dtype=float)
    nm, st = models["normal"], models["student_t"]
    fig = Figure(figsize=(10, 3.9), layout="constrained")
    ax1, ax2 = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.5, 1]})

    dens, edges = np.histogram(x, bins=90, density=True)
    mid, keep = (edges[:-1] + edges[1:]) / 2, dens > 0
    grid = np.linspace(x.min(), x.max(), 600)
    pdf_n = stats.norm.pdf(grid, 100 * nm.mu, 100 * nm.sigma)
    pdf_t = stats.t.pdf(grid, st.nu, 100 * st.loc, 100 * st.scale)
    floor = dens[keep].min() / 4
    _dot(ax1, mid[keep], dens[keep], BLUE, size=20, label="Observed days")
    ax1.plot(grid, pdf_n, color=ORANGE, label="Normal fit")
    ax1.plot(grid, pdf_t, color=MUTED, lw=1.4, label=f"Student-t fit (ν = {st.nu:.1f})")
    ax1.set_yscale("log")
    ax1.set_ylim(floor, dens.max() * 3)
    ax1.xaxis.set_major_formatter(_pct(0))
    ax1.set_xlabel("Daily portfolio return")
    ax1.set_ylabel("Density (log scale)")
    ax1.set_title("(a) Distribution of daily returns", pad=14)
    _subtitle(ax1, f"skewness {stats.skew(x):.2f} · excess kurtosis {stats.kurtosis(x):.1f} "
                   f"(normal: 0 and 0)")
    i = _first_visible(grid, pdf_n, floor * 20)
    _line_label(ax1, grid[i], pdf_n[i], "Normal", 18, -8)
    i = _first_visible(grid, pdf_t, floor * 3)
    _line_label(ax1, grid[i], pdf_t[i], "Student-t", 6, 16)
    ax1.legend(loc="upper right")

    z = np.sort((x - x.mean()) / x.std(ddof=1))
    theo = stats.norm.ppf((np.arange(1, len(z) + 1) - 0.5) / len(z))
    ax2.axline((0, 0), slope=1, color=AXIS, lw=1)
    _dot(ax2, theo, z, BLUE, size=8, ring=False)
    worst = r.idxmin()
    ax2.annotate(f"{worst:%d %b %Y}: {z[0]:.1f}σ", xy=(theo[0], z[0]), xytext=(14, 2),
                 textcoords="offset points", color=INK2, fontsize=8)
    ax2.set_xlabel("Normal quantile (σ)")
    ax2.set_ylabel("Observed quantile (σ)")
    ax2.set_title("(b) Normal QQ plot", pad=14)
    _subtitle(ax2, "points off the line = tails the normal does not expect")
    return fig


@_styled
def fig_threshold(scan: pd.DataFrame, chosen_q: float) -> Figure:
    """EVT threshold diagnostics: mean excess, xi stability, KS distance, with the chosen threshold."""
    q = 100 * scan["q"].to_numpy()
    fig = Figure(figsize=(10, 3.3), layout="constrained")
    ax = fig.subplots(1, 3, sharex=True)
    ax[0].plot(q, 100 * scan["mean_excess"], color=BLUE)
    ax[0].yaxis.set_major_formatter(_pct(2))
    ax[0].set_title("(a) Mean excess loss", pad=14)
    _subtitle(ax[0], "roughly linear once the GPD holds")

    lo, hi = scan["xi"] - 1.96 * scan["xi_se"], scan["xi"] + 1.96 * scan["xi_se"]
    ax[1].fill_between(q, lo, hi, color=BLUE, alpha=0.10, lw=0)
    ax[1].plot(q, scan["xi"], color=BLUE)
    ax[1].set_title("(b) Tail index ξ with 95% interval", pad=14)
    _subtitle(ax[1], "flat once the GPD holds")

    stable = scan["stable"].to_numpy()
    ax[2].plot(q, scan["ks"], color=AXIS, lw=1)
    _dot(ax[2], q[stable], scan["ks"][stable], BLUE, size=22, label="ξ stable")
    _dot(ax[2], q[~stable], scan["ks"][~stable], MUTED, size=22, label="ξ not stable")
    ax[2].set_title("(c) KS distance to fitted GPD", pad=14)
    _subtitle(ax[2], "rule: lowest KS among stable thresholds")
    ax[2].legend(loc="upper left")
    for a in ax:
        a.axvline(100 * chosen_q, color=INK2, lw=1)
        a.set_xlabel("Threshold (percentile of daily losses)")
    ax[1].text(100 * chosen_q, 0.02, f" chosen: {100 * chosen_q:g}th", transform=ax[1].get_xaxis_transform(),
               color=INK2, fontsize=8)
    return fig


@_styled
def fig_evt_fit(evt_model, normal_model) -> Figure:
    """(a) tail probabilities: observed vs GPD vs normal; (b) QQ plot of excesses against the fitted GPD."""
    f, L = evt_model.fit, evt_model.losses
    tail = np.sort(L[L > f.u])
    emp = (len(tail) - np.arange(len(tail))) / len(L)               # share of days with a loss at least this big
    grid = np.linspace(f.u, tail.max() * 1.25, 400)
    fig = Figure(figsize=(10, 3.9), layout="constrained")
    ax1, ax2 = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.5, 1]})

    _dot(ax1, 100 * tail, emp, BLUE, size=10, ring=False, label="Observed days")
    gpd = evt_model.zeta * (1 - gpd_cdf(grid - f.u, f.xi, f.sigma))
    nrm = stats.norm.sf(grid, -normal_model.mu, normal_model.sigma)
    floor = emp.min() / 30
    ax1.plot(100 * grid, gpd, color=AQUA, label="EVT (GPD tail)")
    ax1.plot(100 * grid, nrm, color=ORANGE, label="Normal")
    ax1.set_yscale("log")
    ax1.set_ylim(floor, emp.max() * 2)
    ax1.xaxis.set_major_formatter(_pct(0))
    ax1.set_xlabel("Daily loss")
    ax1.set_ylabel("Probability of a loss at least this large")
    ax1.set_title("(a) Tail of daily losses beyond the threshold", pad=14)
    _subtitle(ax1, f"u = {100 * f.u:.2f}% loss · {f.n_exceed} exceedances · "
                   f"ξ = {f.xi:.2f} (s.e. {f.se[0]:.2f})")
    i = int(len(grid) * 0.85)
    _line_label(ax1, 100 * grid[i], gpd[i], "EVT", 4, 16)
    i = int(np.argmax(nrm < floor * 300))                           # where the normal curve is plunging
    _line_label(ax1, 100 * grid[i], nrm[i], "Normal", 14, 6)
    ax1.legend(loc="upper right")

    y = tail - f.u
    theo = gpd_ppf((np.arange(1, len(y) + 1) - 0.5) / len(y), f.xi, f.sigma)
    ax2.axline((0, 0), slope=1, color=AXIS, lw=1)
    _dot(ax2, 100 * theo, 100 * y, AQUA, size=12, ring=False)
    v = 0.6 * 100 * y.max()
    _line_label(ax2, v, v, "perfect GPD fit", -78, 18)
    ax2.xaxis.set_major_formatter(_pct(0))
    ax2.yaxis.set_major_formatter(_pct(0))
    ax2.set_xlabel("GPD quantile of the excess")
    ax2.set_ylabel("Observed excess over u")
    ax2.set_title("(b) GPD QQ plot of excesses", pad=14)
    _subtitle(ax2, "on the line = the GPD describes the tail")
    return fig


@_styled
def fig_comparison(table: pd.DataFrame, levels=(0.95, 0.99), value: float = PORTFOLIO_VALUE) -> Figure:
    """VaR -> ES per method as a dumbbell, one panel per confidence level: the gap is the point."""
    methods = list(dict.fromkeys(table["method"]))
    y = np.arange(len(methods))[::-1]
    fig = Figure(figsize=(10, 0.42 * len(methods) + 1.5), layout="constrained")
    axes = fig.subplots(1, len(levels), sharey=True, sharex=True)
    for ax, a in zip(np.atleast_1d(axes), levels):
        t = table[table["alpha"] == a].set_index("method").loc[methods]
        ax.hlines(y, t["var_usd"], t["es_usd"], color=AXIS, lw=2, zorder=2)
        _dot(ax, t["var_usd"], y, VAR_SHADE, size=60, label="VaR")
        _dot(ax, t["es_usd"], y, ES_SHADE, size=60, label="Expected Shortfall")
        if "evt" in t.index:
            i = methods.index("evt")
            for col, dy in (("var_usd", -1), ("es_usd", 1)):
                ax.annotate(_usd(t.loc["evt", col]), xy=(t.loc["evt", col], y[i]), xytext=(0, 9 * dy),
                            textcoords="offset points", ha="center", va="center", color=INK2, fontsize=7.5)
        ax.set_title(f"{a:.0%} confidence, one day", pad=6)
        ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(_usd))
        ax.set_xlabel(f"Loss on USD {value / 1e6:.0f}m")
    first = np.atleast_1d(axes)[0]
    first.set_yticks(y, [LABEL.get(m, m) for m in methods])
    first.tick_params(axis="y", labelcolor=INK2, length=0)
    handles, labels = first.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper right", ncols=2)
    return fig


@_styled
def fig_tail_curve(models: dict, value: float = PORTFOLIO_VALUE) -> Figure:
    """VaR as the confidence level rises from 90% to 99.9%: where the models part company."""
    p = np.geomspace(0.10, 0.001, 120)
    featured = [m for m in ("historical", "normal", "evt") if m in models]
    context = [m for m in ("student_t", "mc_t", "garch_evt") if m in models]
    fig = Figure(figsize=(8, 4.4), layout="constrained")
    ax = fig.subplots()
    ends = []
    for m in context + featured:
        v = 100 * loss_fraction(np.array([models[m].var(1 - pi) for pi in p]))
        ax.plot(p, v, color=COLOR.get(m, MUTED) if m in featured else MUTED,
                lw=1.8 if m in featured else 1.1, label=LABEL.get(m, m), zorder=3 if m in featured else 2)
        ends.append((v[-1], f"{LABEL.get(m, m)}  {v[-1]:.1f}%", p[-1]))
    ax.set_xscale("log")
    ax.set_xlim(0.1, 0.00018)                                   # confidence rises to the right; room for labels
    ticks = [0.1, 0.05, 0.01, 0.005, 0.001]
    ax.set_xticks(ticks, [f"{1 - t:.1%}".replace(".0%", "%") for t in ticks])
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.yaxis.set_major_formatter(_pct(0))
    ymax = max(e[0] for e in ends)
    _end_labels(ax, ends, x_text=0.00075, min_gap=0.055 * ymax)
    ax.set_xlabel("Confidence level")
    ax.set_ylabel("One-day VaR (% of portfolio)")
    ax.set_title("VaR by confidence level", pad=14)
    _subtitle(ax, f"USD {value / 1e6:.0f}m portfolio · grey = other models, for context")
    return fig


@_styled
def fig_uncertainty(table: pd.DataFrame, alpha: float = 0.99) -> Figure:
    """Point estimate and 95% bootstrap interval of VaR and ES at one level, per method."""
    t = table[(table["alpha"] == alpha) & table["var_lo"].notna()]
    methods = list(t["method"])
    y = np.arange(len(methods))[::-1]
    fig = Figure(figsize=(10, 0.42 * len(methods) + 1.5), layout="constrained")
    axes = fig.subplots(1, 2, sharey=True)
    for ax, m, title in ((axes[0], "var", "VaR"), (axes[1], "es", "Expected Shortfall")):
        ax.hlines(y, t[f"{m}_lo_usd"], t[f"{m}_hi_usd"], color=BLUE, lw=2, zorder=2)
        _dot(ax, t[f"{m}_usd"], y, BLUE, size=50)
        ax.set_title(f"{alpha:.0%} one-day {title}", pad=14)
        _subtitle(ax, "dot = estimate, line = 95% block-bootstrap interval")
        ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(_usd))
    axes[0].set_yticks(y, [LABEL.get(m, m) for m in methods])
    axes[0].tick_params(axis="y", labelcolor=INK2, length=0)
    return fig


@_styled
def fig_rolling(fc: pd.DataFrame, alpha: float = 0.99, methods=("historical", "garch_evt"),
                zoom=("2020-02-01", "2020-06-30")) -> Figure:
    """Rolling one-day-ahead VaR against realised losses; breach barcode; zoom on one crisis."""
    lvl = f"{alpha * 100:g}"
    loss = -100 * fc["return"]
    fig = Figure(figsize=(10, 6.4), layout="constrained")
    ax1, ax2, ax3 = fig.subplots(3, 1, gridspec_kw={"height_ratios": [2.4, 0.55, 1.9]})
    for ax, d in ((ax1, fc), (ax3, fc.loc[zoom[0]:zoom[1]])):
        l = loss.loc[d.index]
        ax.vlines(d.index, 0, l.clip(lower=0), color=AXIS, lw=0.6 if ax is ax1 else 1.6, label="Daily loss")
        for m in methods:
            v = 100 * d[f"var_{m}_{lvl}"]
            hits = l > v
            name = f"{LABEL.get(m, m)}: {int(hits.sum())} breaches ({100 * hits.mean():.1f}%)" if ax is ax1 \
                else LABEL.get(m, m)
            ax.plot(d.index, v, color=COLOR.get(m, MUTED), lw=1.2 if ax is ax1 else 1.8, label=name)
            if ax is ax3:
                _dot(ax, d.index[hits], l[hits], COLOR.get(m, MUTED), size=24)
        ax.yaxis.set_major_formatter(_pct(0))
        ax.set_ylim(bottom=0)
        loc = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
        ax.grid(axis="x", visible=False)
    ax1.set_title(f"Rolling one-day {alpha:.0%} VaR forecasts vs realised losses", pad=14)
    _subtitle(ax1, f"expected breach rate {100 * (1 - alpha):.0f}% · each forecast uses only earlier data")
    ax1.legend(loc="upper right")
    for k, m in enumerate(methods):
        hits = loss > 100 * fc[f"var_{m}_{lvl}"]
        ax2.vlines(fc.index[hits], k + 0.15, k + 0.85, color=COLOR.get(m, MUTED), lw=1)
    ax2.set_yticks(np.arange(len(methods)) + 0.5, [LABEL.get(m, m) for m in methods])
    ax2.tick_params(axis="y", labelcolor=INK2, length=0)
    ax2.set_ylim(0, len(methods))
    ax2.set_xlim(ax1.get_xlim())
    ax2.grid(False)
    ax2.spines["left"].set_visible(False)
    ax2.xaxis.set_major_formatter(mticker.NullFormatter())
    ax2.set_title("Breach days: clusters are what Christoffersen's test detects", pad=4, fontsize=9)
    ax3.set_title(f"Zoom: {pd.Timestamp(zoom[0]):%b %Y} to {pd.Timestamp(zoom[1]):%b %Y}", pad=6)
    ax3.legend(loc="upper right")
    return fig
