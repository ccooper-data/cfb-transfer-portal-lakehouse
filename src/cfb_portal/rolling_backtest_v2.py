from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Iterable, Mapping


BACKTEST_YEARS = (2022, 2023, 2024)
MIN_TRAIN_ROWS = 40
MIN_HOLDOUT_ROWS = 20
ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0)
DEFAULT_ALPHA = 10.0

FEATURE_SPECS: dict[str, tuple[str, ...]] = {
    "QB": (
        "baseline_pre_production",
        "pre_passing_att",
        "pre_passing_completions",
        "pre_passing_td",
        "pre_passing_int",
        "pre_passing_pct",
        "pre_passing_ypa",
        "pre_rushing_yds",
        "pre_rushing_td",
        "rating",
        "stars",
    ),
    "RB": (
        "baseline_pre_production",
        "pre_rushing_car",
        "pre_rushing_td",
        "pre_rushing_ypc",
        "pre_receiving_rec",
        "pre_receiving_yds",
        "pre_receiving_td",
        "rating",
        "stars",
    ),
    "WR": (
        "baseline_pre_production",
        "pre_receiving_rec",
        "pre_receiving_td",
        "pre_receiving_ypr",
        "pre_receiving_long",
        "pre_rushing_yds",
        "pre_rushing_td",
        "rating",
        "stars",
    ),
    "TE": (
        "baseline_pre_production",
        "pre_receiving_rec",
        "pre_receiving_td",
        "pre_receiving_ypr",
        "pre_receiving_long",
        "rating",
        "stars",
    ),
    "DB": (
        "baseline_pre_production",
        "pre_defensive_solo",
        "pre_defensive_tfl",
        "pre_defensive_sacks",
        "pre_defensive_pd",
        "pre_interceptions_int",
        "pre_interceptions_yds",
        "rating",
        "stars",
    ),
    "DL": (
        "baseline_pre_production",
        "pre_defensive_solo",
        "pre_defensive_tfl",
        "pre_defensive_sacks",
        "pre_defensive_qb_hur",
        "pre_defensive_pd",
        "rating",
        "stars",
    ),
    "EDGE": (
        "baseline_pre_production",
        "pre_defensive_solo",
        "pre_defensive_tfl",
        "pre_defensive_sacks",
        "pre_defensive_qb_hur",
        "pre_defensive_pd",
        "rating",
        "stars",
    ),
    "LB": (
        "baseline_pre_production",
        "pre_defensive_solo",
        "pre_defensive_tfl",
        "pre_defensive_sacks",
        "pre_defensive_qb_hur",
        "pre_defensive_pd",
        "pre_interceptions_int",
        "rating",
        "stars",
    ),
    "K": (
        "baseline_pre_production",
        "pre_kicking_fga",
        "pre_kicking_fgm",
        "pre_kicking_pct",
        "pre_kicking_xpa",
        "pre_kicking_xpm",
        "rating",
        "stars",
    ),
    "P": (
        "baseline_pre_production",
        "pre_punting_no",
        "pre_punting_yds",
        "pre_punting_long",
        "pre_punting_in_20",
        "pre_punting_tb",
        "rating",
        "stars",
    ),
}


def _float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(f"Expected numeric value, got {value!r}") from exc
    if not math.isfinite(number):
        return None
    return number


def _season(row: Mapping[str, object]) -> int:
    return int(str(row["portal_season"]))


def _target(row: Mapping[str, object]) -> float:
    value = _float(row.get("target_post_production"))
    if value is None:
        raise ValueError("target_post_production must be observed")
    return value


def _fit_preprocessor(
    rows: list[Mapping[str, object]],
    features: tuple[str, ...],
) -> dict[str, list[float]]:
    medians: list[float] = []
    means: list[float] = []
    stds: list[float] = []

    for feature in features:
        observed = [
            value
            for row in rows
            if (value := _float(row.get(feature))) is not None
        ]
        median = statistics.median(observed) if observed else 0.0
        medians.append(float(median))

        imputed = [
            median if (value := _float(row.get(feature))) is None else value
            for row in rows
        ]
        mean = sum(float(v) for v in imputed) / len(imputed)
        variance = sum((float(v) - mean) ** 2 for v in imputed) / len(imputed)
        std = math.sqrt(variance)
        if std < 1e-12:
            std = 1.0
        means.append(mean)
        stds.append(std)

    return {"medians": medians, "means": means, "stds": stds}


