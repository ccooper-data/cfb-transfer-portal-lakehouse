import json
import tempfile
import unittest
from pathlib import Path

from cfb_portal.manifest import RawManifest
from cfb_portal.pipeline import build_resolution_dataset


class PipelineTests(unittest.TestCase):
    def test_manifest_to_resolution_outputs_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "raw"
            out = Path(td) / "outputs"
            portal = [{
                "season": 2024, "first_name": "Mike", "last_name": "Smith", "position": "WR",
                "origin": "A", "destination": "Texas", "transfer_date": "2024-01-01",
                "rating": 0.9, "stars": 4, "eligibility": "JR",
            }]
            roster = [{"id": 42, "year": 2024, "team": "Texas", "first_name": "Michael", "last_name": "Smith", "position": "WR"}]
            with RawManifest(raw) as m:
                for endpoint, rows in (("portal", portal), ("roster", roster)):
                    payload = json.dumps(rows).encode()
                    stored = m.store_bytes(payload)
                    m.record_download(endpoint=endpoint, season=2024, params={"year": 2024}, requested_at="a", received_at="b", stored=stored, http_status=200, source_url="x")
            event = build_resolution_dataset(2024, 2024, root=raw, output_dir=out, audit_per_reason=5)
            self.assertEqual(event["rows"], 1)
            self.assertAlmostEqual(event["auto_resolved_rate"], 1.0)
            self.assertTrue((out / "resolutions_2024_2024.jsonl").exists())
            self.assertTrue((out / "resolver_accounting_2024_2024.json").exists())
            self.assertTrue((out / "entity_resolution_audit_2024_2024.csv").exists())


if __name__ == "__main__":
    unittest.main()
