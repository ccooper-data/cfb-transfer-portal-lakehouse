from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Iterable, Mapping


def _slug(value: object) -> str:
    text = "" if value is None else str(value)
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )
    text = text.casefold().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _parse_numeric(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(f"Non-numeric stat value: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"Non-finite stat value: {value!r}")
    return number


def _feature_name(phase: str, category: object, stat_type: object) -> str:
    phase_slug = _slug(phase)
    category_slug = _slug(category)
    stat_slug = _slug(stat_type)
    if not phase_slug or not category_slug or not stat_slug:
        raise ValueError(
            f"Cannot create feature name from phase={phase!r}, "
            f"category={category!r}, stat_type={stat_type!r}"
        )
    return f"{phase_slug}_{category_slug}_{stat_slug}"


def build_player_feature_matrix(
    bridge_rows: Iterable[Mapping[str, object]],
    linked_stat_rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Pivot linked long-form CFBD stats into one row per resolved transfer.

    Feature identity preserves the full `(phase, category, statType)` tuple.
    Missing features remain null/absent rather than being converted to zero.
    Duplicate keys with conflicting values fail closed instead of being
    silently aggregated.
    """
    bridge = [dict(row) for row in bridge_rows]
    bridge_by_key = {
        str(row.get("portal_key") or ""): row
        for row in bridge
        if str(row.get("portal_key") or "")
    }
    if len(bridge_by_key) != len(bridge):
        raise ValueError("Bridge must contain one non-empty unique portal_key per row")

    feature_values: dict[str, dict[str, float]] = defaultdict(dict)
    feature_sources: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    feature_names: set[str] = set()
    source_stat_rows = 0

    for raw in linked_stat_rows:
        row = dict(raw)
        source_stat_rows += 1
        portal_key = str(row.get("portal_key") or "")
        if portal_key not in bridge_by_key:
            raise ValueError(f"Stat row references unknown portal_key={portal_key!r}")

        phase = str(row.get("phase") or "")
        category = row.get("category")
        stat_type = row.get("stat_type")
        feature = _feature_name(phase, category, stat_type)
        value = _parse_numeric(row.get("stat"))

        if value is None:
            continue

        existing = feature_values[portal_key].get(feature)
        if existing is not None and existing != value:
            prev = feature_sources[portal_key][feature]
            raise ValueError(
                "Conflicting duplicate stat for "
                f"portal_key={portal_key} feature={feature}: "
                f"{existing} from {prev} vs {value} "
                f"from {(str(category), str(stat_type))}"
            )

        feature_values[portal_key][feature] = value
        feature_sources[portal_key][feature] = (
            str(category),
            str(stat_type),
        )
        feature_names.add(feature)

    ordered_features = sorted(feature_names)
    full_matrix: list[dict[str, object]] = []
    analysis_cohort: list[dict[str, object]] = []
    by_season: dict[int, Counter[str]] = defaultdict(Counter)

    metadata_fields = [
        "portal_key",
        "portal_season",
        "transfer_date",
        "player_id",
        "portal_first_name",
        "portal_last_name",
        "portal_position",
        "origin",
        "destination",
        "rating",
        "stars",
        "eligibility",
        "resolver_score",
        "resolver_score_margin",
        "match_strategy",
        "roster_match_season",
        "pre_season",
        "post_season",
        "pre_stats_source_available",
        "post_stats_source_available",
        "pre_has_player_stats",
        "pre_has_origin_stats",
        "post_has_player_stats",
        "post_has_destination_stats",
        "pre_team_mismatch",
        "post_team_mismatch",
        "complete_pre_post_expected_team_stats",
        "post_outcome_right_censored",
    ]

    for bridge_row in bridge:
        portal_key = str(bridge_row["portal_key"])
        row: dict[str, object] = {
            field: bridge_row.get(field)
            for field in metadata_fields
        }
        row["analysis_eligible_complete_pre_post"] = bool(
            bridge_row.get("complete_pre_post_expected_team_stats")
        ) and not bool(bridge_row.get("post_outcome_right_censored"))

        values = feature_values.get(portal_key, {})
        for feature in ordered_features:
            row[feature] = values.get(feature)

        full_matrix.append(row)
        if row["analysis_eligible_complete_pre_post"]:
            analysis_cohort.append(dict(row))

        season = int(row["portal_season"])
        c = by_season[season]
        c["rows"] += 1
        c["analysis_eligible_complete_pre_post"] += int(
            bool(row["analysis_eligible_complete_pre_post"])
        )
        c["has_any_pre_feature"] += int(
            any(
                values.get(name) is not None
                for name in ordered_features
                if name.startswith("pre_")
            )
        )
        c["has_any_post_feature"] += int(
            any(
                values.get(name) is not None
                for name in ordered_features
                if name.startswith("post_")
            )
        )

    pre_features = [name for name in ordered_features if name.startswith("pre_")]
    post_features = [name for name in ordered_features if name.startswith("post_")]

    summary = {
        "full_matrix_rows": len(full_matrix),
        "analysis_cohort_rows": len(analysis_cohort),
        "source_linked_stat_rows": source_stat_rows,
        "distinct_feature_columns": len(ordered_features),
        "pre_feature_columns": len(pre_features),
        "post_feature_columns": len(post_features),
        "feature_columns": ordered_features,
        "by_portal_season": {
            str(year): dict(by_season[year])
            for year in sorted(by_season)
        },
        "policy": {
            "feature_identity": "phase + category + statType",
            "missing_stats": "null, never zero-imputed in this layer",
            "duplicate_stats": "identical duplicates tolerated; conflicting duplicates raise",
            "analysis_cohort": (
                "requires expected-team stats in both pre and post seasons "
                "and a completed post-outcome source"
            ),
            "derived_metrics": "none in v1; raw CFBD season stats only",
        },
    }
    return full_matrix, analysis_cohort, summary
