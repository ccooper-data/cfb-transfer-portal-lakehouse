from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Iterable, Mapping

from .normalize import (
    first_name_alias_match,
    normalize_person_name,
    normalize_team,
    position_group,
)


@dataclass(frozen=True)
class MatchCandidate:
    player_id: str
    score: float
    first_score: float
    last_score: float
    position_score: float
    roster_season: int
    roster_team: str
    roster_first_name: str
    roster_last_name: str
    roster_position: str


@dataclass(frozen=True)
class Resolution:
    status: str
    reason: str
    portal_season: int
    portal_first_name: str
    portal_last_name: str
    origin: str
    destination: str
    position: str
    player_id: str | None
    score: float | None
    runner_up_score: float | None
    score_margin: float | None
    candidate_count: int
    top_candidates: tuple[MatchCandidate, ...]

    def to_dict(self) -> dict:
        out = asdict(self)
        out["top_candidates"] = [asdict(x) for x in self.top_candidates]
        return out


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _get(row: Mapping[str, object], *names: str, default=None):
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def _candidate_id(row: Mapping[str, object]) -> str:
    value = _get(row, "id", "player_id", "playerId", "athlete_id", "athleteId")
    return "" if value is None else str(value)


def score_candidate(portal: Mapping[str, object], roster: Mapping[str, object], roster_season: int) -> MatchCandidate:
    p_first, p_last = normalize_person_name(_get(portal, "first_name", "firstName"), _get(portal, "last_name", "lastName"))
    r_first, r_last = normalize_person_name(_get(roster, "first_name", "firstName"), _get(roster, "last_name", "lastName"))

    if first_name_alias_match(p_first, r_first):
        first_score = 1.0
    else:
        first_score = _ratio(p_first, r_first)
    last_score = _ratio(p_last, r_last)

    p_pos = position_group(str(_get(portal, "position", default="")))
    r_pos = position_group(str(_get(roster, "position", default="")))
    position_score = 1.0 if p_pos and r_pos and p_pos == r_pos else (0.5 if not p_pos or not r_pos else 0.0)

    # Name dominates; position is supporting evidence, never enough to rescue a bad name.
    score = 0.30 * first_score + 0.55 * last_score + 0.15 * position_score
    return MatchCandidate(
        player_id=_candidate_id(roster),
        score=round(score, 6),
        first_score=round(first_score, 6),
        last_score=round(last_score, 6),
        position_score=round(position_score, 6),
        roster_season=roster_season,
        roster_team=str(_get(roster, "team", "school", default="")),
        roster_first_name=str(_get(roster, "first_name", "firstName", default="")),
        roster_last_name=str(_get(roster, "last_name", "lastName", default="")),
        roster_position=str(_get(roster, "position", default="")),
    )


def resolve_one(
    portal: Mapping[str, object],
    rosters: Iterable[Mapping[str, object]],
    *,
    roster_season: int | None = None,
    accept_threshold: float = 0.92,
    review_threshold: float = 0.82,
    accept_margin: float = 0.08,
    review_margin: float = 0.03,
) -> Resolution:
    season = int(_get(portal, "season", default=0) or 0)
    effective_roster_season = season if roster_season is None else int(roster_season)
    first = str(_get(portal, "first_name", "firstName", default=""))
    last = str(_get(portal, "last_name", "lastName", default=""))
    origin = str(_get(portal, "origin", default=""))
    destination = str(_get(portal, "destination", default=""))
    position = str(_get(portal, "position", default=""))

    if not destination.strip():
        return Resolution("unresolved", "no_destination", season, first, last, origin, destination, position, None, None, None, None, 0, ())

    dest_key = normalize_team(destination)
    target_pos = position_group(position)
    roster_rows = list(rosters)

    blocked: list[Mapping[str, object]] = []
    same_team: list[Mapping[str, object]] = []
    for row in roster_rows:
        roster_team = normalize_team(str(_get(row, "team", "school", default="")))

        # The CFBD /roster response is already scoped to a season by the API
        # request used to archive this roster. RosterPlayer.year represents
        # the player's class/year, not the roster season, so it must not be
        # compared with the portal season here.
        if roster_team != dest_key:
            continue
        same_team.append(row)
        if not target_pos or position_group(str(_get(row, "position", default=""))) == target_pos:
            blocked.append(row)

    # Position can be dirty/missing. Fall back to destination-team block rather than silently dropping the player.
    candidates_source = blocked or same_team
    if not candidates_source:
        return Resolution("unresolved", "no_destination_roster_candidate", season, first, last, origin, destination, position, None, None, None, None, 0, ())

    scored = sorted((score_candidate(portal, row, effective_roster_season) for row in candidates_source), key=lambda x: (-x.score, x.player_id))
    top = scored[0]
    second_score = scored[1].score if len(scored) > 1 else 0.0
    margin = top.score - second_score if len(scored) > 1 else top.score

    # Exact full-name collisions are deliberately held out unless position blocking removed the collision.
    p_first, p_last = normalize_person_name(first, last)
    exact_name = []
    for row in candidates_source:
        r_first, r_last = normalize_person_name(_get(row, "first_name", "firstName"), _get(row, "last_name", "lastName"))
        if first_name_alias_match(p_first, r_first) and p_last == r_last:
            exact_name.append(row)
    unique_exact_ids = {_candidate_id(row) for row in exact_name if _candidate_id(row)}
    if len(unique_exact_ids) > 1:
        return Resolution(
            "ambiguous",
            "same_name_collision",
            season,
            first,
            last,
            origin,
            destination,
            position,
            None,
            top.score,
            second_score,
            round(margin, 6),
            len(scored),
            tuple(scored[:5]),
        )

    if top.score >= accept_threshold and margin >= accept_margin:
        status, reason = "resolved", "high_confidence"
        player_id = top.player_id or None
    elif top.score >= review_threshold and margin >= review_margin:
        status, reason = "review", "manual_review_required"
        player_id = top.player_id or None
    elif top.score >= review_threshold:
        status, reason = "ambiguous", "small_score_margin"
        player_id = None
    else:
        status, reason = "unresolved", "low_match_score"
        player_id = None

    return Resolution(
        status,
        reason,
        season,
        first,
        last,
        origin,
        destination,
        position,
        player_id,
        top.score,
        second_score,
        round(margin, 6),
        len(scored),
        tuple(scored[:5]),
    )


def resolve_many(portal_rows: Iterable[Mapping[str, object]], roster_rows: Iterable[Mapping[str, object]]) -> list[Resolution]:
    rosters = list(roster_rows)
    return [resolve_one(row, rosters) for row in portal_rows]
