# ADR 0007: Lock 2025 holdout and negative-control evidence

## Status

Accepted — 2026-08-22.

## Context

The player-level forecasting benchmark uses position-specific models with a strict temporal split: portal seasons 2021–2024 are available for fitting and expanding-year hyperparameter selection, while portal season 2025 is reserved for final holdout evaluation.

The benchmark modeling table contains 4,168 paired target rows derived from the complete pre/post production cohort. This paired cohort is useful for a controlled benchmark, but requiring an observed pre-transfer production anchor introduces selection into the analysis population. It is therefore not automatically the final deployment cohort.

The 2025 holdout was evaluated before this ADR was written. Once those results were viewed, 2025 ceased to be an untouched test set for any materially changed model specification.

A separate negative-control diagnostic was then run using the same locked 2025 temporal boundary. Its purpose is to test whether future-side portal information is associated with a performance change that occurred before the transfer. That diagnostic is a falsification/selection check, not a causal estimator and not a forecasting-model improvement.

## Decision

The current 2025 forecasting benchmark and negative-control diagnostic are frozen as **v1 evidence**.

For the forecasting benchmark:

- training seasons: 2021–2024
- holdout season: 2025
- hyperparameter selection: expanding-year validation inside 2021–2024 only
- primary baseline: returning production, where the pre-transfer production anchor predicts the post-transfer anchor
- predictors: pre-transfer numeric profile plus portal rating/stars according to the position-specific feature contract
- post-transfer production features are never used as predictors
- causal claim: none

For the negative-control diagnostic:

- training seasons: 2022–2024
- holdout season: 2025
- target: S-1 anchor production minus S-2 anchor production
- destination encoding is fit on training rows only
- future-side predictors are destination historical signal, portal rating, and portal stars
- post-transfer production is not used as a predictor
- causal claim: none

## Forecasting results

The locked 2025 benchmark produced **1,408 holdout predictions** across **8 evaluated position groups**.

All 8 evaluated groups reduced MAE relative to the returning-production baseline:

| Position | Holdout rows | Baseline MAE | Model MAE | MAE skill |
| --- | ---: | ---: | ---: | ---: |
| DB | 388 | 20.3144 | 17.8936 | 11.92% |
| DL | 194 | 12.2990 | 10.1054 | 17.84% |
| EDGE | 54 | 13.2222 | 10.0862 | 23.72% |
| LB | 154 | 33.6753 | 28.0673 | 16.65% |
| QB | 106 | 897.1792 | 868.0988 | 3.24% |
| RB | 160 | 392.5000 | 279.4723 | 28.80% |
| TE | 91 | 124.4725 | 116.2050 | 6.64% |
| WR | 261 | 285.0536 | 222.7772 | 21.85% |

Punter was skipped because the training sample was below the minimum threshold (30 training rows, 21 holdout rows). Kicker had no rows in the paired modeling cohort.

The appropriate portfolio claim is that the position-specific ridge models **lowered absolute prediction error versus the returning-production baseline on the strict 2025 holdout**. The project does not claim high absolute accuracy. Some position-level R² values are near zero or negative, including LB and RB, so error reduction is the primary evidence.

## Negative-control results

The negative-control panel contains **2,893 rows**, with **1,023 holdout predictions** across **8 evaluated position groups**.

A modest negative-control signal was detected in **3 of 8** evaluated groups:

- DL: MAE skill +2.62%, R² 0.0308
- RB: MAE skill +0.93%, R² 0.0045
- TE: MAE skill +0.90%, R² 0.0043

No signal was detected under the diagnostic rule for DB, EDGE, LB, QB, or WR. Punter was skipped for low sample size, and kicker was absent.

The detected effects are small. They are interpreted as **modest evidence of selection/confounding**: information observed around transfer selection is associated with player performance trajectories that were already underway before transfer.

This does not invalidate forecasting. It strengthens the governance requirement that predictive performance must not be interpreted as a causal school effect, transfer effect, or treatment effect.

## Consequences

1. The 2025 forecasting holdout is locked evidence for v1.
2. Model specifications, feature sets, thresholds, cohort definitions, or hyperparameters changed after viewing 2025 results are v2/exploratory work and must not reuse 2025 as though it were untouched.
3. The negative-control v1 specification is also frozen after viewing its results. Any diagnostic redesign becomes v2/exploratory.
4. The negative control was performed after the forecasting benchmark, using the same 2025 temporal boundary. It is not described as preregistered.
5. The 4,168-row paired benchmark cohort is not automatically the production scoring cohort because requiring observed pre-transfer production can create selection bias.
6. A broader deployment/training table should include outcome-observed resolved players with explicit missingness/availability indicators rather than requiring a complete pre anchor.
7. Because 2025 has already been inspected, evaluation of that broader cohort must be framed as v2/exploratory unless it uses earlier rolling temporal folds or a future untouched season.
8. 2026 may be scored only after the deployment/scoring contract is frozen. Its post-season outcomes are currently unavailable/right-censored, so no 2026 accuracy claim is made.
9. Databricks/MLflow productionization should preserve these versioned evidence boundaries rather than silently recomputing v1 under changed assumptions.

## Reproduction

Forecasting benchmark:

```bash
python scripts/evaluate_holdout_2025.py
```

Negative-control diagnostic:

```bash
python scripts/evaluate_negative_control.py
```

The resulting artifacts remain local/ignored analytical outputs; this ADR records the interpretation and evidence boundary that downstream productionization must preserve.
