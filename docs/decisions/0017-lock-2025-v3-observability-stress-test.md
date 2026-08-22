# ADR 0017: Lock 2025 v3 target-observability temporal stress test

## Status

Accepted before running the 2025 v3 stress-test evaluation.

## Purpose

The first locked v3 target-observability evidence used primary rolling
out-of-time evaluation for 2022-2024.

This follow-up evaluates temporal transport into portal season 2025.

The 2025 target-observability prevalence and aggregate labels were previously
inspected during study formation. Therefore this evaluation is explicitly a
temporal stress test and must not be described as a pristine untouched
holdout or fresh confirmatory test.

## Frozen model family

The stress test uses the same model family and feature contract as the first
locked v3 study:

- L2-regularized logistic regression;
- position-specific predictor sets already defined by the v3 evaluator;
- pre-transfer/scoring-time predictors only;
- no post-transfer predictors;
- explicit pre-feature missingness handling;
- no conversion of missing targets to zero.

No new predictors may be introduced for the 2025 stress test.

## Training and evaluation split

For each scoreable position group:

- training rows: portal seasons 2021-2024;
- stress-test rows: portal season 2025.

No 2025 row may be used to fit preprocessing, coefficients, prevalence
baselines, or hyperparameters.

## Hyperparameter selection

The L2 penalty must be selected using only the 2021-2024 training period,
using the same expanding-year internal validation procedure and Brier-score
criterion used in the locked v3 evaluator.

No L2 value may be selected based on 2025 results.

## Preprocessing

All median imputation, scaling, and missingness transformations must be fit
only on the 2021-2024 training rows for the relevant position group.

## Baseline

The comparison baseline is the position-group target-observed prevalence
estimated only from the 2021-2024 training rows.

The model and baseline must be evaluated on exactly the same 2025 rows.

## Metrics

Report for each evaluable position group:

- N;
- 2025 target-observed prevalence;
- Brier score;
- Brier skill versus the 2021-2024 prevalence baseline;
- log loss;
- ROC AUC when defined;
- PR AUC when defined;
- calibration intercept and slope when estimable.

Also report pooled metrics across all evaluated 2025 rows.

Brier score remains the primary probability metric.

## Interpretation

The stress test asks whether the first v3 modeling approach transports into
the lower-observability 2025 environment.

It does not test:

- probability of playing;
- probability of roster membership;
- probability of meaningful snaps;
- probability of zero football production;
- causal effects of origin or destination.

## Governance

The first locked v3 evidence and its interpretation remain unchanged.

The 2025 stress-test results must be written to new artifacts and hash-locked
before detailed interpretation.

No post-result recalibration, feature changes, or alternate model may replace
the stress-test result. Any later extension must be separately versioned.
