from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Mapping

from .normalize import normalize_team


def _team_set(rows: Iterable[Mapping[str, object]]) -> list[str]:
    teams = {
        str(row.get("team") or "").strip()
        for row in rows
        if str(row.get("team") or "").strip()
    }
    return sorted(teams)


def build_resolved_player_season_bridge(
    resolutions: Iterable[Mapping[str, object]],
    stats_by_year: Mapping[int, Iterable[Mapping[str, object]]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Build a one-row-per-resolved-transfer bridge plus linked long-form stats.

    The bridge only links production rows by the stable CFBD player ID. Team
    agreement is retained as an explicit quality flag. Long-form linked stats
    are limited to the expected origin team for pre-transfer production and the
    expected destination team for post-transfer production.
    """
    resolved_rows = [
        dict(row)
        for row in resolutions
        if str(row.get("status") or "") == "resolved"
        and str(row.get("player_id") or "").strip()
    ]

    needed_ids_by_year: dict[int, set[str]] = defaultdict(set)
    for row in resolved_rows:
        season = int(row["portal_season"])
        player_id = str(row["player_id"])
        needed_ids_by_year[season - 1].add(player_id)
        needed_ids_by_year[season].add(player_id)

    indexed: dict[int, dict[str, list[dict[str, object]]]] = {}
    source_row_counts: dict[int, int] = {}

    for year, raw_rows in stats_by_year.items():
        rows = [dict(r) for r in raw_rows]
        source_row_counts[int(year)] = len(rows)
        needed = needed_ids_by_year.get(int(year), set())
        by_player: dict[str, list[dict[str, object]]] = defaultdict(list)
        if needed:
            for row in rows:
                player_id = str(row.get("playerId") or "").strip()
                if player_id in needed:
                    by_player[player_id].append(row)
        indexed[int(year)] = dict(by_player)

    bridge: list[dict[str, object]] = []
    linked_stats: list[dict[str, object]] = []
    by_season: dict[int, Counter[str]] = defaultdict(Counter)

    for row in resolved_rows:
        season = int(row["portal_season"])
        prior = season - 1
        player_id = str(row["player_id"])
        origin = str(row.get("origin") or "")
        destination = str(row.get("destination") or "")
        origin_norm = normalize_team(origin)
        destination_norm = normalize_team(destination)

        pre_source_available = source_row_counts.get(prior, 0) > 0
        post_source_available = source_row_counts.get(season, 0) > 0

        pre_rows = indexed.get(prior, {}).get(player_id, [])
        post_rows = indexed.get(season, {}).get(player_id, [])

        pre_origin_rows = [
            stat for stat in pre_rows
            if normalize_team(str(stat.get("team") or "")) == origin_norm
        ]
        post_destination_rows = [
            stat for stat in post_rows
            if normalize_team(str(stat.get("team") or "")) == destination_norm
        ]

        pre_teams = _team_set(pre_rows)
        post_teams = _team_set(post_rows)

        bridge_row = {
            "portal_key": row.get("portal_key"),
            "portal_season": season,
            "transfer_date": row.get("transfer_date"),
            "player_id": player_id,
            "portal_first_name": row.get("portal_first_name"),
            "portal_last_name": row.get("portal_last_name"),
            "portal_position": row.get("position"),
            "origin": origin,
            "destination": destination,
            "rating": row.get("rating"),
            "stars": row.get("stars"),
            "eligibility": row.get("eligibility"),
            "resolver_score": row.get("score"),
            "resolver_score_margin": row.get("score_margin"),
            "match_strategy": row.get("match_strategy"),
            "roster_match_season": row.get("roster_match_season"),
            "pre_season": prior,
            "post_season": season,
            "pre_stats_source_available": pre_source_available,
            "post_stats_source_available": post_source_available,
            "pre_has_player_stats": bool(pre_rows),
            "pre_has_origin_stats": bool(pre_origin_rows),
            "post_has_player_stats": bool(post_rows),
            "post_has_destination_stats": bool(post_destination_rows),
            "pre_stat_row_count": len(pre_rows),
            "pre_origin_stat_row_count": len(pre_origin_rows),
            "post_stat_row_count": len(post_rows),
            "post_destination_stat_row_count": len(post_destination_rows),
            "pre_stat_teams": pre_teams,
            "post_stat_teams": post_teams,
            "pre_team_mismatch": bool(pre_rows) and not bool(pre_origin_rows),
            "post_team_mismatch": bool(post_rows) and not bool(post_destination_rows),
            "complete_pre_post_expected_team_stats": (
                bool(pre_origin_rows) and bool(post_destination_rows)
            ),
            "post_outcome_right_censored": not post_source_available,
        }
        bridge.append(bridge_row)

        counter = by_season[season]
        counter["resolved"] += 1
        counter["pre_source_available"] += int(pre_source_available)
        counter["post_source_available"] += int(post_source_available)
        counter["pre_id"] += int(bool(pre_rows))
        counter["pre_origin"] += int(bool(pre_origin_rows))
        counter["post_id"] += int(bool(post_rows))
        counter["post_destination"] += int(bool(post_destination_rows))
        counter["pre_team_mismatch"] += int(bool(pre_rows) and not bool(pre_origin_rows))
        counter["post_team_mismatch"] += int(bool(post_rows) and not bool(post_destination_rows))
        counter["complete_pre_post_expected_team_stats"] += int(
            bool(pre_origin_rows) and bool(post_destination_rows)
        )

        for phase, expected_team, expected_rows in (
            ("pre", origin, pre_origin_rows),
            ("post", destination, post_destination_rows),
        ):
            for stat in expected_rows:
                linked_stats.append({
                    "portal_key": row.get("portal_key"),
                    "portal_season": season,
                    "phase": phase,
                    "player_id": player_id,
                    "expected_team": expected_team,
                    "stat_season": int(stat.get("season") or (prior if phase == "pre" else season)),
                    "player": stat.get("player"),
                    "position": stat.get("position"),
                    "team": stat.get("team"),
                    "conference": stat.get("conference"),
                    "category": stat.get("category"),
                    "stat_type": stat.get("statType"),
                    "stat": stat.get("stat"),
                })

    complete_model_rows = sum(
        int(bool(row["complete_pre_post_expected_team_stats"]))
        for row in bridge
        if not bool(row["post_outcome_right_censored"])
    )
    completed_outcome_rows = sum(
        int(not bool(row["post_outcome_right_censored"]))
        for row in bridge
    )

    summary = {
        "resolved_bridge_rows": len(bridge),
        "linked_long_stat_rows": len(linked_stats),
        "completed_outcome_bridge_rows": completed_outcome_rows,
        "complete_pre_post_expected_team_rows": complete_model_rows,
        "complete_pre_post_expected_team_rate_among_completed_outcomes": (
            complete_model_rows / completed_outcome_rows
            if completed_outcome_rows else None
        ),
        "by_portal_season": {
            str(year): dict(by_season[year])
            for year in sorted(by_season)
        },
        "policy": {
            "identity_join": "exact CFBD player ID only",
            "pre_stats": "expected portal origin team only",
            "post_stats": "expected portal destination team only",
            "team_mismatch": "retained as an explicit flag; mismatched team stats are not silently substituted",
            "missing_stats": "missing is not converted to zero",
            "right_censoring": "post-season stats source unavailable/empty is marked right-censored",
        },
    }
    return bridge, linked_stats, summary
