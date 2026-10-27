"""Formal sequential forecast validation; no inherited portfolio results."""
import numpy as np
import pandas as pd
from scipy.stats import chi2, binomtest
from scipy.special import xlogy


def loglike(k,n,p):
    return float(xlogy(k,p)+xlogy(n-k,1-p))


def exception_tests(hits,alpha=.99):
    x=np.asarray(hits,bool);n=len(x);k=int(x.sum())
    if not n:return {"status":"unavailable","days":0}
    lr=max(0.,2*(loglike(k,n,k/n)-loglike(k,n,1-alpha)))
    counts=[int(np.sum((x[:-1]==a)&(x[1:]==b))) for a,b in [(0,0),(0,1),(1,0),(1,1)]]
    a,b,c,d=counts; independence=None
    if a+b>0 and c+d>0:
        ll=loglike(b,a+b,b/(a+b))+loglike(d,c+d,d/(c+d))
        null=loglike(b+d,n-1,(b+d)/(n-1))
        independence=max(0.,2*(ll-null))
    return {"status":"ok" if independence is not None else "inconclusive transitions","days":n,"breaches":k,
            "expected_breaches":n*(1-alpha),"kupiec_lr":lr,"kupiec_p":float(chi2.sf(lr,1)),
            "transitions":counts,"independence_lr":independence,
            "independence_p":float(chi2.sf(independence,1)) if independence is not None else None,
            "conditional_coverage_p":float(chi2.sf(lr+independence,2)) if independence is not None else None,
            "binomial_p":float(binomtest(k,n,1-alpha).pvalue)}


def assess(fc,weight_hash,method="fhs",alpha=.99,start=None,end=None):
    if "weight_hash" not in fc or not (fc.weight_hash==weight_hash).all():
        raise ValueError("forecast weight hash mismatch")
    frame=fc.loc[start:end];col=f"var_{method}_{alpha*100:g}"
    if col not in frame:return {"status":"unavailable","coverage":0,"zone":"unavailable"}
    good=np.isfinite(frame[col]) & np.isfinite(frame["return"])
    hits=(-frame["return"]>frame[col]).where(good)
    result=exception_tests(hits.dropna().astype(bool).to_numpy(),alpha)
    # Do not bridge transitions across missing forecasts.
    if not good.all():
        pairs=good & good.shift(1,fill_value=False)
        counts=[int(((hits.shift(1)==a)&(hits==b)&pairs).sum()) for a,b in [(False,False),(False,True),(True,False),(True,True)]]
        a,b,c,d=counts
        ind=None
        if a+b and c+d:
            total=a+b+c+d
            ind=max(0.,2*(loglike(b,a+b,b/(a+b))+loglike(d,c+d,d/(c+d))-loglike(b+d,total,(b+d)/total)))
        result.update(transitions=counts,independence_lr=ind,
                      independence_p=float(chi2.sf(ind,1)) if ind is not None else None,
                      conditional_coverage_p=float(chi2.sf(result.get("kupiec_lr",0)+ind,2)) if ind is not None else None)
    last=hits.iloc[-250:]
    zone="unavailable"
    if alpha==.99 and len(last)==250 and last.notna().all():
        k=int(last.sum());zone="green" if k<=4 else "yellow" if k<=9 else "red"
    valid_windows=hits.rolling(250,min_periods=250).sum().dropna()
    result.update(coverage=float(good.mean()) if len(good) else 0,missing_days=int((~good).sum()),zone=zone,
                  red_window_share=float((valid_windows>=10).mean()) if alpha==.99 and len(valid_windows) else None,
                  weight_hash=weight_hash,method=method,alpha=alpha)
    return result


def model_pass(result):
    return bool(result.get("coverage",0)>=.95 and result.get("zone") in ("green","yellow") and
                (result.get("kupiec_p") or 0)>.05 and (result.get("conditional_coverage_p") or 0)>.05)


def verdict(checks,alternatives=()):
    required=("C1","C2","C3","C4","C5")
    if any(checks.get(k) is None for k in required) or checks.get("C4") is not True:
        return {"outcome":"evaluation incomplete","action":"Complete matching evidence or validate a risk model before committing capital."}
    if all(checks[k] for k in required):
        return {"outcome":"Accept","action":"Implement the proposed allocation subject to owner review and monitoring."}
    for name,alt in alternatives:
        if any(alt.get(k) is None for k in required) or alt.get("C4") is not True:
            return {"outcome":"evaluation incomplete","action":f"Complete {name} evaluation before deciding."}
        if all(alt[k] for k in required):
            return {"outcome":"Adjust","alternative":name,"action":f"Adopt {name} only after owner review of the stated trade-off."}
    if not alternatives:return {"outcome":"evaluation incomplete","action":"Evaluate the frozen adjustment set before Reject."}
    return {"outcome":"Reject","action":"Decline the original mandate; explain the infeasible risk, return or stress requirements."}
