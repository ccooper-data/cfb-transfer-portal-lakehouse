from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.observability_v3_stress_test import (
    evaluate_2025_target_observability_stress_test,
)


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for field in row:
            if field not in seen:
                fields.append(field)
                seen.add(field)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the locked 2025 v3 target-observability temporal stress test."
        )
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=Path(
            "outputs/v3_target_observability_cohort_2021_2025.csv"
        ),
    )
    parser.add_argument(
        "--predictions-out",
        type=Path,
        default=Path(
            "outputs/v3_target_observability_stress_test_predictions_2025.csv"
        ),
    )
    parser.add_argument(
        "--results-out",
        type=Path,
        default=Path(
            "outputs/v3_target_observability_stress_test_results_2025.json"
        ),
    )
    args = parser.parse_args()

    rows = read_csv(args.cohort)
    predictions, summary = evaluate_2025_target_observability_stress_test(
        rows
    )

    write_csv(args.predictions_out, predictions)
    args.results_out.parent.mkdir(parents=True, exist_ok=True)
    args.results_out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "v3_2025_observability_stress_test_complete",
        "source_rows": summary["source_rows"],
        "evaluated_position_groups": summary[
            "evaluated_position_groups"
        ],
        "skipped_position_groups": summary[
            "skipped_position_groups"
        ],
        "prediction_rows": summary["prediction_rows"],
        "wins_vs_training_prevalence_brier": summary[
            "wins_vs_training_prevalence_brier"
        ],
        "predictions_out": str(args.predictions_out),
        "results_out": str(args.results_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
