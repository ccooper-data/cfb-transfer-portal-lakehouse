from __future__ import annotations

import unittest

from cfb_portal.forecast_support import (
    LIMITED,
    STANDARD,
    STRONG,
    classify_forecast_support,
    enrich_forecast_support,
)


class ForecastSupportTests(unittest.TestCase):
    def test_strong_when_pre_observed_and_two_or_fewer_missing(self) -> None:
        self.assertEqual(
            classify_forecast_support({
                "baseline_pre_production_missing": False,
                "model_feature_missing_count": 2,
            }),
            STRONG,
        )

    def test_standard_when_pre_observed_and_more_than_two_missing(self) -> None:
        self.assertEqual(
            classify_forecast_support({
                "baseline_pre_production_missing": "false",
                "model_feature_missing_count": "3",
            }),
            STANDARD,
        )

    def test_limited_when_pre_anchor_missing_regardless_of_missing_count(self) -> None:
        self.assertEqual(
            classify_forecast_support({
                "baseline_pre_production_missing": True,
                "model_feature_missing_count": 0,
            }),
            LIMITED,
        )

    def test_enrichment_preserves_point_forecast(self) -> None:
        rows = [{
            "portal_key": "x",
            "predicted_post_transfer_production": "123.456",
            "baseline_pre_production_missing": False,
            "model_feature_missing_count": 1,
        }]
        enriched, summary = enrich_forecast_support(rows)
        self.assertEqual(
            enriched[0]["predicted_post_transfer_production"],
            "123.456",
        )
        self.assertEqual(enriched[0]["forecast_support"], STRONG)
        self.assertFalse(summary["prediction_modified"])

    def test_invalid_boolean_fails(self) -> None:
        with self.assertRaises(ValueError):
            classify_forecast_support({
                "baseline_pre_production_missing": "maybe",
                "model_feature_missing_count": 1,
            })


if __name__ == "__main__":
    unittest.main()
