"""Plot the seven ETF adjusted prices from the frozen competition snapshot.

This chart is descriptive and does not alter the training data or final run.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/clean/prices_clean.csv"
OUTPUT = ROOT / "results/charts/seven_etf_adjusted_prices_1995_to_today.png"
TICKERS = ("SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK")


def main() -> None:
    prices = pd.read_csv(SOURCE, index_col="Date", parse_dates=True)
    missing = set(TICKERS) - set(prices.columns)
    if missing or prices.empty or prices[list(TICKERS)].isna().any().any():
        raise ValueError(f"Invalid frozen price snapshot; missing columns: {sorted(missing)}")
    if not prices.index.is_monotonic_increasing or prices.index.has_duplicates:
        raise ValueError("Price dates must be unique and increasing")

    fig, axes = plt.subplots(4, 2, figsize=(15, 12), sharex=True)
    colors = plt.get_cmap("tab10").colors
    for i, ticker in enumerate(TICKERS):
        ax = axes.flat[i]
        ax.plot(prices.index, prices[ticker], color=colors[i], linewidth=1.15)
        ax.set_title(ticker, loc="left", fontweight="bold")
        ax.set_ylabel("USD, adjusted")
        ax.grid(alpha=0.22)
        ax.set_xlim(pd.Timestamp("1995-01-01"), pd.Timestamp(date.today()))
        ax.xaxis.set_major_locator(mdates.YearLocator(5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes.flat[-1].axis("off")
    fig.suptitle("Seven ETF adjusted prices | 1995 to today", fontsize=16, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.93, bottom=0.12, hspace=0.38, wspace=0.23)
    fig.text(
        0.5, 0.045,
        f"Verified snapshot: {prices.index.min():%d %b %Y}–{prices.index.max():%d %b %Y}. "
        "Blank periods have no verified prices in this dataset. Source: Yahoo Finance via yfinance; "
        "dividend/split-adjusted close. No pre-inception prices or proxies shown.",
        ha="center", fontsize=9,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
