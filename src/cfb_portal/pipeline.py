from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .audit import resolution_accounting, stratified_audit_sample, write_accounting, write_label_template
from .identity import portal_entry_key
from .ingest import ingest_portal, ingest_roster
from .io import read_json, write_jsonl
from .manifest import RawManifest
from .resolver import resolve_many, resolve_one


def _latest_json(root: str | Path, endpoint: str, season: int, params: dict[str, object]):
    with RawManifest(root) as manifest:
        path = manifest.latest_object(endpoint, season, params=params)
    if path is None:
        raise FileNotFoundError(f"No archived {endpoint} response for season={season} params={params}. Run ingestion first.")
    return read_json(path)


def ingest_seasons(start: int, end: int, root: str | Path = "data/raw") -> None:
    for season in range(start, end + 1):
        ingest_portal(season, root=root)
        ingest_roster(season, root=root)


def build_resolution_dataset(
    start: int,
    end: int,
    *,
    root: str | Path = "data/raw",
    output_dir: str | Path = "outputs",
    audit_per_reason: int = 25,
) -> dict[str, object]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, object]] = []
    seasons: dict[str, object] = {}

    for season in range(start, end + 1):
        portal = _latest_json(root, "portal", season, {"year": season})
        roster = _latest_json(root, "roster", season, {"year": season})
        if not isinstance(portal, list) or not isinstance(roster, list):
            raise TypeError(f"Expected list JSON for season {season}")
        resolved = resolve_many(portal, roster)

        # Conservative next-season fallback.
        #
        # We only retry rows that are genuinely unresolved and have a
        # destination. Same-season review and ambiguous outcomes remain
        # held out rather than being overwritten by a later roster.
        try:
            next_roster = _latest_json(
                root,
                "roster",
                season + 1,
                {"year": season + 1},
            )
            if not isinstance(next_roster, list):
                raise TypeError(
                    f"Expected list JSON for season {season + 1}"
                )
        except FileNotFoundError:
            next_roster = None

        season_rows: list[dict[str, object]] = []

        for source, same_season_resolution in zip(portal, resolved):
            resolution = same_season_resolution

            same_season_reason = same_season_resolution.reason
            fallback_attempted = False
            fallback_status: str | None = None
            fallback_reason: str | None = None

            match_strategy = (
                "same_season"
                if same_season_resolution.status == "resolved"
                else "none"
            )

            roster_match_season: int | None = (
                season
                if same_season_resolution.status == "resolved"
                else None
            )

            fallback_eligible = (
                same_season_resolution.status == "unresolved"
                and same_season_resolution.reason != "no_destination"
            )

            if fallback_eligible and next_roster is None:
                fallback_status = "unavailable"
                fallback_reason = "next_roster_not_archived"

            elif fallback_eligible:
                fallback_attempted = True

                fallback = resolve_one(
                    source,
                    next_roster,
                    roster_season=season + 1,
                )

                fallback_status = fallback.status
                fallback_reason = fallback.reason

                if fallback.status == "resolved":
                    resolution = fallback
                    match_strategy = "next_season_fallback"
                    roster_match_season = season + 1

            row = resolution.to_dict()
            row["portal_key"] = portal_entry_key(source)
            row["transfer_date"] = source.get(
                "transfer_date",
                source.get("transferDate", ""),
            )
            row["rating"] = source.get("rating")
            row["stars"] = source.get("stars")
            row["eligibility"] = source.get("eligibility")

            # Resolution provenance.
            row["roster_match_season"] = roster_match_season
            row["match_strategy"] = match_strategy
            row["fallback_attempted"] = fallback_attempted
            row["same_season_reason"] = same_season_reason
            row["fallback_status"] = fallback_status
            row["fallback_reason"] = fallback_reason

            season_rows.append(row)
        all_rows.extend(season_rows)
        seasons[str(season)] = resolution_accounting(season_rows)

    resolutions_path = output_dir / f"resolutions_{start}_{end}.jsonl"
    accounting_path = output_dir / f"resolver_accounting_{start}_{end}.json"
    labels_path = output_dir / f"entity_resolution_audit_{start}_{end}.csv"
    write_jsonl(resolutions_path, all_rows)
    total = resolution_accounting(all_rows)
    report = {"start_season": start, "end_season": end, "overall": total, "by_season": seasons}
    write_accounting(accounting_path, report)
    sample = stratified_audit_sample(all_rows, per_reason=audit_per_reason)
    write_label_template(labels_path, sample)
    with RawManifest(root) as manifest:
        manifest_export = manifest.export_jsonl(output_dir / "raw_manifest.jsonl")
    event = {
        "event": "resolution_dataset_built",
        "rows": len(all_rows),
        "resolutions": str(resolutions_path),
        "accounting": str(accounting_path),
        "audit_template": str(labels_path),
        "manifest_export": str(manifest_export),
        "auto_resolved_rate": total["auto_resolved_rate"],
    }
    print(json.dumps(event, sort_keys=True), flush=True)
    return event


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="End-to-end portal ingestion and entity-resolution workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--start", type=int, required=True)
    p_ingest.add_argument("--end", type=int, required=True)
    p_ingest.add_argument("--root", default="data/raw")

    p_build = sub.add_parser("build")
    p_build.add_argument("--start", type=int, required=True)
    p_build.add_argument("--end", type=int, required=True)
    p_build.add_argument("--root", default="data/raw")
    p_build.add_argument("--output-dir", default="outputs")
    p_build.add_argument("--audit-per-reason", type=int, default=25)

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.end < args.start:
        parser.error("--end must be >= --start")
    if args.command == "ingest":
        ingest_seasons(args.start, args.end, root=args.root)
    else:
        build_resolution_dataset(args.start, args.end, root=args.root, output_dir=args.output_dir, audit_per_reason=args.audit_per_reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