def _transform(
    rows: list[Mapping[str, object]],
    features: tuple[str, ...],
    preprocessor: Mapping[str, list[float]],
) -> list[list[float]]:
    medians = list(preprocessor["medians"])
    means = list(preprocessor["means"])
    stds = list(preprocessor["stds"])

    matrix: list[list[float]] = []
    for row in rows:
        values = [1.0]
        for i, feature in enumerate(features):
            raw = _float(row.get(feature))
            missing = 1.0 if raw is None else 0.0
            value = medians[i] if raw is None else raw
            values.append((value - means[i]) / stds[i])
            values.append(missing)
        matrix.append(values)
    return matrix


def _solve_linear_system(
    a: list[list[float]],
    b: list[float],
) -> list[float]:
    n = len(b)
    aug = [list(a[i]) + [float(b[i])] for i in range(n)]

    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("Singular linear system")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]

        pivot_value = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= pivot_value

        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor == 0:
                continue
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    return [aug[i][n] for i in range(n)]


def _fit_ridge(
    rows: list[Mapping[str, object]],
    features: tuple[str, ...],
    alpha: float,
) -> dict[str, object]:
    preprocessor = _fit_preprocessor(rows, features)
    x = _transform(rows, features, preprocessor)
    y = [_target(row) for row in rows]
    p = 1 + (2 * len(features))

    xtx = [[0.0 for _ in range(p)] for _ in range(p)]
    xty = [0.0 for _ in range(p)]

    for values, target in zip(x, y):
        for i in range(p):
            xty[i] += values[i] * target
            for j in range(p):
                xtx[i][j] += values[i] * values[j]

    for i in range(1, p):
        xtx[i][i] += alpha

    coefficients = _solve_linear_system(xtx, xty)
    return {
        "features": features,
        "alpha": alpha,
        "preprocessor": preprocessor,
        "coefficients": coefficients,
    }


def _predict(
    model: Mapping[str, object],
    rows: list[Mapping[str, object]],
) -> list[float]:
    features = tuple(model["features"])
    matrix = _transform(
        rows,
        features,
        model["preprocessor"],
    )
    coefficients = list(model["coefficients"])
    return [
        sum(value * coef for value, coef in zip(values, coefficients))
        for values in matrix
    ]


def _metrics(
    actual: list[float],
    predicted: list[float],
) -> dict[str, float | None]:
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted lengths differ")
    if not actual:
        return {"mae": None, "rmse": None, "r2": None}

    errors = [pred - obs for obs, pred in zip(actual, predicted)]
    mae = sum(abs(err) for err in errors) / len(errors)
    rmse = math.sqrt(sum(err * err for err in errors) / len(errors))
    mean_y = sum(actual) / len(actual)
    ss_tot = sum((obs - mean_y) ** 2 for obs in actual)
    ss_res = sum(err * err for err in errors)
    r2 = None if ss_tot <= 1e-12 else 1.0 - (ss_res / ss_tot)
    return {"mae": mae, "rmse": rmse, "r2": r2}


