# ADR 0014: Preregister 2026 v2 forecast accuracy protocol

## Status

Accepted for preregistration before 2026 outcomes are observed.

## Purpose

This protocol defines, in advance, how the frozen 2026 v2 player-level forecast
release will be evaluated once 2026 post-transfer outcomes become observable.
It exists to prevent metric selection, cohort changes, exclusions, or
redefinitions after seeing the realized outcomes.

This protocol grades the already-frozen v2 forecast release. It does not modify
the forecast, retrain the model, or retroactively incorporate any later v3
analysis.

## Frozen forecast under evaluation

Primary prediction artifact:

`outputs/player_predictions_2026_v2.csv`

Locked SHA-256:

`306268a4dbb633592c781b2288bb1ff8f93ea8c9584b0f8fb2e32ab08f9e1ef9`

Frozen forecast population:

- portal season: 2026
- prediction rows: 2,074
- position groups: DB, DL, EDGE, LB, QB, RB, TE, WR
- forecast status: `unobserved_2026_outcome`

The forecast population is not to be expanded, reduced, reordered for
performance purposes, or regenerated after 2026 outcomes are observed.

## Outcome source and timing

The realized outcome for each forecast is the same position-specific CFBD
production anchor used by the locked v2 modeling contract:

- QB: passing yards
- RB: rushing yards
- WR: receiving yards
- TE: receiving yards
- DB: total tackles
- DL: total tackles
- EDGE: total tackles
- LB: total tackles

Outcome collection must use the same CFBD player-season statistics semantics
used to construct the historical bridge.

A 2026 outcome is considered final only after the 2026 season source has been
refreshed at a clearly documented post-season cutoff. The first official
scorecard must record the extraction timestamp and source-manifest hashes.

## Cohort accounting

Evaluation begins with all 2,074 frozen forecast rows.

Each row must be assigned exactly one final outcome-accounting state:

1. `observed_target`
2. `linked_no_target_stat`
3. `identity_or_destination_unverifiable`
4. `source_not_final_or_unavailable`

No row may be silently dropped.

The primary v2 production-error metrics are computed only on
`observed_target` rows because the v2 model was trained on observed
position-specific production targets.

Rows without an observed target must remain visible in the scorecard and are
reported separately. They must not be converted to zero unless a separately
locked study establishes that the CFBD source semantics justify zero for that
position/metric.

This distinction is intentional: absence of a CFBD target stat is not
pre-registered as proof of zero production or proof that the player did not
play.

## Primary metrics

For each position group separately, report on `observed_target` rows:

- N evaluated
- mean absolute error (MAE)
- root mean squared error (RMSE)
- median absolute error
- mean signed error (forecast minus observed)
- Pearson correlation, when defined
- R-squared, when defined

The project must not aggregate raw production values across unlike position
groups because the target units differ by position.

## Locked baseline comparisons

### Historical-mean baseline

For every evaluable 2026 row, compare the frozen model forecast to a
position-specific historical-mean baseline computed using only historical
training data available before 2026.

The historical baseline must be reconstructed from the locked v2 training
contract, not recalculated using 2026 outcomes.

For each position group, report:

- model MAE
- historical-mean MAE
- MAE skill = `1 - model_MAE / baseline_MAE`
- paired row-level MAE difference

### Returning-production baseline

On the subset where `baseline_pre_production` was observed in the frozen
forecast artifact, compare:

- frozen model forecast
- returning-production prediction = frozen `baseline_pre_production`

The model and returning-production baseline must be evaluated on exactly the
same paired rows.

Report:

- paired N
- model MAE
- returning-production MAE
- MAE skill = `1 - model_MAE / returning_MAE`
- paired row-level MAE difference

No missing prior-production row may be added to the returning-production
comparison by imputation.

## Statistical uncertainty

For each position-group baseline comparison, report a 95% bootstrap confidence
interval for the paired mean absolute-error difference:

`abs(model_error) - abs(baseline_error)`

Bootstrap resampling must occur at the player/forecast-row level within the
position group with a fixed, published random seed and at least 10,000
replicates.

A negative interval favors the model. A positive interval favors the baseline.
Intervals crossing zero are reported as inconclusive rather than as wins.

The scorecard may additionally report a paired forecast-comparison test, but no
test added later may replace or suppress the pre-registered bootstrap result.

## Forecast Support analysis

The frozen presentation labels are descriptive input-support labels, not
confidence estimates.

Accuracy must therefore be reported by:

- STRONG
- STANDARD
- LIMITED

within each position group where sample size is adequate.

For each support tier report:

- forecast count
- observed-target count
- observed-target rate
- MAE
- median absolute error
- mean signed error

No claim of calibrated uncertainty may be made from these tiers alone.

## Missing-outcome / observability reporting

Because historical v2 training required an observed post-transfer target,
the final scorecard must quantify how often a frozen 2026 forecast does not
produce an observed target.

Report, overall and by position:

- total frozen forecasts
- observed-target rows
- linked rows with no target stat
- unverifiable identity/destination rows
- source-unavailable rows
- observed-target rate

This is a coverage/observability analysis. It is not automatically a
participation or playing-time analysis.

Any future v3 model of destination linkage, stat observability, roster
appearance, or participation is evaluated separately and must not be used to
retroactively alter this v2 scorecard.

## Forecast modifications

The following are prohibited after outcome observation for purposes of the
official v2 scorecard:

- clipping or replacing frozen predictions
- changing position target definitions
- changing the 2,074-row forecast population
- removing poor-performing rows except through the pre-registered accounting
  states above
- changing baseline definitions
- changing primary error metrics
- relabeling Forecast Support as confidence
- using 2026 realized outcomes to regenerate the v2 predictions

Any correction to source identity must be documented row-by-row and accompanied
by an immutable correction log. The original forecast value remains preserved.

## Scorecard outputs

The official post-season evaluation must publish at minimum:

1. a row-level evaluation artifact containing frozen forecast, realized outcome,
   accounting state, model error, and available baseline errors;
2. a machine-readable JSON summary;
3. a human-readable markdown report;
4. SHA-256 hashes for all three;
5. source/extraction provenance for the finalized 2026 outcome data.

The row-level artifact should preserve `portal_key` so every published forecast
can be traced to its frozen release record.

## Reporting rules

The project may say:

- how accurately the frozen 2026 forecasts performed after outcomes are known;
- whether the model beat the locked baselines on paired rows;
- how performance varied by position and Forecast Support tier;
- what fraction of frozen forecasts had observable position-specific outcomes.

The project must not infer from this evaluation:

- causal effects of transferring;
- causal effects of destination schools;
- accuracy for players outside the frozen cohort;
- participation from absence of a target stat unless separately validated;
- calibrated confidence from Forecast Support.

## Publication timing

The official v2 scorecard is published only after the 2026 source is declared
final under the documented cutoff.

Interim monitoring may be performed during the season, but it must be labeled
interim and must not modify this protocol or the frozen release.

## Governance

This protocol is intentionally committed before 2026 outcomes are used for the
official scorecard. Any future amendment must:

1. preserve this version in Git history;
2. state the reason for the amendment;
3. identify whether 2026 outcomes had been inspected before the amendment;
4. never silently replace the original protocol.
