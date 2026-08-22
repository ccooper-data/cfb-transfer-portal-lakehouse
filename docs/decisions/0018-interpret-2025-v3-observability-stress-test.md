# ADR 0018: Interpret locked 2025 v3 observability stress test

## Status

Accepted after publication of the locked 2025 temporal stress-test evidence.

## Context

The 2025 evaluation was preregistered as a temporal stress test rather than a
pristine untouched holdout because aggregate 2025 observability labels had
already been inspected during study formation.

The model family, feature contract, preprocessing, hyperparameter selection,
and prevalence baseline were locked before the 2025 stress-test results were
examined.

## Pooled result

Across 2,431 2025 stress-test rows, the locked v3 logistic observability model
achieved:

- Brier score: 0.1427
- log loss: 0.4551
- ROC AUC: 0.6788
- PR AUC: 0.9053
- calibration intercept: approximately -0.048
- calibration slope: approximately 0.795

The 2021-2024 training-period prevalence baseline achieved:

- Brier score: 0.1500
- log loss: 0.4828
- ROC AUC: 0.5700
- PR AUC: 0.8507

The pooled Brier skill versus the locked prevalence baseline is approximately
+4.9%.

## Position-level transport

All eight evaluated position groups beat their locked prevalence baseline on
Brier score:

- DB: +6.13%
- DL: +5.84%
- EDGE: +0.91%
- LB: +3.07%
- QB: +1.27%
- RB: +1.33%
- TE: +10.37%
- WR: +3.70%

The result therefore represents broad positive temporal transport rather than
a pooled improvement produced by only one position group.

## Calibration

Pooled calibration improved materially relative to the first locked
2022-2024 rolling evidence.

DB and DL produced calibration slopes close to 1.0 in the 2025 stress test.

Position-level calibration remained unstable for some groups, especially
EDGE, LB, and RB. Therefore the evidence does not justify treating all
position-specific probabilities as equally calibrated.

No post-result recalibration is applied to this locked stress-test evidence.

## Interpretation

The 2025 stress test supports the conclusion that pre-transfer/scoring-time
information contains temporally transportable signal about whether the exact
CFBD position-specific target will be observable after transfer.

The strongest 2025 probability evidence is in DB, DL, and TE.

The study remains an observability model. It must not be described as:

- probability that a player will play;
- probability that a player makes the roster;
- probability of meaningful snaps;
- probability of zero production;
- a causal destination effect.

The frozen v2 production forecasts and the first locked v3 rolling evidence
remain unchanged.

Any future recalibration, alternative model, or observability extension must
be separately versioned and may not replace this locked result.
