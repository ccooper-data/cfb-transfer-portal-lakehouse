import unittest

from cfb_portal.observability_v3_stress_test import (
    evaluate_2025_target_observability_stress_test,
)


def wr_row(season: int, index: int, observed: int) -> dict[str, object]:
    return {
        "portal_key": f"{season}-{index}",
        "portal_season": season,
        "model_position_group": "WR",
        "target_metric": "receiving_yds",
        "target_observed": observed,
        "any_stat_observed": observed,
        "baseline_pre_production": (
            None if index % 9 == 0 else float(100 + index)
        ),
        "pre_receiving_rec": 5 + index,
        "pre_receiving_td": observed * 3,
        "pre_receiving_ypr": 12.0,
        "pre_receiving_long": 30.0,
        "pre_rushing_yds": 0.0,
        "pre_rushing_td": 0.0,
        "rating": 0.80,
        "stars": 3,
    }


class ObservabilityV32025StressTestTests(unittest.TestCase):
    def build_rows(self) -> list[dict[str, object]]:
        rows = []
        for season in (2021, 2022, 2023, 2024, 2025):
            for index in range(60):
                observed = 0 if index % 5 == 0 else 1
                rows.append(wr_row(season, index, observed))
        return rows

    def test_2025_is_never_used_for_training(self):
        predictions, summary = (
            evaluate_2025_target_observability_stress_test(
                self.build_rows()
            )
        )

        self.assertTrue(predictions)
        result = summary["position_group_results"][0]
        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["train_rows"], 240)
        self.assertEqual(result["stress_test_rows"], 60)
        self.assertTrue(
            all(int(row["portal_season"]) == 2025 for row in predictions)
        )

    def test_protocol_labels_result_as_stress_test_not_pristine(self):
        _, summary = evaluate_2025_target_observability_stress_test(
            self.build_rows()
        )
        design = summary["evaluation_design"]

        self.assertEqual(design["label"], "2025 temporal stress test")
        self.assertTrue(
            design["aggregate_2025_labels_previously_inspected"]
        )
        self.assertFalse(design["pristine_holdout_claim"])
        self.assertEqual(design["primary_metric"], "Brier score")

    def test_model_and_baseline_score_identical_2025_rows(self):
        predictions, summary = (
            evaluate_2025_target_observability_stress_test(
                self.build_rows()
            )
        )
        result = summary["position_group_results"][0]

        self.assertEqual(len(predictions), result["stress_test_rows"])
        self.assertIsNotNone(result["logistic_v3"]["brier"])
        self.assertIsNotNone(result["prevalence_baseline"]["brier"])
        self.assertTrue(
            all(
                row["training_prevalence_baseline"] is not None
                for row in predictions
            )
        )

    def test_2025_label_changes_do_not_change_training_prevalence(self):
        rows_a = self.build_rows()
        rows_b = [dict(row) for row in rows_a]
        for row in rows_b:
            if int(row["portal_season"]) == 2025:
                row["target_observed"] = 1 - int(row["target_observed"])

        _, summary_a = evaluate_2025_target_observability_stress_test(rows_a)
        _, summary_b = evaluate_2025_target_observability_stress_test(rows_b)

        result_a = summary_a["position_group_results"][0]
        result_b = summary_b["position_group_results"][0]

        self.assertEqual(
            result_a["training_target_observed_prevalence"],
            result_b["training_target_observed_prevalence"],
        )
        self.assertEqual(
            result_a["chosen_l2"],
            result_b["chosen_l2"],
        )


if __name__ == "__main__":
    unittest.main()
