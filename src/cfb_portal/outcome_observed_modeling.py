from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Mapping

from .position_targets import TARGET_SPECS, model_position_group


PRE_METADATA_COLUMNS = {
    "pre_season",
    "pre_stats_source_available",
    "pre_has_player_stats",
    "pre_has_origin_stats",
    "pre_team_mismatch",
}


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Expected numeric value, got {value!r}") from exc


def _raw_pre_feature_columns(columns: Iterable[str]) -> list[str]:
    return sorted(
        column
        for column in columns
        if column.startswith("pre_") and column not in PRE_METADATA_COLUMNS
    )


def build_outcome_observed_modeling_table_v2(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Build a broader outcome-observed training table for v2 forecasting.

    Unlike the v1 paired benchmark, a row is retained when the supported
    post-transfer target is observed even if the prior-season anchor or other
    pre-transfer production features are missing. Missing pre-transfer values
    remain null and receive explicit missingness indicators.

    This table is for predictive modeling only. It does not identify causal
    transfer or destination-school effects.
    """
    source_rows = [dict(row) for row in rows]
    if not source_rows:
        return [], [], {
            "source_rows": 0,
            "modeling_rows": 0,
            "excluded_rows": 0,
            "pre_feature_columns": 0,
            "missingness_indicator_columns": 0,
            "by_position_group": {},
            "policy": {},
        }

    all_columns = list(source_rows[0].keys())
    pre_features = _raw_pre_feature_columns(all_columns)

    modeling: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    by_group: dict[str, Counter[str]] = defaultdict(Counter)

    for row in source_rows:
        group = model_position_group(row.get("portal_position"))
        counts = by_group[group]
        counts["source_rows"] += 1

        if bool(row.get("post_outcome_right_censored")):
            counts["excluded_right_censored"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": row.get("portal_season"),
                "player_id": row.get("player_id"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "exclusion_reason": "post_outcome_right_censored",
            })
            continue

        spec = TARGET_SPECS.get(group)
        if spec is None:
            counts["excluded_unsupported_position"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": row.get("portal_season"),
                "player_id": row.get("player_id"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "exclusion_reason": "unsupported_position_target",
            })
            continue

        category, stat_type = spec
        pre_anchor_column = f"pre_{category}_{stat_type}"
        post_target_column = f"post_{category}_{stat_type}"
        target_post = _as_float(row.get(post_target_column))

        if target_post is None:
            counts["excluded_missing_post_target"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": row.get("portal_season"),
                "player_id": row.get("player_id"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "target_metric": f"{category}_{stat_type}",
                "exclusion_reason": "missing_post_target",
            })
            continue

        baseline_pre = _as_float(row.get(pre_anchor_column))
        output: dict[str, object] = {
            "portal_key": row.get("portal_key"),
            "portal_season": row.get("portal_season"),
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
            "target_metric": f"{category}_{stat_type}",
            "baseline_pre_production": baseline_pre,
            "baseline_pre_production_missing": baseline_pre is None,
            "target_post_production": target_post,
            "target_delta": (
                target_post - baseline_pre if baseline_pre is not None else None
            ),
        }

        observed_pre_features = 0
        for feature in pre_features:
            value = row.get(feature)
            output[feature] = value
            missing = value is None or str(value).strip() == ""
            output[f"missing_{feature}"] = missing
            observed_pre_features += int(not missing)

        output["pre_feature_observed_count"] = observed_pre_features
        output["pre_feature_missing_count"] = len(pre_features) - observed_pre_features
        output["any_pre_feature_observed"] = observed_pre_features > 0

        modeling.append(output)
        counts["modeling_rows"] += 1
        counts["missing_pre_anchor"] += int(baseline_pre is None)
        counts["pre_anchor_observed"] += int(baseline_pre is not None)

    summary = {
        "source_rows": len(source_rows),
        "modeling_rows": len(modeling),
        "excluded_rows": len(exclusions),
        "pre_feature_columns": len(pre_features),
        "missingness_indicator_columns": len(pre_features),
        "pre_feature_names": pre_features,
        "rows_missing_pre_anchor": sum(
            int(bool(row["baseline_pre_production_missing"])) for row in modeling
        ),
        "rows_with_pre_anchor": sum(
            int(not bool(row["baseline_pre_production_missing"])) for row in modeling
        ),
        "by_position_group": {
            group: dict(by_group[group]) for group in sorted(by_group)
        },
        "target_specs": {
            group: {
                "pre_anchor": f"pre_{category}_{stat_type}",
                "post_target": f"post_{category}_{stat_type}",
            }
            for group, (category, stat_type) in sorted(TARGET_SPECS.items())
        },
        "policy": {
            "cohort": (
                "supported position group with observed post-transfer target; "
                "prior production is not required"
            ),
            "pre_feature_missingness": (
                "preserve null and add one explicit missingness indicator per "
                "raw pre-transfer production feature"
            ),
            "post_features_as_predictors": "prohibited",
            "resolver_score_as_predictor": "prohibited",
            "right_censored_rows": "excluded from outcome-observed training table",
            "causal_claim": "none; predictive forecasting only",
            "evaluation_status": (
                "v2/exploratory because the 2025 holdout was already inspected "
                "under the locked v1 benchmark"
            ),
        },
    }
    return modeling, exclusions, summary
