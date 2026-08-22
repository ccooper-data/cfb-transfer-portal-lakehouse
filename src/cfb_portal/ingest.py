from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .client import CFBDClient
from .manifest import RawManifest


ENDPOINTS = {
    "portal": "/player/portal",
    "roster": "/roster",
    "returning": "/player/returning",
    "player_stats": "/stats/player/season",
    "team_stats": "/stats/season",
    "records": "/records",
}


def ingest_endpoint(
    endpoint: str,
    *,
    season: int | None,
    params: dict[str, object],
    root: str | Path = "data/raw",
    client: CFBDClient | None = None,
) -> dict[str, object]:
    if endpoint not in ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint}")
    client = client or CFBDClient()
    requested_at = RawManifest.utc_now()
    response = client.get(ENDPOINTS[endpoint], params=params)
    received_at = RawManifest.utc_now()
    # Validate JSON before archiving it as JSON. Raw bytes remain untouched.
    parsed = response.json()
    if not isinstance(parsed, (list, dict)):
        raise ValueError(f"Unexpected JSON root from {endpoint}: {type(parsed).__name__}")
    with RawManifest(root) as manifest:
        stored = manifest.store_bytes(response.body, suffix=".json")
        download_id = manifest.record_download(
            endpoint=endpoint,
            season=season,
            params=params,
            requested_at=requested_at,
            received_at=received_at,
            stored=stored,
            http_status=response.status,
            source_url=response.url,
            headers=response.headers,
        )
    event = {
        "event": "cfbd_saved",
        "download_id": download_id,
        "endpoint": endpoint,
        "season": season,
        "records": len(parsed) if isinstance(parsed, list) else 1,
        "sha256": stored.sha256,
        "byte_count": stored.byte_count,
        "object_path": stored.object_path,
    }
    print(json.dumps(event, sort_keys=True), flush=True)
    return event


def ingest_portal(season: int, root: str | Path = "data/raw", client: CFBDClient | None = None):
    return ingest_endpoint("portal", season=season, params={"year": season}, root=root, client=client)


def ingest_roster(season: int, team: str | None = None, root: str | Path = "data/raw", client: CFBDClient | None = None):
    params: dict[str, object] = {"year": season}
    if team:
        params["team"] = team
    return ingest_endpoint("roster", season=season, params=params, root=root, client=client)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive CFBD source responses with immutable provenance")
    parser.add_argument("endpoint", choices=sorted(ENDPOINTS))
    parser.add_argument("--season", type=int)
    parser.add_argument("--team")
    parser.add_argument("--root", default="data/raw")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.endpoint in {"portal", "roster", "returning", "player_stats", "team_stats", "records"} and not args.season:
        parser.error("--season is required for this project workflow")
    params: dict[str, object] = {"year": args.season}
    if args.team:
        params["team"] = args.team
    ingest_endpoint(args.endpoint, season=args.season, params=params, root=args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
