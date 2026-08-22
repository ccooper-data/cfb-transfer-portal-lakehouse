# ADR 0015: Lock v3 target-observability study design

## Status

Accepted for design lock before fitting any v3 observability model.

## Motivation

The frozen v2 production model is conditional on an observed post-transfer
position-specific target. A follow-up empirical check established that this
conditioning is primarily a CFBD player-stat observability issue rather than
an arbitrary target-definition issue.

Among 6,478 historical 2021-2025 transfers in the eight v2 scoreable position
groups that were conservatively linked to the destination roster in the same
season and had an available post-season statistics source:

- 5,557 (85.78%) had the exact v2 position target observed;
- 921 (14.22%) did not have the exact target observed;
- 813 (12.55% of all rows) had no CFBD player-stat row at all;
- 108 (1.67% of all rows) had at least one CFBD player-stat row but not the
  exact v2 target.

Therefore the v3 study treats target observability as a data/measurement
outcome. It must not be labeled playing time, participation, roster survival,
or zero production.

## Locked population

Historical study population:

- portal seasons 2021-2025;
- `roster_match_season == portal_season`;
- post-season player-stat source available;
- scoreable position groups: DB, DL, EDGE, LB, QB, RB, TE, WR.

The study is explicitly conditional on a conservative same-season
destination-roster linkage. Unresolved portal records are not treated as
negative football outcomes.

## Primary binary outcome

`target_observed = 1` when the exact v2 post-transfer position-specific target
is present in the player-production feature matrix:

- QB: passing yards
- RB: rushing yards
- WR: receiving yards
- TE: receiving yards
- DB: total tackles
- DL: total tackles
- EDGE: total tackles
- LB: total tackles

Otherwise `target_observed = 0`.

Missing target values are not converted to zero.

## Secondary descriptive outcomes

The study may separately report:

- `any_stat_observed`
- `any_stat_no_target`
- `no_any_stat`

These are source-observability states, not participation states.

## Estimand

The primary estimand is:

`P(target_observed | same-season destination-roster linkage, information available at transfer/scoring time)`

The v2 conditional production model continues to estimate:

`E(target production | target_observed, available pre-transfer/scoring features)`

These two quantities must remain separate.

Because `target_observed == 0` does not imply true production equals zero,
the project must not multiply the observability probability by the conditional
production forecast and call the product expected football production unless a
future, separately locked study establishes the required zero/participation
semantics.

## Predictors

Only information available at or before the forecasting/scoring point may be
used.

Eligible predictor families:

- portal season;
- portal position / model position group;
- origin;
- destination;
- rating;
- stars;
- eligibility;
- pre-transfer production features (`pre_*`);
- pre-transfer feature-missingness indicators derived only from those
  `pre_*` values.

No `post_*` feature, post-season source state, realized target value, or other
outcome-derived variable may enter the predictor matrix.

## Temporal evaluation

Primary v3 evidence uses rolling-origin historical evaluation with holdouts:

- 2022, trained on 2021;
- 2023, trained on 2021-2022;
- 2024, trained on 2021-2023.

The 2025 observability labels have already been inspected in aggregate during
study formation. Therefore 2025 must not be described as a pristine untouched
test set. It may be reported later as a clearly labeled temporal stress test
after the primary design is locked.

## Preprocessing and tuning

All imputation, categorical encoding, scaling, prevalence estimation, and
hyperparameter selection must be fit on the training fold only.

No transformation may be fit on the full historical frame before the temporal
split.

Any hyperparameter selection must occur using only seasons earlier than the
outer holdout season.

## Candidate model

The primary candidate is regularized logistic regression because the purpose
is transparent probability estimation rather than maximum classification
complexity.

Any more complex model added later must be compared against the locked
logistic model and must not replace it silently.

## Baselines

At minimum compare against:

1. training-period overall prevalence within the position group;
2. a training-period position-group prevalence model when evaluating a pooled
   model.

Baselines and the model must be evaluated on identical holdout rows.

## Primary metrics

For each evaluated holdout and position group, report:

- N;
- target-observed prevalence;
- Brier score;
- log loss;
- ROC AUC when both classes are present;
- PR AUC when defined;
- calibration intercept/slope when estimable.

A reliability/calibration table or curve must also be published for pooled
predictions and for position groups with adequate sample size.

Brier score is the primary model-selection/evaluation metric because the
output is a probability and calibration matters.

## Reporting

The project may say that pre-transfer/scoring information predicts CFBD target
observability if temporal evaluation supports that claim.

The project must not translate an observability probability into:

- probability of playing;
- probability of making the roster;
- probability of meaningful snaps;
- probability of zero production;
- causal effect of a destination school.

## Relationship to v2

The frozen v2 forecast release is not modified.

The v3 observability study is a diagnostic and potential future companion
model explaining when the v2 conditional production estimand is likely to be
observable.

All v2 hashes, forecasts, dashboards, and the preregistered 2026 v2 accuracy
protocol remain unchanged.
