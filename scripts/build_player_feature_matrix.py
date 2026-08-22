from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.player_features import build_player_feature_matrix


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


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
        description="Build the one-row-per-transfer player production feature matrix."
    )
    parser.add_argument(
        "--bridge",
        type=Path,
        default=Path("outputs/resolved_player_season_bridge_2021_2026.jsonl"),
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=Path("outputs/resolved_player_stats_long_2021_2026.jsonl"),
    )
    parser.add_argument(
        "--matrix-out",
        type=Path,
        default=Path("outputs/player_production_feature_matrix_2021_2026.jsonl"),
    )
    parser.add_argument(
        "--cohort-out",
        type=Path,
        default=Path("outputs/player_production_analysis_cohort_2021_2025.csv"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("outputs/player_production_feature_matrix_2021_2026_summary.json"),
    )
    args = parser.parse_args()

    bridge_rows = read_jsonl(args.bridge)
    linked_stats = read_jsonl(args.stats)

    matrix, cohort, summary = build_player_feature_matrix(
        bridge_rows,
        linked_stats,
    )

    write_jsonl(args.matrix_out, matrix)
    write_csv(args.cohort_out, cohort)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "player_production_feature_matrix_built",
        "full_matrix_rows": len(matrix),
        "analysis_cohort_rows": len(cohort),
        "distinct_feature_columns": summary["distinct_feature_columns"],
        "pre_feature_columns": summary["pre_feature_columns"],
        "post_feature_columns": summary["post_feature_columns"],
        "matrix_out": str(args.matrix_out),
        "cohort_out": str(args.cohort_out),
        "summary_out": str(args.summary_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
