"""Read-only integrity and cross-artifact checks for a completed submission."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from pypdf import PdfReader
from .config import ROOT
from .portfolio import weight_hash
from .risk import load_forecasts
from .backtest import assess


def verify(run):
    run=Path(run);manifest=json.loads((run/"manifest.json").read_text(encoding="utf-8"))
    bundle=json.loads((run/"submission.json").read_text(encoding="utf-8"));errors=[]
    for name,expected in manifest["files"].items():
        p=run/name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:errors.append("artifact hash: "+name)
    for name,expected in manifest.get("input_hashes",{}).items():
        p=ROOT/name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:errors.append("input hash: "+name)
    for name,expected in manifest.get("source_file_hashes",{}).items():
        p=ROOT/name
        if not p.exists() or hashlib.sha256(p.read_bytes().replace(b"\r\n",b"\n")).hexdigest()!=expected:
            errors.append("source hash: "+name)
    for name,p in bundle["portfolios"].items():
        if not p.get("weights"):continue
        wh=weight_hash(p["weights"])
        if p["weight_hash"]!=wh:errors.append(name+" weights")
        fc=load_forecasts(run/name/"forecasts.csv")
        if not (fc.train_end<fc.index).all():errors.append(name+" timing")
        for saved in p["validation"]:
            current=assess(fc,wh,saved["method"],saved["alpha"],bundle["policy"]["evaluation_start"],bundle["policy"]["snapshot_end"])
            for key in ["days","breaches","zone","coverage","kupiec_p","conditional_coverage_p"]:
                a,b=current.get(key),saved.get(key)
                if a is None and b is None:continue
                if isinstance(a,(int,float)) and isinstance(b,(int,float)):
                    if not np.isclose(a,b,rtol=1e-12,atol=1e-12):errors.append(f"{name} validation {key}")
                elif a!=b:errors.append(f"{name} validation {key}")
        att=p["attribution"]
        if not np.isclose(sum(att["components"].values()),att["es_usd"],atol=1e-6):errors.append(name+" attribution")
    for name,lo,hi in [("investment_memorandum.pdf",7,15),("executive_tear_sheet.pdf",1,1),("committee_memo.pdf",1,1)]:
        pdf=PdfReader(run/"documents"/name)
        if not lo<=len(pdf.pages)<=hi:errors.append(name+" pages")
    chosen=bundle["decision"].get("alternative","selected");p=bundle["portfolios"][chosen]
    report="\n".join(page.extract_text() for page in PdfReader(run/"documents/investment_memorandum.pdf").pages)
    if p["weight_hash"][:12] not in report:errors.append("reported allocation identity")
    if bundle["decision"]["outcome"] not in report:errors.append("reported verdict")
    if errors:raise ValueError("\n".join(errors))
    return {"status":"PASS","allocations":sum(bool(p.get("weights")) for p in bundle["portfolios"].values()),
            "files":len(manifest["files"]),"reported_portfolio":chosen,"decision":bundle["decision"]["outcome"]}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("run");args=parser.parse_args();print(json.dumps(verify(args.run),indent=2))
