# ADR 0008: Lock v2 rolling temporal backtest design

## Status

Accepted before executing the real-data v2 rolling backtest.

## Context

The v1 evidence used a strict 2025 holdout on the paired cohort requiring both
pre-transfer and post-transfer anchor production. After inspecting that 2025
evidence, the project broadened the modeling cohort to retain supported
position-group rows whenever the post-transfer target is observed, even when
prior production is missing.

Because 2025 has already been inspected, it cannot be presented again as a
fresh untouched test season for the broader v2 model.

The broader outcome-observed cohort contains 5,631 rows across 2021-2025.
Historical position counts support rolling-origin evaluation for most major
position groups, while punters remain sparse and some early EDGE folds are too
small.

## Decision

Primary v2 evidence will use rolling-origin backtests with holdout years:

- 2022: train only on 2021
- 2023: train only on 2021-2022
- 2024: train only on 2021-2023

2025 is excluded from primary v2 evidence because it was already inspected
under v1. Any later use of 2025 must be labeled exploratory/development
evidence, not a fresh holdout.

A position-group fold is evaluated only when it has at least 40 training rows
and at least 20 holdout rows. Low-sample folds are reported as skipped rather
than pooled or silently dropped.

The v2 ridge model uses the same transparent, position-aware numeric
pre-transfer production profile as v1. Missing numeric predictors are retained,
imputed using training-fold medians, and paired with explicit missingness
channels. Preprocessing is always fit on the training side of each fold.

The primary all-row baseline is the position-specific historical mean
post-transfer production computed from that fold's training period. This
baseline is available for every holdout row, including players with no observed
prior-production anchor.

Returning production remains a secondary benchmark only on the subset where
`baseline_pre_production` is observed. It is not used to exclude missing-anchor
rows from the primary v2 evaluation.

Ridge alpha selection uses expanding-year validation entirely inside each
fold's training period. When a fold has only one training season and therefore
no internal validation year, alpha 10.0 is used as the pre-specified default.

## Guardrails

- No 2025 primary v2 holdout claim.
- No post-transfer production feature may be used as a predictor.
- Resolver score is not a modeling predictor.
- Missing prior production is not converted to zero.
- No destination-school or transfer causal effect claim.
- Low-sample folds remain explicit.
- The real-data evaluation is executed only after this design and evaluator
  are committed.

## Consequences

The v2 model can be evaluated on a broader, deployment-oriented population
without discarding players solely because prior production is unavailable.

The evidence is temporally weaker than a future untouched season because the
project has only 2021-2025 observed outcomes today. That limitation is explicit.
A future completed season can provide new untouched temporal evidence.
