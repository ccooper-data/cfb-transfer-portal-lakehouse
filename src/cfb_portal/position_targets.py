from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Mapping

from .normalize import normalize_token, position_group


TARGET_SPECS: dict[str, tuple[str, str]] = {
    "QB": ("passing", "yds"),
    "RB": ("rushing", "yds"),
    "WR": ("receiving", "yds"),
    "TE": ("receiving", "yds"),
    "DL": ("defensive", "tot"),
    "EDGE": ("defensive", "tot"),
    "LB": ("defensive", "tot"),
    "DB": ("defensive", "tot"),
    "K": ("kicking", "pts"),
    "P": ("punting", "ypp"),
}


def model_position_group(value: object) -> str:
    raw = normalize_token("" if value is None else str(value)).upper().replace(" ", "")
    if raw in {"K", "PK"}:
        return "K"
    if raw == "P":
        return "P"
    if raw == "LS":
        return "LS"
    grouped = position_group(raw)
    return grouped or "OTHER"


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


def build_position_modeling_table(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Create conservative position-aware predictive targets.

    The target is a transparent anchor production metric for each supported
    position group. Both prior-season and post-transfer anchor values must be
    observed; missing anchors are never converted to zero.

    `target_delta` is descriptive change in observed production, not a causal
    effect of transferring.
    """
    source_rows = [dict(row) for row in rows]
    if not source_rows:
        return [], [], {
            "source_rows": 0,
            "modeling_rows": 0,
            "excluded_rows": 0,
            "by_position_group": {},
            "predictor_policy": {},
        }

    all_columns = list(source_rows[0].keys())
    pre_features = sorted(c for c in all_columns if c.startswith("pre_"))
    post_features = sorted(c for c in all_columns if c.startswith("post_"))

    metadata_predictors = [
        "portal_season",
        "portal_position",
        "origin",
        "destination",
        "rating",
        "stars",
        "eligibility",
    ]
    predictor_columns = metadata_predictors + pre_features

    modeling: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    by_group: dict[str, Counter[str]] = defaultdict(Counter)

    for row in source_rows:
        group = model_position_group(row.get("portal_position"))
        counts = by_group[group]
        counts["source_rows"] += 1

        spec = TARGET_SPECS.get(group)
        if spec is None:
            counts["excluded_unsupported_position"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": row.get("portal_season"),
                "player_id": row.get("player_id"),
                "portal_first_name": row.get("portal_first_name"),
                "portal_last_name": row.get("portal_last_name"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "origin": row.get("origin"),
                "destination": row.get("destination"),
                "exclusion_reason": "unsupported_position_target",
            })
            continue

        category, stat_type = spec
        pre_col = f"pre_{category}_{stat_type}"
        post_col = f"post_{category}_{stat_type}"
        pre_value = _as_float(row.get(pre_col))
        post_value = _as_float(row.get(post_col))

        if pre_value is None:
            counts["excluded_missing_pre_anchor"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": row.get("portal_season"),
                "player_id": row.get("player_id"),
                "portal_first_name": row.get("portal_first_name"),
                "portal_last_name": row.get("portal_last_name"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "origin": row.get("origin"),
                "destination": row.get("destination"),
                "target_metric": f"{category}_{stat_type}",
                "exclusion_reason": "missing_pre_anchor",
            })
            continue

        if post_value is None:
            counts["excluded_missing_post_anchor"] += 1
            exclusions.append({
                "portal_key": row.get("portal_key"),
                "portal_season": row.get("portal_season"),
                "player_id": row.get("player_id"),
                "portal_first_name": row.get("portal_first_name"),
                "portal_last_name": row.get("portal_last_name"),
                "portal_position": row.get("portal_position"),
                "model_position_group": group,
                "origin": row.get("origin"),
                "destination": row.get("destination"),
                "target_metric": f"{category}_{stat_type}",
                "exclusion_reason": "missing_post_anchor",
            })
            continue

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
            "target_metric": f"{category}_{stat_type}",
            "baseline_pre_production": pre_value,
            "target_post_production": post_value,
            "target_delta": post_value - pre_value,
        }

        for feature in pre_features:
            output[feature] = row.get(feature)

        modeling.append(output)
        counts["modeling_rows"] += 1

    summary = {
        "source_rows": len(source_rows),
        "modeling_rows": len(modeling),
        "excluded_rows": len(exclusions),
        "supported_position_groups": sorted(TARGET_SPECS),
        "target_specs": {
            group: {
                "pre_anchor": f"pre_{category}_{stat_type}",
                "post_target": f"post_{category}_{stat_type}",
                "interpretation": "raw CFBD season production anchor",
            }
            for group, (category, stat_type) in sorted(TARGET_SPECS.items())
        },
        "by_position_group": {
            group: dict(by_group[group])
            for group in sorted(by_group)
        },
        "predictor_policy": {
            "allowed_predictor_columns": predictor_columns,
            "post_feature_columns_excluded_from_predictors": post_features,
            "resolver_score_excluded": True,
            "missing_anchor_policy": "exclude; never zero-impute",
            "target_delta_interpretation": (
                "descriptive pre/post production change only; not causal transfer impact"
            ),
            "modeling_strategy": "fit/evaluate separate models by position group",
        },
    }

    return modeling, exclusions, summary
