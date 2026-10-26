# Extreme Value Theory work specification

## Tail construction and fitting

Use portfolio log losses L=-r_p. For threshold u, fit positive exceedances Y=L-u conditional on L>u. Record n observations, k exceedances and zeta=k/n. Current implementation is in `evt.py` with `GPDFit`, `fit_gpd`, `EVT`, `threshold_scan`, `select_threshold` and `fit_evt`.

The GPD has positive scale sigma and shape xi; its support satisfies 1+xi*y/sigma>0. At xi=0 use the exponential limit. Negative xi implies a finite upper endpoint for excesses. Implement support and limit checks and verify against [SciPy's GPD reference](https://scipy.github.io/devdocs/tutorial/stats/continuous_genpareto.html), using the installed version's API.

Check finite positive excesses, enough distinct data, nonzero dispersion, optimizer convergence, finite likelihood and valid fitted support. Current fitting consumes optimizer parameters without checking success. Return useful status information rather than silently accepting failures. Test parameter estimates and log likelihood against an independent implementation on synthetic known tails.

## Threshold selection

Current development settings scan loss percentiles 0.800 to 0.985 in increments of 0.005, requiring at least 50 exceedances. These are chosen settings to defend, not competition rules. Every candidate records threshold, count, mean excess, xi, xi standard error, sigma, modified scale sigma-xi*u, KS distance, and 99% VaR/ES.

Current stability flag checks whether a candidate's xi falls within the approximate interval of every higher eligible candidate. Current selection minimizes KS distance among flagged candidates. This is an implemented heuristic; do not claim it is an established universally optimal GPD rule or attribute the complete procedure to a power-law paper without verifying that attribution.

Required work:

1. Plot mean excess against actual threshold u. The existing plot uses threshold percentile, on which apparent linearity is not the standard mean-excess diagnostic.
2. Plot xi and uncertainty across thresholds, plus modified-scale stability, exceedance counts and KS distance. `sigma_star` is already tabulated but not plotted.
3. Define a defensible stability region and minimum count, balancing bias at low thresholds against variance at high thresholds.
4. Inspect whether the last candidate passes vacuously because it is compared only with itself. Require meaningful evidence across neighbouring thresholds or explicitly describe the limitation.
5. Define behaviour for empty scans, invalid fits, no acceptable stable region and ties. Existing empty scans can fail with missing columns. A fallback to all candidates must be flagged, not called successful stability validation.
6. Compare the chosen rule with fixed 90th/95th-percentile candidates where sample counts permit. Report risk-estimate sensitivity, not only the selected xi.
7. Choose thresholds entirely within training data for rolling forecasts and freeze selection rules before final validation.

Approximate xi standard errors currently assume xi>-0.5 and adequate sample size. Guard this validity range and report uncertainty honestly. Ordinary KS p-values are not automatically calibrated when parameters and the threshold are fitted on the same observations; the existing KS statistic is a distance diagnostic.

## Tail formulas and confidence coverage

For a>=1-zeta, the model's tail quantile is:

```text
xi != 0: VaR_log(a) = u + sigma/xi * ((zeta/(1-a))^xi - 1)
xi == 0: VaR_log(a) = u + sigma * log(zeta/(1-a))
xi < 1:  ES_log(a)  = (VaR_log(a) + sigma - xi*u)/(1-xi)
xi >= 1: finite log ES does not exist
```

Check support, continuity, numerical stability near xi=0, and the bounded endpoint when xi<0. The exceedance rate zeta is essential: fitting a conditional tail without it cannot yield unconditional portfolio VaR.

Current `EVT` combines an empirical body with a GPD tail. Retain this approach only after validating its probability normalization, body/tail boundary, ties and ES integration. At sidebar levels below the tail cutoff label the result as an empirical-body/hybrid estimate, not a pure extrapolated EVT quantile. An alternative is an explicit unavailable pure-tail result with an explanation; coordinate the display with Person 5 so the required dashboard remains understandable.

For dollar/percentage ES integrate transformed losses over the full relevant quantile tail, including the empirical-body portion where applicable. An infinite log ES requires a separate status; see the valuation contract for why monetary ES is a different calculation.

## Uncertainty and dependence

Current uncertainty code uses 500 circular moving-block resamples of length 20 days, 20,000 Monte Carlo scenarios per replicate, and 95% percentile intervals. These are development defaults. Resample whole asset rows to retain cross-asset dependence. Assess block-length and repetition-count sensitivity and log unsuccessful replicates; never silently discard them.

Current bootstrap fixes the selected threshold percentile and recomputes its numeric threshold per resample. Its intervals omit uncertainty from reselecting the threshold rule. Label them accordingly or add full reselection sensitivity. Distinguish parameter uncertainty, Monte Carlo noise, threshold uncertainty and model misspecification.

Extreme days can cluster. Examine dependence and discuss the implications for raw-loss POT. Existing `garch_evt` fits a tail to standardized GJR-GARCH residual losses with a fixed 90th-percentile threshold. That fixed choice needs its own diagnostics; the raw-loss threshold scan does not justify it. Check residual dependence and conditional-model convergence before claiming filtering solved clustering. If declustering is introduced, explain how it changes the event rate and risk target.

## Required EVT handoff

Supply threshold scan and selected-rule metadata, mean-excess and stability plots, empirical versus fitted tail probabilities, excess QQ/PP diagnostics, confidence-specific risk estimates, warning states, threshold/window sensitivity, and a plain-language explanation. Explain positive/zero/negative xi without translating xi alone into a crash probability. Additional 99.9% estimates are optional and must show their greater extrapolation uncertainty.
