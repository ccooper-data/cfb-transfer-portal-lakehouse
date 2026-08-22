# ADR 0016: Interpret first locked v3 target-observability evidence

## Status

Accepted after publication of the first locked v3 evidence.

## Locked evidence

The first v3 target-observability evidence was generated once and published
without post-result tuning.

Primary evidence:

- 6,478 historical cohort rows
- 3,251 out-of-time predictions
- 19 evaluated position-year folds
- 5 skipped folds
- 13 of 19 evaluated folds beat the training-period prevalence baseline on Brier score

## Pooled result

The v3 logistic model achieved:

- Brier score: 0.1048
- log loss: 0.3654
- ROC AUC: 0.6731
- PR AUC: 0.9286

The prevalence baseline achieved:

- Brier score: 0.1066
- log loss: 0.3683
- ROC AUC: 0.5671
- PR AUC: 0.9004

The pooled Brier improvement is approximately 1.7%.

## Position-level interpretation

The strongest temporal consistency appeared in QB and DB.

QB beat the prevalence baseline in all three evaluable years:

- 2022: +13.01% Brier skill
- 2023: +2.25%
- 2024: +4.38%

DB also beat the prevalence baseline in all three years:

- 2022: +2.06%
- 2023: +2.48%
- 2024: +5.25%

Other position groups were mixed. Large negative folds occurred for LB in
2023 and EDGE in 2024. RB and TE included folds whose difference from the
prevalence baseline was very small.

Therefore the evidence does not support a claim that observability is equally
predictable across positions.

## Calibration

The pooled calibration intercept was approximately 0.85 and the pooled
calibration slope approximately 0.51.

A slope materially below 1.0 indicates that the first locked probability
model is not sufficiently calibrated to be presented as a production-ready
probability estimator.

No post-result recalibration is applied to the locked evidence.

## Conclusion

The first v3 study supports the narrower conclusion that CFBD target
observability contains measurable out-of-time predictive signal beyond
position-specific historical prevalence.

The evidence is strongest for QB and DB.

The model remains a diagnostic study. It must not be described as:

- probability that a player will play;
- probability that a player makes a roster;
- probability of zero production;
- a calibrated production probability;
- a causal model.

The frozen v2 forecasts remain unchanged.

Future v3 extensions must be versioned separately and may not replace or
rewrite this first locked result.
