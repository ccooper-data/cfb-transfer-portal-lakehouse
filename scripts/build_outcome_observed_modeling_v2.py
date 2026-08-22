from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.outcome_observed_modeling import (
    build_outcome_observed_modeling_table_v2,
)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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
        description="Build the broader v2 outcome-observed modeling table."
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path("outputs/player_production_feature_matrix_2021_2026.jsonl"),
    )
    parser.add_argument(
        "--modeling-out",
        type=Path,
        default=Path(
            "outputs/player_outcome_observed_modeling_table_v2_2021_2025.csv"
        ),
    )
    parser.add_argument(
        "--exclusions-out",
        type=Path,
        default=Path(
            "outputs/player_outcome_observed_modeling_exclusions_v2_2021_2026.csv"
        ),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path(
            "outputs/player_outcome_observed_modeling_summary_v2.json"
        ),
    )
    parser.add_argument("--expected-modeling-rows", type=int)
    args = parser.parse_args()

    rows = read_jsonl(args.matrix)
    modeling, exclusions, summary = build_outcome_observed_modeling_table_v2(rows)

    if (
        args.expected_modeling_rows is not None
        and len(modeling) != args.expected_modeling_rows
    ):
        raise ValueError(
            f"Expected {args.expected_modeling_rows} modeling rows, "
            f"found {len(modeling)}"
        )

    write_csv(args.modeling_out, modeling)
    write_csv(args.exclusions_out, exclusions)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "outcome_observed_modeling_v2_built",
        "source_rows": summary["source_rows"],
        "modeling_rows": summary["modeling_rows"],
        "excluded_rows": summary["excluded_rows"],
        "rows_missing_pre_anchor": summary["rows_missing_pre_anchor"],
        "rows_with_pre_anchor": summary["rows_with_pre_anchor"],
        "pre_feature_columns": summary["pre_feature_columns"],
        "missingness_indicator_columns": summary[
            "missingness_indicator_columns"
        ],
        "modeling_out": str(args.modeling_out),
        "exclusions_out": str(args.exclusions_out),
        "summary_out": str(args.summary_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
