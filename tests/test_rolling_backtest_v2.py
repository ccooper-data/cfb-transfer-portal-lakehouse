import unittest

from cfb_portal.rolling_backtest_v2 import (
    _fit_preprocessor,
    _transform,
    evaluate_rolling_backtest_v2,
)


class RollingBacktestV2Tests(unittest.TestCase):
    def test_missing_numeric_feature_gets_missingness_channel(self):
        rows = [{"x": None}, {"x": 10.0}, {"x": 20.0}]
        prep = _fit_preprocessor(rows, ("x",))
        matrix = _transform(rows, ("x",), prep)

        self.assertEqual(len(matrix[0]), 3)
        self.assertEqual(matrix[0][2], 1.0)
        self.assertEqual(matrix[1][2], 0.0)

    def test_2025_is_excluded_from_primary_backtest(self):
        rows = []
        for season in (2021, 2022, 2023, 2024, 2025):
            for i in range(50):
                rows.append({
                    "portal_key": f"{season}-{i}",
                    "portal_season": season,
                    "model_position_group": "RB",
                    "target_post_production": 100 + i,
                    "baseline_pre_production": 90 + i,
                    "pre_rushing_car": 10 + i,
                    "pre_rushing_td": 1,
                    "pre_rushing_ypc": 4.0,
                    "pre_receiving_rec": 5,
                    "pre_receiving_yds": 50,
                    "pre_receiving_td": 1,
                    "rating": 0.8,
                    "stars": 3,
                })
        predictions, summary = evaluate_rolling_backtest_v2(rows)

        self.assertTrue(predictions)
        self.assertTrue(all(row["holdout_year"] != 2025 for row in predictions))
        self.assertEqual(
            summary["evaluation_design"]["excluded_from_primary_v2_evidence"],
            [2025],
        )

    def test_low_sample_group_fold_is_skipped(self):
        rows = []
        for i in range(10):
            rows.append({
                "portal_key": f"2021-{i}",
                "portal_season": 2021,
                "model_position_group": "EDGE",
                "target_post_production": 10 + i,
            })
        for i in range(30):
            rows.append({
                "portal_key": f"2022-{i}",
                "portal_season": 2022,
                "model_position_group": "EDGE",
                "target_post_production": 20 + i,
            })

        _, summary = evaluate_rolling_backtest_v2(rows)
        edge_2022 = [
            result
            for result in summary["fold_results"]
            if result["holdout_year"] == 2022
            and result["model_position_group"] == "EDGE"
        ][0]
        self.assertEqual(edge_2022["status"], "skipped_low_sample")

    def test_all_row_baseline_works_when_pre_anchor_missing(self):
        rows = []
        for season, n in ((2021, 45), (2022, 25)):
            for i in range(n):
                rows.append({
                    "portal_key": f"{season}-{i}",
                    "portal_season": season,
                    "model_position_group": "WR",
                    "target_post_production": 100 + i,
                    "baseline_pre_production": None if i % 2 == 0 else 80 + i,
                    "pre_receiving_rec": None if i % 3 == 0 else 10 + i,
                    "pre_receiving_td": 1,
                    "pre_receiving_ypr": 12,
                    "pre_receiving_long": 30,
                    "pre_rushing_yds": 0,
                    "pre_rushing_td": 0,
                    "rating": 0.8,
                    "stars": 3,
                })

        predictions, summary = evaluate_rolling_backtest_v2(rows)
        wr_2022 = [
            result
            for result in summary["fold_results"]
            if result["holdout_year"] == 2022
            and result["model_position_group"] == "WR"
        ][0]

        self.assertEqual(wr_2022["status"], "evaluated")
        self.assertEqual(len(predictions), 25)
        self.assertEqual(
            wr_2022["all_row_historical_mean_baseline"]["mae"] is not None,
            True,
        )
        self.assertLess(
            wr_2022["paired_rows_with_observed_pre_anchor"],
            wr_2022["holdout_rows"],
        )


if __name__ == "__main__":
    unittest.main()
