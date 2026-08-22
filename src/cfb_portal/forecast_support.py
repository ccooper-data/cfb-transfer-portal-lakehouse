from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

STRONG = "STRONG"
STANDARD = "STANDARD"
LIMITED = "LIMITED"

SUPPORT_ORDER = (STRONG, STANDARD, LIMITED)

SUPPORT_REASONS = {
    STRONG: "prior production observed; at most 2 model features missing",
    STANDARD: "prior production observed; more than 2 model features missing",
    LIMITED: (
        "prior production unavailable; forecast relies more heavily on "
        "imputation and remaining observed features"
    ),
}


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def classify_forecast_support(row: Mapping[str, object]) -> str:
    """Return the locked descriptive support label for one 2026 forecast."""
    missing_pre = _bool(row.get("baseline_pre_production_missing"))
    missing_count_raw = row.get("model_feature_missing_count")
    if missing_count_raw in (None, ""):
        raise ValueError("model_feature_missing_count is required")
    missing_count = int(str(missing_count_raw))

    if missing_count < 0:
        raise ValueError("model_feature_missing_count cannot be negative")
    if missing_pre:
        return LIMITED
    if missing_count <= 2:
        return STRONG
    return STANDARD


def enrich_forecast_support(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Add presentation-only support metadata without changing predictions."""
    enriched: list[dict[str, object]] = []
    counts: Counter[str] = Counter()

    for raw in rows:
        row = dict(raw)
        if "predicted_post_transfer_production" not in row:
            raise ValueError("predicted_post_transfer_production is required")

        original_prediction = row["predicted_post_transfer_production"]
        support = classify_forecast_support(row)

        output = dict(row)
        output["forecast_support"] = support
        output["forecast_support_reason"] = SUPPORT_REASONS[support]

        if output["predicted_post_transfer_production"] != original_prediction:
            raise AssertionError("Forecast point estimate was modified")

        enriched.append(output)
        counts[support] += 1

    summary = {
        "rows": len(enriched),
        "support_counts": {
            level: counts[level] for level in SUPPORT_ORDER
        },
        "semantics": (
            "data-completeness/model-input-support label; not calibrated confidence"
        ),
        "prediction_modified": False,
        "2026_outcome_used": False,
        "causal_claim": False,
    }
    return enriched, summary
