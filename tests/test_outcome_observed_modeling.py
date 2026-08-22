import unittest

from cfb_portal.outcome_observed_modeling import (
    build_outcome_observed_modeling_table_v2,
)


class OutcomeObservedModelingV2Tests(unittest.TestCase):
    def test_missing_pre_anchor_is_retained_with_indicator(self):
        rows = [{
            "portal_key": "r1",
            "portal_season": 2025,
            "portal_position": "RB",
            "post_outcome_right_censored": False,
            "pre_rushing_yds": None,
            "post_rushing_yds": 900,
            "pre_receiving_yds": 120,
        }]
        modeling, exclusions, summary = build_outcome_observed_modeling_table_v2(rows)

        self.assertEqual(exclusions, [])
        self.assertEqual(len(modeling), 1)
        self.assertIsNone(modeling[0]["baseline_pre_production"])
        self.assertTrue(modeling[0]["baseline_pre_production_missing"])
        self.assertEqual(modeling[0]["target_post_production"], 900.0)
        self.assertIsNone(modeling[0]["target_delta"])
        self.assertTrue(modeling[0]["missing_pre_rushing_yds"])
        self.assertFalse(modeling[0]["missing_pre_receiving_yds"])
        self.assertEqual(summary["rows_missing_pre_anchor"], 1)

    def test_missing_post_target_is_excluded(self):
        rows = [{
            "portal_key": "q1",
            "portal_season": 2025,
            "portal_position": "QB",
            "post_outcome_right_censored": False,
            "pre_passing_yds": 1200,
            "post_passing_yds": None,
        }]
        modeling, exclusions, _ = build_outcome_observed_modeling_table_v2(rows)

        self.assertEqual(modeling, [])
        self.assertEqual(exclusions[0]["exclusion_reason"], "missing_post_target")

    def test_right_censored_row_is_excluded(self):
        rows = [{
            "portal_key": "w1",
            "portal_season": 2026,
            "portal_position": "WR",
            "post_outcome_right_censored": True,
            "pre_receiving_yds": 700,
            "post_receiving_yds": 800,
        }]
        modeling, exclusions, _ = build_outcome_observed_modeling_table_v2(rows)

        self.assertEqual(modeling, [])
        self.assertEqual(
            exclusions[0]["exclusion_reason"],
            "post_outcome_right_censored",
        )

    def test_post_features_are_not_copied_into_predictor_table(self):
        rows = [{
            "portal_key": "t1",
            "portal_season": 2025,
            "portal_position": "TE",
            "post_outcome_right_censored": False,
            "pre_receiving_yds": 300,
            "post_receiving_yds": 500,
            "pre_receiving_td": 2,
            "post_receiving_td": 5,
        }]
        modeling, _, _ = build_outcome_observed_modeling_table_v2(rows)

        self.assertIn("pre_receiving_td", modeling[0])
        self.assertNotIn("post_receiving_td", modeling[0])

    def test_pre_metadata_columns_are_not_raw_features(self):
        rows = [{
            "portal_key": "d1",
            "portal_season": 2025,
            "portal_position": "DB",
            "post_outcome_right_censored": False,
            "pre_season": 2024,
            "pre_stats_source_available": True,
            "pre_has_player_stats": True,
            "pre_has_origin_stats": True,
            "pre_team_mismatch": False,
            "pre_defensive_tot": 30,
            "post_defensive_tot": 40,
        }]
        modeling, _, summary = build_outcome_observed_modeling_table_v2(rows)

        self.assertEqual(summary["pre_feature_names"], ["pre_defensive_tot"])
        self.assertIn("missing_pre_defensive_tot", modeling[0])
        self.assertNotIn("missing_pre_season", modeling[0])


if __name__ == "__main__":
    unittest.main()
