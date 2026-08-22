from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Iterable, Mapping


HOLDOUT_SEASON = 2025
MIN_TRAIN_ROWS = 50
MIN_HOLDOUT_ROWS = 10
ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0)

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


def _baseline(row: Mapping[str, object]) -> float:
    value = _float(row.get("baseline_pre_production"))
    if value is None:
        raise ValueError("baseline_pre_production must be observed")
    return value


def _fit_preprocessor(
    rows: list[Mapping[str, object]],
    features: tuple[str, ...],
) -> tuple[list[float], list[float], list[float]]:
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
            _float(row.get(feature))
            if _float(row.get(feature)) is not None
            else median
            for row in rows
        ]
        mean = sum(float(v) for v in imputed) / len(imputed)
        variance = sum((float(v) - mean) ** 2 for v in imputed) / len(imputed)
        std = math.sqrt(variance)
        if std < 1e-12:
            std = 1.0
        means.append(mean)
        stds.append(std)

    return medians, means, stds


def _transform(
    rows: list[Mapping[str, object]],
    features: tuple[str, ...],
    medians: list[float],
    means: list[float],
    stds: list[float],
) -> list[list[float]]:
    matrix: list[list[float]] = []
    for row in rows:
        values = [1.0]
        for i, feature in enumerate(features):
            raw = _float(row.get(feature))
            value = medians[i] if raw is None else raw
            values.append((value - means[i]) / stds[i])
        matrix.append(values)
    return matrix


def _solve_linear_system(a: list[list[float]], b: list[float]) -> list[float]:
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
    medians, means, stds = _fit_preprocessor(rows, features)
    x = _transform(rows, features, medians, means, stds)
    y = [_target(row) for row in rows]
    p = len(features) + 1

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
        "medians": medians,
        "means": means,
        "stds": stds,
        "coefficients": coefficients,
    }


def _predict(model: Mapping[str, object], rows: list[Mapping[str, object]]) -> list[float]:
    features = tuple(model["features"])
    x = _transform(
        rows,
        features,
        list(model["medians"]),
        list(model["means"]),
        list(model["stds"]),
    )
    coefficients = list(model["coefficients"])
    return [
        sum(value * coef for value, coef in zip(values, coefficients))
        for values in x
    ]


def _metrics(actual: list[float], predicted: list[float]) -> dict[str, float | None]:
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
) -> tuple[float, dict[str, float]]:
    years = sorted({_season(row) for row in train_rows})
    validation_years = years[1:]
    scores: dict[str, float] = {}

    if not validation_years:
        return 10.0, {"10.0": float("nan")}

    for alpha in ALPHAS:
        absolute_errors: list[float] = []
        for validation_year in validation_years:
            fold_train = [
                row for row in train_rows
                if _season(row) < validation_year
            ]
            fold_valid = [
                row for row in train_rows
                if _season(row) == validation_year
            ]
            if len(fold_train) < 10 or len(fold_valid) < 5:
                continue
            model = _fit_ridge(fold_train, features, alpha)
            predictions = _predict(model, fold_valid)
            absolute_errors.extend(
                abs(pred - _target(row))
                for row, pred in zip(fold_valid, predictions)
            )

        score = (
            sum(absolute_errors) / len(absolute_errors)
            if absolute_errors else float("inf")
        )
        scores[str(alpha)] = score

    chosen = min(ALPHAS, key=lambda alpha: scores.get(str(alpha), float("inf")))
    return chosen, scores


