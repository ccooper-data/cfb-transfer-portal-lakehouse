from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

from .observability_v3 import (
    MIN_HOLDOUT_ROWS,
    MIN_TRAIN_CLASS_ROWS,
    MIN_TRAIN_ROWS,
    SCOREABLE_GROUPS,
    _binary,
    _choose_l2,
    _class_counts,
    _fit_logistic,
    _predict_probability,
    _probability_metrics,
    _reliability_table,
    _season,
)
from .rolling_backtest_v2 import FEATURE_SPECS

STRESS_TEST_YEAR = 2025
TRAINING_YEARS = (2021, 2022, 2023, 2024)


def evaluate_2025_target_observability_stress_test(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Run the locked 2025 v3 temporal stress test.

    This consumes the already-frozen v3 historical cohort. It does not rebuild
    the cohort and does not modify the first locked 2022-2024 evaluation.
    """
    source = [dict(row) for row in rows]

    by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in source:
        season = _season(row)
        group = str(row.get("model_position_group") or "")
        if (
            group in SCOREABLE_GROUPS
            and season in (*TRAINING_YEARS, STRESS_TEST_YEAR)
        ):
            by_group[group].append(row)

    predictions_out: list[dict[str, object]] = []
    group_results: list[dict[str, object]] = []

    for group in sorted(by_group):
        features = FEATURE_SPECS[group]
        group_rows = by_group[group]

        train_rows = [
            row for row in group_rows if _season(row) in TRAINING_YEARS
        ]
        stress_rows = [
            row for row in group_rows if _season(row) == STRESS_TEST_YEAR
        ]

        train_positive, train_negative = _class_counts(train_rows)
        stress_positive, stress_negative = _class_counts(stress_rows)

        result: dict[str, object] = {
            "stress_test_year": STRESS_TEST_YEAR,
            "model_position_group": group,
            "train_years": list(TRAINING_YEARS),
            "train_rows": len(train_rows),
            "stress_test_rows": len(stress_rows),
            "train_positive": train_positive,
            "train_negative": train_negative,
            "stress_test_positive": stress_positive,
            "stress_test_negative": stress_negative,
            "features": list(features),
            "minimum_train_rows": MIN_TRAIN_ROWS,
            "minimum_stress_test_rows": MIN_HOLDOUT_ROWS,
            "minimum_train_class_rows": MIN_TRAIN_CLASS_ROWS,
        }

        if (
            len(train_rows) < MIN_TRAIN_ROWS
            or len(stress_rows) < MIN_HOLDOUT_ROWS
        ):
            result["status"] = "skipped_low_sample"
            group_results.append(result)
            continue

        if (
            train_positive < MIN_TRAIN_CLASS_ROWS
            or train_negative < MIN_TRAIN_CLASS_ROWS
        ):
            result["status"] = "skipped_low_train_class_count"
            group_results.append(result)
            continue

        chosen_l2, cv_scores = _choose_l2(train_rows, features)
        model = _fit_logistic(train_rows, features, chosen_l2)
        probabilities = _predict_probability(model, stress_rows)

        actual = [
            _binary(row.get("target_observed"))
            for row in stress_rows
        ]
        train_prevalence = train_positive / len(train_rows)
        baseline_probabilities = [
            train_prevalence for _ in stress_rows
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
            stress_rows,
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
                "stress_test_year": STRESS_TEST_YEAR,
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
            "stress_test_target_observed_prevalence": (
                stress_positive / len(stress_rows)
            ),
            "model_converged": bool(model["converged"]),
            "model_iterations": int(model["iterations"]),
            "prevalence_baseline": baseline_metrics,
            "logistic_v3": model_metrics,
            "brier_skill_vs_training_prevalence": brier_skill,
            "model_beats_training_prevalence_brier": (
                model_brier < baseline_brier
            ),
            "reliability": _reliability_table(actual, probabilities),
        })
        group_results.append(result)

    evaluated = [
        result for result in group_results
        if result["status"] == "evaluated"
    ]
    skipped = [
        result for result in group_results
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
            "label": "2025 temporal stress test",
            "stress_test_year": STRESS_TEST_YEAR,
            "training_years": list(TRAINING_YEARS),
            "training_rule": "fit only on portal seasons 2021-2024",
            "aggregate_2025_labels_previously_inspected": True,
            "pristine_holdout_claim": False,
            "primary_metric": "Brier score",
            "model": "same L2-regularized logistic family as locked v3",
            "hyperparameter_selection": (
                "same expanding-year training-only validation using Brier "
                "score; 2025 is never used for L2 selection"
            ),
            "preprocessing": (
                "fit only on 2021-2024 training rows for each position group"
            ),
            "baseline": (
                "position-group target-observed prevalence estimated only "
                "from 2021-2024 training rows"
            ),
            "cohort_source": (
                "frozen outputs/v3_target_observability_cohort_2021_2025.csv"
            ),
            "post_transfer_predictors": "prohibited",
            "interpretation": "target observability, not participation",
            "missing_target_converted_to_zero": False,
        },
        "source_rows": len(source),
        "evaluated_position_groups": len(evaluated),
        "skipped_position_groups": len(skipped),
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
        "position_group_results": group_results,
    }
    return predictions_out, summary
