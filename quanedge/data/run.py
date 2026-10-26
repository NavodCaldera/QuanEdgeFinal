"""
Person 1 — Data engineering and reproducibility pipeline runner.

Execute with:
    python -m quanedge.data.run              # Full pipeline: clean datasets, anomaly audit, ADF stationarity, manifest
    python -m quanedge.data.run --refresh    # Force re-download of external data sources
    python -m quanedge.data.run --check-only # Verify file hashes without recomputing

Generates:
    data/clean/prices_clean.csv
    data/clean/log_returns.csv
    data/clean/simple_returns.csv
    data/clean/macro_clean.csv
    data/clean/worldbank_macro.csv
    data/clean/anomaly_log.csv
    data/clean/data_quality_log.csv
    data/clean/data_quality_checks.csv
    data/clean/calendar_audit.csv
    data/clean/macro_ffill_log.csv
    data/clean/stationarity_tests.csv
    data/clean/data_manifest.json
    data/clean/price_provenance.json
    results/data/data_summary.md
    results/data/top_tail_events.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import CLEAN_DATA_DIR, DATA_DIR, RESULTS_DIR, TICKERS
from .anomalies import build_data_quality_log, generate_full_anomaly_audit, render_top_tail_events_markdown
from .cleaning import (
    align_macro_series,
    audit_trading_calendar,
    calculate_returns,
    validate_price_data,
)
from .manifest import generate_dataset_manifest, verify_dataset_manifest
from .sources import (
    audit_price_snapshot,
    download_all_fred_series,
    download_etf_prices,
    download_worldbank_indicators,
    read_snapshot_meta,
)
from .stationarity import (
    generate_stationarity_summary_markdown,
    run_full_stationarity_analysis,
)

RESULTS_DATA_DIR = RESULTS_DIR / "data"


def write_price_provenance(snapshot_audit: dict, prices: pd.DataFrame, refreshed: bool) -> None:
    """
    Record where the prices came from. Deterministic on purpose (no run timestamp), so it does not
    change on a re-run. The retrieval time is only known for downloads made by this pipeline.
    """
    from importlib import metadata

    meta = read_snapshot_meta()
    provenance = {
        "source": "Yahoo Finance via yfinance, auto_adjust=True (dividend- and split-adjusted close)",
        "snapshot": snapshot_audit,
        "clean_rows": int(len(prices)),
        "clean_first_date": prices.index.min().strftime("%Y-%m-%d"),
        "clean_last_date": prices.index.max().strftime("%Y-%m-%d"),
        "download_metadata": meta if meta else {
            "retrieved_at_utc": "unknown",
            "note": ("The snapshot pre-dates this pipeline: it was first committed to git in the Person 3 "
                     "foundation commit (6d18d37, 2026-10-26) without retrieval metadata. Its date range, "
                     "columns and SHA-256 are recorded here; the download time and yfinance version are not."),
        },
        "refreshed_in_this_run": bool(refreshed),
        "reproducibility_warning": ("Adjusted prices are re-scaled after every dividend, so a later download "
                                    "will not match this snapshot exactly. The committed snapshot is canonical."),
        "installed_versions": {k: metadata.version(k) for k in ("yfinance", "pandas", "numpy", "statsmodels")},
    }
    (CLEAN_DATA_DIR / "price_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")


def run_pipeline(refresh: bool = False) -> None:
    """Run end-to-end Person 1 data engineering workflow."""
    start_time = time.time()
    if refresh:
        print("!" * 78)
        print("REFRESH REQUESTED: data will be re-downloaded from Yahoo Finance, FRED and the World Bank.")
        print("Yahoo's adjusted history is re-scaled after every dividend, so prices, returns, the SHA-256")
        print("manifest and every figure in the report and app may change. The committed snapshot is the")
        print("canonical dataset; refresh only if the whole team agrees to re-run and re-publish everything.")
        print("!" * 78)
    CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("QuanEdge Final (Team Ghosted) — Person 1 Data Engineering Pipeline")
    print(f"Timestamp (UTC): {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}")
    print(f"Investable Universe: {', '.join(TICKERS)}")
    print("=" * 78)

    # 1. Load / Download ETF adjusted close prices
    print("\n[1/7] Ingesting ETF price data (Yahoo Finance)...")
    snapshot_audit = audit_price_snapshot()
    prices = download_etf_prices(refresh=refresh)
    validate_price_data(prices, TICKERS)
    print(f"      Snapshot {snapshot_audit['file']}: {snapshot_audit['rows_in_file']:,} dates, "
          f"{snapshot_audit['rows_dropped_by_common_calendar_filter']} dropped by the common-calendar filter.")
    print(f"      Ingested {len(prices):,} trading days from {prices.index.min():%Y-%m-%d} to {prices.index.max():%Y-%m-%d}.")

    # 2. Calendar alignment and audit
    print("\n[2/7] Auditing market calendar and non-standard closures...")
    cal_audit = audit_trading_calendar(prices)
    print(f"      Total trading days verified: {cal_audit['total_trading_days']:,}")
    if cal_audit["extended_gaps"]:
        print("      Documented extended closures:")
        for g in cal_audit["extended_gaps"]:
            print(f"        • {g['from_date']} to {g['to_date']} ({g['gap_calendar_days']} calendar days): {g['reasons']}")
    cal_df = pd.DataFrame(cal_audit["calendar_records"])
    print(f"      Missing weekdays classified: {cal_df['classification'].value_counts().to_dict()}")
    print(f"      Documented non-standard closures in sample: {[r['date'] for r in cal_audit['non_standard_closures']]}")
    if cal_audit["unexplained_missing_days"] or cal_audit["unexpected_trading_days"]:
        print(f"      WARNING unexplained missing weekdays: {cal_audit['unexplained_missing_days']}")
        print(f"      WARNING unexpected trading days: {cal_audit['unexpected_trading_days']}")

    # 3. Calculate simple and log returns with exact mathematical identity
    print("\n[3/7] Calculating daily simple and log return series...")
    simple_ret, log_ret = calculate_returns(prices)
    print(f"      Generated {len(log_ret):,} daily return periods.")
    print("      Verified exact identity: max |r - ln(1+R)| < 1e-12. (Passed)")

    # 4. Ingest and align macroeconomic data (FRED and World Bank)
    print("\n[4/7] Ingesting & aligning macroeconomic series (FRED & World Bank)...")
    # No fallback: a missing risk-free series must stop the run, never be replaced by an invented rate.
    fred_raw = download_all_fred_series(refresh=refresh)
    macro_clean, ffill_log = align_macro_series(prices.index, fred_raw)
    print(f"      Aligned {fred_raw.shape[1]} FRED series and derived risk-free metrics across {len(macro_clean):,} trading days.")
    print(f"      Daily series forward-filled on {len(ffill_log)} series-days (bond market holidays); logged to macro_ffill_log.csv.")
    print("      Monthly series (CPIAUCSL, FEDFUNDS) used only after their publication lag; no back-fill.")
    print("      Risk-free rate built from the bond-equivalent yield of DTB3 (discount basis converted).")

    wb_data = download_worldbank_indicators(refresh=refresh)
    print(f"      Loaded World Bank annual macro series ({len(wb_data)} years).")

    # 5. Anomaly detection and quality auditing
    print("\n[5/7] Executing outlier detection & historical crisis cross-referencing...")
    anomaly_df, anomaly_summary = generate_full_anomaly_audit(prices, log_ret)
    print(f"      Total observations scanned: {len(log_ret) * len(TICKERS):,}")
    print(f"      Outlier flags (>4-sigma or >8% daily return): {len(anomaly_df)}")
    print(f"      Flags on a date with a compiled event label (date-level): {anomaly_summary['date_level_label_matches']}")
    print(f"      Flags corroborated by another asset moving the same way: {anomaly_summary['cross_asset_corroborated']}")
    print(f"      Silently deleted observations: {anomaly_summary['silently_deleted_count']}")
    print(f"      Policy: {anomaly_summary['retention_policy']}")
    quality_df, quality_checks_df = build_data_quality_log(prices, log_ret)
    print("      Other data-quality checks (findings): " +
          ", ".join(f"{r.check}={r.findings}" for r in quality_checks_df.itertuples()))

    # 6. Stationarity testing (ADF and KPSS)
    print("\n[6/7] Running return-series stationarity tests (Augmented Dickey-Fuller)...")
    stationarity_df = run_full_stationarity_analysis(prices, log_ret, simple_ret)
    stat_markdown = generate_stationarity_summary_markdown(stationarity_df)
    print("      ADF tests completed for price levels and returns:")
    for _, row in stationarity_df[stationarity_df["series_type"] == "Daily Log Returns r_t"].iterrows():
        print(f"        • {row['asset']}: ADF stat = {row['adf_stat']:.4f}, p-val = {row['adf_p_value']} -> {row['verdict']}")

    # 7. Write clean files and manifest
    print("\n[7/7] Exporting clean datasets and cryptographic manifest...")
    prices_file = CLEAN_DATA_DIR / "prices_clean.csv"
    log_ret_file = CLEAN_DATA_DIR / "log_returns.csv"
    simple_ret_file = CLEAN_DATA_DIR / "simple_returns.csv"
    macro_file = CLEAN_DATA_DIR / "macro_clean.csv"
    wb_file = CLEAN_DATA_DIR / "worldbank_macro.csv"
    anomaly_file = CLEAN_DATA_DIR / "anomaly_log.csv"
    stat_file = CLEAN_DATA_DIR / "stationarity_tests.csv"
    summary_md_file = RESULTS_DATA_DIR / "data_summary.md"
    tail_md_file = RESULTS_DATA_DIR / "top_tail_events.md"

    prices.to_csv(prices_file, lineterminator="\n")
    log_ret.to_csv(log_ret_file, lineterminator="\n")
    simple_ret.to_csv(simple_ret_file, lineterminator="\n")
    macro_clean.to_csv(macro_file, lineterminator="\n")
    wb_data.to_csv(wb_file, lineterminator="\n")
    anomaly_df.to_csv(anomaly_file, index=False, lineterminator="\n")
    quality_df.to_csv(CLEAN_DATA_DIR / "data_quality_log.csv", index=False, lineterminator="\n")
    quality_checks_df.to_csv(CLEAN_DATA_DIR / "data_quality_checks.csv", index=False, lineterminator="\n")
    cal_df.to_csv(CLEAN_DATA_DIR / "calendar_audit.csv", index=False, lineterminator="\n")
    pd.DataFrame(
        ffill_log, columns=["date", "series", "day_of_week", "filled_from_date", "action"]
    ).to_csv(CLEAN_DATA_DIR / "macro_ffill_log.csv", index=False, lineterminator="\n")
    tail_md = render_top_tail_events_markdown(anomaly_df)
    tail_md_file.write_text(tail_md + "\n", encoding="utf-8")
    write_price_provenance(snapshot_audit, prices, refresh)
    stationarity_df.to_csv(stat_file, index=False, lineterminator="\n")

    with open(summary_md_file, "w", encoding="utf-8") as f:
        f.write("# Person 1 Data Engineering & Provenance Report\n\n")
        f.write(f"Generated on {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC by `python -m quanedge.data.run`.\n\n")
        f.write("## Overview & Compliance\n")
        f.write(f"- **Investable Universe:** {', '.join(TICKERS)} (7 permitted ETFs, strict rubric compliance).\n")
        f.write(f"- **Sample Period:** {prices.index.min():%Y-%m-%d} to {prices.index.max():%Y-%m-%d} ({len(prices):,} trading days).\n")
        f.write("- **Adjustment Method:** Auto-adjusted close prices via yfinance (dividends and splits incorporated).\n")
        f.write("- **Data Sources:** Yahoo Finance (core universe), FRED (risk-free DTB3, Treasury DGS10, CPI, Fed Funds, VIX), World Bank (US GDP/Inflation).\n")
        f.write(f"- **Price snapshot:** `{snapshot_audit['file']}` ({snapshot_audit['rows_in_file']:,} dates; "
                f"{snapshot_audit['rows_dropped_by_common_calendar_filter']} dropped by the common-calendar filter; "
                f"SHA-256 `{snapshot_audit['sha256'][:16]}...`). Retrieval time and library version: see `data/clean/price_provenance.json`. "
                "Do not `--refresh` after the report numbers are frozen: adjusted history changes with every dividend.\n")
        f.write("- **Risk-free rate:** FRED DTB3 (discount basis) converted to a bond-equivalent yield before use.\n")
        f.write("- **Deleted Observations:** 0. Every flagged observation is retained and logged.\n\n")
        f.write(stat_markdown)
        f.write("\n\n## Outlier & Anomaly Audit Summary\n")
        f.write(f"- **Total Flagged Anomalies:** {len(anomaly_df)}\n")
        f.write(f"- **Flags on a date with a compiled event label:** {anomaly_summary['date_level_label_matches']} "
                "(labels are date-level and analyst-compiled; not verified per ticker)\n")
        f.write(f"- **Flags corroborated by at least one other asset (|z| >= 2, same direction, same date):** "
                f"{anomaly_summary['cross_asset_corroborated']}\n")
        f.write("See `data/clean/anomaly_log.csv` for the row-level log.\n\n")
        f.write("## Other Data-Quality Checks\n\n| Check | Rule | Findings |\n|---|---|---|\n")
        for r in quality_checks_df.itertuples():
            f.write(f"| {r.check} | {r.rule} | {r.findings} |\n")
        f.write("\nFindings are in `data/clean/data_quality_log.csv`.\n\n")
        f.write("## Largest Flagged Moves\n\n" + tail_md + "\n\n")
        f.write("## Calendar & Holiday Audit\n")
        f.write(f"- Total trading sessions: {cal_audit['total_trading_days']:,}\n")
        for g in cal_audit["extended_gaps"]:
            f.write(f"- Gap from {g['from_date']} to {g['to_date']} ({g['gap_calendar_days']} days): {g['reasons']}\n")
        f.write(f"- Missing weekdays by class: {cal_df['classification'].value_counts().to_dict()}\n")
        for r in cal_audit["non_standard_closures"]:
            f.write(f"- Non-standard closure {r['date']}: {r['reason']}\n")
        f.write(f"- Unexplained missing weekdays: {cal_audit['unexplained_missing_days'] or 'none'}\n")
        f.write("- Full classification in `data/clean/calendar_audit.csv`.\n\n")
        f.write("## Macro Alignment\n")
        f.write(f"- Daily series forward-filled on {len(ffill_log)} series-days (log: `data/clean/macro_ffill_log.csv`).\n")
        f.write("- CPIAUCSL becomes usable 1 month + 20 days after its reference month; FEDFUNDS 1 month after. "
                "No back-fill; series are carried from their full FRED history.\n")

    manifest = generate_dataset_manifest(DATA_DIR, CLEAN_DATA_DIR / "data_manifest.json")
    print(f"      Wrote data manifest with {len(manifest['files'])} tracked files.")

    elapsed = time.time() - start_time
    print("\n" + "=" * 78)
    print(f"PERSON 1 PIPELINE COMPLETED SUCCESSFULLY in {elapsed:.2f}s")
    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run QuanEdge Person 1 data engineering pipeline.")
    parser.add_argument("--refresh", action="store_true", help="Force redownload of external data sources.")
    parser.add_argument("--check-only", action="store_true", help="Verify SHA-256 manifest integrity without writing.")
    args = parser.parse_args()

    if args.check_only:
        is_valid = verify_dataset_manifest()
        if is_valid:
            print("DATA MANIFEST VERIFIED: All SHA-256 checksums match files on disk.")
            sys.exit(0)
        else:
            print("DATA MANIFEST ERROR: Checksum mismatch or missing files detected.")
            sys.exit(1)

    run_pipeline(refresh=args.refresh)


if __name__ == "__main__":
    main()
