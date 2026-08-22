from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping


def evaluate_resolutions(resolutions: Iterable[Mapping[str, object]], labels: Iterable[Mapping[str, object]]) -> dict[str, object]:
    label_map = {}
    for row in labels:
        portal_key = str(row.get("portal_key") or "").strip()
        key = ("portal_key", portal_key) if portal_key else (
            str(row.get("season", "")),
            str(row.get("first_name", "")).strip().casefold(),
            str(row.get("last_name", "")).strip().casefold(),
            str(row.get("origin", "")).strip().casefold(),
            str(row.get("destination", "")).strip().casefold(),
        )
        label_map[key] = row

    total = correct = false_positive = false_negative = 0
    by_status = Counter()
    for r in resolutions:
        portal_key = str(r.get("portal_key") or "").strip()
        key = ("portal_key", portal_key) if portal_key else (
            str(r.get("portal_season", "")),
            str(r.get("portal_first_name", "")).strip().casefold(),
            str(r.get("portal_last_name", "")).strip().casefold(),
            str(r.get("origin", "")).strip().casefold(),
            str(r.get("destination", "")).strip().casefold(),
        )
        if key not in label_map:
            continue
        total += 1
        expected = str(label_map[key].get("expected_player_id") or "")
        predicted = str(r.get("player_id") or "")
        status = str(r.get("status") or "")
        by_status[status] += 1
        if expected and predicted == expected:
            correct += 1
        elif expected and not predicted:
            false_negative += 1
        elif predicted and predicted != expected:
            false_positive += 1

    return {
        "labeled_n": total,
        "correct_n": correct,
        "accuracy": (correct / total) if total else None,
        "false_positive_n": false_positive,
        "false_negative_n": false_negative,
        "status_counts": dict(by_status),
    }
