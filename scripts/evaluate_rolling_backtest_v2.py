from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.rolling_backtest_v2 import evaluate_rolling_backtest_v2


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
        description="Evaluate the locked-design v2 rolling temporal backtest."
    )
    parser.add_argument(
        "--modeling-table",
        type=Path,
        default=Path(
            "outputs/player_outcome_observed_modeling_table_v2_2021_2025.csv"
        ),
    )
    parser.add_argument(
        "--predictions-out",
        type=Path,
        default=Path("outputs/v2_rolling_backtest_predictions_2022_2024.csv"),
    )
    parser.add_argument(
        "--results-out",
        type=Path,
        default=Path("outputs/v2_rolling_backtest_results_2022_2024.json"),
    )
    args = parser.parse_args()

    rows = read_csv(args.modeling_table)
    predictions, summary = evaluate_rolling_backtest_v2(rows)
    write_csv(args.predictions_out, predictions)
    args.results_out.parent.mkdir(parents=True, exist_ok=True)
    args.results_out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "v2_rolling_backtest_complete",
        "source_rows_all_seasons": summary["source_rows_all_seasons"],
        "source_rows_primary_backtest_period": (
            summary["source_rows_primary_backtest_period"]
        ),
        "evaluated_group_folds": summary["evaluated_group_folds"],
        "skipped_group_folds": summary["skipped_group_folds"],
        "prediction_rows": summary["prediction_rows"],
        "all_row_wins_vs_historical_mean": (
            summary["all_row_wins_vs_historical_mean"]
        ),
        "paired_subset_wins_vs_returning_production": (
            summary["paired_subset_wins_vs_returning_production"]
        ),
        "predictions_out": str(args.predictions_out),
        "results_out": str(args.results_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
