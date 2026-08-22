import tempfile
import unittest
from pathlib import Path

from cfb_portal.manifest import RawManifest


class ManifestParamTests(unittest.TestCase):
    def test_latest_object_can_require_exact_params(self):
        with tempfile.TemporaryDirectory() as td:
            with RawManifest(td) as m:
                full = m.store_bytes(b'[{"id":1}]')
                m.record_download(endpoint="roster", season=2024, params={"year": 2024}, requested_at="a", received_at="b", stored=full, http_status=200, source_url="x")
                team = m.store_bytes(b'[{"id":2}]')
                m.record_download(endpoint="roster", season=2024, params={"year": 2024, "team": "Texas"}, requested_at="c", received_at="d", stored=team, http_status=200, source_url="y")
                self.assertEqual(m.latest_object("roster", 2024, params={"year": 2024}), Path(td) / full.object_path)
                self.assertEqual(m.latest_object("roster", 2024, params={"year": 2024, "team": "Texas"}), Path(td) / team.object_path)


if __name__ == "__main__":
    unittest.main()
