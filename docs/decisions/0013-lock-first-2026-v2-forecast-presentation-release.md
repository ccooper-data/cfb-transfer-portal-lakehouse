# ADR 0013: Lock first 2026 v2 forecast presentation release

## Status

Accepted.

## Context

The frozen first 2026 v2 forecast release was already locked before downstream
inspection and presentation work.

A presentation-only support contract was subsequently locked in ADR 0012.
That contract adds descriptive `forecast_support` metadata without changing any
point prediction.

The first real support-enriched presentation artifact has now been built from
the frozen forecast release.

## First presentation release

The first presentation release contains exactly 2,074 rows:

- STRONG: 1,521
- STANDARD: 84
- LIMITED: 469

The build reported:

- `predictions_modified: false`
- 2026 outcomes remain unobserved
- no causal claim
- no confidence or calibrated-uncertainty interpretation

## Content-addressed evidence

The frozen source forecast remains unchanged:

`outputs/player_predictions_2026_v2.csv`

SHA-256:

`306268a4dbb633592c781b2288bb1ff8f93ea8c9584b0f8fb2e32ab08f9e1ef9`

The first presentation derivative is:

`outputs/player_predictions_2026_v2_presentation.csv`

SHA-256:

`5b57993e1611f931f2bcba52e8e891d551754f12b62546dd5421f298af97bfe9`

Its summary is:

`outputs/player_predictions_2026_v2_presentation_summary.json`

SHA-256:

`3cb175ff48426fe90731ad76e0931859d34342dae2a43d600848ceb288eac90d`

## Freeze rule

This first presentation release is frozen before it is uploaded to Databricks,
used by a dashboard, ranked for publication, or otherwise transformed
downstream.

The files above must not be silently overwritten and treated as the same
release after presentation inspection.

Any later change to:

- support thresholds
- support terminology
- support explanations
- row population
- point predictions
- ranking logic
- display-time post-processing

must be separately versioned.

## Interpretation guardrails

`forecast_support` is descriptive model-input support metadata.

It is not:

- a probability
- a confidence score
- a prediction interval
- a guarantee of correctness
- a 2026 accuracy result
- a causal estimate

The 2026 point forecasts remain unobserved forecasts until actual 2026 outcomes
become available.
