"""Unit tests for activematter_parser.parser module."""
import unittest
from unittest.mock import patch
from activematter_parser.parser import (
    load_global_content,
    get_player_profile,
    get_current_loadout,
    get_raids,
    prettify_item_name,
    categorize_template,
    format_epoch_dt,
    resolve_effective_uid,
    safe_int,
    safe_float,
)


class TestParser(unittest.TestCase):

    def test_item_prettify_and_categorization(self):
        self.assertEqual(prettify_item_name("active_matter_item"), "Активная материя")
        self.assertEqual(prettify_item_name("m4a1_gun"), "Штурмовая винтовка M4A1")
        self.assertEqual(prettify_item_name("sm_reaper_item"), "Тяжелый экзокостюм «Жнец»")

        self.assertEqual(categorize_template("m4a1_gun"), "Оружие и модификации")
        self.assertEqual(categorize_template("box_9mm_magazine"), "Боеприпасы и магазины")
        self.assertEqual(categorize_template("item_healkit"), "Медицина и стимуляторы")
        self.assertEqual(categorize_template("active_matter_item"), "Останки и артефакты аномалий")

    def test_format_epoch(self):
        from datetime import datetime
        ts = 1760004000
        formatted = format_epoch_dt(ts)
        self.assertTrue(len(formatted) >= 10)
        expected_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        self.assertTrue(formatted.startswith(expected_date))

    def test_synthetic_profile_and_loadout_parsing(self):
        synthetic_content = {
            "player_presets": {
                "playerPreset_lastUsed": {
                    "presetName": "Тестовый штурмовик",
                    "helmet": {"itemTemplate": "helmet_pasgt_tactical"},
                    "backpack": {"itemTemplate": "small_backpack"},
                    "safepack": {"itemTemplate": "small_safepack"},
                    "weapons": [
                        {
                            "itemTemplate": "m4a1_gun",
                            "attachments": {
                                "scope": {"itemTemplate": "scope_sig_tango_6"}
                            }
                        }
                    ],
                    "inventories": {
                        "pouch": {
                            "capacity": 4,
                            "items": [
                                {"itemTemplate": "box_9mm_magazine", "count": 2, "ammoCount": 60}
                            ]
                        }
                    }
                }
            },
            "battleResults": [
                {
                    "id": "raid-test-1",
                    "dateTime": 1760004000,
                    "battleStat": {"isSuccessRaid": 1},
                    "battleAreaInfo": {"raidName": "raid+dalniy_factory+ordinary"},
                    "debriefingStatsV2": {"playTime": 300, "dealtDamage": 450, "playerPathLen": 1200},
                    "loadout": [{"templateName": "active_matter_item", "count": 50, "isFoundInRaid": True}]
                }
            ]
        }

        with patch("activematter_parser.parser.load_global_content", return_value=synthetic_content):
            loadout = get_current_loadout()
            self.assertEqual(loadout["preset_name"], "Тестовый штурмовик")
            self.assertEqual(loadout["helmet_name"], "Тактический шлем PASGT")
            self.assertEqual(len(loadout["weapons"]), 1)
            self.assertEqual(loadout["weapons"][0]["name"], "Штурмовая винтовка M4A1")
            self.assertEqual(len(loadout["pouch_items"]), 1)

            profile = get_player_profile()
            self.assertEqual(profile["total_raids"], 1)
            self.assertEqual(profile["survived_raids"], 1)
            self.assertEqual(profile["survival_rate_pct"], 100.0)

            raids = get_raids()
            self.assertEqual(len(raids), 1)
            self.assertEqual(raids[0]["raid_id"], "raid-test-1")
            self.assertTrue(raids[0]["outcome"]["survived"])
            self.assertEqual(raids[0]["outcome"]["status"], "EXTRACTED")
            self.assertEqual(raids[0]["outcome"]["play_time_formatted"], "05:00")
            self.assertEqual(len(raids[0]["loot"]["found_in_raid"]), 1)
            self.assertEqual(raids[0]["loot"]["found_in_raid"][0]["count"], 50)

    def test_find_global_json_directory_resolution(self):
        import tempfile
        from pathlib import Path
        from activematter_parser.parser import find_global_json

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "online_storage"
            user_dir = root / "998877" / "active_matter" / "am-production"
            user_dir.mkdir(parents=True)
            target_json = user_dir / "global.json"
            target_json.write_text('{"content": {}}', encoding="utf-8")

            # 1. Resolving from user directory directly
            self.assertEqual(find_global_json(user_dir), target_json)

            # 2. Resolving from root folder with lastUid
            last_dir = root / "last"
            last_dir.mkdir()
            (last_dir / "lastUid").write_text("998877", encoding="utf-8")
            self.assertEqual(find_global_json(root), target_json)

    def test_ammo_zero_and_charges_zero_not_falsy(self):
        synthetic = {
            "player_presets": {
                "playerPreset_lastUsed": {
                    "presetName": "Пустой магазин",
                    "weapons": [
                        {
                            "itemTemplate": "m4a1_gun",
                            "ammoCount": 0,
                            "charges": 0,
                        }
                    ],
                    "inventories": {
                        "pouch": {
                            "capacity": 2,
                            "items": [
                                {"itemTemplate": "box_9mm_magazine", "count": 1, "ammoCount": 0, "charges": 0}
                            ]
                        }
                    }
                }
            }
        }
        loadout = get_current_loadout(synthetic)
        self.assertEqual(loadout["weapons"][0]["ammo_count"], 0)
        self.assertEqual(loadout["weapons"][0]["charges"], 0)
        self.assertEqual(loadout["pouch_items"][0]["ammo_count"], 0)
        self.assertEqual(loadout["pouch_items"][0]["charges"], 0)

    def test_item_categories_healkit_magazine_priority(self):
        # Compound names containing both 'healkit' and 'magazine' must be Medicine, not Ammo
        self.assertEqual(categorize_template("loot_item_healkit_magazine_small"), "Медицина и стимуляторы")
        self.assertEqual(categorize_template("tactical_healkit_pack"), "Медицина и стимуляторы")
        self.assertEqual(categorize_template("ak74_magazine_30"), "Боеприпасы и магазины")

    def test_pre_unwrapped_global_json(self):
        # When global.json has no outer 'content' key
        raw_unwrapped = {
            "battleResults": [
                {
                    "id": "unwrapped-raid-1",
                    "dateTime": 1760004000,
                    "battleStat": {"isSuccessRaid": 1},
                    "battleAreaInfo": {"raidName": "raid+dalniy_factory+ordinary"},
                    "debriefingStatsV2": {"playTime": 150, "dealtDamage": 200},
                    "loadout": []
                }
            ]
        }
        res = load_global_content(raw_unwrapped)
        self.assertIn("battleResults", res)
        raids = get_raids(raw_unwrapped)
        self.assertEqual(len(raids), 1)
        self.assertEqual(raids[0]["raid_id"], "unwrapped-raid-1")

    def test_safe_int_safe_float_robustness(self):
        self.assertEqual(safe_int("330.5"), 330)
        self.assertEqual(safe_int("not_a_number", default=42), 42)
        self.assertEqual(safe_int(None, default=0), 0)

        self.assertEqual(safe_float("1420.5"), 1420.5)
        self.assertEqual(safe_float("NaN", default=0.0), 0.0)
        self.assertEqual(safe_float("Infinity", default=0.0), 0.0)
        self.assertEqual(safe_float("-inf", default=0.0), 0.0)
        self.assertEqual(safe_float(None, default=0.0), 0.0)

    def test_team_info_squadmate_resolution(self):
        synthetic = {
            "battleResults": [
                {
                    "id": "team-test-1",
                    "dateTime": 1760004000,
                    "teamInfo": [
                        {"userId": "100001", "name": "Squadmate_Bob", "suitTemplate": "light_suit"},
                        {"userId": "100002", "name": "My_True_Hero", "suitTemplate": "sm_reaper_item", "isLocal": True},
                    ],
                    "debriefingStatsV2": {"playTime": 200, "dealtDamage": 100},
                }
            ]
        }
        # Operative matching isLocal/effective UID
        profile = get_player_profile(synthetic)
        self.assertEqual(profile["operative_name"], "My_True_Hero")
        self.assertEqual(profile["current_suit"], "Тяжелый экзокостюм «Жнец»")

    def test_resolve_effective_uid(self):
        # 1. From path containing UID directory
        p = "/path/to/online_storage/240872112/active_matter/am-production/global.json"
        self.assertEqual(resolve_effective_uid(p), "240872112")

        # 2. From teamInfo in dict
        data = {
            "battleResults": [
                {"teamInfo": [{"userId": "987654321", "name": "Ghost"}]}
            ]
        }
        self.assertEqual(resolve_effective_uid(data), "987654321")

        # 3. Path with 4-digit backup year folder (e.g. 2026) must NOT be mistaken for player UID
        year_path = "C:/Backups/2026/custom_folder/global.json"
        self.assertEqual(resolve_effective_uid(year_path, content=data), "987654321")

    def test_corrupted_json_sys_stderr(self):
        import io
        import sys
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as tf:
            tf.write("{ this is invalid json syntax !!!")
            tf_path = Path(tf.name)

        try:
            stderr_capture = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = stderr_capture
            try:
                res = load_global_content(tf_path)
            finally:
                sys.stderr = old_stderr

            self.assertEqual(res, {})
            self.assertIn("[activematter-parser WARNING] Failed to read/parse", stderr_capture.getvalue())
        finally:
            if tf_path.exists():
                tf_path.unlink()


if __name__ == "__main__":
    unittest.main()
