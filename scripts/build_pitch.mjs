// Editable committee presentation from the frozen run. Uses the bundled Artifact Tool.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const runtime=process.env.QUANTEDGE_RUNTIME || 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES ||= path.join(runtime,'node/node_modules');
const skill=process.env.QUANTEDGE_PRESENTATION_SKILL || 'C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/presentations';
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation,resolvePresentationFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const root=process.cwd();
const runId=process.argv[2] || (await fs.readFile(path.join(root,'results/latest.txt'),'utf8')).trim();
const run=path.join(root,'results',runId);
const bundle=JSON.parse(await fs.readFile(path.join(run,'submission.json'),'utf8'));
const chosen=bundle.decision.alternative || 'selected';
const rec=bundle.portfolios[chosen];
const capital=rec.real_capital_survival?.results || [];
const build=path.join(root,'.cache','pitch',runId);await fs.mkdir(build,{recursive:true});
const out=path.join(run,'documents');await fs.mkdir(out,{recursive:true});
const font=resolvePresentationFont({fontFamily:'Arial'});
const p=Presentation.create({slideSize:{width:1280,height:720}});
function text(slide,content,x,y,w,h,size=30,bold=false,color='#233d50') {
 const s=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=content;s.text.style={typeface:font,fontSize:size,bold,color};return s;
}
function slide(title,body,notes) {
 const s=p.slides.add();s.background.fill='#F7F9FA';
 text(s,title,64,48,1152,108,46,true,'#102D45');
 if(body)text(s,body,64,190,1152,425,30);
 text(s,`Ghosted · ${bundle.metadata.snapshot_end} · owner review pending`,64,661,1100,32,18,false,'#617886');
 s.speakerNotes.text=notes+'\nEvidence: results/'+runId+'/submission.json and per-allocation files. Authoritative source: Quant edge 1.0 Final Challenge 1.pdf.';
 return s;
}
const money=v=>v==null?'Unavailable':`$${Math.round(v).toLocaleString('en-US')}`;
const pct=v=>v==null?'Unavailable':`${(100*v).toFixed(2)}%`;
slide('Endowment investment decision',`USD 10 million\n${bundle.decision.outcome}\n${bundle.decision.action}`,
 '60 seconds. Lead with the action and the largest reason. This is an algorithmic proposal, not independent human sign-off.');
slide('Spending and capital preservation',`Perpetual endowment, five-year strategic review\n4% annual spending after returns and costs\n2.5% assumed inflation and 6.77% return hurdle\nUSD 250,000 one-day ES99 budget\n20% historical stress/drawdown limit`,
 '55 seconds. Explain (1+inflation)/(1-spending)-1. These are owner-accepted policy assumptions, not competition rules. Each 0.5 percentage point spending change is initially USD 50,000 per year.');
const alloc=slide('Proposed allocation','', '55 seconds. Explain concentration, equity cap, gold cap and bond rate risk. Allocation is W_rec, estimated through snapshot end.');
const values=[['ETF','Weight','Initial exposure'],...Object.entries(rec.weights||{}).map(([t,w])=>[t,pct(w),money(w*1e7)])];
const table=alloc.tables.add({rows:values.length,columns:3,left:64,top:180,width:1152,height:415,values});
for(let r=0;r<values.length;r++)for(let c=0;c<3;c++) {
 const cell=table.getCell(r,c);cell.text.style={typeface:font,fontSize:27,bold:r===0,color:'#102D45'};
 cell.fill=r===0?'#E1EAF0':'#F7F9FA';
}
slide('Data and portfolio accounting','Seven eligible ETFs, adjusted Yahoo closes\n5,470 price dates through 30 September 2026\n242 flagged moves retained\nAggregate simple returns before converting to log\nFRED risk-free rates and CPI with disclosed lags',
 '55 seconds. Explain adjusted closes, no dividend or expense double counting, and why weighted asset log returns are wrong. Contemporary revised macro data is not a vintage archive. Source: data/clean manifests and audits.');
slide('Selection and alternatives','Maximise expected return within historical CVaR99\nCompare minimum CVaR, minimum variance and near-parity\nCompare 40/60, 60/40 and adapted permanent portfolio\nFreeze procedure before current post-training evaluation\nHistorical allocations remain retrospective',
 '60 seconds. Explain mean shrinkage, Ledoit-Wolf, LP objective and secondary CVaR objective. A benchmark gap does not isolate a constraint effect. See results/training/constraint_effects.json.');
slide('Performance and the hurdle',`After-cost historical CAGR: ${pct(rec.performance?.cagr)}\nHistorical maximum drawdown: ${pct(rec.performance?.maximum_drawdown)}\nExpected geometric return: ${pct(rec.expected_geometric)}\nAnnual spending reduces NAV once\nReal-capital target uses the CPI ratio\nIllustrative 5/10-year shortfall: ${pct(capital[0]?.shortfall_probability)} / ${pct(capital[1]?.shortfall_probability)}`,
 '55 seconds. Historical performance is not expected return. Explain quarterly/drift costs versus daily constant-weight risk replay, geometric versus arithmetic means, and the spending convention.');
