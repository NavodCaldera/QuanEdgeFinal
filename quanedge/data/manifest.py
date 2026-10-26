"""
Data provenance and cryptographic manifest generator.

Ensures end-to-end reproducibility and data integrity by calculating
SHA-256 checksums, recording exact row counts, date ranges, and software
versions for all raw and cleaned datasets.
"""
from __future__ import annotations

import hashlib
import json
import logging
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..config import CLEAN_DATA_DIR, DATA_DIR, TICKERS

logger = logging.getLogger(__name__)


def _version(package: str) -> str:
    from importlib import metadata
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not installed"


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 cryptographic hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_dataset_manifest(
    data_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, object]:
    """
    Generate complete metadata manifest including SHA-256 checksums,
    row counts, dates, and environment details.
    """
    data_dir = data_dir or DATA_DIR
    clean_dir = data_dir / "clean"
    output_path = output_path or (clean_dir / "data_manifest.json")

    manifest = {
        "manifest_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "team": "Team Ghosted",
        "competition": "SAIFA Quant Edge 1.0",
        "client": "The Serendib University Endowment Fund (USD 10 Million)",
        "workstream": "Person 1 — Data Engineering & Reproducibility Lead",
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
            "yfinance_version": _version("yfinance"),
            "statsmodels_version": _version("statsmodels"),
        },
        "investable_universe": TICKERS,
        "files": {},
    }

    for csv_file in sorted(data_dir.rglob("*.csv")):
        rel_path = str(csv_file.relative_to(data_dir))
        sha = compute_file_sha256(csv_file)
        file_size = csv_file.stat().st_size

        file_meta = {
            "relative_path": rel_path,
            "size_bytes": file_size,
            "sha256": sha,
        }

        try:
            df = pd.read_csv(csv_file, index_col=0)
            file_meta["rows"] = len(df)
            file_meta["columns"] = list(df.columns)
            if isinstance(df.index, pd.DatetimeIndex) or any(k in (df.index.name or "") for k in ["Date", "date", "year"]):
                try:
                    dt_idx = pd.to_datetime(df.index)
                    file_meta["start_date"] = dt_idx.min().strftime("%Y-%m-%d")
                    file_meta["end_date"] = dt_idx.max().strftime("%Y-%m-%d")
                except Exception:
                    pass
        except Exception as e:
            file_meta["inspect_error"] = str(e)

        manifest["files"][rel_path] = file_meta

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Saved data manifest with %d files to %s", len(manifest["files"]), output_path)
    return manifest


def verify_dataset_manifest(manifest_path: Optional[Path] = None, data_dir: Optional[Path] = None) -> bool:
    """
    Verify that files on disk match the recorded SHA-256 checksums in the manifest.
    """
    data_dir = data_dir or DATA_DIR
    manifest_path = manifest_path or (data_dir / "clean" / "data_manifest.json")

    if not manifest_path.exists():
        logger.error("Manifest file does not exist: %s", manifest_path)
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    all_valid = True
    for rel_path, info in manifest.get("files", {}).items():
        file_path = data_dir / rel_path
        if not file_path.exists():
            logger.error("Missing file listed in manifest: %s", file_path)
            all_valid = False
            continue

        disk_sha = compute_file_sha256(file_path)
        if disk_sha != info.get("sha256"):
            logger.error("Checksum mismatch for %s: expected %s, got %s", rel_path, info.get("sha256"), disk_sha)
            all_valid = False

    return all_valid
