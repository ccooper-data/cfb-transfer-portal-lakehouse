import unittest

from cfb_portal.scoring_2026 import (
    SCOREABLE_GROUPS,
    build_2026_scoring_cohort,
)


class Scoring2026ContractTests(unittest.TestCase):
    def test_missing_pre_anchor_is_retained(self):
        rows = [{
            "portal_key": "r1",
            "portal_season": 2026,
            "portal_position": "RB",
            "player_id": "1",
            "pre_rushing_yds": None,
            "pre_rushing_car": 40,
            "pre_rushing_td": 2,
            "pre_rushing_ypc": 4.5,
            "pre_receiving_rec": 5,
            "pre_receiving_yds": 50,
            "pre_receiving_td": 1,
            "post_rushing_yds": None,
            "rating": 0.8,
            "stars": 3,
        }]
        scoring, exclusions, summary = build_2026_scoring_cohort(rows)

        self.assertEqual(exclusions, [])
        self.assertEqual(len(scoring), 1)
        self.assertIsNone(scoring[0]["baseline_pre_production"])
        self.assertTrue(scoring[0]["baseline_pre_production_missing"])
        self.assertEqual(summary["pre_anchor_missing_rows"], 1)

    def test_punter_is_excluded_for_insufficient_locked_evidence(self):
        rows = [{
            "portal_key": "p1",
            "portal_season": 2026,
            "portal_position": "P",
            "player_id": "2",
            "pre_punting_ypp": 42,
        }]
        scoring, exclusions, _ = build_2026_scoring_cohort(rows)

        self.assertEqual(scoring, [])
        self.assertEqual(
            exclusions[0]["exclusion_reason"],
            "insufficient_locked_v2_validation_evidence",
        )

    def test_post_features_are_not_copied(self):
        rows = [{
            "portal_key": "w1",
            "portal_season": 2026,
            "portal_position": "WR",
            "player_id": "3",
            "pre_receiving_yds": 700,
            "pre_receiving_rec": 50,
            "pre_receiving_td": 6,
            "pre_receiving_ypr": 14,
            "pre_receiving_long": 60,
            "pre_rushing_yds": 20,
            "pre_rushing_td": 1,
            "post_receiving_yds": 999,
            "rating": 0.9,
            "stars": 4,
        }]
        scoring, _, _ = build_2026_scoring_cohort(rows)

        self.assertNotIn("post_receiving_yds", scoring[0])
        self.assertEqual(
            scoring[0]["post_outcome_status"],
            "right_censored_unobserved",
        )

    def test_non_2026_rows_do_not_enter_scoring_cohort(self):
        rows = [{
            "portal_key": "q1",
            "portal_season": 2025,
            "portal_position": "QB",
            "player_id": "4",
            "pre_passing_yds": 1000,
        }]
        scoring, exclusions, summary = build_2026_scoring_cohort(rows)

        self.assertEqual(scoring, [])
        self.assertEqual(exclusions, [])
        self.assertEqual(summary["scoreable_rows"], 0)

    def test_scoreable_groups_match_locked_evidence(self):
        self.assertEqual(
            SCOREABLE_GROUPS,
            ("DB", "DL", "EDGE", "LB", "QB", "RB", "TE", "WR"),
        )


if __name__ == "__main__":
    unittest.main()
