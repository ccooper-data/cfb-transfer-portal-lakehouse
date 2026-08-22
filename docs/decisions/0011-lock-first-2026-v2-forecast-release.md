# ADR 0011: Lock first 2026 v2 forecast release

## Status

Accepted. This records the first real 2026 scoring release produced after the
2026 v2 scoring contract was committed in ADR 0010.

## Governance sequence

The 2026 v2 scoring contract was committed before any real 2026 predictions
were produced as commit:

- `bfccf65` — `Lock 2026 v2 scoring contract`

Only after that commit was pushed was the real scoring command executed.

No scoring population rule, model family, feature specification, missing-data
policy, alpha-selection rule, or output contract is changed in this ADR.

## First-release scope

The first 2026 v2 scoring release produced:

- 2,074 scoreable rows
- 2,074 prediction rows
- 1,605 rows with observed prior-production anchors
- 469 rows retained despite missing prior-production anchors
- 562 excluded rows under the locked scoring contract

The first release covers:

- DB
- DL
- EDGE
- LB
- QB
- RB
- TE
- WR

P is excluded because it lacked evaluable locked v2 validation evidence. K is
not scored.

## Outcome status

2026 outcomes are not observed.

Every prediction in this release is a forecast of the position-specific
post-transfer production anchor. No statement in this release represents
measured 2026 accuracy.

The predictions are not causal estimates of transfer effects or destination-
school effects.

## Locked release files

The first scoring release is content-addressed by SHA-256.

`outputs/player_scoring_cohort_2026_v2.csv`

- SHA-256:
  `86dfe5490ff48866396878787bd6e9c99a748fe86796c55167345499e0f8472c`

`outputs/player_scoring_exclusions_2026_v2.csv`

- SHA-256:
  `1ee05a4f631cf29d55945d83a645a65431edfeed450d8d6db7b023325d5de0b7`

`outputs/player_predictions_2026_v2.csv`

- SHA-256:
  `306268a4dbb633592c781b2288bb1ff8f93ea8c9584b0f8fb2e32ab08f9e1ef9`

`outputs/player_predictions_2026_v2_summary.json`

- SHA-256:
  `23af46a1c2ad30d241708ca1047c54106a14400a470c6e32f2c437338fb322e5`

These hashes identify the exact first 2026 forecast release.

## Freeze rule

This first forecast release is frozen before individual player predictions are
inspected, ranked, highlighted, published, or moved into additional downstream
presentation layers.

Do not alter model specifications, scoring rules, clipping rules, player
eligibility, or thresholds based on individual 2026 forecast values and then
replace this release while presenting it as the original first-run forecast.

Any later scoring modification must be versioned separately.

## Allowed next steps

After this release is locked, downstream work may:

- publish the frozen forecasts to Databricks
- build forecast monitoring and presentation tables
- inspect distributions and individual predictions
- add MLflow/model-registry metadata
- build portfolio/dashboard presentation layers

Those downstream steps must preserve the distinction between a forecast and an
observed outcome.
