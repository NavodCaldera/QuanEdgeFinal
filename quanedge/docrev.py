"""Documentation revision r1 of a frozen run: addenda only, analysis unchanged (task DOC-007).

The parent run's documents and manifest are never rewritten. The revision copies the
parent memorandum and tear sheet, appends or overlays clearly labelled addenda built
from the parent run and the standalone context (quanedge.context), and records its own
hashes and parent identity.

    python -m quanedge.docrev            # build results/docrev/<run>-r1
    python -m quanedge.docrev --verify   # read-only checks of an existing revision
"""
import argparse
import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Frame, Image, KeepInFrame, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle
from . import config, context
from .portfolio import hurdle, weight_hash
from .reporting import fmt

REVISION = "r1"
CHANGES = [
    "Memorandum: two addendum pages appended (return-estimator sensitivity and spending sustainability; standalone long-history context). Parent pages unchanged.",
    "Executive tear sheet: parent page with a labelled revision box added in its unused lower space.",
    "Speaker/Q&A notes: parent notes plus revision questions. The PPTX deck and committee memo are not revised.",
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def styles():
    s = getSampleStyleSheet()      # same palette and body style as quanedge.reporting
    s.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10.5, leading=15, spaceAfter=9, textColor=colors.HexColor("#25364a")))
    s.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=9, leading=12, spaceAfter=4, textColor=colors.HexColor("#25364a")))
    s["Heading1"].textColor = colors.HexColor("#102d45")
    return s


def table(rows, widths, st):
    t = Table([[Paragraph(escape(str(v)), st["Small"]) for v in row] for row in rows], colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eff3")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#75929e")),
                           ("LINEBELOW", (0, 1), (-1, -1), .3, colors.HexColor("#d8e0e5"))]))
    return t


def evidence(run):
    """Every number the addenda quote, read from the parent run and the hash-checked context outputs."""
    bundle = json.loads((run/"submission.json").read_text(encoding="utf-8")); cfg = bundle["policy"]
    out = context.out_dir(); ctx = json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    if ctx["parent_manifest_sha256"] != sha256(run/"manifest.json"):
        raise ValueError("context outputs were built from a different parent run")
    for name, digest in ctx["files"].items():
        if sha256(out/name) != digest:
            raise ValueError(f"context output altered: {name}")
    read = lambda name: pd.read_csv(out/f"{name}.csv")
    reported = bundle["decision"].get("reported_portfolio", bundle["decision"].get("alternative", "selected"))
    for name in dict.fromkeys(["selected", reported]):
        p = bundle["portfolios"][name]
        if weight_hash(p["weights"]) != p["weight_hash"]:
            raise ValueError(f"{name}: weight hash mismatch")
    survival = json.loads((run/"survival.json").read_text(encoding="utf-8"))
    return {"bundle": bundle, "cfg": cfg, "reported": reported, "h": hurdle(cfg["inflation"], cfg["spending"]), "ctx": ctx,
            "sens": read("estimator_sensitivity"), "coverage": read("coverage"), "drawdowns": read("drawdowns"),
            "dotcom": read("dotcom_partial"), "overlap": read("overlap_check"), "windows": read("risk_windows"),
            "survival": {"selected": survival["selected"]["results"],
                         reported: bundle["portfolios"][reported]["real_capital_survival"]["results"]}}


def deeper_before_2005(e):
    """ETFs whose full-history maximum drawdown is deeper than the one inside the frozen sample."""
    dd = e["drawdowns"].set_index(["ticker", "sample"])
    return [t for t in e["coverage"].ticker if dd.loc[(t, "full history"), "max_drawdown"] < dd.loc[(t, "since 2005"), "max_drawdown"] - 1e-9]


def listed(items):
    items = list(items)
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else "".join(items)


def geometric(e, name, shrink):
    s = e["sens"]; rows = s[(s.portfolio == name) & (s.mean_shrinkage == shrink)].set_index("lookback_years")
    return rows.loc[["5", "10", "all"], "expected_geometric"]


