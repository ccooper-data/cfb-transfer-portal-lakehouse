from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cfb_portal.position_targets import build_position_modeling_table


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
        description="Build conservative position-aware transfer modeling targets."
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=Path("outputs/player_production_analysis_cohort_2021_2025.csv"),
    )
    parser.add_argument(
        "--modeling-out",
        type=Path,
        default=Path("outputs/player_position_modeling_table_2021_2025.csv"),
    )
    parser.add_argument(
        "--exclusions-out",
        type=Path,
        default=Path("outputs/player_position_target_exclusions_2021_2025.csv"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("outputs/player_position_target_summary_2021_2025.json"),
    )
    args = parser.parse_args()

    rows = read_csv(args.cohort)
    modeling, exclusions, summary = build_position_modeling_table(rows)

    write_csv(args.modeling_out, modeling)
    write_csv(args.exclusions_out, exclusions)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "position_modeling_table_built",
        "source_rows": len(rows),
        "modeling_rows": len(modeling),
        "excluded_rows": len(exclusions),
        "modeling_out": str(args.modeling_out),
        "exclusions_out": str(args.exclusions_out),
        "summary_out": str(args.summary_out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