def _choose_alpha(
    train_rows: list[Mapping[str, object]],
    features: tuple[str, ...],
) -> tuple[float, dict[str, float | None]]:
    years = sorted({_season(row) for row in train_rows})
    validation_years = years[1:]

    if not validation_years:
        return DEFAULT_ALPHA, {
            str(alpha): (None if alpha != DEFAULT_ALPHA else float("nan"))
            for alpha in ALPHAS
        }

    scores: dict[str, float | None] = {}
    for alpha in ALPHAS:
        errors: list[float] = []
        for validation_year in validation_years:
            fold_train = [
                row for row in train_rows if _season(row) < validation_year
            ]
            fold_valid = [
                row for row in train_rows if _season(row) == validation_year
            ]
            if len(fold_train) < 20 or len(fold_valid) < 10:
                continue
            model = _fit_ridge(fold_train, features, alpha)
            predictions = _predict(model, fold_valid)
            errors.extend(
                abs(prediction - _target(row))
                for row, prediction in zip(fold_valid, predictions)
            )
        scores[str(alpha)] = (
            sum(errors) / len(errors) if errors else None
        )

    finite = [
        (alpha, scores[str(alpha)])
        for alpha in ALPHAS
        if scores[str(alpha)] is not None
    ]
    if not finite:
        return DEFAULT_ALPHA, scores

    chosen = min(finite, key=lambda item: float(item[1]))[0]
    return chosen, scores


