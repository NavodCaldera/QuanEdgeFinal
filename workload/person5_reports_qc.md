# Person 5: Reports, presentation and quality control

**Mission:** turn the run into documents a committee can act on, keep every number consistent across app, report and deck, and own the final submission. Decision quality is 30% of the rubric and communication 15%, so this role carries much of the score.

## Code and files owned

| Path | Purpose |
|---|---|
| `quanedge/reporting.py` | Generates the memorandum, tear sheet, committee memo, pitch content and Q&A notes from a run |
| `quanedge/verify.py` | Read-only check of hashes, timing, identities, backtests, ES reconciliation and page counts |
| `scripts/build_pitch.mjs` | Builds the PPTX deck from `pitch_content.json` |
| `results/<run_id>/documents/` | `investment_memorandum.pdf/.md`, `executive_tear_sheet.pdf`, `committee_memo.pdf`, `committee_pitch_v2.pptx`, `speaker_qa_notes.md`, `page_counts.json` |
| `README.md` | Setup, reproduce, structure, decision, AI disclosure |
| `PLAN.md` section 18, `AGENTS.md` decision log | Submission checklist and decision record |

## Tasks

### 1. Write the technical report and committee memo
- **Investment memorandum (D3), 7-15 pages** (`reporting.py` enforces the range): mandate and policy, data sources and cleaning (from Person 1), methodology for all five layers, candidate comparison (Person 2), VaR/ES/EVT results and disagreement (Person 3), backtests, stress and risk contributions, recommendation, assumptions and limitations.
- Include the "alternatives considered" paragraph (pairs trading and market-neutral strategies rejected) and the rebalanced versus buy-and-hold figure labelled as policy cost/benefit.
- **One-page committee memo (D4b):** plain English verdict (Accept / Adjust / Reject), answers to the three questions (what can go wrong, how bad, how confident), actions and monitoring triggers.
- Every result carries its evaluation label: retrospective, sequential risk forecast, or post-snapshot monitoring. Never write "genuinely out of sample".

### 2. Prepare the tear sheet and presentation
- **Executive tear sheet (D4a), exactly one page:** recommended weights, key KPIs, ES99 in USD versus budget, worst stress, traffic light, verdict. Readable in under five minutes.
- **Pitch deck (D5), 10-12 minutes:** about 12 slides mirroring the committee memo. Content lives in `pitch_content.json`; build with `scripts/build_pitch.mjs`.
- **Speaker and Q&A notes:** collect the "Questions you must answer" lists from all five workload files, write a short answer for each with the source table, and run at least two rehearsals with judges played by teammates.
- Assign each speaker the section they own (data, portfolio, risk, app demo, recommendation).

### 3. Explain assumptions and limitations
Write the Assumptions & Limitations page (app and report) with Person 4. At minimum:
- Policy assumptions: 4% spending, 2.5% inflation, 6.77% hurdle, USD 250,000 ES99 budget, 20% drawdown limit.
- All historical replays are retrospective; the policy was written knowing 2008 and 2022.
- No untouched historical period exists; post-snapshot data is descriptive only.
- Risk replay is daily rebalanced without costs; performance uses quarterly/drift rebalancing with 5 bp costs.
- Survival simulation is illustrative (about 260 months of history).
- FHS cannot give asset attribution; the budget uses unconditional ES.
- Basel traffic light is a monitoring comparison, not a regulatory requirement.
- Single-run, seven-ETF universe; ETF returns net of fees.

### 4. Check that numbers match across the app, report and presentation
- Run `python -m quanedge.verify results/<run_id>` and fix or escalate every failure.
- Build a number cross-check sheet: for each headline number (weights, verdict, ES99 USD, VaR by method, breach count, Kupiec p, traffic light, worst stress USD, hurdle, survival probabilities), record its value in the run folder, app page, memorandum page, tear sheet, committee memo and slide. All must match.
- Check units on every number (log loss vs percentage vs USD).
- Confirm the run ID and weight hash shown in the app match the documents.
- Regenerate documents only from a completed run; never hand-edit a number in a PDF or slide.

### 5. Maintain the AI-use disclosure and final submission checklist
- **AI-use log:** tool, purpose, which components it produced, and how a human validated them. Collect entries from all five people. Publish the final disclosure in README and the memorandum.
- Record human validation: reviewer name and date for each module (currently pending in `config/final.yaml`).
- **Submission checklist** (`PLAN.md` section 18): repository access for judges, one-command app, 7-15 page report, one-page tear sheet, one-page committee memo, deck, AI disclosure, verdict rule and freeze tag, three questions answered.
- Confirm deadline and eligibility with organisers in writing, and record the answer.
- Final README review: setup, reproduce commands, structure, decision summary and links to every document.

## Handoffs

| From | What |
|---|---|
| Person 1 | Data dictionary, data-quality report, source list |
| Person 2 | Candidate table, KPI definitions, selection rule, hand checks |
| Person 3 | Risk tables, disagreement and threshold explanations, backtest and stress narratives |
| Person 4 | Final run ID, app screenshots, reproduce commands |

## Checks to keep green
- `python -m quanedge.verify results/<run_id>` passes.
- `page_counts.json`: memorandum 7-15 pages, tear sheet and committee memo exactly 1 page.
- The cross-check sheet has no mismatches.

## Done when
- [ ] Memorandum, tear sheet, committee memo, deck and Q&A notes are generated from the final run.
- [ ] Every headline number matches across app, report, tear sheet, memo and deck.
- [ ] Assumptions & Limitations are complete in both the app and the report.
- [ ] AI-use disclosure and human-validation record are final.
- [ ] Submission checklist is fully ticked and the repository is accessible to judges.

## Questions you must answer in Q&A
- What is the verdict, in one sentence, and why not Accept?
- What are the biggest limitations of this analysis?
- What would make the committee change the decision (triggers)?
- Which parts were AI-assisted, and how did you validate them?
- If the survival simulation shows shortfall risk, why still recommend this allocation?
