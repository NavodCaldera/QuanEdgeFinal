"""Rank non-overlapping underwater episodes in the standalone ETF snapshot."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TICKERS = ("SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK")
GFC = ("Global financial crisis: housing/credit collapse, banking stress and recession.", "https://www.federalreservehistory.org/essays/great-recession-and-its-aftermath")
DOTCOM = ("Dot-com bust and early-2000s recession; EFA observes only the later portion.", "https://www.federalreserve.gov/econres/feds/files/2020028pap.pdf")
COVID = ("COVID-19 pandemic and associated market/liquidity disruption.", "https://www.federalreserve.gov/econres/notes/feds-notes/treasury-market-functioning-during-the-covid-19-outbreak-evidence-from-collateral-re-use-20201204.html")
RATES = ("Inflation and rising yields/rates; existing fixed-rate bond values and equity valuations came under pressure.", "https://www.federalreserve.gov/publications/2022-may-financial-stability-report-near-term-risks.htm")
TRADE_COVID = ("Episode spans the 2018 trade-tension period and the 2020 pandemic crash.", "https://www.imf.org/en/Blogs/Articles/2022/10/27/asia-and-the-world-face-growing-risks-from-economic-fragmentation; " + COVID[1])
CONTEXT = {
    ("SPY", 1): GFC, ("SPY", 2): DOTCOM, ("SPY", 3): COVID,
    ("EFA", 1): GFC, ("EFA", 2): TRADE_COVID, ("EFA", 3): DOTCOM,
    ("EEM", 1): GFC,
    ("EEM", 2): ("China property/lockdown stresses and global inflation/monetary tightening.", "https://www.imf.org/en/publications/gfsr/issues/2022/10/11/global-financial-stability-report-october-2022"),
    ("EEM", 3): TRADE_COVID,
    ("AGG", 1): RATES, ("AGG", 2): GFC, ("AGG", 3): COVID,
    ("GLD", 1): ("Multi-year gold bear market; late-stage dollar strength, rate expectations and ETF outflows.", "https://www.sec.gov/Archives/edgar/data/1222333/000119312516423358/d116864dfwp.htm"),
    ("GLD", 2): ("Financial-crisis cash/liquidity demand and dollar strength caused gold selling.", "https://www.gold.org/goldhub/research/gold-investor/gold-investor-february-2019/the-gold-perspective-10-years-after-lehman-brothers-failed"),
    ("GLD", 3): ("Gold correction after January 2026 records; changing sentiment, positioning and profit taking. Source covers H1, not the exact July ETF trough.", "https://www.gold.org/goldhub/research/gold-mid-year-outlook-2026"),
    ("XLE", 1): ("Episode spans the 2014-16 oil collapse and the 2020 pandemic oil-demand shock.", "https://documents1.worldbank.org/curated/en/800281600695886152/pdf/Implications-of-Cheap-Oil-for-Emerging-Markets.pdf"),
    ("XLE", 2): ("Global recession and demand-driven oil collapse during the financial crisis.", "https://www.elibrary.imf.org/view/journals/006/2015/015/article-A001-en.xml"),
    ("XLE", 3): ("Early-2000s recession and equity-market downturn; exact energy-sector causal attribution not established.", DOTCOM[1]),
    ("XLK", 1): DOTCOM, ("XLK", 2): RATES, ("XLK", 3): COVID,
}


def episodes(series):
    series = series.dropna()
    peak_date = series.index[0]
    peak_value = float(series.iloc[0])
    trough_date, trough_value = peak_date, peak_value
    active = False
    rows = []
    for when, value in series.items():
        if value >= peak_value:
            if active:
                rows.append((peak_date, trough_date, when, trough_value / peak_value - 1))
            peak_date, peak_value = when, float(value)
            trough_date, trough_value = when, float(value)
            active = False
        else:
            active = True
            if value < trough_value:
                trough_date, trough_value = when, float(value)
    if active:
        rows.append((peak_date, trough_date, None, trough_value / peak_value - 1))
    return sorted(rows, key=lambda row: row[3])[:3]


def main():
    source = ROOT / "context/raw/prices_full_history.csv"
    manifest = json.loads(source.with_name("manifest.json").read_text())
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != manifest["files"][source.name]:
        raise ValueError("Context snapshot hash mismatch")
    prices = pd.read_csv(source, index_col=0, parse_dates=True)
    rows, averages = [], []
    for ticker in TICKERS:
        series = prices[ticker].dropna()
        completed = []
        for rank, (peak, trough, recovery, depth) in enumerate(episodes(series), 1):
            end = recovery if recovery is not None else series.index[-1]
            years = (end - peak).days / 365.25
            if recovery is not None:
                completed.append(years)
            market_context, source_url = CONTEXT[(ticker, rank)]
            rows.append(dict(ticker=ticker, rank=rank, peak=str(peak.date()),
                             trough=str(trough.date()), drawdown_pct=depth * 100,
                             recovery=str(recovery.date()) if recovery is not None else "",
                             recovered=recovery is not None,
                             peak_to_recovery_years=years if recovery is not None else None,
                             elapsed_years=years,
                             trading_intervals=int(((series.index > peak) & (series.index <= end)).sum()),
                             market_context=market_context, context_source=source_url))
        averages.append(dict(ticker=ticker, completed_episodes=len(completed),
                             selected_episodes=len(episodes(series)),
                             mean_completed_recovery_years=sum(completed) / len(completed) if completed else None))
    output = ROOT / "results/charts"
    output.mkdir(exist_ok=True, parents=True)
    pd.DataFrame(rows).to_csv(output / "etf_top3_drawdowns.csv", index=False)
    pd.DataFrame(averages).to_csv(output / "etf_top3_recovery_averages.csv", index=False)
    (output / "etf_top3_drawdowns.metadata.json").write_text(json.dumps(dict(
        source=str(source.relative_to(ROOT)), source_sha256=digest, as_of=str(prices.index[-1].date()),
        method="Non-overlapping episodes below a running all-time adjusted-price high, ranked by peak-to-trough depth; nested declines are not separate episodes.",
        timing="Calendar years = elapsed calendar days / 365.25; peak uses the most recent equal high before the decline.",
        average="Arithmetic mean of completed peak-to-recovery durations among the three deepest episodes only; unrecovered episodes are excluded and counts disclosed.",
        interpretation="Descriptive nominal adjusted-price history, not recovery forecasts or the frozen portfolio analysis."
    ), indent=2))
    lines = ["# Three deepest ETF drawdown episodes and peak-to-recovery times", "",
             "Snapshot ends 30 September 2026. Non-overlapping episodes; a new episode begins only after the previous peak is regained. Nested crises are not counted twice.", "",
             "Calendar years = days / 365.25. Adjusted prices approximate reinvested nominal returns, with no university withdrawals. Market explanations are sourced context, not identified ETF-specific causal estimates.", "",
             "| ETF | Rank | Peak | Trough | Fall | Recovery | Years | Market context |",
             "|---|---:|---|---|---:|---|---:|---|"]
    for row in rows:
        duration = f"{row['peak_to_recovery_years']:.2f}" if row["recovered"] else f"Unrecovered; {row['elapsed_years']:.2f} elapsed"
        links = ", ".join(f"[source {i}]({url})" for i, url in enumerate(row["context_source"].split("; "), 1))
        lines.append(f"| {row['ticker']} | {row['rank']} | {row['peak']} | {row['trough']} | {row['drawdown_pct']:.2f}% | {row['recovery'] or 'Not recovered'} | {duration} | {row['market_context']} {links} |")
    lines.extend(["", "## Average completed recovery duration among the three selected episodes", "",
                  "Unrecovered episodes are excluded, not assigned zero. This makes averages incomplete and potentially optimistic, especially for AGG. These are not estimates of future recovery times.", "",
                  "| ETF | Completed / selected | Average years |", "|---|---:|---:|"])
    for row in averages:
        lines.append(f"| {row['ticker']} | {row['completed_episodes']} / {row['selected_episodes']} | {row['mean_completed_recovery_years']:.2f} |")
    (output / "etf_top3_drawdowns.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved tables and sourced report to {output}")
    print(pd.DataFrame(averages).to_string(index=False))


if __name__ == "__main__":
    main()
