import unittest

from cfb_portal.resolver import resolve_one


class ResolverTests(unittest.TestCase):
    def test_exact_name_destination_and_position_resolves(self):
        portal = {"season": 2024, "first_name": "Jordan", "last_name": "Smith Jr.", "position": "WR", "origin": "A", "destination": "Ohio State"}
        rosters = [
            {"year": 2024, "team": "Ohio State", "id": "101", "firstName": "Jordan", "lastName": "Smith", "position": "WR"},
            {"year": 2024, "team": "Ohio State", "id": "102", "firstName": "John", "lastName": "Smith", "position": "WR"},
        ]
        r = resolve_one(portal, rosters)
        self.assertEqual(r.status, "resolved")
        self.assertEqual(r.player_id, "101")

    def test_nickname_alias_resolves_mike_to_michael(self):
        portal = {"season": 2024, "first_name": "Mike", "last_name": "Brown", "position": "QB", "origin": "A", "destination": "Texas"}
        rosters = [
            {"year": 2024, "team": "Texas", "id": "7", "first_name": "Michael", "last_name": "Brown", "position": "QB"},
            {"year": 2024, "team": "Texas", "id": "8", "first_name": "Mason", "last_name": "Brown", "position": "QB"},
        ]
        r = resolve_one(portal, rosters)
        self.assertEqual(r.status, "resolved")
        self.assertEqual(r.player_id, "7")

    def test_same_name_collision_is_held_out(self):
        portal = {"season": 2024, "first_name": "Chris", "last_name": "Jones", "position": "DB", "origin": "A", "destination": "Miami"}
        rosters = [
            {"year": 2024, "team": "Miami", "id": "1", "first_name": "Chris", "last_name": "Jones", "position": "CB"},
            {"year": 2024, "team": "Miami", "id": "2", "first_name": "Christopher", "last_name": "Jones", "position": "S"},
        ]
        r = resolve_one(portal, rosters)
        self.assertEqual(r.status, "ambiguous")
        self.assertEqual(r.reason, "same_name_collision")
        self.assertIsNone(r.player_id)

    def test_missing_destination_is_not_guessed(self):
        portal = {"season": 2024, "first_name": "A", "last_name": "B", "position": "WR", "origin": "A", "destination": None}
        r = resolve_one(portal, [])
        self.assertEqual(r.status, "unresolved")
        self.assertEqual(r.reason, "no_destination")

    def test_no_roster_candidate_is_explicit(self):
        portal = {"season": 2024, "first_name": "A", "last_name": "B", "position": "WR", "origin": "A", "destination": "LSU"}
        r = resolve_one(portal, [{"year": 2024, "team": "Alabama", "id": "1", "first_name": "A", "last_name": "B", "position": "WR"}])
        self.assertEqual(r.status, "unresolved")
        self.assertEqual(r.reason, "no_destination_roster_candidate")

    def test_roster_player_year_is_not_treated_as_roster_season(self):
        portal = {
            "season": 2024,
            "first_name": "A",
            "last_name": "B",
            "position": "WR",
            "origin": "A",
            "destination": "LSU",
        }
        # RosterPlayer.year is player class/year, not season.
        # The roster dataset itself was already fetched for season 2024.
        roster = [{
            "year": 3,
            "team": "LSU",
            "id": "1",
            "first_name": "A",
            "last_name": "B",
            "position": "WR",
        }]
        r = resolve_one(portal, roster)
        self.assertEqual(r.status, "resolved")
        self.assertEqual(r.player_id, "1")

    def test_position_block_disambiguates_same_last_name(self):
        portal = {"season": 2024, "first_name": "Alex", "last_name": "Lee", "position": "QB", "origin": "A", "destination": "UCLA"}
        rosters = [
            {"year": 2024, "team": "UCLA", "id": "1", "first_name": "Alex", "last_name": "Lee", "position": "QB"},
            {"year": 2024, "team": "UCLA", "id": "2", "first_name": "Alex", "last_name": "Lee", "position": "CB"},
        ]
        r = resolve_one(portal, rosters)
        self.assertEqual(r.status, "resolved")
        self.assertEqual(r.player_id, "1")


if __name__ == "__main__":
    unittest.main()
