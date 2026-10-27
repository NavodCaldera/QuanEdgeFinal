"""Separate descriptive post-snapshot monitoring; never feeds portfolio selection."""
import argparse
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json
import numpy as np
import pandas as pd
from scipy.stats import binom,binomtest
from .config import ROOT,TICKERS
from .pipeline import git,write_json
from .risk import portfolio_log_returns,rolling_forecasts,save_forecasts


def run(run_id):
    if not git("tag","--list",f"final-run-{run_id}"):
        raise ValueError("Tag the final run before retrieving monitoring data")
    bundle=json.loads((ROOT/"results"/run_id/"submission.json").read_text(encoding="utf-8"));cfg=bundle["policy"]
    chosen=bundle["decision"].get("alternative","selected");rec=bundle["portfolios"][chosen]
    folder=ROOT/"monitoring"/run_id;folder.mkdir(parents=True,exist_ok=True)
    snapshot=folder/"prices.csv"
    if snapshot.exists():raise ValueError("Monitoring snapshot already exists; retained rather than refreshed")
    import yfinance as yf
    end=(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()
    raw=yf.download(TICKERS,start=cfg["snapshot_end"],end=end,auto_adjust=True,progress=False)
    prices=raw["Close"][TICKERS].dropna()
    if len(prices)<2:raise ValueError("No post-snapshot observations available")
    prices.to_csv(snapshot)
    new=prices.pct_change().dropna();new=new.loc[new.index>pd.Timestamp(cfg["snapshot_end"])]
    historical=pd.read_csv(ROOT/"data/clean/simple_returns.csv",index_col=0,parse_dates=True)
    x=pd.concat([historical.tail(cfg["window"]),new]);r=portfolio_log_returns(np.log1p(x),rec["weights"])
    forecast=rolling_forecasts(r,methods=[cfg["primary"],cfg["challenger"]],alphas=[.99],window=cfg["window"],refit=cfg["refit"])
    forecast["weight_hash"]=rec["weight_hash"];forecast["evaluation_label"]="untouched evaluation"
    save_forecasts(forecast,folder/"forecasts.csv")
    rows=[]
    for m in [cfg["primary"],cfg["challenger"]]:
        col=f"var_{m}_99";good=forecast[col].notna();hits=-forecast.loc[good,"return"]>forecast.loc[good,col]
        n=len(hits);k=int(hits.sum())
        rows.append({"method":m,"n":n,"breaches":k,"exact_count_probability":float(binom.pmf(k,n,.01)),
                     "binomial_p":float(binomtest(k,n,.01).pvalue) if n else None,
                     "label":"post-snapshot monitoring, descriptive only; no traffic light"})
    write_json(folder/"summary.json",{"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"source":"Yahoo Finance via yfinance",
               "first":str(new.index.min().date()),"last":str(new.index.max().date()),"weight_hash":rec["weight_hash"],
               "portfolio":chosen,"results":rows,"note":"New-download adjacent price ratios avoid cross-snapshot dividend rescaling. Frozen selection and verdict are unchanged. Conditional parameters refit at monitoring start, then every 21 days."})
    return folder


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("run_id");args=p.parse_args();print(run(args.run_id))
