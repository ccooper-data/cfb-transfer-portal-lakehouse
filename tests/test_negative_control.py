import unittest

from cfb_portal.negative_control import (
    _fit_destination_encoding,
    _with_destination_signal,
    build_negative_control_panel,
    evaluate_negative_control_2025,
)


class NegativeControlTests(unittest.TestCase):
    def test_panel_target_is_prior_change(self):
        modeling = [{
            "portal_key": "k1",
            "portal_season": "2024",
            "player_id": "11",
            "model_position_group": "QB",
            "target_metric": "passing_yds",
            "baseline_pre_production": "1500",
            "destination": "New School",
            "rating": "0.9",
            "stars": "4",
        }]
        stats = {
            2022: [{
                "season": 2022,
                "playerId": "11",
                "category": "passing",
                "statType": "YDS",
                "stat": "1000",
            }]
        }
        panel, exclusions, _ = build_negative_control_panel(modeling, stats)
        self.assertEqual(exclusions, [])
        self.assertEqual(panel[0]["s2_production"], 1000.0)
        self.assertEqual(panel[0]["s1_production"], 1500.0)
        self.assertEqual(panel[0]["negative_control_prior_change"], 500.0)

    def test_missing_s2_is_excluded_not_zero_imputed(self):
        modeling = [{
            "portal_key": "k2",
            "portal_season": "2024",
            "player_id": "22",
            "model_position_group": "RB",
            "target_metric": "rushing_yds",
            "baseline_pre_production": "700",
        }]
        panel, exclusions, _ = build_negative_control_panel(modeling, {2022: []})
        self.assertEqual(panel, [])
        self.assertEqual(
            exclusions[0]["exclusion_reason"],
            "missing_s2_anchor",
        )

    def test_destination_encoding_uses_training_fallback_for_unseen_team(self):
        train = [
            {
                "destination": "A",
                "negative_control_prior_change": 10.0,
            },
            {
                "destination": "B",
                "negative_control_prior_change": 30.0,
            },
        ]
        mapping, fallback = _fit_destination_encoding(train)
        holdout = _with_destination_signal(
            [{"destination": "UNSEEN"}],
            mapping,
            fallback,
        )
        self.assertEqual(fallback, 20.0)
        self.assertEqual(
            holdout[0]["destination_prior_change_signal"],
            20.0,
        )

    def test_2025_is_negative_control_holdout_only(self):
        rows = []
        for year in [2022, 2023, 2024]:
            for i in range(20):
                rows.append({
                    "portal_key": f"train-{year}-{i}",
                    "portal_season": year,
                    "model_position_group": "WR",
                    "target_metric": "receiving_yds",
                    "destination": "A" if i % 2 == 0 else "B",
                    "rating": 0.8 + i / 1000.0,
                    "stars": 3,
                    "negative_control_prior_change": float(i * 2),
                })
        for i in range(12):
            rows.append({
                "portal_key": f"holdout-{i}",
                "portal_season": 2025,
                "model_position_group": "WR",
                "target_metric": "receiving_yds",
                "destination": "A",
                "rating": 0.85,
                "stars": 4,
                "negative_control_prior_change": float(i),
            })

        predictions, summary = evaluate_negative_control_2025(rows)
        result = summary["position_results"]["WR"]
        self.assertEqual(result["train_rows"], 60)
        self.assertEqual(result["holdout_rows"], 12)
        self.assertEqual(len(predictions), 12)
        self.assertFalse(summary["guardrails"]["2025_used_for_fit"])
        self.assertFalse(
            summary["guardrails"]["2025_used_for_destination_encoding"]
        )


if __name__ == "__main__":
    unittest.main()