const risk=slide('One-day downside risk','', '60 seconds. VaR is a threshold; ES averages tail severity. Dollar ES averages dollar losses. Explain normal, Monte Carlo and EVT differences. Confidence is 99%, value USD 10 million.');
const csv=await fs.readFile(path.join(run,chosen,'risk.csv'),'utf8');
// CSV fields used here have no embedded commas before the numeric columns.
const lines=csv.trim().split(/\r?\n/);const headers=lines[0].split(',');
const rows=lines.slice(1).map(l=>Object.fromEntries(l.split(',').map((v,i)=>[headers[i],v]))).filter(r=>Number(r.alpha)===.99&&['historical','normal','mc_t','evt'].includes(r.method));
const riskValues=[['Method','VaR USD','ES USD'],...rows.map(r=>[r.method,money(Number(r.var_usd)),money(Number(r.es_usd))])];
const rt=risk.tables.add({rows:riskValues.length,columns:3,left:64,top:190,width:1152,height:350,values:riskValues});
for(let r=0;r<riskValues.length;r++)for(let c=0;c<3;c++)rt.getCell(r,c).text.style={typeface:font,fontSize:28,bold:r===0,color:'#102D45'};
slide('Tail estimates and uncertainty','EVT threshold supported by stability and tail diagnostics\nSparse extremes widen uncertainty\nEmpirical-body estimates labelled below the threshold\nCircular block bootstrap preserves whole asset rows\nFixed threshold percentile omits selection uncertainty',
 '55 seconds. Explain positive, zero and negative GPD shape, support and threshold trade-off. High shape does not mean high crash probability. Compare threshold and block sensitivities.');
const validation=rec.validation?.filter(r=>r.alpha===.99&&['fhs','garch_evt'].includes(r.method))||[];
slide('Allocation-specific model validation',validation.map(r=>`${r.method}: ${r.breaches}/${r.days} breaches, final zone ${r.zone}\nKupiec p ${r.kupiec_p?.toFixed(3)}, conditional coverage p ${r.conditional_coverage_p?.toFixed(3)}`).join('\n\n')+'\nPrior-day forecasts and a separate annual walk-forward check',
 '65 seconds. Explain Kupiec frequency, Christoffersen clustering, missing forecasts and 250-day 99% Basel calibration. Disclose earlier equal-weight FHS failure, primary/challenger order and no untouched historical holdout. BIS source: https://www.bis.org/committees/bcbs/basel-framework/standard/mar/99/inforce/2019-12-15/published/2019-12-15');
slide('Stress losses and risk contributions',(rec.stress||[]).map(s=>`${s.scenario}: ${money(s.loss_usd)}`).join('\n')+'\nShared historical tail weights reconcile dollar ES\nPortfolio-only FHS attribution is unavailable',
 '60 seconds. Historical paths are buy-and-hold from SPY peak to trough. Hypothetical shocks have no calibrated probability. Explain negative ES contributions, scenario dependence and why bonds/gold can fail.');
slide('Committee action and governance',`${bundle.decision.outcome}: ${bundle.decision.action}\n\nReview: 10% drawdown or yellow zone\nConsider validated de-risk allocation: 15% or red\nOwner review and solo eligibility remain pending`,
 '60 seconds. Explain checks C1-C5 and adjustment order A1-A5. Missing or failed model validation means evaluation incomplete. Owner must independently review and defend the recommendation. AI assisted code and documents; disclose Claude Code, Antigravity and Codex according to records.');
slide('Committee questions','Why this allocation rather than all bonds?\nWhat if both risk models fail?\nHow much spending can the endowment sustain?\nWhat evidence would change the decision?',
 '45 seconds plus Q&A. Answer with the frozen limits, empirical stress evidence, spending hurdle and each allocation’s own validation. Do not claim independent human approval or guarantee protection.');

await (await PresentationFile.exportPptx(p)).save(path.join(build,'candidate.pptx'));
for(const [i,s] of p.slides.items.entries()) {
 const img=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await img.arrayBuffer()));
}
const python=path.join(runtime,'python/python.exe');
const final=path.join(out,process.env.QUANTEDGE_PITCH_NAME || 'committee_pitch.pptx');
await finalizePresentation({workspaceDir:root,candidatePath:path.join(build,'candidate.pptx'),finalPath:final,
 pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',
             '--require-native-table-slide','3','--require-native-table-slide','7'],
 explicitTotalSlideCount:12,requiredNativeTableOwnerSlides:[3,7],requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(build,path.basename(final)+'.validation.json')});
console.log(final);
