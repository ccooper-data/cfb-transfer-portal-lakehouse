import csv
import tempfile
import unittest
from pathlib import Path

from cfb_portal.audit import resolution_accounting, stratified_audit_sample, write_label_template


class AuditTests(unittest.TestCase):
    def test_resolution_accounting_is_complete(self):
        rows = [
            {"status": "resolved", "reason": "high_confidence"},
            {"status": "resolved", "reason": "high_confidence"},
            {"status": "ambiguous", "reason": "same_name_collision"},
            {"status": "unresolved", "reason": "no_destination"},
        ]
        out = resolution_accounting(rows)
        self.assertEqual(out["portal_entries"], 4)
        self.assertEqual(out["auto_resolved_n"], 2)
        self.assertAlmostEqual(out["auto_resolved_rate"], 0.5)
        self.assertEqual(out["held_out_n"], 2)

    def test_audit_sample_is_deterministic_and_stratified(self):
        rows = []
        for reason in ("high_confidence", "same_name_collision", "no_destination"):
            status = "resolved" if reason == "high_confidence" else "unresolved"
            for i in range(10):
                rows.append({"status": status, "reason": reason, "portal_key": f"{reason}-{i}"})
        a = stratified_audit_sample(rows, per_reason=3, seed=7)
        b = stratified_audit_sample(rows, per_reason=3, seed=7)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 9)

    def test_label_template_keeps_portal_key(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "labels.csv"
            write_label_template(path, [{
                "portal_key": "abc", "portal_season": 2024, "portal_first_name": "A", "portal_last_name": "B",
                "position": "WR", "origin": "X", "destination": "Y", "status": "resolved",
                "player_id": "123", "score": 0.99,
            }])
            with path.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["portal_key"], "abc")
            self.assertEqual(rows[0]["predicted_player_id"], "123")


if __name__ == "__main__":
    unittest.main()
