import json
import tempfile
import unittest
from pathlib import Path

from cfb_portal.manifest import RawManifest
from cfb_portal.pipeline import build_resolution_dataset


def archive(manifest, endpoint, season, rows):
    payload = json.dumps(rows).encode()
    stored = manifest.store_bytes(payload)

    manifest.record_download(
        endpoint=endpoint,
        season=season,
        params={"year": season},
        requested_at="a",
        received_at="b",
        stored=stored,
        http_status=200,
        source_url="x",
    )


class FallbackTests(unittest.TestCase):

    def test_unresolved_same_season_can_resolve_on_next_season(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "raw"
            out = Path(td) / "outputs"

            portal = [{
                "season": 2024,
                "first_name": "Cameron",
                "last_name": "Wilkins",
                "position": "LB",
                "origin": "Missouri",
                "destination": "UTSA",
                "transfer_date": "2024-07-31",
                "rating": None,
                "stars": 3,
                "eligibility": "Immediate",
            }]

            same_roster = [{
                "id": "1",
                "year": 3,
                "team": "UTSA",
                "first_name": "Nate",
                "last_name": "Hawkins",
                "position": "LB",
            }]

            next_roster = [{
                "id": "2",
                "year": 4,
                "team": "UTSA",
                "first_name": "Cameron",
                "last_name": "Wilkins",
                "position": "LB",
            }]

            with RawManifest(raw) as m:
                archive(m, "portal", 2024, portal)
                archive(m, "roster", 2024, same_roster)
                archive(m, "roster", 2025, next_roster)

            event = build_resolution_dataset(
                2024,
                2024,
                root=raw,
                output_dir=out,
            )

            self.assertAlmostEqual(
                event["auto_resolved_rate"],
                1.0,
            )

            with (
                out / "resolutions_2024_2024.jsonl"
            ).open() as handle:
                row = json.loads(next(handle))

            self.assertEqual(row["player_id"], "2")
            self.assertEqual(
                row["match_strategy"],
                "next_season_fallback",
            )
            self.assertEqual(
                row["roster_match_season"],
                2025,
            )
            self.assertTrue(row["fallback_attempted"])
            self.assertEqual(
                row["same_season_reason"],
                "low_match_score",
            )

    def test_ambiguous_same_season_is_not_overridden(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "raw"
            out = Path(td) / "outputs"

            portal = [{
                "season": 2024,
                "first_name": "Chris",
                "last_name": "Jones",
                "position": "DB",
                "origin": "A",
                "destination": "Miami",
                "transfer_date": "2024-01-01",
                "rating": None,
                "stars": 3,
                "eligibility": "JR",
            }]

            same_roster = [
                {
                    "id": "1",
                    "year": 2,
                    "team": "Miami",
                    "first_name": "Chris",
                    "last_name": "Jones",
                    "position": "CB",
                },
                {
                    "id": "2",
                    "year": 3,
                    "team": "Miami",
                    "first_name": "Christopher",
                    "last_name": "Jones",
                    "position": "S",
                },
            ]

            next_roster = [{
                "id": "3",
                "year": 4,
                "team": "Miami",
                "first_name": "Chris",
                "last_name": "Jones",
                "position": "DB",
            }]

            with RawManifest(raw) as m:
                archive(m, "portal", 2024, portal)
                archive(m, "roster", 2024, same_roster)
                archive(m, "roster", 2025, next_roster)

            build_resolution_dataset(
                2024,
                2024,
                root=raw,
                output_dir=out,
            )

            with (
                out / "resolutions_2024_2024.jsonl"
            ).open() as handle:
                row = json.loads(next(handle))

            self.assertEqual(row["status"], "ambiguous")
            self.assertEqual(
                row["reason"],
                "same_name_collision",
            )
            self.assertFalse(row["fallback_attempted"])
            self.assertEqual(row["match_strategy"], "none")
            self.assertIsNone(row["roster_match_season"])

    def test_missing_next_roster_is_recorded_as_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td) / "raw"
            out = Path(td) / "outputs"

            portal = [{
                "season": 2026,
                "first_name": "Future",
                "last_name": "Player",
                "position": "WR",
                "origin": "A",
                "destination": "Texas",
                "transfer_date": "2026-07-01",
                "rating": None,
                "stars": 3,
                "eligibility": "JR",
            }]

            same_roster = [{
                "id": "1",
                "year": 2,
                "team": "Texas",
                "first_name": "Other",
                "last_name": "Player",
                "position": "WR",
            }]

            with RawManifest(raw) as m:
                archive(m, "portal", 2026, portal)
                archive(m, "roster", 2026, same_roster)

            build_resolution_dataset(
                2026,
                2026,
                root=raw,
                output_dir=out,
            )

            with (
                out / "resolutions_2026_2026.jsonl"
            ).open() as handle:
                row = json.loads(next(handle))

            self.assertEqual(row["status"], "unresolved")
            self.assertFalse(row["fallback_attempted"])
            self.assertEqual(
                row["fallback_status"],
                "unavailable",
            )
            self.assertEqual(
                row["fallback_reason"],
                "next_roster_not_archived",
            )
            self.assertIsNone(row["roster_match_season"])


if __name__ == "__main__":
    unittest.main()
