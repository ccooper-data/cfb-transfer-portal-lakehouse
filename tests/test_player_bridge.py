import unittest

from cfb_portal.player_bridge import build_resolved_player_season_bridge


class PlayerBridgeTests(unittest.TestCase):
    def test_exact_id_and_expected_teams_link_pre_and_post(self):
        resolutions = [{
            "status": "resolved",
            "portal_key": "k1",
            "portal_season": 2024,
            "player_id": "11",
            "portal_first_name": "Test",
            "portal_last_name": "Player",
            "position": "RB",
            "origin": "Old School",
            "destination": "New School",
            "score": 1.0,
            "score_margin": 0.5,
            "match_strategy": "same_season",
            "roster_match_season": 2024,
        }]
        stats = {
            2023: [{
                "season": 2023, "playerId": "11", "player": "Test Player",
                "position": "RB", "team": "Old School", "conference": "X",
                "category": "rushing", "statType": "YDS", "stat": "500",
            }],
            2024: [{
                "season": 2024, "playerId": "11", "player": "Test Player",
                "position": "RB", "team": "New School", "conference": "Y",
                "category": "rushing", "statType": "YDS", "stat": "800",
            }],
        }

        bridge, linked, summary = build_resolved_player_season_bridge(
            resolutions, stats
        )
        self.assertEqual(len(bridge), 1)
        self.assertTrue(bridge[0]["pre_has_origin_stats"])
        self.assertTrue(bridge[0]["post_has_destination_stats"])
        self.assertTrue(bridge[0]["complete_pre_post_expected_team_stats"])
        self.assertEqual({r["phase"] for r in linked}, {"pre", "post"})
        self.assertEqual(summary["complete_pre_post_expected_team_rows"], 1)

    def test_wrong_team_is_flagged_and_not_silently_substituted(self):
        resolutions = [{
            "status": "resolved",
            "portal_key": "k2",
            "portal_season": 2024,
            "player_id": "22",
            "origin": "Portal Origin",
            "destination": "Destination",
        }]
        stats = {
            2023: [{
                "season": 2023, "playerId": "22", "player": "P",
                "position": "WR", "team": "Different Team", "conference": "X",
                "category": "receiving", "statType": "YDS", "stat": "300",
            }],
            2024: [],
        }

        bridge, linked, _ = build_resolved_player_season_bridge(
            resolutions, stats
        )
        self.assertTrue(bridge[0]["pre_has_player_stats"])
        self.assertFalse(bridge[0]["pre_has_origin_stats"])
        self.assertTrue(bridge[0]["pre_team_mismatch"])
        self.assertEqual(len(linked), 0)

    def test_empty_post_source_marks_right_censored(self):
        resolutions = [{
            "status": "resolved",
            "portal_key": "k3",
            "portal_season": 2026,
            "player_id": "33",
            "origin": "Origin",
            "destination": "Destination",
        }]
        stats = {
            2025: [{
                "season": 2025, "playerId": "33", "player": "P",
                "position": "QB", "team": "Origin", "conference": "X",
                "category": "passing", "statType": "YDS", "stat": "2000",
            }],
            2026: [],
        }

        bridge, _, _ = build_resolved_player_season_bridge(
            resolutions, stats
        )
        self.assertTrue(bridge[0]["pre_has_origin_stats"])
        self.assertFalse(bridge[0]["post_stats_source_available"])
        self.assertTrue(bridge[0]["post_outcome_right_censored"])


if __name__ == "__main__":
    unittest.main()
