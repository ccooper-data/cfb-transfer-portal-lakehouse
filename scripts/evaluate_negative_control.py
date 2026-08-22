from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.io import read_json
from cfb_portal.manifest import RawManifest
from cfb_portal.negative_control import (
    build_negative_control_panel,
    evaluate_negative_control_2025,
)


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
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
                seen.add(field)
                fields.append(field)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a pre-transfer negative-control / selection diagnostic."
    )
    parser.add_argument(
        "--modeling-table",
        type=Path,
        default=Path("outputs/player_position_modeling_table_2021_2025.csv"),
    )
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--panel-out",
        type=Path,
        default=Path("outputs/negative_control_panel_2022_2025.csv"),
    )
    parser.add_argument(
        "--exclusions-out",
        type=Path,
        default=Path("outputs/negative_control_exclusions_2021_2025.csv"),
    )
    parser.add_argument(
        "--panel-summary-out",
        type=Path,
        default=Path("outputs/negative_control_panel_summary.json"),
    )
    parser.add_argument(
        "--predictions-out",
        type=Path,
        default=Path("outputs/negative_control_holdout_2025_predictions.csv"),
    )
    parser.add_argument(
        "--results-out",
        type=Path,
        default=Path("outputs/negative_control_holdout_2025_results.json"),
    )
    args = parser.parse_args()

    modeling_rows = read_csv(args.modeling_table)

    stats_by_year: dict[int, list[dict[str, object]]] = {}
    for year in range(2020, 2024):
        with RawManifest(args.raw_root) as manifest:
            path = manifest.latest_object(
                "player_stats",
                year,
                params={"year": year},
            )
        if path is None:
            stats_by_year[year] = []
            continue
        rows = read_json(path)
        if not isinstance(rows, list):
            raise TypeError(f"Expected list for player_stats {year}")
        stats_by_year[year] = rows

    panel, exclusions, panel_summary = build_negative_control_panel(
        modeling_rows,
        stats_by_year,
    )
    predictions, results = evaluate_negative_control_2025(panel)

    write_csv(args.panel_out, panel)
    write_csv(args.exclusions_out, exclusions)
    write_csv(args.predictions_out, predictions)

    args.panel_summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.panel_summary_out.write_text(
        json.dumps(panel_summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.results_out.write_text(
        json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "negative_control_2025_evaluated",
        "panel_rows": len(panel),
        "excluded_rows": len(exclusions),
        "holdout_prediction_rows": len(predictions),
        "evaluated_position_groups": results["evaluated_position_groups"],
        "position_groups_with_negative_control_signal": results[
            "position_groups_with_negative_control_signal"
        ],
        "panel_out": str(args.panel_out),
        "results_out": str(args.results_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
