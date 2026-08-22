from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.holdout_model import evaluate_2025_holdout


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate position-specific transfer production models on 2025."
    )
    parser.add_argument(
        "--modeling-table",
        type=Path,
        default=Path("outputs/player_position_modeling_table_2021_2025.csv"),
    )
    parser.add_argument(
        "--predictions-out",
        type=Path,
        default=Path("outputs/position_model_holdout_2025_predictions.csv"),
    )
    parser.add_argument(
        "--results-out",
        type=Path,
        default=Path("outputs/position_model_holdout_2025_results.json"),
    )
    args = parser.parse_args()

    rows = read_csv(args.modeling_table)
    predictions, summary = evaluate_2025_holdout(rows)

    write_csv(args.predictions_out, predictions)
    args.results_out.parent.mkdir(parents=True, exist_ok=True)
    args.results_out.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "position_model_2025_holdout_evaluated",
        "source_modeling_rows": summary["source_modeling_rows"],
        "holdout_prediction_rows": summary["holdout_prediction_rows"],
        "evaluated_position_groups": summary["evaluated_position_groups"],
        "position_groups_beating_baseline_mae": summary[
            "position_groups_beating_baseline_mae"
        ],
        "predictions_out": str(args.predictions_out),
        "results_out": str(args.results_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
