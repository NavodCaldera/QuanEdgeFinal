"""Freeze dividends/unadjusted prices for yield, and explicit source metadata."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from ..config import DATA_DIR,START_DATE,END_DATE,TICKERS


def run():
    import yfinance as yf
    raw_dir=DATA_DIR/"raw";raw_dir.mkdir(exist_ok=True,parents=True)
    dest=raw_dir/"distributions.csv"
    if not dest.exists():
        raw=yf.download(TICKERS,start=START_DATE,end=END_DATE,auto_adjust=False,actions=True,progress=False)
        frames=[]
        for ticker in TICKERS:
            for field in ["Close","Dividends"]:
                if field not in raw.columns.get_level_values(0):raise ValueError(f"Missing {field}")
            frames.append(pd.DataFrame({"date":raw.index,"ticker":ticker,"close":raw["Close"][ticker].to_numpy(),
                                        "dividend":raw["Dividends"][ticker].to_numpy()}))
        pd.concat(frames).to_csv(dest,index=False)
        (raw_dir/"distributions.meta.json").write_text(json.dumps({"source":"Yahoo Finance via yfinance, auto_adjust=False, actions=True",
            "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"requested_start":START_DATE,
            "requested_end_exclusive":END_DATE,"yfinance_version":yf.__version__},indent=2),encoding="utf-8")
    evidence=[]
    for p in raw_dir.glob("*.csv"):
        evidence.append({"file":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                         "source":"FRED" if p.name.startswith("fred_") else "World Bank" if p.name.startswith("worldbank_") else "Yahoo Finance",
                         "snapshot_write_time_utc":datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
                         "timestamp_note":"file write time; original ingestion did not separately record HTTP retrieval timestamp"})
    (raw_dir/"source_inventory.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")


if __name__=="__main__":run()