def evaluate_rolling_backtest_v2(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Evaluate the broader v2 cohort using historical rolling-origin folds.

    Primary evidence uses 2022, 2023 and 2024 only. The already-inspected 2025
    season is deliberately excluded from this evaluator.

    The all-row baseline is the position-specific historical mean post-transfer
    production computed from the fold's training period. Returning production is
    retained as a secondary benchmark only on rows where the pre-transfer anchor
    is actually observed.
    """
    source = [dict(row) for row in rows]
    if any(_season(row) == 2025 for row in source):
        source_for_backtest = [row for row in source if _season(row) < 2025]
    else:
        source_for_backtest = source

    by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in source_for_backtest:
        group = str(row.get("model_position_group") or "")
        by_group[group].append(row)

    predictions_out: list[dict[str, object]] = []
    fold_results: list[dict[str, object]] = []

    for holdout_year in BACKTEST_YEARS:
        for group in sorted(by_group):
            features = FEATURE_SPECS.get(group)
            if not features:
                continue

            group_rows = by_group[group]
            train_rows = [
                row for row in group_rows if _season(row) < holdout_year
            ]
            holdout_rows = [
                row for row in group_rows if _season(row) == holdout_year
            ]

            result: dict[str, object] = {
                "holdout_year": holdout_year,
                "model_position_group": group,
                "train_rows": len(train_rows),
                "holdout_rows": len(holdout_rows),
                "minimum_train_rows": MIN_TRAIN_ROWS,
                "minimum_holdout_rows": MIN_HOLDOUT_ROWS,
                "features": list(features),
            }

            if (
                len(train_rows) < MIN_TRAIN_ROWS
                or len(holdout_rows) < MIN_HOLDOUT_ROWS
            ):
                result["status"] = "skipped_low_sample"
                fold_results.append(result)
                continue

            chosen_alpha, cv_scores = _choose_alpha(train_rows, features)
            model = _fit_ridge(train_rows, features, chosen_alpha)
            model_predictions = _predict(model, holdout_rows)

            actual = [_target(row) for row in holdout_rows]
            historical_mean = sum(_target(row) for row in train_rows) / len(train_rows)
            historical_predictions = [historical_mean for _ in holdout_rows]

            model_metrics = _metrics(actual, model_predictions)
            historical_metrics = _metrics(actual, historical_predictions)

            historical_mae = float(historical_metrics["mae"])
            model_mae = float(model_metrics["mae"])
            historical_skill = (
                None if historical_mae <= 1e-12
                else 1.0 - (model_mae / historical_mae)
            )

            paired_actual: list[float] = []
            paired_model: list[float] = []
            paired_returning: list[float] = []

            for row, actual_y, model_y in zip(
                holdout_rows,
                actual,
                model_predictions,
            ):
                baseline_pre = _float(row.get("baseline_pre_production"))
                if baseline_pre is not None:
                    paired_actual.append(actual_y)
                    paired_model.append(model_y)
                    paired_returning.append(baseline_pre)

                predictions_out.append({
                    "portal_key": row.get("portal_key"),
                    "player_id": row.get("player_id"),
                    "portal_first_name": row.get("portal_first_name"),
                    "portal_last_name": row.get("portal_last_name"),
                    "model_position_group": group,
                    "origin": row.get("origin"),
                    "destination": row.get("destination"),
                    "target_metric": row.get("target_metric"),
                    "holdout_year": holdout_year,
                    "actual_post_production": actual_y,
                    "historical_mean_prediction": historical_mean,
                    "ridge_v2_prediction": model_y,
                    "baseline_pre_production": baseline_pre,
                    "baseline_pre_production_missing": baseline_pre is None,
                    "historical_mean_absolute_error": abs(
                        historical_mean - actual_y
                    ),
                    "ridge_v2_absolute_error": abs(model_y - actual_y),
                    "returning_production_absolute_error": (
                        None
                        if baseline_pre is None
                        else abs(baseline_pre - actual_y)
                    ),
                })

            paired_model_metrics = _metrics(paired_actual, paired_model)
            returning_metrics = _metrics(paired_actual, paired_returning)
            returning_mae = returning_metrics["mae"]
            paired_model_mae = paired_model_metrics["mae"]
            returning_skill = (
                None
                if returning_mae is None or float(returning_mae) <= 1e-12
                else 1.0 - (
                    float(paired_model_mae) / float(returning_mae)
                )
            )

            result.update({
                "status": "evaluated",
                "chosen_alpha": chosen_alpha,
                "expanding_validation_mae_by_alpha": cv_scores,
                "all_row_historical_mean_baseline": historical_metrics,
                "all_row_ridge_v2": model_metrics,
                "all_row_mae_skill_vs_historical_mean": historical_skill,
                "all_row_model_beats_historical_mean_mae": (
                    model_mae < historical_mae
                ),
                "paired_rows_with_observed_pre_anchor": len(paired_actual),
                "paired_returning_production_baseline": returning_metrics,
                "paired_ridge_v2": paired_model_metrics,
                "paired_mae_skill_vs_returning_production": returning_skill,
                "paired_model_beats_returning_production_mae": (
                    returning_mae is not None
                    and paired_model_mae is not None
                    and float(paired_model_mae) < float(returning_mae)
                ),
            })
            fold_results.append(result)

    evaluated = [
        result for result in fold_results if result["status"] == "evaluated"
    ]
    skipped = [
        result for result in fold_results if result["status"] != "evaluated"
    ]

    all_row_wins = sum(
        bool(result["all_row_model_beats_historical_mean_mae"])
        for result in evaluated
    )
    paired_wins = sum(
        bool(result["paired_model_beats_returning_production_mae"])
        for result in evaluated
        if int(result["paired_rows_with_observed_pre_anchor"]) > 0
    )

    summary = {
        "evaluation_design": {
            "evidence_backtest_years": list(BACKTEST_YEARS),
            "excluded_from_primary_v2_evidence": [2025],
            "exclusion_reason_2025": (
                "2025 was already inspected under the locked v1 evaluation; "
                "it is not treated as fresh untouched v2 test evidence"
            ),
            "training_rule": "for holdout year Y, train only on seasons < Y",
            "hyperparameter_selection": (
                "expanding-year validation within each fold's training years only; "
                "default alpha 10.0 when no internal validation year is available"
            ),
            "minimum_train_rows": MIN_TRAIN_ROWS,
            "minimum_holdout_rows": MIN_HOLDOUT_ROWS,
            "primary_baseline": (
                "position-specific historical mean post-transfer production "
                "computed from the fold training period; available for every row"
            ),
            "secondary_baseline": (
                "returning production on the observed-pre-anchor subset only"
            ),
            "missing_pre_policy": (
                "retain rows; training-fold median imputation plus explicit "
                "missingness channel per numeric feature"
            ),
            "post_transfer_predictors": "prohibited",
            "causal_claim": False,
        },
        "source_rows_all_seasons": len(source),
        "source_rows_primary_backtest_period": len(source_for_backtest),
        "evaluated_group_folds": len(evaluated),
        "skipped_group_folds": len(skipped),
        "prediction_rows": len(predictions_out),
        "all_row_wins_vs_historical_mean": all_row_wins,
        "paired_subset_wins_vs_returning_production": paired_wins,
        "fold_results": fold_results,
    }
    return predictions_out, summary
