"""Unit tests for activematter_parser.slicer module (JSON Schema 2.0)."""
import unittest
import tempfile
import json
from pathlib import Path
from activematter_parser.slicer import slice_raids, slice_single_raid_by_id, sanitize_filename
from activematter_parser.schema_v2 import transform_to_schema_v2


class TestSlicer(unittest.TestCase):

    def setUp(self):
        self.mock_raid = {
            "id": "7395399309",
            "sessionId": "sess-alpha-99",
            "version": "0.1.2",
            "dateTime": 1760004000,
            "battleStat": {"isSuccessRaid": 1},
            "battleAreaInfo": {"raidName": "raid+dalniy_factory+ordinary"},
            "teamInfo": [{"name": "Ghost", "suitTemplate": "sm_reaper_item"}],
            "debriefingStatsV2": {
                "playTime": 330,
                "dealtDamage": 520,
                "receivedDamage": 85,
                "playerPathLen": 1420.5,
                "medicineUsed": 2,
                "lootedCommonContainers": 4,
                "lootedSecretContainers": 1,
                "lootedBodies": 2,
            },
            "loadout": [
                {"templateName": "active_matter_item", "count": 25, "isFoundInRaid": True},
                {"templateName": "m4a1_gun", "count": 1, "isFoundInRaid": False},
            ],
            "trackPoints": [
                {
                    "eventType": "positionPoint",
                    "position": {"x": 10.0, "y": 20.0, "z": 30.0},
                    "timestamp": 5.0,
                },
                {
                    "eventType": "kill",
                    "victimType": "militant",
                    "name": "Enemy_Sniper",
                    "weaponName": "items/sv98_gun",
                    "killDistance": 125.4,
                    "damagedParts": {"head": 150.0},
                    "timestamp": 45.0,
                    "position": {"x": 50.0, "y": 25.0, "z": 80.0},
                },
                {
                    "eventType": "kill",
                    "victimType": "militant",
                    "name": "Enemy_Rusher",
                    "weaponName": "items/m4a1_gun",
                    "killDistance": 15.2,
                    "damagedParts": {"body": 140.0, "head": 80.0},
                    "timestamp": 52.0,  # 7 seconds later -> multi-kill!
                    "position": {"x": 55.0, "y": 25.0, "z": 85.0},
                },
            ],
        }

    def test_schema_v2_transformation(self):
        v2 = transform_to_schema_v2(self.mock_raid, player_uid="12345")
        self.assertEqual(v2["schema_version"], "2.0")
        self.assertEqual(v2["raid_id"], "7395399309")
        self.assertEqual(v2["session_id"], "sess-alpha-99")
        self.assertEqual(v2["outcome"]["status"], "EXTRACTED")
        self.assertTrue(v2["outcome"]["survived"])
        self.assertEqual(v2["outcome"]["play_time_formatted"], "05:30")

        # Combat & Multi-kill check
        combat = v2["combat"]
        self.assertEqual(combat["kills_total"], 2)
        self.assertEqual(combat["pvp_kills"], 2)
        self.assertEqual(combat["multi_kills"], 1)  # chained within 15s!
        self.assertEqual(combat["longest_kill_m"], 125.4)
        self.assertGreaterEqual(combat["pvp_damage"], 370)

        # Loot check
        loot = v2["loot"]
        self.assertEqual(loot["found_in_raid_count"], 1)
        self.assertEqual(loot["found_in_raid_units"], 25)
        self.assertEqual(len(loot["brought_in_gear"]), 1)

        # Telemetry check
        self.assertEqual(v2["telemetry"]["points_count"], 3)
        self.assertEqual(v2["telemetry"]["path_length_m"], 1420.5)

    def test_slice_raids_to_disk(self):
        synthetic_global = {
            "content": {
                "battleResults": [
                    self.mock_raid,
                    {
                        "id": "7395399310",
                        "dateTime": 1760005000,
                        "battleStat": {"isSuccessRaid": 0},
                        "battleAreaInfo": {"raidName": "raid+africa_airport+ordinary"},
                        "debriefingStatsV2": {"playTime": 120, "dealtDamage": 0, "receivedDamage": 150},
                        "trackPoints": [],
                        "loadout": [],
                    }
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "sliced_raids"
            files = slice_raids(source=synthetic_global, output_dir=out_dir)

            self.assertEqual(len(files), 2)
            file1 = out_dir / "raid_7395399309.json"
            file2 = out_dir / "raid_7395399310.json"
            self.assertTrue(file1.exists())
            self.assertTrue(file2.exists())

            # Read back and verify valid JSON Schema 2.0
            data1 = json.loads(file1.read_text(encoding="utf-8"))
            self.assertEqual(data1["schema_version"], "2.0")
            self.assertEqual(data1["raid_id"], "7395399309")
            self.assertEqual(data1["location"]["sublocation"], "Завод")
            self.assertEqual(data1["location"]["region"], "Дальний остров")

            data2 = json.loads(file2.read_text(encoding="utf-8"))
            self.assertEqual(data2["outcome"]["status"], "KIA")
            self.assertFalse(data2["outcome"]["survived"])
            self.assertEqual(data2["location"]["region"], "Африка")

    def test_slice_single_raid_by_id(self):
        synthetic_global = {"content": {"battleResults": [self.mock_raid]}}

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "single_test"
            res = slice_single_raid_by_id("7395399309", source=synthetic_global, output_dir=out_dir)
            self.assertIsNotNone(res)
            self.assertTrue(res.exists())

            # Searching for non-existent raid
            res_none = slice_single_raid_by_id("999999999", source=synthetic_global, output_dir=out_dir)
            self.assertIsNone(res_none)

    def test_edge_cases_and_missing_fields(self):
        # Empty raid dict
        v2_empty = transform_to_schema_v2({})
        self.assertEqual(v2_empty["schema_version"], "2.0")
        self.assertEqual(v2_empty["raid_id"], "")
        self.assertEqual(v2_empty["outcome"]["status"], "KIA")
        self.assertFalse(v2_empty["outcome"]["survived"])
        self.assertEqual(v2_empty["combat"]["kills_total"], 0)

        # Include raw flag
        v2_with_raw = transform_to_schema_v2({"id": "raw-123"}, include_raw=True)
        self.assertIn("raw_game_data", v2_with_raw)
        self.assertEqual(v2_with_raw["raw_game_data"]["id"], "raw-123")

    def test_sublocation_matching_precedence(self):
        from activematter_parser.schema_v2 import parse_location_info
        # factory_mir must match 'Завод МИР', not 'Завод'
        loc = parse_location_info("raid+nexus_factory_mir+ordinary")
        self.assertEqual(loc["sublocation"], "Завод МИР")

        # ore_quarry must match 'Карьер руды', not 'Карьер'
        loc_quarry = parse_location_info("raid+dalniy_ore_quarry+ordinary")
        self.assertEqual(loc_quarry["sublocation"], "Карьер руды")

    def test_portal_usage_counting(self):
        raid_with_portals = {
            "id": "portal-test",
            "trackPoints": [
                {"eventType": "transPortalFrom", "timestamp": 10.0},
                {"eventType": "transPortalTo", "timestamp": 12.0},
                {"eventType": "transPortalFrom", "timestamp": 30.0},
                {"eventType": "transPortalTo", "timestamp": 32.0},
            ]
        }
        v2 = transform_to_schema_v2(raid_with_portals)
        # Two complete portal traversals should equal 2 uses, not 4
        self.assertEqual(v2["activity"]["portals_used"], 2)

    def test_sanitize_filename_traversal(self):
        # Path traversal characters and Windows forbidden characters
        self.assertEqual(sanitize_filename("../../etc/passwd"), "etc_passwd")
        self.assertEqual(sanitize_filename("raid:123*?<>|45"), "raid_123_____45")
        self.assertEqual(sanitize_filename("..."), "unknown_raid")
        self.assertEqual(sanitize_filename("raid-normal_01"), "raid-normal_01")

        # Verify safe slicing with path traversal raid ID
        synthetic_global = {
            "content": {
                "battleResults": [
                    {"id": "../../bad_dir/raid:test"}
                ]
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "safe_slice"
            files = slice_raids(source=synthetic_global, output_dir=out_dir)
            self.assertEqual(len(files), 1)
            # The saved file must reside inside out_dir, not outside
            self.assertTrue(files[0].parent.samefile(out_dir))
            self.assertEqual(files[0].name, "raid_bad_dir_raid_test.json")

    def test_out_of_order_track_points_multi_kill(self):
        # Out-of-order timestamps:
        # kill 1 at 10.0
        # kill 2 at 50.0
        # kill 3 at 45.0 (out of order, was 5s before kill 2)
        # kill 4 at 52.0 (2s after kill 2)
        raid_out_of_order = {
            "id": "ooo-kill-test",
            "trackPoints": [
                {"eventType": "kill", "victimType": "militant", "timestamp": 10.0},
                {"eventType": "kill", "victimType": "militant", "timestamp": 50.0},
                {"eventType": "kill", "victimType": "militant", "timestamp": 45.0},
                {"eventType": "kill", "victimType": "militant", "timestamp": 52.0},
            ]
        }
        v2 = transform_to_schema_v2(raid_out_of_order)
        # Chronological order of kills is: 10.0, 45.0 (delta 35), 50.0 (delta 5 -> multi-kill 1), 52.0 (delta 2 -> multi-kill 2)
        # If un-sorted: 10.0 -> 50.0 (delta 40) -> 45.0 (delta -5! If bug present, -5 <= 15 triggers false multi-kill!) -> 52.0 (delta 7)
        # With timestamp sorting and 0.0 <= delta <= 15.0:
        # 10.0 -> 45.0: no
        # 45.0 -> 50.0: yes (5.0s <= 15.0s)
        # 50.0 -> 52.0: yes (2.0s <= 15.0s)
        self.assertEqual(v2["combat"]["kills_total"], 4)
        self.assertEqual(v2["combat"]["multi_kills"], 2)

    def test_schema_v2_zero_ammo_and_charges(self):
        raid_zero = {
            "id": "zero-ammo-test",
            "loadout": [
                {"templateName": "box_9mm_magazine", "count": 1, "ammoCount": 0, "charges": 0, "isFoundInRaid": True}
            ]
        }
        v2 = transform_to_schema_v2(raid_zero)
        item = v2["loot"]["found_in_raid"][0]
        self.assertEqual(item["ammo_count"], 0)
        self.assertEqual(item["charges"], 0)


if __name__ == "__main__":
    unittest.main()
