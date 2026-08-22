from __future__ import annotations

import argparse
import json
from pathlib import Path

from cfb_portal.io import read_json
from cfb_portal.manifest import RawManifest
from cfb_portal.player_bridge import build_resolved_player_season_bridge


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the resolved transfer -> player-season production bridge."
    )
    parser.add_argument(
        "--resolutions",
        type=Path,
        default=Path("outputs/resolutions_2021_2026.jsonl"),
    )
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--start-stat-season", type=int, default=2020)
    parser.add_argument("--end-stat-season", type=int, default=2026)
    parser.add_argument(
        "--bridge-out",
        type=Path,
        default=Path("outputs/resolved_player_season_bridge_2021_2026.jsonl"),
    )
    parser.add_argument(
        "--stats-out",
        type=Path,
        default=Path("outputs/resolved_player_stats_long_2021_2026.jsonl"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("outputs/resolved_player_season_bridge_2021_2026_summary.json"),
    )
    args = parser.parse_args()

    resolutions = read_jsonl(args.resolutions)

    stats_by_year: dict[int, list[dict[str, object]]] = {}
    for year in range(args.start_stat_season, args.end_stat_season + 1):
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

    bridge, linked_stats, summary = build_resolved_player_season_bridge(
        resolutions,
        stats_by_year,
    )

    write_jsonl(args.bridge_out, bridge)
    write_jsonl(args.stats_out, linked_stats)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "event": "resolved_player_season_bridge_built",
        "bridge_rows": len(bridge),
        "linked_stat_rows": len(linked_stats),
        "bridge_out": str(args.bridge_out),
        "stats_out": str(args.stats_out),
        "summary_out": str(args.summary_out),
        "complete_pre_post_expected_team_rows": summary[
            "complete_pre_post_expected_team_rows"
        ],
        "complete_pre_post_expected_team_rate_among_completed_outcomes": summary[
            "complete_pre_post_expected_team_rate_among_completed_outcomes"
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
