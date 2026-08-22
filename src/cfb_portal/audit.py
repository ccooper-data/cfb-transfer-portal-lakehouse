from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping


def resolution_accounting(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    rows = list(rows)
    status = Counter(str(r.get("status") or "unknown") for r in rows)
    reason = Counter(str(r.get("reason") or "unknown") for r in rows)
    n = len(rows)
    return {
        "portal_entries": n,
        "status_counts": dict(sorted(status.items())),
        "reason_counts": dict(sorted(reason.items())),
        "auto_resolved_n": status.get("resolved", 0),
        "auto_resolved_rate": (status.get("resolved", 0) / n) if n else None,
        "held_out_n": status.get("review", 0) + status.get("ambiguous", 0) + status.get("unresolved", 0),
    }


def stratified_audit_sample(rows: Iterable[Mapping[str, object]], per_reason: int = 25, seed: int = 20260821) -> list[dict[str, object]]:
    buckets: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        item = dict(row)
        key = f"{item.get('status','')}::{item.get('reason','')}"
        buckets.setdefault(key, []).append(item)
    rng = random.Random(seed)
    out: list[dict[str, object]] = []
    for key in sorted(buckets):
        bucket = buckets[key][:]
        rng.shuffle(bucket)
        out.extend(bucket[:per_reason])
    return out


def write_label_template(path: str | Path, rows: Iterable[Mapping[str, object]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "portal_key", "season", "first_name", "last_name", "position", "origin", "destination",
        "predicted_status", "predicted_player_id", "predicted_score", "expected_player_id",
        "label_outcome", "split", "reviewer", "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "portal_key": r.get("portal_key", ""),
                "season": r.get("portal_season", ""),
                "first_name": r.get("portal_first_name", ""),
                "last_name": r.get("portal_last_name", ""),
                "position": r.get("position", ""),
                "origin": r.get("origin", ""),
                "destination": r.get("destination", ""),
                "predicted_status": r.get("status", ""),
                "predicted_player_id": r.get("player_id", ""),
                "predicted_score": r.get("score", ""),
                "expected_player_id": "",
                "label_outcome": "",
                "split": "",
                "reviewer": "",
                "notes": "",
            })


def write_accounting(path: str | Path, accounting: Mapping[str, object]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(accounting), indent=2, sort_keys=True) + "\n", encoding="utf-8")