def sensitivity_chart(e, path):
    h = e["h"]; labels = ["5 years", "10 years", "Full sample"]; x = range(3)
    series = [(f"{e['reported']}, raw means", geometric(e, e["reported"], 0.), "#9bb6c4"),
              (f"{e['reported']}, frozen {e['cfg']['mean_shrinkage']:.0%} shrinkage", geometric(e, e["reported"], e["cfg"]["mean_shrinkage"]), "#176f83"),
              ("Original W_rec, raw means", geometric(e, "selected", 0.), "#c98b3b")]
    fig, ax = plt.subplots(figsize=(8, 2.9))
    for i, (label, values, colour) in enumerate(series):
        ax.bar([v + (i - 1)*.26 for v in x], 100*values.to_numpy(), .25, label=label, color=colour)
    ax.axhline(100*h, color="#8a2b2b", ls="--", lw=1.2); ax.text(-.45, 100*h + .15, f"Hurdle {h:.2%}", ha="left", fontsize=8, color="#8a2b2b")
    ax.set_xticks(list(x), labels); ax.set_ylabel("Expected geometric return (%)"); ax.grid(axis="y", alpha=.2)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left", ncol=3, bbox_to_anchor=(0, 1.16))
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)


def addendum_text(e):
    cfg, h, rep = e["cfg"], e["h"], e["reported"]
    pct = lambda v: fmt(float(v), "pct"); usd = lambda v: fmt(float(v), "usd")
    raw, frozen = geometric(e, rep, 0.), geometric(e, rep, cfg["mean_shrinkage"])
    quarter, orig_raw = geometric(e, rep, .25), geometric(e, "selected", 0.)
    surv_rep, surv_sel = e["survival"][rep], e["survival"]["selected"]
    weights = " · ".join(f"{t} {v:.0%}" for t, v in e["bundle"]["portfolios"][rep]["weights"].items() if v)
    dd = e["drawdowns"].set_index(["ticker", "sample"]); cov = e["coverage"].set_index("ticker")
    deeper = deeper_before_2005(e)
    same = [t for t in cov.index if t not in deeper and cov.loc[t, "omitted_before_frozen_start"] > 0]
    dc = e["dotcom"]; dc_sel, dc_rep = dc[dc.portfolio == "selected"], dc[dc.portfolio == rep]
    def observed(rows):
        seen = rows[rows.observed]
        return seen.weight.sum(), seen.sleeve_loss_usd.sum(), listed(rows[~rows.observed].ticker)
    sel_w, sel_loss, sel_missing = observed(dc_sel); rep_w, rep_loss, rep_missing = observed(dc_rep)
    win = e["windows"]; es = lambda name: win[(win.portfolio == name) & (win.method == "historical")].set_index("window").es_usd
    budget = cfg["es_budget"]*cfg["value"]
    page1 = [
        f"Documentation revision {REVISION} of run {e['bundle']['metadata']['run_id']}. These addenda disclose evidence that qualifies the frozen recommendation. "
        "They change no data, weights, forecasts, gates or verdict; the pages above are the parent memorandum unchanged.",
        f"C3 compares expected geometric return after the {cfg['cost']*cfg['expected_annual_turnover']:.2%} cost reserve with the {pct(h)} hurdle. "
        f"For the proposed adjustment {rep} ({weights}), the frozen estimator gives {pct(frozen['all'])} on the full sample, so C3 passes. "
        f"On raw historical means the same weights give {pct(raw['5'])} (5 years), {pct(raw['10'])} (10 years) and {pct(raw['all'])} (full sample): below the hurdle in every window. "
        f"At 25% shrinkage the estimate is {pct(quarter.min())} to {pct(quarter.max())}, at the hurdle. The return conclusion depends materially on the estimation assumption.",
        f"Why: the frozen estimator moves each ETF's annual mean {cfg['mean_shrinkage']:.0%} of the way toward the seven-ETF average. Equities pull that average up, so AGG's "
        f"estimate rises; with {e['bundle']['portfolios'][rep]['weights']['AGG']:.0%} in AGG the portfolio estimate rises with it. Raw means are an alternative estimate, not the truth: "
        "short windows are noisy and each window reflects its own interest-rate regime. Neither is a forecast.",
        f"The original W_rec clears the hurdle on raw means too ({pct(orig_raw.min())} to {pct(orig_raw.max())}). The adjustment therefore trades the GFC drawdown failure of W_rec "
        "for a return objective that fails on raw means and is marginal at 25% shrinkage. The recomputation used here reproduces the run's exported sensitivity file exactly before adding W_rec rows.",
        f"Spending sustainability points the same way. Under the documented resampled-history simulation, the probability that after-spending NAV ends below USD 10 million "
        f"grown with CPI is {pct(surv_rep[0]['shortfall_probability'])} at five years and {pct(surv_rep[-1]['shortfall_probability'])} at ten for {rep}, against "
        f"{pct(surv_sel[0]['shortfall_probability'])} and {pct(surv_sel[-1]['shortfall_probability'])} for W_rec. Shortfall means failing to preserve real capital, not exhausting the fund. "
        "These paths are illustrative, not calibrated forecasts.",
        "Owner decision points: whether the adjustment's lower drawdown justifies a return objective that fails under raw means; whether a lower spending rate (A3) or a different "
        "allocation should be evaluated in a new, separately identified run. The recorded C3 result and Adjust verdict stand as computed.",
    ]
    if deeper != ["XLK"]:
        raise ValueError(f"addendum text assumes only XLK has a deeper pre-2005 drawdown; data shows {deeper}")
    xlk_full, xlk_2005 = dd.loc[("XLK", "full history")], dd.loc[("XLK", "since 2005")]
    page2 = [
        f"{context.LABEL} Yahoo Finance via yfinance, auto-adjusted closes, retrieved {e['ctx'].get('created_at_utc', '')[:10]} from each ETF's first available price through "
        f"{context.SNAPSHOT_END}. No pre-launch prices, zero-filled returns or proxies. Over the frozen sample's dates the two snapshots' daily returns differ by at most "
        f"{e['overlap'].max_abs_difference.max():.1e}.",
        f"Only XLK has a deeper drawdown before 2005: {pct(xlk_full.max_drawdown)} from {xlk_full.peak} to {xlk_full.trough}, recovered {xlk_full.recovery} after "
        f"{xlk_full.under_water_years:.1f} years, against {pct(xlk_2005.max_drawdown)} since 2005. For {listed(same)}, the pre-2005 observations contain no deeper drawdown than the one already in the frozen sample. "
        "Full-history tables omit nothing; first-price dates come from the data, not issuer launch announcements.",
        f"The dot-com crash cannot be replayed for either portfolio because {sel_missing} did not yet trade. Buy-and-hold over {dc.window.iloc[0].split(' ', 3)[-1]}, "
        f"the observed sleeves of W_rec ({pct(sel_w)} of NAV: SPY and XLK) lost {usd(sel_loss)}, {pct(sel_loss/cfg['value'])} of NAV, before any AGG/GLD result. "
        f"For {rep} the observed SPY sleeve ({pct(rep_w)} of NAV) lost {usd(rep_loss)}; {rep_missing} ({pct(1 - rep_w)}) are unobserved. These are partial sleeve losses, not portfolio losses, "
        "and not tests of the 20% limit.",
        f"Descriptive window sensitivity (fixed weights, historical one-day ES99, no traffic lights): {rep} {usd(es(rep).min())} to {usd(es(rep).max())} across 3-year, 5-year, "
        f"10-year and full common windows; W_rec {usd(es('selected').min())} to {usd(es('selected').max())} against the {usd(budget)} budget, which C2 measures on each "
        "allocation's own estimation sample. Recent windows are not more reliable by construction.",
    ]
    return page1, page2


