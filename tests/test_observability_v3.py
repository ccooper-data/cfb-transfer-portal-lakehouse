import unittest

from cfb_portal.observability_v3 import (
    _fit_logistic,
    build_target_observability_rows,
    evaluate_target_observability_v3,
)


class TargetObservabilityV3Tests(unittest.TestCase):
    def test_builder_uses_same_season_link_and_exact_target(self):
        bridge = [
            {
                "portal_key": "keep-1",
                "portal_season": 2024,
                "roster_match_season": 2024,
                "post_stats_source_available": True,
                "portal_position": "RB",
                "post_has_player_stats": True,
                "post_has_destination_stats": True,
            },
            {
                "portal_key": "keep-2",
                "portal_season": 2024,
                "roster_match_season": 2024,
                "post_stats_source_available": True,
                "portal_position": "RB",
                "post_has_player_stats": False,
                "post_has_destination_stats": False,
            },
            {
                "portal_key": "fallback",
                "portal_season": 2024,
                "roster_match_season": 2025,
                "post_stats_source_available": True,
                "portal_position": "RB",
            },
            {
                "portal_key": "future",
                "portal_season": 2026,
                "roster_match_season": 2026,
                "post_stats_source_available": True,
                "portal_position": "RB",
            },
        ]
        feature = [
            {
                "portal_key": "keep-1",
                "pre_rushing_yds": 400,
                "post_rushing_yds": 600,
                "pre_rushing_car": 80,
                "pre_rushing_td": 4,
                "pre_rushing_ypc": 5,
                "pre_receiving_rec": 10,
                "pre_receiving_yds": 90,
                "pre_receiving_td": 1,
                "rating": 0.85,
                "stars": 3,
            },
            {
                "portal_key": "keep-2",
                "pre_rushing_yds": 20,
                "post_rushing_yds": None,
                "pre_rushing_car": 4,
                "pre_rushing_td": 0,
                "pre_rushing_ypc": 5,
                "pre_receiving_rec": None,
                "pre_receiving_yds": None,
                "pre_receiving_td": None,
                "rating": None,
                "stars": None,
            },
            {"portal_key": "fallback"},
            {"portal_key": "future"},
        ]

        cohort, summary = build_target_observability_rows(
            bridge,
            feature,
        )

        self.assertEqual(len(cohort), 2)
        self.assertEqual(
            [row["target_observed"] for row in cohort],
            [1, 0],
        )
        self.assertEqual(summary["accounting"]["cohort_rows"], 2)
        self.assertEqual(
            summary["accounting"]["excluded_not_same_season_roster_link"],
            1,
        )
        self.assertEqual(
            summary["accounting"]["excluded_outside_2021_2025"],
            1,
        )

    def test_builder_retains_no_post_production_predictor(self):
        bridge = [{
            "portal_key": "x",
            "portal_season": 2024,
            "roster_match_season": 2024,
            "post_stats_source_available": True,
            "portal_position": "WR",
            "post_has_player_stats": True,
            "post_has_destination_stats": True,
        }]
        feature = [{
            "portal_key": "x",
            "pre_receiving_yds": 100,
            "post_receiving_yds": 200,
            "post_receiving_td": 10,
        }]
        cohort, _ = build_target_observability_rows(bridge, feature)

        self.assertTrue(cohort)
        self.assertFalse(
            any(
                name.startswith("post_")
                for name in cohort[0]
            )
        )

    def test_logistic_preprocessor_is_fit_on_supplied_training_rows_only(self):
        rows = []
        for i in range(20):
            rows.append({
                "target_observed": 0 if i < 10 else 1,
                "x": float(i),
            })

        model = _fit_logistic(rows, ("x",), 1.0)

        self.assertEqual(model["preprocessor"]["medians"], [9.5])

    def test_primary_backtest_never_scores_2025(self):
        rows = []
        for season in (2021, 2022, 2023, 2024, 2025):
            for i in range(60):
                observed = 0 if i % 5 == 0 else 1
                rows.append({
                    "portal_key": f"{season}-{i}",
                    "portal_season": season,
                    "model_position_group": "RB",
                    "target_observed": observed,
                    "any_stat_observed": observed,
                    "baseline_pre_production": (
                        20.0 if observed == 0 else 500.0
                    ),
                    "pre_rushing_car": 5 + i,
                    "pre_rushing_td": observed * 5,
                    "pre_rushing_ypc": 4.5,
                    "pre_receiving_rec": observed * 10,
                    "pre_receiving_yds": observed * 100,
                    "pre_receiving_td": observed,
                    "rating": 0.70 + (0.1 * observed),
                    "stars": 2 + observed,
                })

        predictions, summary = evaluate_target_observability_v3(rows)

        self.assertTrue(predictions)
        self.assertTrue(
            all(int(row["holdout_year"]) < 2025 for row in predictions)
        )
        self.assertEqual(
            summary["evaluation_design"][
                "excluded_from_primary_evidence"
            ],
            [2025],
        )
        self.assertEqual(
            summary["evaluation_design"]["primary_metric"],
            "Brier score",
        )

    def test_model_and_prevalence_baseline_use_identical_holdout_rows(self):
        rows = []
        for season in (2021, 2022, 2023, 2024):
            for i in range(60):
                observed = 0 if i % 4 == 0 else 1
                rows.append({
                    "portal_key": f"{season}-{i}",
                    "portal_season": season,
                    "model_position_group": "WR",
                    "target_observed": observed,
                    "any_stat_observed": observed,
                    "baseline_pre_production": (
                        None if i % 7 == 0 else 100 + i
                    ),
                    "pre_receiving_rec": 5 + i,
                    "pre_receiving_td": observed * 4,
                    "pre_receiving_ypr": 12,
                    "pre_receiving_long": 30,
                    "pre_rushing_yds": 0,
                    "pre_rushing_td": 0,
                    "rating": 0.8,
                    "stars": 3,
                })

        predictions, summary = evaluate_target_observability_v3(rows)
        wr_2022 = [
            result
            for result in summary["fold_results"]
            if result["holdout_year"] == 2022
            and result["model_position_group"] == "WR"
        ][0]

        self.assertEqual(wr_2022["status"], "evaluated")
        self.assertEqual(
            len(
                [
                    row for row in predictions
                    if row["holdout_year"] == 2022
                    and row["model_position_group"] == "WR"
                ]
            ),
            wr_2022["holdout_rows"],
        )
        self.assertIsNotNone(wr_2022["logistic_v3"]["brier"])
        self.assertIsNotNone(
            wr_2022["prevalence_baseline"]["brier"]
        )


if __name__ == "__main__":
    unittest.main()
