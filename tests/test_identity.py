import unittest

from cfb_portal.identity import portal_entry_key


class IdentityTests(unittest.TestCase):
    def test_portal_key_is_stable_across_equivalent_formatting(self):
        a = {
            "season": 2024, "first_name": "Mike", "last_name": "Smith Jr.", "position": "WR",
            "origin": "Ohio State", "destination": "Texas", "transfer_date": "2024-01-05",
            "rating": 0.91, "stars": 4, "eligibility": "Junior",
        }
        b = {
            "season": 2024, "firstName": "Mike", "lastName": "Smith, Jr", "position": "wr",
            "origin": "Ohio-State", "destination": "Texas", "transferDate": "2024-01-05",
            "rating": 0.91, "stars": 4, "eligibility": "junior",
        }
        self.assertEqual(portal_entry_key(a), portal_entry_key(b))

    def test_portal_key_changes_for_distinct_destination(self):
        a = {"season": 2024, "first_name": "John", "last_name": "Doe", "destination": "Texas"}
        b = {"season": 2024, "first_name": "John", "last_name": "Doe", "destination": "USC"}
        self.assertNotEqual(portal_entry_key(a), portal_entry_key(b))


if __name__ == "__main__":
    unittest.main()
