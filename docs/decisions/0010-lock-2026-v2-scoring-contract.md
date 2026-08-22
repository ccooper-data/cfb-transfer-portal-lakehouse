# ADR 0010: Lock 2026 v2 scoring contract

## Status

Accepted before fitting final 2021-2025 models or producing any 2026
predictions.

## Context

The v2 rolling temporal backtest evidence is frozen in ADR 0009. The project
can now produce 2026 forecasts, but 2026 outcomes are not observed and must not
be used during model fitting, hyperparameter selection, filtering, or scoring.

The full 2026 resolved feature matrix contains 2,131 rows in supported target
positions:

- DB: 556
- DL: 295
- EDGE: 114
- LB: 208
- P: 57
- QB: 161
- RB: 203
- TE: 164
- WR: 373

Across those 2,131 rows, 489 lack the position-specific prior-production
anchor and 1,642 have it observed.

P had no evaluable fold in the locked v2 rolling backtest because of the
pre-specified sample thresholds. K has no outcome-observed training cohort in
the locked v2 evidence.

## Decision

### Scoring population

The first 2026 v2 scoring release will score only position groups with
evaluable locked v2 backtest evidence:

- DB
- DL
- EDGE
- LB
- QB
- RB
- TE
- WR

P is excluded from first-release scoring because it lacks evaluable locked v2
validation evidence. K is not scored.

This yields an expected 2026 scoring population of **2,074 rows**.

Within those 2,074 rows:

- 1,605 have the position-specific pre-production anchor observed
- 469 have that anchor missing

Missing prior production does not exclude a player.

### Final training data

For each scoreable position group, the final v2 model is fit on all available
outcome-observed v2 training rows from portal seasons 2021-2025.

Expected total training rows across scoreable groups: **5,557**.

The 2025 season may be used for final model development and training because it
is no longer being represented as fresh v2 test evidence. Its role remains
explicitly development/final-training data.

### Model specification

The scoring model keeps the locked v2 model family and position-specific
numeric feature specifications.

Missing numeric predictors are handled with the same mechanism used in the
locked v2 backtest:

- median imputation fit only on the training data
- one explicit missingness channel per numeric model feature

Ridge alpha is selected independently by position group using expanding-year
validation within 2021-2025 only, then the model is refit on all 2021-2025
training rows for that group.

### Output contract

Each 2026 forecast row must include at least:

- portal key
- player ID and player/position metadata
- origin and destination
- target metric
- predicted post-transfer production
- whether prior anchor production was missing
- model-feature missing count
- selected ridge alpha
- training-row count
- an explicit status that the 2026 outcome is unobserved

No realized 2026 outcome field is permitted in the scoring output.

## Guardrails

- The locked v2 backtest is not modified or re-run as new untouched evidence.
- No 2026 outcome is used.
- No post-transfer production feature is used as a predictor.
- Missing prior production is not converted to zero.
- P is not scored until adequate validation evidence exists.
- 2026 forecasts are not labeled as measured 2026 accuracy.
- Predictions are not causal estimates of transfer or destination-school
  effects.
- No post-hoc clipping or result-based adjustment is applied to first-release
  predictions.

## Consequence

The first scoring release covers 2,074 resolved 2026 transfers across eight
historically evaluated position groups, including 469 players who would have
been lost under the old complete-pre-anchor requirement.

Future 2026 accuracy can be measured only after 2026 outcomes become available.
