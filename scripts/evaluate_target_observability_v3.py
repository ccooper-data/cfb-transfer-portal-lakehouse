from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.observability_v3 import (
    build_target_observability_rows,
    evaluate_target_observability_v3,
)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        return [
            json.loads(line)
            for line in handle
            if line.strip()
        ]


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
            "Build and evaluate the locked v3 CFBD target-observability "
            "rolling temporal study."
        )
    )
    parser.add_argument(
        "--bridge",
        type=Path,
        default=Path(
            "outputs/resolved_player_season_bridge_2021_2026.jsonl"
        ),
    )
    parser.add_argument(
        "--feature-matrix",
        type=Path,
        default=Path(
            "outputs/player_production_feature_matrix_2021_2026.jsonl"
        ),
    )
    parser.add_argument(
        "--cohort-out",
        type=Path,
        default=Path(
            "outputs/v3_target_observability_cohort_2021_2025.csv"
        ),
    )
    parser.add_argument(
        "--predictions-out",
        type=Path,
        default=Path(
            "outputs/v3_target_observability_predictions_2022_2024.csv"
        ),
    )
    parser.add_argument(
        "--results-out",
        type=Path,
        default=Path(
            "outputs/v3_target_observability_results_2022_2024.json"
        ),
    )
    args = parser.parse_args()

    bridge_rows = read_jsonl(args.bridge)
    feature_rows = read_jsonl(args.feature_matrix)
    cohort, cohort_summary = build_target_observability_rows(
        bridge_rows,
        feature_rows,
    )
    predictions, evaluation_summary = evaluate_target_observability_v3(
        cohort
    )
    evaluation_summary["cohort_summary"] = cohort_summary

    write_csv(args.cohort_out, cohort)
    write_csv(args.predictions_out, predictions)
    args.results_out.parent.mkdir(parents=True, exist_ok=True)
    args.results_out.write_text(
        json.dumps(evaluation_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    accounting = cohort_summary["accounting"]
    print(json.dumps({
        "event": "v3_target_observability_backtest_complete",
        "cohort_rows": accounting.get("cohort_rows", 0),
        "target_observed": accounting.get("target_observed", 0),
        "target_missing": accounting.get("target_missing", 0),
        "evaluated_group_folds": evaluation_summary[
            "evaluated_group_folds"
        ],
        "skipped_group_folds": evaluation_summary[
            "skipped_group_folds"
        ],
        "prediction_rows": evaluation_summary["prediction_rows"],
        "wins_vs_training_prevalence_brier": evaluation_summary[
            "wins_vs_training_prevalence_brier"
        ],
        "cohort_out": str(args.cohort_out),
        "predictions_out": str(args.predictions_out),
        "results_out": str(args.results_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
