import unittest

from cfb_portal.evaluation import evaluate_resolutions


class EvaluationTests(unittest.TestCase):
    def test_labeled_accuracy_counts_only_labeled_rows(self):
        resolutions = [
            {"portal_season": 2024, "portal_first_name": "Mike", "portal_last_name": "Brown", "origin": "A", "destination": "B", "status": "resolved", "player_id": "11"},
            {"portal_season": 2024, "portal_first_name": "Chris", "portal_last_name": "Jones", "origin": "C", "destination": "D", "status": "ambiguous", "player_id": None},
        ]
        labels = [
            {"season": 2024, "first_name": "Mike", "last_name": "Brown", "origin": "A", "destination": "B", "expected_player_id": "11"},
            {"season": 2024, "first_name": "Chris", "last_name": "Jones", "origin": "C", "destination": "D", "expected_player_id": "22"},
        ]
        out = evaluate_resolutions(resolutions, labels)
        self.assertEqual(out["labeled_n"], 2)
        self.assertEqual(out["correct_n"], 1)
        self.assertEqual(out["false_negative_n"], 1)
        self.assertEqual(out["accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
