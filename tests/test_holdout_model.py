import unittest

from cfb_portal.holdout_model import (
    FEATURE_SPECS,
    _metrics,
    evaluate_2025_holdout,
)


class HoldoutModelTests(unittest.TestCase):
    def test_feature_specs_contain_no_post_features(self):
        for group, features in FEATURE_SPECS.items():
            self.assertTrue(features, group)
            self.assertFalse(
                any(feature.startswith("post_") for feature in features),
                group,
            )

    def test_baseline_metric_math(self):
        metrics = _metrics([10.0, 20.0], [12.0, 16.0])
        self.assertAlmostEqual(metrics["mae"], 3.0)
        self.assertAlmostEqual(metrics["rmse"], (10.0 ** 0.5))

    def test_2025_is_holdout_only(self):
        rows = []
        for year in [2021, 2022, 2023, 2024]:
            for i in range(20):
                pre = float(i + year - 2020)
                rows.append({
                    "portal_key": f"train-{year}-{i}",
                    "portal_season": str(year),
                    "model_position_group": "QB",
                    "target_metric": "passing_yds",
                    "baseline_pre_production": str(pre),
                    "target_post_production": str(pre * 1.2 + 100.0),
                    "pre_passing_yds": str(pre),
                    "pre_passing_att": str(pre / 2.0),
                })
        for i in range(20):
            pre = float(i + 10)
            rows.append({
                "portal_key": f"holdout-{i}",
                "portal_season": "2025",
                "model_position_group": "QB",
                "target_metric": "passing_yds",
                "baseline_pre_production": str(pre),
                "target_post_production": str(pre * 1.2 + 100.0),
                "pre_passing_yds": str(pre),
                "pre_passing_att": str(pre / 2.0),
            })

        predictions, summary = evaluate_2025_holdout(rows)
        result = summary["position_results"]["QB"]
        self.assertEqual(result["train_rows"], 80)
        self.assertEqual(result["holdout_rows"], 20)
        self.assertEqual(len(predictions), 20)
        self.assertTrue(all(r["portal_season"] == 2025 for r in predictions))
        self.assertTrue(summary["leakage_controls"]["holdout_2025_never_used_for_fit"])

    def test_returning_production_is_the_recorded_baseline(self):
        rows = []
        for year in [2021, 2022, 2023, 2024]:
            for i in range(20):
                rows.append({
                    "portal_key": f"t-{year}-{i}",
                    "portal_season": str(year),
                    "model_position_group": "RB",
                    "target_metric": "rushing_yds",
                    "baseline_pre_production": str(100 + i),
                    "target_post_production": str(150 + i),
                    "pre_rushing_yds": str(100 + i),
                })
        for i in range(10):
            rows.append({
                "portal_key": f"h-{i}",
                "portal_season": "2025",
                "model_position_group": "RB",
                "target_metric": "rushing_yds",
                "baseline_pre_production": str(300 + i),
                "target_post_production": str(350 + i),
                "pre_rushing_yds": str(300 + i),
            })

        predictions, _ = evaluate_2025_holdout(rows)
        for row in predictions:
            self.assertAlmostEqual(
                row["returning_production_prediction"],
                300.0 + int(str(row["portal_key"]).split("-")[-1]),
            )


if __name__ == "__main__":
    unittest.main()
