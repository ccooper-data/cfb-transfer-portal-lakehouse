from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Mapping

from .position_targets import TARGET_SPECS, model_position_group
from .rolling_backtest_v2 import (
    FEATURE_SPECS,
    _choose_alpha,
    _fit_ridge,
    _float,
    _predict,
    _season,
)


SCORING_SEASON = 2026
TRAINING_SEASONS = (2021, 2022, 2023, 2024, 2025)

# Only groups with at least one evaluated fold in the locked v2 rolling backtest
# are eligible for 2026 scoring. P had no evaluable fold; K had no training
# cohort in the locked v2 evidence.
SCOREABLE_GROUPS = ("DB", "DL", "EDGE", "LB", "QB", "RB", "TE", "WR")


def _pre_anchor_column(group: str) -> str:
    category, stat_type = TARGET_SPECS[group]
    return f"pre_{category}_{stat_type}"


def build_2026_scoring_cohort(
    matrix_rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Build the target-free 2026 scoring cohort from the full feature matrix.

    The scoring cohort retains players with missing prior production. It never
    copies post-transfer production fields and does not require a 2026 outcome.
    """
    scoring: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    by_group: dict[str, Counter[str]] = defaultdict(Counter)

    for raw in matrix_rows:
        row = dict(raw)
        if int(str(row.get("portal_season"))) != SCORING_SEASON:
            continue

        group = model_position_group(row.get("portal_position"))
        counts = by_group[group]
        counts["source_rows"] += 1

        if group not in TARGET_SPECS:
            counts["excluded_unsupported_position"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": SCORING_SEASON,
                "player_id": row.get("player_id"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "exclusion_reason": "unsupported_position_target",
            })
            continue

        if group not in SCOREABLE_GROUPS:
            counts["excluded_insufficient_validation_evidence"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": SCORING_SEASON,
                "player_id": row.get("player_id"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "exclusion_reason": "insufficient_locked_v2_validation_evidence",
            })
            continue

        features = FEATURE_SPECS[group]
        pre_anchor_col = _pre_anchor_column(group)
        baseline_pre = _float(row.get(pre_anchor_col))

        output: dict[str, object] = {
            "portal_key": row.get("portal_key"),
            "portal_season": SCORING_SEASON,
            "transfer_date": row.get("transfer_date"),
            "player_id": row.get("player_id"),
            "portal_first_name": row.get("portal_first_name"),
            "portal_last_name": row.get("portal_last_name"),
            "portal_position": row.get("portal_position"),
            "model_position_group": group,
            "origin": row.get("origin"),
            "destination": row.get("destination"),
            "rating": row.get("rating"),
            "stars": row.get("stars"),
            "eligibility": row.get("eligibility"),
            "match_strategy": row.get("match_strategy"),
            "roster_match_season": row.get("roster_match_season"),
            "target_metric": "_".join(TARGET_SPECS[group]),
            "baseline_pre_production": baseline_pre,
            "baseline_pre_production_missing": baseline_pre is None,
            "post_outcome_status": "right_censored_unobserved",
        }

        feature_missing_count = 0
        for feature in features:
            if feature == "baseline_pre_production":
                value = baseline_pre
            else:
                value = row.get(feature)
            output[feature] = value
            missing = _float(value) is None
            output[f"missing_{feature}"] = missing
            feature_missing_count += int(missing)

        output["model_feature_count"] = len(features)
        output["model_feature_missing_count"] = feature_missing_count
        output["model_feature_observed_count"] = len(features) - feature_missing_count

        scoring.append(output)
        counts["scoreable_rows"] += 1
        counts["pre_anchor_observed"] += int(baseline_pre is not None)
        counts["pre_anchor_missing"] += int(baseline_pre is None)

    summary = {
        "scoring_season": SCORING_SEASON,
        "scoreable_groups": list(SCOREABLE_GROUPS),
        "scoreable_rows": len(scoring),
        "excluded_rows": len(exclusions),
        "pre_anchor_observed_rows": sum(
            int(not bool(row["baseline_pre_production_missing"]))
            for row in scoring
        ),
        "pre_anchor_missing_rows": sum(
            int(bool(row["baseline_pre_production_missing"]))
            for row in scoring
        ),
        "by_position_group": {
            group: dict(by_group[group]) for group in sorted(by_group)
        },
        "policy": {
            "outcome_requirement": "none; 2026 outcomes are right-censored",
            "missing_pre_policy": (
                "retain row; same training-fold median imputation and explicit "
                "missingness channels used by locked v2 model"
            ),
            "post_transfer_predictors": "prohibited",
            "scoreable_group_rule": (
                "must have evaluable locked v2 rolling-backtest evidence"
            ),
            "causal_claim": False,
        },
    }
    return scoring, exclusions, summary


def fit_and_score_2026(
    training_rows: Iterable[Mapping[str, object]],
    scoring_rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Fit final v2 position models on 2021-2025 and score 2026.

    2025 is allowed in final model development/training. It is not relabeled as
    fresh v2 test evidence. No 2026 outcome is used.
    """
    training = [
        dict(row)
        for row in training_rows
        if _season(row) in TRAINING_SEASONS
        and str(row.get("model_position_group") or "") in SCOREABLE_GROUPS
    ]
    scoring = [
        dict(row)
        for row in scoring_rows
        if int(str(row.get("portal_season"))) == SCORING_SEASON
        and str(row.get("model_position_group") or "") in SCOREABLE_GROUPS
    ]

    train_by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
    score_by_group: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in training:
        train_by_group[str(row["model_position_group"])].append(row)
    for row in scoring:
        score_by_group[str(row["model_position_group"])].append(row)

    predictions: list[dict[str, object]] = []
    model_summary: dict[str, object] = {}

    for group in SCOREABLE_GROUPS:
        train_group = train_by_group.get(group, [])
        score_group = score_by_group.get(group, [])
        features = FEATURE_SPECS[group]

        if not score_group:
            model_summary[group] = {
                "status": "no_2026_scoring_rows",
                "training_rows": len(train_group),
                "scoring_rows": 0,
            }
            continue
        if not train_group:
            raise ValueError(f"No training rows for scoreable group {group}")

        chosen_alpha, cv_scores = _choose_alpha(train_group, features)
        model = _fit_ridge(train_group, features, chosen_alpha)
        group_predictions = _predict(model, score_group)

        for row, prediction in zip(score_group, group_predictions):
            predictions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": SCORING_SEASON,
                "player_id": row.get("player_id"),
                "portal_first_name": row.get("portal_first_name"),
                "portal_last_name": row.get("portal_last_name"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "origin": row.get("origin"),
                "destination": row.get("destination"),
                "target_metric": row.get("target_metric"),
                "predicted_post_transfer_production": prediction,
                "baseline_pre_production": row.get("baseline_pre_production"),
                "baseline_pre_production_missing": row.get(
                    "baseline_pre_production_missing"
                ),
                "model_feature_missing_count": row.get(
                    "model_feature_missing_count"
                ),
                "chosen_alpha": chosen_alpha,
                "training_rows": len(train_group),
                "forecast_status": "unobserved_2026_outcome",
            })

        model_summary[group] = {
            "status": "scored",
            "training_rows": len(train_group),
            "training_seasons": list(TRAINING_SEASONS),
            "scoring_rows": len(score_group),
            "chosen_alpha": chosen_alpha,
            "expanding_validation_mae_by_alpha": cv_scores,
            "features": list(features),
        }

    summary = {
        "scoring_season": SCORING_SEASON,
        "training_seasons": list(TRAINING_SEASONS),
        "training_rows": len(training),
        "scoring_rows": len(scoring),
        "prediction_rows": len(predictions),
        "scoreable_groups": list(SCOREABLE_GROUPS),
        "models": model_summary,
        "governance": {
            "locked_backtest_modified": False,
            "2025_role": (
                "development/final-training data only; not fresh v2 test evidence"
            ),
            "2026_outcome_used": False,
            "prediction_interpretation": (
                "forecast of position-specific post-transfer production anchor"
            ),
            "accuracy_claim_for_2026": "none until outcomes are observed",
            "causal_claim": False,
        },
    }
    return predictions, summary
