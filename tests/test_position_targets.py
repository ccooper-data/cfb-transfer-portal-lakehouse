import unittest

from cfb_portal.position_targets import (
    build_position_modeling_table,
    model_position_group,
)


class PositionTargetTests(unittest.TestCase):
    def test_kicker_and_punter_remain_separate(self):
        self.assertEqual(model_position_group("K"), "K")
        self.assertEqual(model_position_group("PK"), "K")
        self.assertEqual(model_position_group("P"), "P")

    def test_qb_uses_passing_yards_anchor(self):
        rows = [{
            "portal_key": "q1",
            "portal_season": "2024",
            "portal_position": "QB",
            "pre_passing_yds": "1200",
            "post_passing_yds": "1800",
            "pre_rushing_yds": "300",
            "post_rushing_yds": "600",
        }]
        modeling, exclusions, summary = build_position_modeling_table(rows)
        self.assertEqual(exclusions, [])
        self.assertEqual(modeling[0]["target_metric"], "passing_yds")
        self.assertEqual(modeling[0]["baseline_pre_production"], 1200.0)
        self.assertEqual(modeling[0]["target_post_production"], 1800.0)
        self.assertEqual(modeling[0]["target_delta"], 600.0)
        self.assertNotIn(
            "post_passing_yds",
            summary["predictor_policy"]["allowed_predictor_columns"],
        )

    def test_offensive_line_is_explicitly_excluded(self):
        rows = [{
            "portal_key": "o1",
            "portal_season": "2024",
            "portal_position": "OT",
            "pre_defensive_tot": "1",
            "post_defensive_tot": "1",
        }]
        modeling, exclusions, _ = build_position_modeling_table(rows)
        self.assertEqual(modeling, [])
        self.assertEqual(
            exclusions[0]["exclusion_reason"],
            "unsupported_position_target",
        )
        self.assertEqual(exclusions[0]["model_position_group"], "OL")

    def test_missing_anchor_is_not_zero_imputed(self):
        rows = [{
            "portal_key": "r1",
            "portal_season": "2024",
            "portal_position": "RB",
            "pre_rushing_yds": "",
            "post_rushing_yds": "900",
        }]
        modeling, exclusions, _ = build_position_modeling_table(rows)
        self.assertEqual(modeling, [])
        self.assertEqual(exclusions[0]["exclusion_reason"], "missing_pre_anchor")


if __name__ == "__main__":
    unittest.main()