def evaluate_2025_holdout(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Evaluate position-specific ridge models on a strict 2025 holdout.

    Models train only on portal seasons 2021-2024. Hyperparameter selection
    uses expanding-year validation wholly inside the training period.
    The primary benchmark is returning production: predict 2025 production
    with the player's observed pre-transfer anchor production.
    """
    source = [dict(row) for row in rows]
    by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in source:
        group = str(row.get("model_position_group") or "")
        by_group[group].append(row)

    predictions_out: list[dict[str, object]] = []
    position_results: dict[str, object] = {}

    for group in sorted(by_group):
        group_rows = by_group[group]
        features = FEATURE_SPECS.get(group)
        if not features:
            continue

        train_rows = [row for row in group_rows if _season(row) < HOLDOUT_SEASON]
        holdout_rows = [row for row in group_rows if _season(row) == HOLDOUT_SEASON]

        base_result: dict[str, object] = {
            "train_rows": len(train_rows),
            "holdout_rows": len(holdout_rows),
            "features": list(features),
            "target_metric": (
                str(group_rows[0].get("target_metric") or "")
                if group_rows else ""
            ),
        }

        if len(train_rows) < MIN_TRAIN_ROWS or len(holdout_rows) < MIN_HOLDOUT_ROWS:
            base_result.update({
                "status": "skipped_low_sample",
                "minimum_train_rows": MIN_TRAIN_ROWS,
                "minimum_holdout_rows": MIN_HOLDOUT_ROWS,
            })
            position_results[group] = base_result
            continue

        alpha, cv_scores = _choose_alpha(train_rows, features)
        model = _fit_ridge(train_rows, features, alpha)
        model_predictions = _predict(model, holdout_rows)

        actual = [_target(row) for row in holdout_rows]
        baseline_predictions = [_baseline(row) for row in holdout_rows]

        model_metrics = _metrics(actual, model_predictions)
        baseline_metrics = _metrics(actual, baseline_predictions)

        baseline_mae = float(baseline_metrics["mae"])
        model_mae = float(model_metrics["mae"])
        skill = (
            None if baseline_mae <= 1e-12
            else 1.0 - (model_mae / baseline_mae)
        )

        base_result.update({
            "status": "evaluated",
            "chosen_alpha": alpha,
            "expanding_validation_mae_by_alpha": cv_scores,
            "baseline_returning_production": baseline_metrics,
            "ridge_numeric_profile": model_metrics,
            "mae_skill_vs_returning_production": skill,
            "model_beats_baseline_mae": model_mae < baseline_mae,
        })
        position_results[group] = base_result

        for row, actual_y, baseline_y, model_y in zip(
            holdout_rows,
            actual,
            baseline_predictions,
            model_predictions,
        ):
            predictions_out.append({
                "portal_key": row.get("portal_key"),
                "player_id": row.get("player_id"),
                "portal_first_name": row.get("portal_first_name"),
                "portal_last_name": row.get("portal_last_name"),
                "model_position_group": group,
                "origin": row.get("origin"),
                "destination": row.get("destination"),
                "target_metric": row.get("target_metric"),
                "portal_season": HOLDOUT_SEASON,
                "actual_post_production": actual_y,
                "returning_production_prediction": baseline_y,
                "ridge_prediction": model_y,
                "baseline_absolute_error": abs(baseline_y - actual_y),
                "ridge_absolute_error": abs(model_y - actual_y),
            })

    evaluated = [
        result
        for result in position_results.values()
        if result.get("status") == "evaluated"
    ]
    wins = sum(bool(result["model_beats_baseline_mae"]) for result in evaluated)

    summary = {
        "evaluation_design": {
            "train_seasons": [2021, 2022, 2023, 2024],
            "holdout_season": HOLDOUT_SEASON,
            "hyperparameter_selection": (
                "expanding-year validation within 2021-2024 only"
            ),
            "primary_baseline": (
                "returning production: pre-transfer anchor predicts "
                "post-transfer anchor"
            ),
            "model": "position-specific ridge regression, numeric pre-transfer profile",
            "causal_claim": False,
        },
        "source_modeling_rows": len(source),
        "holdout_prediction_rows": len(predictions_out),
        "evaluated_position_groups": len(evaluated),
        "position_groups_beating_baseline_mae": wins,
        "position_results": position_results,
        "leakage_controls": {
            "holdout_2025_never_used_for_fit": True,
            "holdout_2025_never_used_for_alpha_selection": True,
            "post_features_used_as_predictors": False,
            "feature_specs": {
                group: list(features)
                for group, features in sorted(FEATURE_SPECS.items())
            },
        },
    }
    return predictions_out, summary
