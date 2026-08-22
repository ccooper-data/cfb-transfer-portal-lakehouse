from __future__ import annotations

import hashlib
import json
from typing import Mapping

from .normalize import normalize_person_name, normalize_team, normalize_token, position_group

PORTAL_ID_FIELDS = (
    "season",
    "first_name",
    "last_name",
    "position",
    "origin",
    "destination",
    "transfer_date",
    "rating",
    "stars",
    "eligibility",
)


def _get(row: Mapping[str, object], snake: str, camel: str | None = None):
    if snake in row:
        return row.get(snake)
    if camel and camel in row:
        return row.get(camel)
    return None


def canonical_portal_identity(row: Mapping[str, object]) -> dict[str, object]:
    first, last = normalize_person_name(_get(row, "first_name", "firstName"), _get(row, "last_name", "lastName"))
    return {
        "season": int(_get(row, "season") or 0),
        "first_name": first,
        "last_name": last,
        "position": position_group(str(_get(row, "position") or "")),
        "origin": normalize_team(str(_get(row, "origin") or "")),
        "destination": normalize_team(str(_get(row, "destination") or "")),
        "transfer_date": normalize_token(str(_get(row, "transfer_date", "transferDate") or "")),
        "rating": str(_get(row, "rating") or ""),
        "stars": str(_get(row, "stars") or ""),
        "eligibility": normalize_token(str(_get(row, "eligibility") or "")),
    }


def portal_entry_key(row: Mapping[str, object]) -> str:
    payload = json.dumps(canonical_portal_identity(row), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
