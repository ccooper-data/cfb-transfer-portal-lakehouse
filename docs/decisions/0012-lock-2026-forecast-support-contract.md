# ADR 0012: Lock 2026 forecast-support presentation contract

## Status

Accepted for the frozen first 2026 v2 forecast release.

This ADR governs presentation metadata only. It does not change the locked
scoring population, model specification, feature set, imputation behavior,
regularization selection, point predictions, ranking, or first-release hashes.

## Motivation

Post-release quality review showed a strong descriptive difference in data
support between forecasts with an observed prior-production anchor and those
without one.

For the frozen 2,074-player 2026 release:

- 1,521 forecasts meet the `STRONG` support rule
- 84 forecasts meet the `STANDARD` support rule
- 469 forecasts meet the `LIMITED` support rule

The purpose of this metadata is to expose how much observed pre-transfer
information supports a point forecast.

## Terminology

The field is named `forecast_support`.

It MUST NOT be presented as:

- confidence
- probability of correctness
- prediction interval
- calibrated uncertainty
- accuracy
- causal certainty

No statistical calibration of these labels has been performed.

## Locked rule

For each frozen 2026 prediction:

### STRONG

Assign `STRONG` when:

- `baseline_pre_production_missing == false`, and
- `model_feature_missing_count <= 2`

### STANDARD

Assign `STANDARD` when:

- `baseline_pre_production_missing == false`, and
- `model_feature_missing_count > 2`

### LIMITED

Assign `LIMITED` when:

- `baseline_pre_production_missing == true`

The missing prior-production anchor rule takes precedence over the feature
missing-count threshold.

## Presentation explanation

Derived rows should also expose `forecast_support_reason`:

- `STRONG`: `prior production observed; at most 2 model features missing`
- `STANDARD`: `prior production observed; more than 2 model features missing`
- `LIMITED`: `prior production unavailable; forecast relies more heavily on imputation and remaining observed features`

## Frozen-prediction guarantee

The support derivation MUST copy the exact point prediction from the frozen
first-release file without modification.

No clipping, rescaling, replacement, shrinkage, post-hoc adjustment, or
support-based reranking is allowed.

The source forecast remains:

`outputs/player_predictions_2026_v2.csv`

with locked SHA-256:

`306268a4dbb633592c781b2288bb1ff8f93ea8c9584b0f8fb2e32ab08f9e1ef9`

The support-enriched presentation artifact is a downstream derivative and must
not replace the frozen first-release artifact.

## Expected frozen-release counts

The support-enriched frozen release must contain exactly 2,074 rows:

- STRONG: 1,521
- STANDARD: 84
- LIMITED: 469

If those counts do not match, the build must fail rather than silently publish
a changed presentation population.

## Interpretation

`forecast_support` is a data-completeness and model-input-support label.

It is useful for dashboard filtering, disclosure, and responsible presentation.
It is not evidence that a STRONG forecast will be correct or that a LIMITED
forecast will be wrong.

2026 outcomes remain unobserved.
