# Active Matter Parser & Raid Slicer (JSON 2.0)

<p align="center">
  <a href="README.md"><b>English</b></a> •
  <a href="README_RU.md"><b>Русский</b></a>
</p>

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![BattlEye Safe](https://img.shields.io/badge/BattlEye-100%25%20Safe%20(Passive)-brightgreen)](#-battleye-anti-cheat-safety)
[![Zero External Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-success)](#)

**activematter-parser** is a lightweight, pure Python parser and telemetry extraction tool for **Active Matter** (Dagor Engine / Gaijin Network). It parses local profile storage and slices match histories into individual, standardized JSON files following the **Schema 2.0** specification.

Zero third-party dependencies — built entirely on Python's standard library (no OpenCV, PyTorch, Pillow, or compiled C++ extensions required).

---

## 🛡️ BattlEye Anti-Cheat Safety

> **Account Safety Guarantee**:
> - **NO** process memory reading (`ReadProcessMemory`).
> - **NO** DLL injection, API hooks, or background threads attached to the game.
> - **NO** game client or executable modifications.
> - Strictly performs read-only file parsing of the local JSON cache that the official game client writes to disk:  
>   `%LOCALAPPDATA%\active_matter\downloads\online_storage\<UID>\active_matter\am-production\global.json`
> - 100% passive, safe, and transparent.

---

## ⚡ Features

1. **Player Profile & Career Statistics (`get_player_profile`)**:
   - Auto-detection of active user account UID and local storage paths.
   - Operative callsign, active gear preset, total raids, survival rate (%), and extracted match metrics.

2. **Equipped Loadout & Weapons (`get_current_loadout`)**:
   - Full armor suit breakdown (e.g. *Reaper Exosuit*) and equipped ballistic plates (`equipment_mod_*`).
   - Tactical helmets, backpacks, and secure pouches (*safepack*).
   - Primary and secondary weapons with all attached modifications (scopes, suppressors, lasers, stocks, pistol grips, magazines).
   - Pouch contents with live round counts and artifact charges.

3. **Raid Slicer into Standalone JSON Files (`slice_raids`)**:
   - Slices monolithic `battleResults` arrays from `global.json` into separate `raid_<id>.json` files.
   - Enriches each raid with **JSON Schema 2.0** metadata, location tags, combat breakdowns, and GPS tracks.

4. **Combat Analytics & GPS Telemetry**:
   - **Multi-kill detection** (chained frag streaks within a 15-second floating window).
   - Accurate damage split: **PvP** (real player operatives) vs **PvE** (anomalous creatures/creepers).
   - Per-second 3D movement coordinates (`track_points`) with combat event markers (kills, wounds, medkits used, containers looted).
   - Strict separation of **Found in Raid (FIR)** loot from player gear brought into the raid.

---

## 📋 JSON Schema 2.0 Specification

Each sliced match is saved as an independent, fully-typed JSON document:

```json
{
  "schema_version": "2.0",
  "raid_id": "7397945507",
  "session_id": "2466891402207512785",
  "game_version": "8",
  "timestamp": 1792996215,
  "date_time_iso": "2026-10-26T06:30:15Z",
  "date_time_local": "2026-10-26 09:30:15",
  "location": {
    "code": "raid+dalniy_factory+hive",
    "region": "Дальний остров",
    "sublocation": "Завод",
    "mode": "Улей",
    "full_name": "Завод (Дальний остров) [Улей]"
  },
  "outcome": {
    "survived": false,
    "status": "KIA",
    "play_time_seconds": 445,
    "play_time_formatted": "07:25"
  },
  "player": {
    "uid": "100294812",
    "operative_name": "Ghost",
    "suit": "sm_reaper_item",
    "suit_name": "Тяжелый экзокостюм «Жнец»"
  },
  "combat": {
    "damage_dealt": 281,
    "damage_received": 843,
    "pvp_damage": 0,
    "pve_damage": 281,
    "kills_total": 3,
    "pvp_kills": 0,
    "pve_kills": 3,
    "kills": [
      {
        "victim_name": "Аномалия",
        "victim_type": "monster_changed",
        "is_pvp": false,
        "weapon": "Оружие",
        "distance_m": 0.0,
        "timestamp_sec": 426.91,
        "damaged_parts": {}
      }
    ],
    "multi_kills": 1,
    "longest_kill_m": 0.0,
    "death": {
      "killer_name": "Неизвестный противник",
      "killer_type": "monster_hound",
      "is_pvp": false,
      "murder_weapon": "Огнестрельное оружие",
      "death_cause": "снаряд",
      "kill_distance_m": 0.0,
      "timestamp_sec": 444.82
    }
  },
  "activity": {
    "containers_looted": 3,
    "bodies_looted": 1,
    "medicine_used": 2,
    "player_fights": 0,
    "portals_used": 0
  },
  "loot": {
    "found_in_raid_count": 5,
    "found_in_raid_units": 18,
    "found_in_raid": [
      {
        "template": "active_matter_item",
        "name": "Активная материя",
        "category": "Останки и артефакты аномалий",
        "count": 10,
        "is_corrupted": false
      }
    ],
    "brought_in_gear": []
  },
  "telemetry": {
    "path_length_m": 948.3,
    "points_count": 48,
    "track_points": [
      {
        "x": 262.8,
        "y": 58.6,
        "z": -727.4,
        "timestamp": 0.0,
        "event": "respawned"
      }
    ]
  }
}
```

---

## 📖 In-Game Data Dictionary (Dagor Engine / Gaijin)

For developers inspecting raw game storage files or building custom dashboards, here is the field mapping between raw `global.json` keys and Schema 2.0:

| Raw Game Key (`global.json`) | Type | In-Game Meaning | Schema 2.0 Field |
| :--- | :--- | :--- | :--- |
| **`battleStat.isSuccessRaid`** | `int` | `1` = Extraction (Survived), `0` = KIA / MIA | `outcome.survived` (`bool`), `outcome.status` (`EXTRACTED`/`KIA`) |
| **`battleAreaInfo.raidName`** | `str` | Location code: `raid+<sector>+<mode>` (e.g. `raid+dalniy_factory+hive`) | `location.region`, `location.sublocation`, `location.mode` |
| **`debriefingStatsV2.playTime`** | `int` | Match survival time in seconds | `outcome.play_time_seconds`, `play_time_formatted` (`MM:SS`) |
| **`debriefingStatsV2.playerPathLen`**| `float` | Distance walked/run across terrain in meters | `telemetry.path_length_m` |
| **`debriefingStatsV2.dealtDamage`** | `int` | Total damage inflicted (PvP + PvE) | `combat.damage_dealt`, attributed to `pvp_damage` & `pve_damage` |
| **`debriefingStatsV2.receivedDamage`**| `int` | Total damage sustained before death/extraction | `combat.damage_received` |
| **`debriefingStatsV2.medicineUsed`** | `int` | Medical items used (medkits, bandages, injectors) | `activity.medicine_used` |
| **`debriefingStatsV2.lootedCommonContainers`** | `int` | Common loot crates and lockers opened | `activity.common_containers` |
| **`debriefingStatsV2.lootedSecretContainers`** | `int` | Hidden anomaly caches looted | `activity.secret_containers` |
| **`debriefingStatsV2.lootedBodies`** | `int` | Corpses searched (operatives or monsters) | `activity.bodies_looted` |
| **`trackPoints[].eventType`** | `str` | Event tag: `positionPoint`, `kill`, `died`, `metPlayerBattle`, `transPortalFrom/To` | `telemetry.track_points[].event`, `combat.kills`, `combat.death` |
| **`trackPoints[].victimType`** | `str` | **`militant` = Human Player Operative (PvP)**, `monster_*` = Anomaly Creatures (PvE) | `combat.kills[].is_pvp` (`true`/`false`), `combat.pvp_kills` |
| **`trackPoints[].damagedParts`** | `dict` | Exact limb damage breakdown (`head`, `body`, `left_hand`, `right_hand`, `left_leg`, `right_leg`) | `combat.kills[].damaged_parts` |
| **`loadout[].isFoundInRaid`** | `bool` | **Found-in-Raid (FIR) Flag**: `True` = looted in this match. `False` = starting gear brought from stash | Segregates into `loot.found_in_raid` and `loot.brought_in_gear` |
| **`loadout[].isCorrupted`** | `bool` | Active matter anomaly corruption flag | `loot.found_in_raid[].is_corrupted` |
| **`player_presets`** | `dict` | Active loadout: weapons with attachments, suits (`chronogene_primary_1`), pouch (`inventories.pouch`) | Parsed via `get_current_loadout()` |

---

## 🚀 Installation

```bash
git clone https://github.com/Bathert/active-matter-parser.git
cd active-matter-parser
pip install -e .
```

---

## 💻 CLI Usage

Once installed, the `activematter-parser` command is available system-wide:

### 1. Slice raids into individual JSON 2.0 files
```bash
# Slices all raids from local game storage into ./raids_v2
activematter-parser slice

# Specify custom destination directory
activematter-parser slice --output-dir ./my_raids

# Slice a specific downloaded global.json file
activematter-parser slice --input path/to/global.json --output-dir ./my_raids

# Slice a single raid by ID
activematter-parser slice --raid-id 7397945507
```

### 2. View player profile & career stats
```bash
activematter-parser profile
```

### 3. Inspect currently equipped loadout and pouch
```bash
activematter-parser loadout
```

### 4. View recent raids summary
```bash
activematter-parser raids --limit 10
```

---

## 🐍 Python Library API

```python
from activematter_parser import (
    load_global_content,
    get_player_profile,
    get_current_loadout,
    get_raids,
    slice_raids,
)

# 1. Player profile & career overview
profile = get_player_profile()
print(f"Operative: {profile['operative_name']} | Survival Rate: {profile['survival_rate_pct']}%")

# 2. Currently equipped gear
loadout = get_current_loadout()
print(f"Suit: {loadout['armor']['suit_name']}")
for w in loadout['weapons']:
    print(f"Weapon: {w['name']} (Attachments: {len(w['attachments'])})")

# 3. Retrieve recent raids in Schema 2.0 format
raids = get_raids(limit=5)
for r in raids:
    status = "EXTRACTED" if r["outcome"]["survived"] else "KIA"
    print(f"[{status}] {r['location']['full_name']} | Kills: {r['combat']['kills_total']}")

# 4. Slice all raids to individual JSON 2.0 files
saved_paths = slice_raids(output_dir="./sliced_raids")
print(f"Successfully sliced {len(saved_paths)} match files.")
```

---

## 📂 Repository Structure

```text
active-matter-parser/
├── activematter_parser/
│   ├── __init__.py      # Public API exports
│   ├── parser.py        # Local storage discovery, profile & loadout parser
│   ├── slicer.py        # Raid slicer into standalone JSON 2.0 files
│   ├── schema_v2.py     # Schema 2.0 normalization & field transformers
│   └── cli.py           # Command-line interface (slice, profile, loadout, raids)
├── examples/
│   └── quickstart.py    # Quickstart example script
├── tests/
│   ├── test_parser.py   # Unit tests for profile and loadout parsing
│   └── test_slicer.py   # Unit tests for raid slicing and Schema 2.0 validation
├── pyproject.toml       # PEP 517/518 build metadata
├── setup.py             # pip backward-compatibility
├── .gitignore           # Git ignore rules (caches, temp raid dumps)
├── LICENSE              # MIT License
├── README.md            # English documentation
├── README_RU.md         # Russian documentation
└── FOR_AI.md            # Project architecture brief for AI assistants
```

---

## 🧪 Running Unit Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

```text
Ran 20 tests in 0.022s

OK
```

---

## 📤 Publishing to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Active Matter Parser & Raid Slicer (JSON 2.0)"
git branch -M main
git remote add origin https://github.com/<your-username>/active-matter-parser.git
git push -u origin main
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.  
Active Matter is a trademark of Gaijin Network Ltd. This project is an independent community tool and is not affiliated with Gaijin Network Ltd.
