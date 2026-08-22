from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Iterable, Mapping


HOLDOUT_SEASON = 2025
MIN_TRAIN_ROWS = 40
MIN_HOLDOUT_ROWS = 10
ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0)

TARGET_STAT_KEYS: dict[str, tuple[str, str]] = {
    "passing_yds": ("passing", "yds"),
    "rushing_yds": ("rushing", "yds"),
    "receiving_yds": ("receiving", "yds"),
    "defensive_tot": ("defensive", "tot"),
    "kicking_pts": ("kicking", "pts"),
    "punting_ypp": ("punting", "ypp"),
}

FUTURE_NUMERIC_FEATURES = ("destination_prior_change_signal", "rating", "stars")


def _float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
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


def build_negative_control_panel(
    modeling_rows: Iterable[Mapping[str, object]],
    player_stats_by_year: Mapping[int, Iterable[Mapping[str, object]]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Build a falsification panel whose outcome predates the transfer.

    For portal season S, the negative-control outcome is:
        production(S-1) - production(S-2)

    The future-side features used later are destination, portal rating, and
    stars. Because the target is completed before the portal move, predictive
    signal from those features is evidence of selection/confounding, not a
    transfer effect.

    Rows with missing or ambiguous S-2 anchor production are excluded rather
    than zero-imputed.
    """
    rows = [dict(row) for row in modeling_rows]
    needed: dict[int, set[tuple[str, str, str]]] = defaultdict(set)

    for row in rows:
        season = _season(row)
        target_metric = str(row.get("target_metric") or "")
        spec = TARGET_STAT_KEYS.get(target_metric)
        player_id = str(row.get("player_id") or "").strip()
        if season >= 2022 and spec and player_id:
            category, stat_type = spec
            needed[season - 2].add((player_id, category, stat_type))

    index: dict[int, dict[tuple[str, str, str], list[float]]] = {}
    for year, raw_rows in player_stats_by_year.items():
        wanted = needed.get(int(year), set())
        by_key: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        if wanted:
            for raw in raw_rows:
                row = dict(raw)
                key = (
                    str(row.get("playerId") or "").strip(),
                    str(row.get("category") or "").strip().casefold(),
                    str(row.get("statType") or "").strip().casefold(),
                )
                if key not in wanted:
                    continue
                value = _float(row.get("stat"))
                if value is not None:
                    by_key[key].append(value)
        index[int(year)] = dict(by_key)

    panel: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    by_group: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        group = str(row.get("model_position_group") or "")
        counts = by_group[group]
        counts["source_rows"] += 1
        season = _season(row)

        if season < 2022:
            counts["excluded_s2_source_unavailable"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": season,
                "model_position_group": group,
                "exclusion_reason": "s2_source_unavailable",
            })
            continue

        target_metric = str(row.get("target_metric") or "")
        spec = TARGET_STAT_KEYS.get(target_metric)
        if spec is None:
            counts["excluded_unsupported_target"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": season,
                "model_position_group": group,
                "target_metric": target_metric,
                "exclusion_reason": "unsupported_target_metric",
            })
            continue

        pre_value = _float(row.get("baseline_pre_production"))
        if pre_value is None:
            counts["excluded_missing_s1_anchor"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": season,
                "model_position_group": group,
                "target_metric": target_metric,
                "exclusion_reason": "missing_s1_anchor",
            })
            continue

        player_id = str(row.get("player_id") or "").strip()
        category, stat_type = spec
        values = index.get(season - 2, {}).get(
            (player_id, category, stat_type),
            [],
        )
        unique_values = sorted(set(values))

        if not unique_values:
            counts["excluded_missing_s2_anchor"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": season,
                "player_id": player_id,
                "model_position_group": group,
                "target_metric": target_metric,
                "exclusion_reason": "missing_s2_anchor",
            })
            continue

        if len(unique_values) > 1:
            counts["excluded_ambiguous_s2_anchor"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": season,
                "player_id": player_id,
                "model_position_group": group,
                "target_metric": target_metric,
                "s2_values": unique_values,
                "exclusion_reason": "ambiguous_s2_anchor",
            })
            continue

        s2_value = unique_values[0]
        panel.append({
            "portal_key": row.get("portal_key"),
            "portal_season": season,
            "player_id": player_id,
            "portal_first_name": row.get("portal_first_name"),
            "portal_last_name": row.get("portal_last_name"),
            "model_position_group": group,
            "origin": row.get("origin"),
            "destination": row.get("destination"),
            "rating": row.get("rating"),
            "stars": row.get("stars"),
            "target_metric": target_metric,
            "s2_season": season - 2,
            "s1_season": season - 1,
            "s2_production": s2_value,
            "s1_production": pre_value,
            "negative_control_prior_change": pre_value - s2_value,
        })
        counts["panel_rows"] += 1

    summary = {
        "source_modeling_rows": len(rows),
        "negative_control_panel_rows": len(panel),
        "excluded_rows": len(exclusions),
        "by_position_group": {
            group: dict(by_group[group])
            for group in sorted(by_group)
        },
        "design": {
            "outcome": "S-1 anchor production minus S-2 anchor production",
            "outcome_timing": "completed before the portal move",
            "future_features": ["destination", "rating", "stars"],
            "interpretation": (
                "predictive signal is selection/confounding evidence, "
                "not evidence that destination caused prior performance"
            ),
            "missing_s2_policy": "exclude; never zero-impute",
            "ambiguous_s2_policy": "exclude conflicting player-season anchor values",
        },
    }
    return panel, exclusions, summary


def _fit_destination_encoding(
    rows: list[Mapping[str, object]],
) -> tuple[dict[str, float], float]:
    targets = [float(row["negative_control_prior_change"]) for row in rows]
    global_mean = sum(targets) / len(targets)
    by_destination: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        destination = str(row.get("destination") or "").strip().casefold()
        if destination:
            by_destination[destination].append(
                float(row["negative_control_prior_change"])
            )
    mapping = {
        destination: sum(values) / len(values)
        for destination, values in by_destination.items()
    }
    return mapping, global_mean


def _with_destination_signal(
    rows: list[Mapping[str, object]],
    mapping: Mapping[str, float],
    fallback: float,
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for raw in rows:
        row = dict(raw)
        destination = str(row.get("destination") or "").strip().casefold()
        row["destination_prior_change_signal"] = float(
            mapping.get(destination, fallback)
        )
        out.append(row)
    return out


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
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def _fit_ridge(
    rows: list[Mapping[str, object]],
    alpha: float,
) -> dict[str, object]:
    features = FUTURE_NUMERIC_FEATURES
    medians, means, stds = _fit_preprocessor(rows, features)
    x = _transform(rows, features, medians, means, stds)
    y = [float(row["negative_control_prior_change"]) for row in rows]
    p = len(features) + 1
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p

    for values, target in zip(x, y):
        for i in range(p):
            xty[i] += values[i] * target
            for j in range(p):
                xtx[i][j] += values[i] * values[j]

    for i in range(1, p):
        xtx[i][i] += alpha

    return {
        "features": features,
        "alpha": alpha,
        "medians": medians,
        "means": means,
        "stds": stds,
        "coefficients": _solve_linear_system(xtx, xty),
    }


def _predict(model: Mapping[str, object], rows: list[Mapping[str, object]]) -> list[float]:
    x = _transform(
        rows,
        tuple(model["features"]),
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


def _choose_alpha(train_rows: list[Mapping[str, object]]) -> tuple[float, dict[str, float]]:
    years = sorted({_season(row) for row in train_rows})
    validation_years = years[1:]
    scores: dict[str, float] = {}

    for alpha in ALPHAS:
        errors: list[float] = []
        for validation_year in validation_years:
            fold_train_raw = [
                row for row in train_rows if _season(row) < validation_year
            ]
            fold_valid_raw = [
                row for row in train_rows if _season(row) == validation_year
            ]
            if len(fold_train_raw) < 20 or len(fold_valid_raw) < 5:
                continue

            mapping, fallback = _fit_destination_encoding(fold_train_raw)
            fold_train = _with_destination_signal(
                fold_train_raw, mapping, fallback
            )
            fold_valid = _with_destination_signal(
                fold_valid_raw, mapping, fallback
            )
            model = _fit_ridge(fold_train, alpha)
            preds = _predict(model, fold_valid)
            errors.extend(
                abs(pred - float(row["negative_control_prior_change"]))
                for row, pred in zip(fold_valid, preds)
            )
        scores[str(alpha)] = (
            sum(errors) / len(errors) if errors else float("inf")
        )

    chosen = min(ALPHAS, key=lambda a: scores.get(str(a), float("inf")))
    return chosen, scores


def evaluate_negative_control_2025(
    panel_rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Evaluate whether future portal information predicts a pre-transfer outcome.

    The strict 2025 holdout is not used for destination encoding, model fitting,
    or alpha selection. A model beating the historical-mean baseline indicates
    selection/confounding signal and strengthens the rationale for avoiding
    causal interpretations of transfer outcomes.
    """
    source = [dict(row) for row in panel_rows]
    by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in source:
        by_group[str(row.get("model_position_group") or "")].append(row)

    predictions: list[dict[str, object]] = []
    results: dict[str, object] = {}

    for group in sorted(by_group):
        rows = by_group[group]
        train_raw = [row for row in rows if _season(row) < HOLDOUT_SEASON]
        holdout_raw = [row for row in rows if _season(row) == HOLDOUT_SEASON]

        result: dict[str, object] = {
            "train_rows": len(train_raw),
            "holdout_rows": len(holdout_raw),
            "target_metric": str(rows[0].get("target_metric") or "") if rows else "",
        }

        if len(train_raw) < MIN_TRAIN_ROWS or len(holdout_raw) < MIN_HOLDOUT_ROWS:
            result.update({
                "status": "skipped_low_sample",
                "minimum_train_rows": MIN_TRAIN_ROWS,
                "minimum_holdout_rows": MIN_HOLDOUT_ROWS,
            })
            results[group] = result
            continue

        alpha, cv_scores = _choose_alpha(train_raw)
        mapping, fallback = _fit_destination_encoding(train_raw)
        train = _with_destination_signal(train_raw, mapping, fallback)
        holdout = _with_destination_signal(holdout_raw, mapping, fallback)

        model = _fit_ridge(train, alpha)
        model_pred = _predict(model, holdout)
        actual = [float(row["negative_control_prior_change"]) for row in holdout]

        train_mean = sum(
            float(row["negative_control_prior_change"]) for row in train_raw
        ) / len(train_raw)
        baseline_pred = [train_mean] * len(holdout)

        model_metrics = _metrics(actual, model_pred)
        baseline_metrics = _metrics(actual, baseline_pred)
        baseline_mae = float(baseline_metrics["mae"])
        model_mae = float(model_metrics["mae"])
        skill = (
            None if baseline_mae <= 1e-12
            else 1.0 - (model_mae / baseline_mae)
        )

        signal = (
            model_mae < baseline_mae
            and model_metrics["r2"] is not None
            and float(model_metrics["r2"]) > 0.0
        )

        result.update({
            "status": "evaluated",
            "chosen_alpha": alpha,
            "expanding_validation_mae_by_alpha": cv_scores,
            "historical_mean_baseline": baseline_metrics,
            "future_portal_metadata_model": model_metrics,
            "mae_skill_vs_historical_mean": skill,
            "negative_control_signal_detected": signal,
            "interpretation": (
                "If true, future portal metadata predicts a performance change "
                "that occurred before the transfer; this is selection/confounding "
                "evidence, not a causal transfer effect."
            ),
        })
        results[group] = result

        for row, observed, base_pred, pred in zip(
            holdout, actual, baseline_pred, model_pred
        ):
            predictions.append({
                "portal_key": row.get("portal_key"),
                "player_id": row.get("player_id"),
                "portal_first_name": row.get("portal_first_name"),
                "portal_last_name": row.get("portal_last_name"),
                "model_position_group": group,
                "origin": row.get("origin"),
                "destination": row.get("destination"),
                "portal_season": HOLDOUT_SEASON,
                "target_metric": row.get("target_metric"),
                "s2_production": row.get("s2_production"),
                "s1_production": row.get("s1_production"),
                "actual_prior_change": observed,
                "historical_mean_prediction": base_pred,
                "future_portal_metadata_prediction": pred,
                "destination_prior_change_signal": row.get(
                    "destination_prior_change_signal"
                ),
            })

    evaluated = [
        result for result in results.values()
        if result.get("status") == "evaluated"
    ]
    signal_groups = sum(
        bool(result.get("negative_control_signal_detected"))
        for result in evaluated
    )

    summary = {
        "source_panel_rows": len(source),
        "holdout_prediction_rows": len(predictions),
        "evaluated_position_groups": len(evaluated),
        "position_groups_with_negative_control_signal": signal_groups,
        "evaluation_design": {
            "train_seasons": [2022, 2023, 2024],
            "holdout_season": HOLDOUT_SEASON,
            "negative_control_outcome": (
                "S-1 anchor production minus S-2 anchor production"
            ),
            "future_features": [
                "destination training-only historical signal",
                "portal rating",
                "portal stars",
            ],
            "destination_encoding": (
                "fit on training rows only; unseen holdout destinations "
                "fall back to training global mean"
            ),
            "hyperparameter_selection": (
                "expanding-year validation inside training period only"
            ),
            "causal_claim": False,
        },
        "position_results": results,
        "guardrails": {
            "2025_used_for_fit": False,
            "2025_used_for_destination_encoding": False,
            "2025_used_for_alpha_selection": False,
            "post_transfer_production_used_as_predictor": False,
            "interpretation": (
                "This is a falsification/selection diagnostic. Signal is expected "
                "to caution against causal attribution, not invalidate predictive "
                "forecasting."
            ),
        },
    }
    return predictions, summary
