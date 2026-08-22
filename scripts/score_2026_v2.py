from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.scoring_2026 import (
    build_2026_scoring_cohort,
    fit_and_score_2026,
)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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
        description="Fit locked-contract v2 models and generate 2026 forecasts."
    )
    parser.add_argument(
        "--feature-matrix",
        type=Path,
        default=Path(
            "outputs/player_production_feature_matrix_2021_2026.jsonl"
        ),
    )
    parser.add_argument(
        "--training-table",
        type=Path,
        default=Path(
            "outputs/player_outcome_observed_modeling_table_v2_2021_2025.csv"
        ),
    )
    parser.add_argument(
        "--scoring-cohort-out",
        type=Path,
        default=Path("outputs/player_scoring_cohort_2026_v2.csv"),
    )
    parser.add_argument(
        "--exclusions-out",
        type=Path,
        default=Path("outputs/player_scoring_exclusions_2026_v2.csv"),
    )
    parser.add_argument(
        "--predictions-out",
        type=Path,
        default=Path("outputs/player_predictions_2026_v2.csv"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("outputs/player_predictions_2026_v2_summary.json"),
    )
    parser.add_argument("--expected-scoring-rows", type=int, default=2074)
    args = parser.parse_args()

    matrix = read_jsonl(args.feature_matrix)
    training = read_csv(args.training_table)

    scoring, exclusions, cohort_summary = build_2026_scoring_cohort(matrix)
    if len(scoring) != args.expected_scoring_rows:
        raise ValueError(
            f"Expected {args.expected_scoring_rows} 2026 scoring rows, "
            f"found {len(scoring)}"
        )

    predictions, model_summary = fit_and_score_2026(training, scoring)
    if len(predictions) != len(scoring):
        raise ValueError(
            f"Prediction/scoring row mismatch: "
            f"{len(predictions)} != {len(scoring)}"
        )

    write_csv(args.scoring_cohort_out, scoring)
    write_csv(args.exclusions_out, exclusions)
    write_csv(args.predictions_out, predictions)

    combined_summary = {
        "cohort": cohort_summary,
        "scoring": model_summary,
    }
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(combined_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "player_2026_v2_scoring_complete",
        "scoreable_rows": len(scoring),
        "prediction_rows": len(predictions),
        "excluded_rows": len(exclusions),
        "pre_anchor_observed_rows": cohort_summary[
            "pre_anchor_observed_rows"
        ],
        "pre_anchor_missing_rows": cohort_summary[
            "pre_anchor_missing_rows"
        ],
        "predictions_out": str(args.predictions_out),
        "summary_out": str(args.summary_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
