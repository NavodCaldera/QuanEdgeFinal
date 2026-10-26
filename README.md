# QuanEdgeFinal

Team Ghosted — SAIFA Quant Edge 1.0 final challenge.

## Competition objective

Build a transparent Python and Streamlit investment-risk application for a conservative university endowment managing a USD 10 million portfolio. The recommendation must prioritize capital preservation, explain downside risk, survive historical and hypothetical stress scenarios, and be supported by reproducible analysis.

Permitted assets: SPY, EFA, EEM, AGG, GLD, XLE, and XLK.

## Five-person workload split

Each person owns the deliverables below, but every member must understand and be able to defend the submitted code, assumptions, calculations, and recommendation. Use pull requests or clearly separated branches, and have at least one other member review every material result.

### Person 1 — Data engineering and reproducibility lead

- Build the data-download and caching pipeline using `yfinance`; obtain risk-free and macro data from FRED and, where useful, World Bank/IMF.
- Use adjusted close prices, align market calendars, calculate simple and log returns, and document missing values, unusual observations, and any flagged data issues.
- Run return-series stationarity checks such as the Augmented Dickey-Fuller test.
- Create the common clean dataset and data dictionary used by everyone else.
- Add reproducible setup instructions, dependency management, and data-source citations to the README.

Primary outputs: `data/`, data-cleaning module, validation checks, data documentation, reproducible data workflow.

### Person 2 — Portfolio construction and performance lead

- Define the investment policy: horizon, target return, acceptable loss, risk limits, constraints, and suitability for a conservative endowment.
- Implement expected returns, volatility, correlations, covariance matrix, diversification analysis, Markowitz mean-variance optimisation, and CAPM comparisons.
- Compare candidate portfolios and justify the selected allocation and position sizes.
- Calculate and interpret cumulative return, Sharpe, Sortino, Treynor, Jensen's alpha, Information ratio, maximum drawdown, and Calmar ratio.
- Provide portfolio weights and performance series to the risk and Streamlit workstreams.

Primary outputs: portfolio-construction module, optimisation results, KPI tables/charts, investment-policy assumptions.

### Person 3 — VaR, Expected Shortfall, and EVT lead

- Implement historical, parametric, and Monte Carlo VaR at 90%, 95%, and 99% where applicable, with mandatory comparison at 95% and 99%.
- Implement Expected Shortfall and explain why it adds information beyond VaR for a conservative investor.
- Identify extreme negative returns, justify the EVT threshold, fit a Generalized Pareto or other appropriate tail model, and estimate extreme losses.
- Compare VaR, ES, and EVT results, including model assumptions and reasons for disagreement.
- Expose reusable functions and clearly documented inputs for the Streamlit dashboard.

Primary outputs: risk-measurement module, tail-risk tables, threshold diagnostics, VaR/ES/EVT charts and interpretation.

### Person 4 — Backtesting, stress testing, and risk-budgeting lead

- Create an out-of-sample backtest for the selected VaR model.
- Implement Kupiec proportion-of-failures, Christoffersen independence, and Basel traffic-light classification.
- Test the 2008 Global Financial Crisis, March 2020 COVID crash, and 2022 interest-rate hiking period.
- Design and justify one hypothetical scenario, then report portfolio return, dollar loss, asset-level effects, damage sources, and endowment acceptability.
- Calculate marginal VaR, component VaR, marginal Expected Shortfall, and risk contributions; recommend position-size or risk-budget changes where needed.

Primary outputs: validation module, crisis-scenario definitions, stress-test results, risk-contribution analysis, model-acceptability conclusions.

### Person 5 — Streamlit, communication, and integration lead

- Build the Streamlit application for a non-technical investment committee.
- Include sidebar controls for confidence level (90%, 95%, 99%), VaR method, backtest date range, and portfolio weights.
- Add the portfolio panel, cumulative-return and drawdown charts, side-by-side VaR/ES/EVT results, backtesting panel, traffic-light indicator, and stress-test panel.
- Add a clearly labelled **Assumptions & Limitations** page in plain language.
- Integrate all modules, manage the final user experience, and run end-to-end checks.
- Coordinate the 7–15-page technical report, one-page executive tear sheet, 10–12-minute presentation, final investment recommendation, and AI-use disclosure.

Primary outputs: Streamlit app, report, tear sheet, presentation, final recommendation, release checklist.

## Shared delivery sequence

1. **Foundation checkpoint:** Person 1 publishes the clean, reproducible dataset and Person 2 agrees the investment policy and portfolio interface.
2. **Model checkpoint:** Persons 2–4 independently produce tested modules using the shared data and standardised portfolio inputs.
3. **Integration checkpoint:** Person 5 connects the modules to Streamlit; all members verify numerical outputs against hand calculations or independent checks.
4. **Decision checkpoint:** The team agrees on one recommendation, one risk limit, and one consistent set of numbers across the app, report, tear sheet, and presentation.
5. **Defence checkpoint:** Every member rehearses the full pipeline and can explain data cleaning, assumptions, formulas, limitations, and AI-assisted components.

## Required submission checklist

- Public or judge-accessible GitHub repository with clean, documented, reproducible code.
- Working Streamlit application runnable locally with one command or deployed for judges.
- 7–15-page technical report/investment memorandum.
- One-page executive tear sheet.
- 10–12-minute live presentation if selected for the final five.
- AI disclosure covering tools used, purpose, human validation, and AI-assisted components.

## Technical requirements to keep visible

- Use only the permitted investment universe and approved data sources.
- Do not silently remove or manually edit observations; document all cleaning and outlier decisions.
- Use log returns for statistical analysis and explain any use of simple returns.
- Compare all three VaR methods, report ES, justify EVT threshold selection, and backtest the selected VaR model out of sample.
- Translate every metric into an actionable decision for a conservative endowment, including what could go wrong and how severe losses could be.

## Risk measurement module (Person 3)

VaR, Expected Shortfall and EVT live in [`quanedge/risk/`](quanedge/risk/). They are built and tested, but run on **placeholder inputs**: a temporary yfinance loader and equal weights stand in until Person 1's dataset and Person 2's weights land.

```bash
pip install -r requirements.txt
python -m quanedge.risk.run           # tables, figures and summary in results/risk/ (a few minutes)
python -m quanedge.risk.run --quick   # fast look: 50 bootstrap resamples, no rolling forecasts
python -m pytest                      # unit tests against closed forms, simulations and known tails
```

- Detailed Person 3 instructions, remaining work, conventions, testing and team handoffs: [docs/person-3/AGENTS.md](docs/person-3/AGENTS.md)
- Project-wide agent instructions: [AGENTS.md](AGENTS.md)
- Latest numbers, every sentence computed from the tables: [results/risk/summary.md](results/risk/summary.md)
