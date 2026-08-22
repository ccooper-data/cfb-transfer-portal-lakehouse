from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.forecast_support import enrich_forecast_support

DEFAULT_INPUT = "outputs/player_predictions_2026_v2.csv"
DEFAULT_OUTPUT = "outputs/player_predictions_2026_v2_presentation.csv"
DEFAULT_SUMMARY = "outputs/player_predictions_2026_v2_presentation_summary.json"

EXPECTED_ROWS = 2074
EXPECTED_SUPPORT_COUNTS = {
    "STRONG": 1521,
    "STANDARD": 84,
    "LIMITED": 469,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    with open(args.input, newline="") as f:
        source_rows = list(csv.DictReader(f))

    enriched, summary = enrich_forecast_support(source_rows)

    if len(enriched) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS:,} frozen prediction rows, "
            f"found {len(enriched):,}"
        )
    if summary["support_counts"] != EXPECTED_SUPPORT_COUNTS:
        raise ValueError(
            "Frozen-release forecast-support counts changed: "
            f"expected={EXPECTED_SUPPORT_COUNTS} "
            f"actual={summary['support_counts']}"
        )

    source_by_key = {
        row["portal_key"]: row["predicted_post_transfer_production"]
        for row in source_rows
    }
    if len(source_by_key) != len(source_rows):
        raise ValueError("Frozen prediction portal_key values must be unique")

    for row in enriched:
        key = row["portal_key"]
        if row["predicted_post_transfer_production"] != source_by_key[key]:
            raise ValueError(f"Point forecast changed for portal_key={key}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(enriched[0].keys()) if enriched else []
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    summary_payload = {
        **summary,
        "source_predictions": args.input,
        "presentation_out": args.output,
        "support_contract": {
            "STRONG": (
                "prior production observed and model_feature_missing_count <= 2"
            ),
            "STANDARD": (
                "prior production observed and model_feature_missing_count > 2"
            ),
            "LIMITED": "prior production unavailable",
        },
        "governance": {
            "support_is_confidence": False,
            "support_is_prediction_interval": False,
            "support_is_accuracy": False,
            "point_forecasts_changed": False,
            "2026_outcomes_observed": False,
        },
    }
    with open(args.summary, "w") as f:
        json.dump(summary_payload, f, indent=2, sort_keys=True)
        f.write("\n")

    print(json.dumps({
        "event": "player_2026_forecast_presentation_built",
        "rows": len(enriched),
        "strong": summary["support_counts"]["STRONG"],
        "standard": summary["support_counts"]["STANDARD"],
        "limited": summary["support_counts"]["LIMITED"],
        "predictions_modified": False,
        "presentation_out": args.output,
        "summary_out": args.summary,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
