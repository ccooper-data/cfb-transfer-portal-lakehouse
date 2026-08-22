from __future__ import annotations

import argparse
import json
from pathlib import Path

from .io import read_json, write_jsonl
from .resolver import resolve_many


def main() -> int:
    parser = argparse.ArgumentParser(description="CFB transfer portal lakehouse utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("resolve", help="Resolve portal rows to roster player IDs")
    r.add_argument("--portal", required=True, help="Portal JSON array")
    r.add_argument("--roster", required=True, help="Roster JSON array")
    r.add_argument("--output", default="outputs/resolutions.jsonl")

    args = parser.parse_args()
    if args.command == "resolve":
        portal = read_json(args.portal)
        roster = read_json(args.roster)
        results = [r.to_dict() for r in resolve_many(portal, roster)]
        write_jsonl(args.output, results)
        counts = {}
        for row in results:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        print(json.dumps({"rows": len(results), "status_counts": counts, "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
