# ADR 0009: Lock v2 rolling temporal backtest evidence

## Status

Accepted. This records the first real-data execution of the v2 rolling temporal
backtest after the design was committed in ADR 0008.

## Governance sequence

The v2 rolling-backtest design and evaluator were committed before real-data
evaluation as commit:

- `e83bae8` — `Lock v2 rolling temporal backtest design`

Only after that commit was pushed was the real-data evaluator executed.

No model specification, feature specification, fold threshold, baseline,
hyperparameter-selection rule, or missing-data policy is changed in this ADR.

## Evidence scope

Primary v2 evidence uses rolling-origin holdouts:

- 2022: train on seasons before 2022
- 2023: train on seasons before 2023
- 2024: train on seasons before 2024

The 2025 season is not treated as fresh v2 test evidence because it had already
been inspected under the locked v1 evaluation.

The broader v2 outcome-observed cohort contains 5,631 rows across 2021-2025.
The primary backtest period through 2024 contains 3,605 source rows.

## First-run results

The first real-data execution produced:

- 2,941 out-of-sample predictions
- 20 evaluated position-year folds
- 7 low-sample folds skipped under the pre-specified thresholds
- 16 of 20 evaluated folds beating the all-row historical-mean baseline on MAE
- 18 of 20 paired comparisons beating the returning-production baseline on MAE

### Fold-level pattern

The model was not uniformly superior in the earliest period.

2022 all-row losses:
- DL: -12.49% MAE skill versus historical mean
- RB: -6.72%
- WR: -12.31%

2022 paired returning-production losses:
- RB: -4.53%
- WR: -15.09%

2023 all-row loss:
- DL: -1.57%

All other evaluated 2023 folds beat both relevant baselines.

In the 2024 rolling holdout, every position group with sufficient sample size
beat both baselines:

- DB: +5.95% all-row skill; +14.91% paired skill
- DL: +4.22%; +16.55%
- EDGE: +2.10%; +27.35%
- LB: +5.65%; +10.69%
- QB: +9.90%; +2.99%
- RB: +4.47%; +9.99%
- TE: +8.85%; +3.51%
- WR: +2.06%; +18.47%

P remained below the pre-specified sample threshold and was skipped rather than
pooled or forced into the evaluation.

## Locked evidence files

The first-run output files are content-addressed by SHA-256:

`outputs/v2_rolling_backtest_predictions_2022_2024.csv`

- SHA-256:
  `a51403ae7898827552381122e3e4b94175198cf2defe7bf58584f497d0f069f5`

`outputs/v2_rolling_backtest_results_2022_2024.json`

- SHA-256:
  `f64a830ae984defb40f28d60f2b150bc82f4e2451a9856a7cb0ce0c01bf17f68`

These hashes identify the exact first-run evidence evaluated under ADR 0008.

## Interpretation

The defensible portfolio statement is:

> Across 2,941 rolling-origin predictions from 2022-2024, the broader v2 model
> beat the all-player historical-mean baseline in 16 of 20 evaluable
> position-year folds and beat returning production in 18 of 20 paired
> comparisons. Performance strengthened as training history accumulated, with
> every evaluable position beating both benchmarks in the 2024 backtest.

This is predictive evidence only. It is not evidence of a causal transfer
effect or causal destination-school effect.

## Freeze rule

This first-run v2 evidence is now frozen.

Do not tune the v2 feature specifications, model family, thresholds, missingness
policy, or alpha-selection procedure using these results and then represent the
same 2022-2024 backtest as untouched evidence.

Any post-result modeling change must be labeled as a new version or exploratory
development. A future completed season can provide genuinely new temporal test
evidence.

The 2025 season remains development/exploratory evidence for v2 and must not be
relabeled as a fresh untouched holdout.
