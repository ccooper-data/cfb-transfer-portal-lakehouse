from __future__ import annotations

import re
import unicodedata

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

FIRST_NAME_GROUPS = [
    {"mike", "michael"},
    {"matt", "matthew"},
    {"chris", "christopher"},
    {"nick", "nicholas"},
    {"nate", "nathan", "nathaniel"},
    {"alex", "alexander"},
    {"ben", "benjamin"},
    {"will", "william", "bill", "billy"},
    {"rob", "robert", "bob", "bobby"},
    {"jon", "john", "johnny"},
    {"jake", "jacob"},
    {"zach", "zachary"},
    {"gabe", "gabriel"},
    {"sam", "samuel"},
    {"joe", "joseph", "joey"},
    {"tony", "anthony"},
]

ALIAS_LOOKUP: dict[str, set[str]] = {}
for group in FIRST_NAME_GROUPS:
    for value in group:
        ALIAS_LOOKUP[value] = group

POSITION_GROUPS = {
    "QB": "QB",
    "RB": "RB",
    "HB": "RB",
    "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "OT": "OL",
    "OG": "OL",
    "C": "OL",
    "OL": "OL",
    "IOL": "OL",
    "DL": "DL",
    "DT": "DL",
    "NT": "DL",
    "DE": "EDGE",
    "EDGE": "EDGE",
    "LB": "LB",
    "ILB": "LB",
    "OLB": "LB",
    "CB": "DB",
    "S": "DB",
    "DB": "DB",
    "K": "ST",
    "P": "ST",
    "LS": "ST",
    "ATH": "ATH",
}


def _ascii(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch))


def normalize_token(value: str | None) -> str:
    if not value:
        return ""
    value = _ascii(str(value)).casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_person_name(first: str | None, last: str | None) -> tuple[str, str]:
    first_n = normalize_token(first)
    last_parts = normalize_token(last).split()
    if last_parts and last_parts[-1] in SUFFIXES:
        last_parts = last_parts[:-1]
    return first_n, " ".join(last_parts)


def first_name_alias_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    return b in ALIAS_LOOKUP.get(a, set()) or a in ALIAS_LOOKUP.get(b, set())


def normalize_team(value: str | None) -> str:
    return normalize_token(value)


def position_group(value: str | None) -> str:
    raw = normalize_token(value).upper().replace(" ", "")
    return POSITION_GROUPS.get(raw, raw)