def build(run, out):
    e = evidence(run); st = styles(); out.mkdir(parents=True, exist_ok=True)
    rep, h = e["reported"], e["h"]
    page1, page2 = addendum_text(e)
    chart = out/"estimator_sensitivity.png"; sensitivity_chart(e, chart)
    parent_memo = PdfReader(run/"documents/investment_memorandum.pdf"); offset = len(parent_memo.pages)
    run_id = e["bundle"]["metadata"]["run_id"]
    def footer(c, doc):
        c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#567080"))
        c.drawString(42, 24, f"Ghosted | {run_id} | documentation revision {REVISION} | Owner review pending")
        c.drawRightString(A4[0] - 42, 24, str(offset + doc.page))
    pct = lambda v: fmt(float(v), "pct")
    sens_rows = [["Window", f"{rep} raw means", f"{rep} frozen shrinkage", "W_rec raw means", "Hurdle"]]
    for key, label in [("5", "5 years"), ("10", "10 years"), ("all", "Full sample")]:
        sens_rows.append([label, pct(geometric(e, rep, 0.)[key]), pct(geometric(e, rep, e["cfg"]["mean_shrinkage"])[key]), pct(geometric(e, "selected", 0.)[key]), pct(h)])
    dd = e["drawdowns"].set_index(["ticker", "sample"]); cov = e["coverage"].set_index("ticker")
    dd_rows = [["ETF", "First price", "Days pre-2005", "Dot-com", "Max DD full", "Peak to trough (full)", "Max DD since 2005", "Worst day"]]
    for t in cov.index:
        full = dd.loc[(t, "full history")]
        dd_rows.append([t, cov.loc[t, "first_price_date"], f"{cov.loc[t, 'omitted_before_frozen_start']:,}", cov.loc[t, "Dot-com bear market"],
                        pct(full.max_drawdown), f"{full.peak} to {full.trough}", pct(dd.loc[(t, "since 2005"), "max_drawdown"]),
                        f"{pct(full.worst_daily_return)} {full.worst_daily_date}"])
    story = [Paragraph(f"Addendum A ({REVISION}): return-estimator sensitivity and spending sustainability", st["Heading1"])]
    story += [Paragraph(escape(t), st["Body"]) for t in page1[:3]]
    story += [table(sens_rows, [80, 105, 120, 105, 60], st), Image(str(chart), width=500, height=181)]
    story += [Paragraph(escape(t), st["Body"]) for t in page1[3:]]
    story += [PageBreak(), Paragraph(f"Addendum B ({REVISION}): what earlier ETF history shows", st["Heading1"])]
    story += [Paragraph(escape(page2[0]), st["Body"]), table(dd_rows, [34, 64, 54, 48, 48, 100, 56, 107], st)]
    story += [Paragraph(escape(t), st["Body"]) for t in page2[1:]]
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42,
                      title="Investment memorandum addendum").build(story, onFirstPage=footer, onLaterPages=footer)
    addendum = PdfReader(buffer)
    if len(addendum.pages) != 2:
        raise ValueError(f"addendum must be two pages, got {len(addendum.pages)}")
    memo = PdfWriter()
    for p in list(parent_memo.pages) + list(addendum.pages):
        memo.add_page(p)
    with (out/"investment_memorandum.pdf").open("wb") as f:
        memo.write(f)
    parent_md = (run/"documents/investment_memorandum.md").read_text(encoding="utf-8")
    md_tables = "\n".join("| " + " | ".join(map(str, r)) + " |" + ("\n|" + "---|"*len(r) if i == 0 else "") for i, r in enumerate(sens_rows))
    (out/"investment_memorandum.md").write_text(parent_md.rstrip() + f"\n\n## Addendum A ({REVISION}): return-estimator sensitivity and spending sustainability\n\n"
        + "\n\n".join(page1) + "\n\n" + md_tables + f"\n\n## Addendum B ({REVISION}): what earlier ETF history shows\n\n" + "\n\n".join(page2) + "\n",
        encoding="utf-8", newline="\n")
    tear_sheet(run, out, e, st)
    notes = (run/"documents/speaker_qa_notes.md").read_text(encoding="utf-8").rstrip()
    qa = [("Does the return objective depend on your estimator?", page1[1] + " " + page1[2]),
          ("Why not use each ETF's full history?", "Every decision uses one aligned 2005-2026 panel so means, covariances and joint tails come from the same dates. " + page2[1]),
          ("What would the dot-com crash have done to your portfolio?", page2[2]),
          ("Is the spending rate sustainable?", page1[4])]
    (out/"speaker_qa_notes.md").write_text(notes + f"\n\n## Revision {REVISION} questions\n\nAdded after preregistration; the frozen verdict is unchanged.\n\n"
        + "\n\n".join(f"### {q}\n\n{a}" for q, a in qa) + "\n", encoding="utf-8", newline="\n")
    counts = {p.name: len(PdfReader(p).pages) for p in out.glob("*.pdf")}
    (out/"page_counts.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    files = sorted(p.name for p in out.iterdir() if p.is_file() and p.name != "revision.json")
    record = {"revision": REVISION, "label": "Documentation revision; analysis unchanged; added after preregistration",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "git_head_at_build": revision,
              "parent_run": run_id, "parent_manifest_sha256": sha256(run/"manifest.json"),
              "parent_documents": {n: sha256(run/"documents"/n) for n in ["investment_memorandum.pdf", "executive_tear_sheet.pdf", "speaker_qa_notes.md"]},
              "context_manifest_sha256": sha256(context.out_dir()/"manifest.json"), "reported_portfolio": rep,
              "reported_weight_hash": e["bundle"]["portfolios"][rep]["weight_hash"], "verdict": e["bundle"]["decision"]["outcome"],
              "changes": CHANGES, "page_counts": counts, "files": {n: sha256(out/n) for n in files}}
    (out/"revision.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return verify(out, run)


def tear_sheet(run, out, e, st):
    """Overlay a labelled revision box on the parent tear sheet's unused lower space."""
    rep, h, cfg = e["reported"], e["h"], e["cfg"]
    raw = geometric(e, rep, 0.); dd = e["drawdowns"].set_index(["ticker", "sample"])
    dc = e["dotcom"]; missing = listed(dc[(dc.portfolio == rep) & ~dc.observed].ticker)
    deeper = deeper_before_2005(e)
    pct = lambda v: fmt(float(v), "pct")
    lines = [f"<b>Documentation revision {REVISION}: disclosures added after preregistration; frozen analysis and verdict unchanged.</b>",
             f"Return objective: C3 passes under the frozen {cfg['mean_shrinkage']:.0%} mean shrinkage ({pct(geometric(e, rep, cfg['mean_shrinkage'])['all'])} vs the {pct(h)} hurdle). "
             f"On raw historical means this allocation gives {pct(raw.min())} to {pct(raw.max())}, below the hurdle in every 5-year, 10-year and full-sample window. "
             "Shrinkage toward the seven-ETF average raises AGG's estimate.",
             "Long history: " + "; ".join(f"{t} fell {pct(-dd.loc[(t, 'full history'), 'max_drawdown'])} from {dd.loc[(t, 'full history'), 'peak']} to {dd.loc[(t, 'full history'), 'trough']}" for t in deeper)
             + "; no other ETF shows a deeper pre-2005 drawdown. "
             f"The dot-com crash cannot be replayed for this allocation because {missing} did not yet trade. Shortfall above means real capital not preserved, not fund exhaustion."]
    flow = [Paragraph(t, st["Small"]) for t in lines]
    height = sum(f.wrap(A4[0] - 104, 1000)[1] + st["Small"].spaceAfter for f in flow) + 10
    if height > 150:                         # parent content ends about 212 pt above the page bottom
        raise ValueError("revision box overflows the tear sheet's free space")
    buffer = io.BytesIO(); c = rl_canvas.Canvas(buffer, pagesize=A4)
    c.setStrokeColor(colors.HexColor("#b07a2a")); c.setLineWidth(.8); c.rect(42, 46, A4[0] - 84, height + 4)
    frame = Frame(48, 48, A4[0] - 96, height, leftPadding=4, rightPadding=4, topPadding=4, bottomPadding=2, showBoundary=0)
    frame.addFromList(flow, c)
    if flow:
        raise ValueError("revision box overflows the tear sheet's free space")
    c.save()
    page = PdfReader(run/"documents/executive_tear_sheet.pdf").pages[0]
    page.merge_page(PdfReader(buffer).pages[0])
    writer = PdfWriter(); writer.add_page(page)
    with (out/"executive_tear_sheet.pdf").open("wb") as f:
        writer.write(f)


def verify(out, run):
    """Read-only: parent identity, own hashes, page limits and unchanged parent pages."""
    record = json.loads((out/"revision.json").read_text(encoding="utf-8")); errors = []
    if record["parent_manifest_sha256"] != sha256(run/"manifest.json"):
        errors.append("parent manifest changed")
    for name, digest in record["parent_documents"].items():
        if sha256(run/"documents"/name) != digest:
            errors.append("parent document changed: " + name)
    for name, digest in record["files"].items():
        if not (out/name).exists() or sha256(out/name) != digest:
            errors.append("revision file hash: " + name)
    memo, parent = PdfReader(out/"investment_memorandum.pdf"), PdfReader(run/"documents/investment_memorandum.pdf")
    if not 7 <= len(memo.pages) <= 15:
        errors.append("memorandum pages")
    if any(memo.pages[i].extract_text() != p.extract_text() for i, p in enumerate(parent.pages)):
        errors.append("parent memorandum pages altered")
    if len(PdfReader(out/"executive_tear_sheet.pdf").pages) != 1:
        errors.append("tear sheet pages")
    text = "\n".join(p.extract_text() for p in memo.pages)
    if record["reported_weight_hash"][:12] not in text or record["verdict"] not in text:
        errors.append("reported allocation identity or verdict missing")
    if errors:
        raise ValueError("\n".join(errors))
    return {"status": "PASS", "revision": record["revision"], "parent_run": record["parent_run"], "page_counts": record["page_counts"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default=None, help="parent run folder (default: results/latest.txt)")
    parser.add_argument("--verify", action="store_true", help="check an existing revision without rebuilding")
    args = parser.parse_args()
    root = config.ROOT
    run = root/"results"/(args.run or (root/"results/latest.txt").read_text(encoding="utf-8").strip())
    out = root/"results/docrev"/f"{run.name}-{REVISION}"
    print(json.dumps(verify(out, run) if args.verify else build(run, out), indent=2))
