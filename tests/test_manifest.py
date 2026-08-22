import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cfb_portal.manifest import RawManifest


class ManifestTests(unittest.TestCase):
    def test_content_addressed_dedup_keeps_multiple_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "raw"
            payload = b'[{"season":2021,"first_name":"Mike"}]'
            with RawManifest(root) as m:
                obj1 = m.store_bytes(payload)
                obj2 = m.store_bytes(payload)
                self.assertEqual(obj1.sha256, obj2.sha256)
                self.assertEqual(obj1.object_path, obj2.object_path)
                for i in range(2):
                    m.record_download(
                        endpoint="portal",
                        season=2021,
                        params={"year": 2021},
                        requested_at=f"2026-01-01T00:00:0{i}.000Z",
                        received_at=f"2026-01-01T00:00:0{i}.100Z",
                        stored=obj1,
                        http_status=200,
                        source_url="https://api.collegefootballdata.com/player/portal?year=2021",
                    )
            db = sqlite3.connect(root / "manifest.sqlite")
            self.assertEqual(db.execute("select count(*) from downloads").fetchone()[0], 2)
            objects = list((root / "objects").rglob("*.json"))
            self.assertEqual(len(objects), 1)

    def test_manifest_records_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "raw"
            with RawManifest(root) as m:
                stored = m.store_bytes(b"[]")
                m.record_download(
                    endpoint="roster",
                    season=2024,
                    params={"year": 2024, "team": "Ohio State"},
                    requested_at="2026-01-01T00:00:00.000Z",
                    received_at="2026-01-01T00:00:00.100Z",
                    stored=stored,
                    http_status=200,
                    source_url="https://example/roster",
                    headers={"ETag": "abc", "Last-Modified": "yesterday", "X-Request-Id": "req-1"},
                )
            db = sqlite3.connect(root / "manifest.sqlite")
            row = db.execute("select endpoint, season, params_json, etag, last_modified, request_id from downloads").fetchone()
            self.assertEqual(row[0], "roster")
            self.assertEqual(row[1], 2024)
            self.assertEqual(json.loads(row[2])["team"], "Ohio State")
            self.assertEqual(row[3:], ("abc", "yesterday", "req-1"))


if __name__ == "__main__":
    unittest.main()
