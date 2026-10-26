# VaR and Expected Shortfall specification

## Shared definitions

For loss L, VaR at confidence a is its a-quantile. ES is the average of its worst 1-a probability mass, equivalently the quantile integral divided by 1-a. A conditional mean beyond VaR matches ES for suitable continuous distributions; empirical samples and ties need explicit boundary weighting. See the supplied advanced-risk slides 12-14 and [Acerbi and Tasche, On the coherence of Expected Shortfall](https://arxiv.org/abs/cond-mat/0104295).

Validate 0<a<1, sufficient finite observations, positive portfolio value and each model's parameter domain. Return a clear error or unavailable result for invalid estimation cases. Positive loss is a sign convention, not a requirement to clip negative VaR to zero in an all-gain distribution.

## Historical method: `var_es.Empirical`, `historical`

1. Form losses from the agreed portfolio return series without discarding real crisis days.
2. Document the quantile estimator. VaR uses NumPy linear interpolation (type 7).
3. Empirical ES is the exact worst-probability-mass average (since 70153ba; the earlier mean of losses at or above the interpolated quantile is retired). Sort losses descending, let h=n*(1-a), k=floor(h), and average the largest k observations plus fraction h-k of the next observation, dividing by h; k=0 and integer h need no special case in `var_es.tail_integral`, which integrates the empirical step quantile. Paired with type-7 VaR, ES >= VaR holds for every sample, because the interpolated VaR never lies above the observations carrying the worst mass. The team still has to agree this convention (05, Priority 0).
4. Monetary ES applies the same probability-mass rule to the dollar losses of each scenario (`es_fraction`); the completed log ES is never transformed.
5. Report sample size, effective tail count, window dates, VaR, ES and estimator settings.

Explain that the empirical distribution cannot extrapolate beyond observed sample extrema and that window selection changes crisis representation. Small tail counts require disclosure even when the function returns a number.

## Normal parametric method: `var_es.Normal`

Existing code estimates portfolio log-return mean mu and sample standard deviation sigma (`ddof=1`). With z=Phi^-1(a):

```text
VaR_log = -mu + sigma*z
ES_log  = -mu + sigma*phi(z)/(1-a)
```

Preserve and independently check these formulas. State whether mean is estimated or intentionally set to zero; do not change it only for one comparator. Reject insufficient data; provide defined behaviour for zero volatility. Validate exact transformed monetary ES independently. For sigma>0, one available check is:

```text
ES_fraction = 1 - exp(mu + sigma^2/2) * Phi(-z-sigma)/(1-a)
```

Evaluate this stably in extreme tails and cross-check by integration. This formula is specific to normal log returns. Explain normality, stable mean/variance, and dependence assumptions using measured diagnostics. Normal estimates are not guaranteed to be smaller than historical estimates at every level.

## Monte Carlo method: `var_es.monte_carlo`

`mc_normal` simulates correlated asset log returns from estimated mean/covariance, aggregates scenarios in simple returns and returns their portfolio log losses. Requirements and how they are met (70153ba):

- Validate asset order, covariance symmetry and finite entries; define a documented response to singular or non-positive-definite covariance. Do not silently add arbitrary diagonal jitter. *A failed Cholesky factorisation raises `ModelFitError`, so the model is reported unavailable; no jitter.*
- Keep a deterministic random seed and record simulation count. *Defaults are 100,000 scenarios and seed 20261026; both are in the model's `params` and the run manifest.*
- Estimate VaR/ES consistently with the empirical estimator, including exact monetary scenario ES. *MC results are `Empirical` models, so they share its estimators.*
- Retain or expose per-asset scenarios for Person 4's attribution; document their units, ordering and seed. *`.scenarios` holds asset log-return scenarios, columns in `.assets` order, seed in `.params`.*
- Check convergence across increasing sample sizes and independent seeds; use `batch_se` with adequate nonempty batches. Distinguish simulation error from parameter uncertainty. *`mc_convergence` (5 sizes x 3 seeds) is saved with each run; `batch_se` refuses batches with fewer than 10 tail points.*
- Check extreme simulated log returns and exponential overflow. Do not silently clip simulated disasters to obtain finite results. *Overflow or a non-positive portfolio value raises `ModelFitError`.*

Normal portfolio-log-return fitting and nonlinear aggregation of multivariate normal asset log returns are not identical distributions. Exact agreement is expected in the one-asset matching-model case; small multi-asset differences need not vanish with more simulation. Compare assumption differences before blaming simulation error.

## Existing optional Student-t methods

`StudentT` fits location, scale and degrees of freedom by MLE. The t scale is not its standard deviation. If q=t_nu^-1(a):

```text
VaR_log = -loc + scale*q
ES_log = -loc + scale * t_pdf(q,nu)*(nu+q^2)/((nu-1)*(1-a))
```

Log ES needs nu>1; finite variance needs nu>2. Current univariate bounds force nu>1.05: disclose this modelling constraint and diagnose boundary fits. Optimizer success, zero-MAD samples and collapse onto a point mass are checked (70153ba); a fit at the nu bound carries a warning status. For `mc_t`, existing nu bounds exceed 2 and covariance is held equal to sample covariance using the corresponding t dispersion. One shared chi-square scale per scenario preserves the model's joint tail dependence.

Do not claim Student-t always exceeds normal VaR or that equal covariance guarantees equal distribution of portfolio losses. Explain fitted degrees of freedom, central/tail trade-offs, covariance estimation and parameter uncertainty. Optional models must not delay delivery of the mandatory comparison.

## Comparison outputs

At 95% and 99%, report each required family on identical exposures, training data, value and one-day horizon. Include 90% for the app. Show VaR and ES in log units for research and exact percentage/USD units for investment reporting, fit warnings and sample size. Compare absolute dollar gaps and relative gaps only with valid denominators.

For each disagreement identify evidence: distribution fit, tail count, threshold, sample period, conditional volatility or simulation uncertainty. Do not average different models without a justified decision rule. Supply a candidate validation model to Person 4 with its settings frozen before inspecting the final test period.
