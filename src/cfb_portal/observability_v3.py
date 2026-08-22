from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable, Mapping

from .position_targets import TARGET_SPECS, model_position_group
from .rolling_backtest_v2 import (
    FEATURE_SPECS,
    _fit_preprocessor,
    _solve_linear_system,
    _transform,
)

BACKTEST_YEARS = (2022, 2023, 2024)
SCOREABLE_GROUPS = ("DB", "DL", "EDGE", "LB", "QB", "RB", "TE", "WR")
MIN_TRAIN_ROWS = 40
MIN_HOLDOUT_ROWS = 20
MIN_TRAIN_CLASS_ROWS = 5
L2_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
DEFAULT_L2 = 1.0
MAX_NEWTON_ITERATIONS = 50
NEWTON_TOLERANCE = 1e-7
PROBABILITY_EPSILON = 1e-9


def _season(row: Mapping[str, object]) -> int:
    return int(str(row["portal_season"]))


def _present(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def _binary(value: object) -> int:
    if value in (True, 1, "1", "true", "True"):
        return 1
    if value in (False, 0, "0", "false", "False", None, ""):
        return 0
    raise ValueError(f"Expected binary value, got {value!r}")


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _clamp_probability(value: float) -> float:
    return min(1.0 - PROBABILITY_EPSILON, max(PROBABILITY_EPSILON, value))


def build_target_observability_rows(
    bridge_rows: Iterable[Mapping[str, object]],
    feature_rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Build the locked v3 historical target-observability cohort.

    Population:
    - 2021-2025 only;
    - same-season conservative destination-roster linkage;
    - post-season stats source available;
    - one of the eight v2 scoreable position groups.

    The output intentionally carries only pre-transfer/scoring-time predictors
    plus observability labels. No `post_*` production column is retained.
    """
    features_by_key = {
        str(row["portal_key"]): dict(row)
        for row in feature_rows
        if row.get("portal_key") not in (None, "")
    }

    cohort: list[dict[str, object]] = []
    accounting: Counter[str] = Counter()
    by_group: dict[str, Counter[str]] = defaultdict(Counter)
    by_season: dict[int, Counter[str]] = defaultdict(Counter)

    for raw_bridge in bridge_rows:
        bridge = dict(raw_bridge)
        accounting["bridge_rows"] += 1

        season = _season(bridge)
        if season < 2021 or season > 2025:
            accounting["excluded_outside_2021_2025"] += 1
            continue

        roster_match_season = bridge.get("roster_match_season")
        if roster_match_season in (None, "") or int(roster_match_season) != season:
            accounting["excluded_not_same_season_roster_link"] += 1
            continue

        if not bool(bridge.get("post_stats_source_available")):
            accounting["excluded_post_stats_source_unavailable"] += 1
            continue

        group = model_position_group(bridge.get("portal_position"))
        if group not in SCOREABLE_GROUPS:
            accounting["excluded_unsupported_position"] += 1
            continue

        key = str(bridge.get("portal_key") or "")
        feature = features_by_key.get(key)
        if feature is None:
            accounting["excluded_missing_feature_row"] += 1
            continue

        category, stat_type = TARGET_SPECS[group]
        target_column = f"post_{category}_{stat_type}"
        pre_target_column = f"pre_{category}_{stat_type}"
        target_observed = int(_present(feature.get(target_column)))
        any_stat_observed = int(bool(bridge.get("post_has_player_stats")))
        destination_stat_observed = int(
            bool(bridge.get("post_has_destination_stats"))
        )

        output: dict[str, object] = {
            "portal_key": key,
            "portal_season": season,
            "player_id": bridge.get("player_id"),
            "portal_first_name": bridge.get("portal_first_name"),
            "portal_last_name": bridge.get("portal_last_name"),
            "portal_position": bridge.get("portal_position"),
            "model_position_group": group,
            "origin": bridge.get("origin"),
            "destination": bridge.get("destination"),
            "target_metric": f"{category}_{stat_type}",
            "target_observed": target_observed,
            "any_stat_observed": any_stat_observed,
            "destination_stat_observed": destination_stat_observed,
            "any_stat_no_target": int(
                any_stat_observed == 1 and target_observed == 0
            ),
            "no_any_stat": int(any_stat_observed == 0),
            "baseline_pre_production": feature.get(pre_target_column),
        }

        for predictor in FEATURE_SPECS[group]:
            if predictor == "baseline_pre_production":
                continue
            if predictor.startswith("post_"):
                raise ValueError(
                    f"Locked v3 predictor contract prohibits {predictor!r}"
                )
            output[predictor] = feature.get(predictor)

        if any(name.startswith("post_") for name in output):
            raise ValueError("v3 observability cohort retained a post_* field")

        cohort.append(output)
        accounting["cohort_rows"] += 1
        accounting["target_observed"] += target_observed
        accounting["target_missing"] += 1 - target_observed
        accounting["any_stat_observed"] += any_stat_observed
        accounting["any_stat_no_target"] += output["any_stat_no_target"]
        accounting["no_any_stat"] += output["no_any_stat"]

        for bucket in (by_group[group], by_season[season]):
            bucket["rows"] += 1
            bucket["target_observed"] += target_observed
            bucket["target_missing"] += 1 - target_observed
            bucket["any_stat_observed"] += any_stat_observed
            bucket["any_stat_no_target"] += output["any_stat_no_target"]
            bucket["no_any_stat"] += output["no_any_stat"]

    summary = {
        "population_contract": {
            "seasons": [2021, 2022, 2023, 2024, 2025],
            "same_season_destination_roster_link_required": True,
            "post_stats_source_available_required": True,
            "scoreable_position_groups": list(SCOREABLE_GROUPS),
            "missing_target_converted_to_zero": False,
            "post_transfer_predictors_retained": False,
            "interpretation": "CFBD target observability, not participation",
        },
        "accounting": dict(accounting),
        "by_position_group": {
            group: dict(by_group[group]) for group in sorted(by_group)
        },
        "by_season": {
            str(season): dict(by_season[season])
            for season in sorted(by_season)
        },
    }
    return cohort, summary


def _fit_logistic(
    rows: list[Mapping[str, object]],
    features: tuple[str, ...],
    l2: float,
) -> dict[str, object]:
    if not rows:
        raise ValueError("Cannot fit logistic regression with no rows")
    y = [_binary(row.get("target_observed")) for row in rows]
    if len(set(y)) < 2:
        raise ValueError("Logistic training rows require both classes")

    preprocessor = _fit_preprocessor(rows, features)
    matrix = _transform(rows, features, preprocessor)
    p = len(matrix[0])
    coefficients = [0.0 for _ in range(p)]
    converged = False
    iterations = 0

    for iteration in range(1, MAX_NEWTON_ITERATIONS + 1):
        iterations = iteration
        probabilities = [
            _sigmoid(sum(xj * bj for xj, bj in zip(values, coefficients)))
            for values in matrix
        ]

        gradient = [0.0 for _ in range(p)]
        information = [[0.0 for _ in range(p)] for _ in range(p)]

        for values, target, probability in zip(matrix, y, probabilities):
            residual = float(target) - probability
            weight = max(
                PROBABILITY_EPSILON,
                probability * (1.0 - probability),
            )
            for i in range(p):
                gradient[i] += values[i] * residual
                for j in range(p):
                    information[i][j] += weight * values[i] * values[j]

        information[0][0] += 1e-8
        for i in range(1, p):
            gradient[i] -= l2 * coefficients[i]
            information[i][i] += l2

        step = _solve_linear_system(information, gradient)
        coefficients = [
            coefficient + delta
            for coefficient, delta in zip(coefficients, step)
        ]

        if max(abs(delta) for delta in step) < NEWTON_TOLERANCE:
            converged = True
            break

    return {
        "features": features,
        "l2": float(l2),
        "preprocessor": preprocessor,
        "coefficients": coefficients,
        "converged": converged,
        "iterations": iterations,
    }


def _predict_probability(
    model: Mapping[str, object],
    rows: list[Mapping[str, object]],
) -> list[float]:
    features = tuple(model["features"])
    matrix = _transform(rows, features, model["preprocessor"])
    coefficients = list(model["coefficients"])
    return [
        _clamp_probability(
            _sigmoid(
                sum(value * coefficient for value, coefficient in zip(values, coefficients))
            )
        )
        for values in matrix
    ]


def _roc_auc(actual: list[int], predicted: list[float]) -> float | None:
    positives = sum(actual)
    negatives = len(actual) - positives
    if positives == 0 or negatives == 0:
        return None

    ordered = sorted(
        enumerate(predicted),
        key=lambda item: item[1],
    )
    ranks = [0.0 for _ in predicted]
    start = 0
    while start < len(ordered):
        end = start + 1
        while (
            end < len(ordered)
            and abs(ordered[end][1] - ordered[start][1]) <= 1e-15
        ):
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for index in range(start, end):
            ranks[ordered[index][0]] = average_rank
        start = end

    positive_rank_sum = sum(
        rank for rank, target in zip(ranks, actual) if target == 1
    )
    return (
        positive_rank_sum - (positives * (positives + 1) / 2.0)
    ) / (positives * negatives)


def _average_precision(
    actual: list[int],
    predicted: list[float],
) -> float | None:
    positives = sum(actual)
    if positives == 0:
        return None
    if not predicted:
        return None
    if max(predicted) - min(predicted) <= 1e-15:
        return positives / len(actual)

    ordered = sorted(
        zip(predicted, actual),
        key=lambda item: item[0],
        reverse=True,
    )
    true_positives = 0
    precision_sum = 0.0
    for rank, (_, target) in enumerate(ordered, 1):
        if target == 1:
            true_positives += 1
            precision_sum += true_positives / rank
    return precision_sum / positives


def _calibration_intercept_slope(
    actual: list[int],
    predicted: list[float],
) -> dict[str, float | None]:
    if len(set(actual)) < 2:
        return {"intercept": None, "slope": None}
    logits = [
        math.log(_clamp_probability(p) / (1.0 - _clamp_probability(p)))
        for p in predicted
    ]
    if max(logits) - min(logits) <= 1e-12:
        return {"intercept": None, "slope": None}

    coefficients = [0.0, 1.0]
    try:
        for _ in range(40):
            probabilities = [
                _sigmoid(coefficients[0] + coefficients[1] * logit)
                for logit in logits
            ]
            gradient = [0.0, 0.0]
            information = [[0.0, 0.0], [0.0, 0.0]]
            for logit, target, probability in zip(
                logits,
                actual,
                probabilities,
            ):
                values = (1.0, logit)
                residual = float(target) - probability
                weight = max(
                    PROBABILITY_EPSILON,
                    probability * (1.0 - probability),
                )
                for i in range(2):
                    gradient[i] += values[i] * residual
                    for j in range(2):
                        information[i][j] += weight * values[i] * values[j]
            information[0][0] += 1e-8
            information[1][1] += 1e-8
            step = _solve_linear_system(information, gradient)
            coefficients = [
                coefficient + delta
                for coefficient, delta in zip(coefficients, step)
            ]
            if max(abs(delta) for delta in step) < 1e-7:
                break
    except ValueError:
        return {"intercept": None, "slope": None}

    if not all(math.isfinite(value) for value in coefficients):
        return {"intercept": None, "slope": None}
    return {
        "intercept": coefficients[0],
        "slope": coefficients[1],
    }


def _probability_metrics(
    actual: list[int],
    predicted: list[float],
) -> dict[str, object]:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths differ")
    if not actual:
        return {
            "brier": None,
            "log_loss": None,
            "roc_auc": None,
            "pr_auc": None,
            "calibration_intercept": None,
            "calibration_slope": None,
        }

    probabilities = [_clamp_probability(value) for value in predicted]
    brier = sum(
        (probability - target) ** 2
        for target, probability in zip(actual, probabilities)
    ) / len(actual)
    log_loss = -sum(
        (
            target * math.log(probability)
            + (1 - target) * math.log(1.0 - probability)
        )
        for target, probability in zip(actual, probabilities)
    ) / len(actual)
    calibration = _calibration_intercept_slope(actual, probabilities)

    return {
        "brier": brier,
        "log_loss": log_loss,
        "roc_auc": _roc_auc(actual, probabilities),
        "pr_auc": _average_precision(actual, probabilities),
        "calibration_intercept": calibration["intercept"],
        "calibration_slope": calibration["slope"],
    }


def _reliability_table(
    actual: list[int],
    predicted: list[float],
    bins: int = 10,
) -> list[dict[str, object]]:
    buckets = [
        {"count": 0, "probability_sum": 0.0, "observed_sum": 0}
        for _ in range(bins)
    ]
    for target, probability in zip(actual, predicted):
        p = min(1.0, max(0.0, float(probability)))
        index = min(bins - 1, int(p * bins))
        buckets[index]["count"] += 1
        buckets[index]["probability_sum"] += p
        buckets[index]["observed_sum"] += int(target)

    output: list[dict[str, object]] = []
    for index, bucket in enumerate(buckets):
        count = int(bucket["count"])
        output.append({
            "bin": index + 1,
            "lower_bound": index / bins,
            "upper_bound": (index + 1) / bins,
            "count": count,
            "mean_predicted_probability": (
                None
                if count == 0
                else float(bucket["probability_sum"]) / count
            ),
            "observed_rate": (
                None
                if count == 0
                else int(bucket["observed_sum"]) / count
            ),
        })
    return output


def _class_counts(rows: list[Mapping[str, object]]) -> tuple[int, int]:
    positives = sum(_binary(row.get("target_observed")) for row in rows)
    negatives = len(rows) - positives
    return positives, negatives


def _choose_l2(
    train_rows: list[Mapping[str, object]],
    features: tuple[str, ...],
) -> tuple[float, dict[str, float | None]]:
    years = sorted({_season(row) for row in train_rows})
    validation_years = years[1:]
    if not validation_years:
        return DEFAULT_L2, {
            str(l2): None for l2 in L2_GRID
        }

    scores: dict[str, float | None] = {}
    for l2 in L2_GRID:
        squared_errors: list[float] = []
        for validation_year in validation_years:
            fold_train = [
                row for row in train_rows if _season(row) < validation_year
            ]
            fold_valid = [
                row for row in train_rows if _season(row) == validation_year
            ]
            positives, negatives = _class_counts(fold_train)
            if (
                len(fold_train) < 20
                or len(fold_valid) < 10
                or positives < 3
                or negatives < 3
            ):
                continue
            model = _fit_logistic(fold_train, features, l2)
            probabilities = _predict_probability(model, fold_valid)
            squared_errors.extend(
                (probability - _binary(row.get("target_observed"))) ** 2
                for row, probability in zip(fold_valid, probabilities)
            )
        scores[str(l2)] = (
            None
            if not squared_errors
            else sum(squared_errors) / len(squared_errors)
        )

    finite = [
        (l2, scores[str(l2)])
        for l2 in L2_GRID
        if scores[str(l2)] is not None
    ]
    if not finite:
        return DEFAULT_L2, scores
    return min(finite, key=lambda item: float(item[1]))[0], scores


def evaluate_target_observability_v3(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Run the locked rolling-origin v3 target-observability evaluation."""
    source = [dict(row) for row in rows]
    source_for_primary = [
        row for row in source if _season(row) < 2025
    ]

    by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in source_for_primary:
        group = str(row.get("model_position_group") or "")
        if group in SCOREABLE_GROUPS:
            by_group[group].append(row)

    predictions_out: list[dict[str, object]] = []
    fold_results: list[dict[str, object]] = []

    for holdout_year in BACKTEST_YEARS:
        for group in sorted(by_group):
            features = FEATURE_SPECS[group]
            group_rows = by_group[group]
            train_rows = [
                row for row in group_rows if _season(row) < holdout_year
            ]
            holdout_rows = [
                row for row in group_rows if _season(row) == holdout_year
            ]
            train_positive, train_negative = _class_counts(train_rows)
            holdout_positive, holdout_negative = _class_counts(holdout_rows)

            result: dict[str, object] = {
                "holdout_year": holdout_year,
                "model_position_group": group,
                "train_rows": len(train_rows),
                "holdout_rows": len(holdout_rows),
                "train_positive": train_positive,
                "train_negative": train_negative,
                "holdout_positive": holdout_positive,
                "holdout_negative": holdout_negative,
                "features": list(features),
                "minimum_train_rows": MIN_TRAIN_ROWS,
                "minimum_holdout_rows": MIN_HOLDOUT_ROWS,
                "minimum_train_class_rows": MIN_TRAIN_CLASS_ROWS,
            }

            if (
                len(train_rows) < MIN_TRAIN_ROWS
                or len(holdout_rows) < MIN_HOLDOUT_ROWS
            ):
                result["status"] = "skipped_low_sample"
                fold_results.append(result)
                continue

            if (
                train_positive < MIN_TRAIN_CLASS_ROWS
                or train_negative < MIN_TRAIN_CLASS_ROWS
            ):
                result["status"] = "skipped_low_train_class_count"
                fold_results.append(result)
                continue

            chosen_l2, cv_scores = _choose_l2(train_rows, features)
            model = _fit_logistic(train_rows, features, chosen_l2)
            probabilities = _predict_probability(model, holdout_rows)

            actual = [
                _binary(row.get("target_observed"))
                for row in holdout_rows
            ]
            train_prevalence = train_positive / len(train_rows)
            baseline_probabilities = [
                train_prevalence for _ in holdout_rows
            ]

            model_metrics = _probability_metrics(actual, probabilities)
            baseline_metrics = _probability_metrics(
                actual,
                baseline_probabilities,
            )
            model_brier = float(model_metrics["brier"])
            baseline_brier = float(baseline_metrics["brier"])
            brier_skill = (
                None
                if baseline_brier <= 1e-15
                else 1.0 - (model_brier / baseline_brier)
            )

            for row, target, probability, baseline_probability in zip(
                holdout_rows,
                actual,
                probabilities,
                baseline_probabilities,
            ):
                predictions_out.append({
                    "portal_key": row.get("portal_key"),
                    "portal_season": row.get("portal_season"),
                    "player_id": row.get("player_id"),
                    "portal_first_name": row.get("portal_first_name"),
                    "portal_last_name": row.get("portal_last_name"),
                    "model_position_group": group,
                    "origin": row.get("origin"),
                    "destination": row.get("destination"),
                    "target_metric": row.get("target_metric"),
                    "holdout_year": holdout_year,
                    "target_observed": target,
                    "any_stat_observed": row.get("any_stat_observed"),
                    "observability_probability_v3": probability,
                    "training_prevalence_baseline": baseline_probability,
                    "v3_brier_component": (probability - target) ** 2,
                    "prevalence_brier_component": (
                        baseline_probability - target
                    ) ** 2,
                })

            result.update({
                "status": "evaluated",
                "chosen_l2": chosen_l2,
                "expanding_validation_brier_by_l2": cv_scores,
                "training_target_observed_prevalence": train_prevalence,
                "holdout_target_observed_prevalence": (
                    holdout_positive / len(holdout_rows)
                ),
                "model_converged": bool(model["converged"]),
                "model_iterations": int(model["iterations"]),
                "prevalence_baseline": baseline_metrics,
                "logistic_v3": model_metrics,
                "brier_skill_vs_training_prevalence": brier_skill,
                "model_beats_training_prevalence_brier": (
                    model_brier < baseline_brier
                ),
                "reliability": _reliability_table(
                    actual,
                    probabilities,
                ),
            })
            fold_results.append(result)

    evaluated = [
        result for result in fold_results
        if result["status"] == "evaluated"
    ]
    skipped = [
        result for result in fold_results
        if result["status"] != "evaluated"
    ]

    pooled_actual = [
        int(row["target_observed"]) for row in predictions_out
    ]
    pooled_model = [
        float(row["observability_probability_v3"])
        for row in predictions_out
    ]
    pooled_baseline = [
        float(row["training_prevalence_baseline"])
        for row in predictions_out
    ]

    summary = {
        "evaluation_design": {
            "primary_backtest_years": list(BACKTEST_YEARS),
            "excluded_from_primary_evidence": [2025],
            "training_rule": "for holdout year Y, train only on seasons < Y",
            "primary_metric": "Brier score",
            "model": "L2-regularized logistic regression",
            "hyperparameter_selection": (
                "expanding-year training-only validation using Brier score; "
                "default L2=1.0 when no inner validation fold is available"
            ),
            "preprocessing": (
                "training-fold median imputation, training-fold scaling, "
                "explicit missingness channel"
            ),
            "baseline": (
                "position-group target-observed prevalence estimated from "
                "the outer fold training period"
            ),
            "post_transfer_predictors": "prohibited",
            "interpretation": "target observability, not participation",
            "missing_target_converted_to_zero": False,
        },
        "source_rows_all_seasons": len(source),
        "source_rows_primary_period": len(source_for_primary),
        "evaluated_group_folds": len(evaluated),
        "skipped_group_folds": len(skipped),
        "prediction_rows": len(predictions_out),
        "wins_vs_training_prevalence_brier": sum(
            bool(result["model_beats_training_prevalence_brier"])
            for result in evaluated
        ),
        "pooled_model_metrics": _probability_metrics(
            pooled_actual,
            pooled_model,
        ),
        "pooled_prevalence_baseline_metrics": _probability_metrics(
            pooled_actual,
            pooled_baseline,
        ),
        "pooled_reliability": _reliability_table(
            pooled_actual,
            pooled_model,
        ),
        "fold_results": fold_results,
    }
    return predictions_out, summary
