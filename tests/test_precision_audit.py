import unittest

from cfb_portal.precision_audit import evaluate_precision_audit


class PrecisionAuditTests(unittest.TestCase):
    def _row(self, season, outcome, group="same_season_sample"):
        predicted = f"{season}-{outcome}"
        return {
            "audit_group": group,
            "portal_season": season,
            "predicted_player_id": predicted,
            "expected_player_id": predicted if outcome == "correct" else "",
            "label_outcome": outcome,
        }

    def test_stratified_precision_uses_population_weights(self):
        rows = [
            self._row(2021, "correct"),
            self._row(2021, "incorrect"),
            self._row(2022, "correct"),
            self._row(2022, "correct"),
            self._row(2023, "correct"),
            self._row(2023, "correct"),
            self._row(2024, "correct"),
            self._row(2024, "correct"),
            self._row(2025, "correct"),
            self._row(2025, "correct"),
            self._row(2026, "correct"),
            self._row(2026, "correct"),
            self._row(2021, "correct", "next_season_fallback_census"),
        ]
        population = {2021: 1, 2022: 1, 2023: 1, 2024: 1, 2025: 1, 2026: 1}
        out = evaluate_precision_audit(
            rows,
            same_season_population=population,
            production_auto_resolutions=7,
        )
        self.assertAlmostEqual(
            out["same_season_sample"]["strict_verified_rate"],
            (0.5 + 1 + 1 + 1 + 1 + 1) / 6,
        )
        self.assertEqual(out["audit"]["incorrect"], 1)

    def test_uncertain_is_not_silently_counted_as_correct(self):
        rows = []
        for season in (2021, 2022, 2023, 2024, 2025, 2026):
            rows.extend([self._row(season, "correct"), self._row(season, "correct")])
        rows[-1] = self._row(2026, "uncertain")
        rows.append(self._row(2021, "correct", "next_season_fallback_census"))

        population = {2021: 1, 2022: 1, 2023: 1, 2024: 1, 2025: 1, 2026: 1}
        out = evaluate_precision_audit(
            rows,
            same_season_population=population,
            production_auto_resolutions=7,
        )
        self.assertLess(out["same_season_sample"]["strict_verified_rate"], 1.0)
        self.assertAlmostEqual(out["same_season_sample"]["possible_upper_bound"], 1.0)

    def test_correct_requires_expected_id_to_match_prediction(self):
        rows = [
            {
                "audit_group": "same_season_sample",
                "portal_season": season,
                "predicted_player_id": str(season),
                "expected_player_id": "wrong" if season == 2021 else str(season),
                "label_outcome": "correct",
            }
            for season in (2021, 2022, 2023, 2024, 2025, 2026)
        ]
        rows.append(self._row(2021, "correct", "next_season_fallback_census"))
        with self.assertRaises(ValueError):
            evaluate_precision_audit(rows)


if __name__ == "__main__":
    unittest.main()
