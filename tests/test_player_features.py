import unittest

from cfb_portal.player_features import build_player_feature_matrix


class PlayerFeatureTests(unittest.TestCase):
    def test_category_and_stat_type_are_both_preserved(self):
        bridge = [{
            "portal_key": "k1",
            "portal_season": 2024,
            "complete_pre_post_expected_team_stats": True,
            "post_outcome_right_censored": False,
        }]
        stats = [
            {
                "portal_key": "k1",
                "phase": "pre",
                "category": "passing",
                "stat_type": "YDS",
                "stat": "1000",
            },
            {
                "portal_key": "k1",
                "phase": "pre",
                "category": "rushing",
                "stat_type": "YDS",
                "stat": "250",
            },
            {
                "portal_key": "k1",
                "phase": "post",
                "category": "passing",
                "stat_type": "YDS",
                "stat": "1200",
            },
        ]

        matrix, cohort, summary = build_player_feature_matrix(bridge, stats)
        self.assertEqual(matrix[0]["pre_passing_yds"], 1000.0)
        self.assertEqual(matrix[0]["pre_rushing_yds"], 250.0)
        self.assertEqual(matrix[0]["post_passing_yds"], 1200.0)
        self.assertEqual(len(cohort), 1)
        self.assertEqual(summary["distinct_feature_columns"], 3)

    def test_missing_stats_remain_null(self):
        bridge = [{
            "portal_key": "k2",
            "portal_season": 2024,
            "complete_pre_post_expected_team_stats": False,
            "post_outcome_right_censored": False,
        }, {
            "portal_key": "k3",
            "portal_season": 2024,
            "complete_pre_post_expected_team_stats": False,
            "post_outcome_right_censored": False,
        }]
        stats = [{
            "portal_key": "k2",
            "phase": "pre",
            "category": "rushing",
            "stat_type": "YDS",
            "stat": "400",
        }]

        matrix, cohort, _ = build_player_feature_matrix(bridge, stats)
        by_key = {r["portal_key"]: r for r in matrix}
        self.assertEqual(by_key["k2"]["pre_rushing_yds"], 400.0)
        self.assertIsNone(by_key["k3"]["pre_rushing_yds"])
        self.assertEqual(cohort, [])

    def test_conflicting_duplicate_stats_fail_closed(self):
        bridge = [{
            "portal_key": "k4",
            "portal_season": 2024,
            "complete_pre_post_expected_team_stats": True,
            "post_outcome_right_censored": False,
        }]
        stats = [
            {
                "portal_key": "k4",
                "phase": "pre",
                "category": "receiving",
                "stat_type": "YDS",
                "stat": "500",
            },
            {
                "portal_key": "k4",
                "phase": "pre",
                "category": "receiving",
                "stat_type": "YDS",
                "stat": "501",
            },
        ]

        with self.assertRaises(ValueError):
            build_player_feature_matrix(bridge, stats)


if __name__ == "__main__":
    unittest.main()
