# 🤖 Project Context & Developer Brief for AI Assistants

> **Note for AI (ChatGPT, Claude, Gemini, etc.)**:  
> Read this file first. It summarizes the entire architecture, purpose, constraints, and data model of the `activematter-parser` codebase.

---

## 🎯 1. Project Goal & Purpose

`activematter-parser` is an independent, zero-dependency, pure Python 3.9+ library and CLI utility for the tactical extraction shooter game **Active Matter** (developed by Gaijin Network on Dagor Engine).

Its primary responsibilities:
1. **Passive Local Storage Parsing**: Auto-detects and parses the player's local `%LOCALAPPDATA%` game storage (`global.json`).
2. **Profile & Loadout Extraction**: Extracts operative callsign, UID, career stats, and full equipped loadout (armor suits, plates, weapons with attachments, and pouch items).
3. **Raid Slicer (JSON Schema 2.0)**: Slices the monolithic `battleResults` match history array into individual, standardized, self-contained `raid_<id>.json` files formatted according to **JSON Schema 2.0**.
4. **Combat & Telemetry Normalization**:
   - Multi-kill detection (chained frags within a 15-second floating window).
   - Strict PvP (human players) vs PvE (monsters/creepers) damage & kill attribution.
   - 3D GPS movement tracks (`track_points`) with combat event markers.
   - Segregation of Found in Raid (FIR) loot from starting stash gear.

---

## 🛡️ 2. Non-Negotiable Architectural Constraints

When modifying, extending, or building upon this codebase, maintain the following rules:

1. **BattlEye Anti-Cheat Safety**:
   - 100% passive, read-only file reading on disk.
   - **NO** memory reading (`ReadProcessMemory`), **NO** DLL injection, **NO** API hooks, **NO** active process interaction.
2. **Zero External Runtime Dependencies**:
   - The package runs strictly on Python standard library modules (`json`, `pathlib`, `os`, `sys`, `datetime`, `argparse`, `typing`).
   - Do **NOT** add heavy dependencies like OpenCV, Pillow, PyTorch, or Pandas to the core package.
3. **Python Compatibility**:
   - Supports Python 3.9 through 3.14+ across Windows and OS-independent environments (e.g. for parsing uploaded files on Linux servers).

---

## 📂 3. Repository Architecture

```text
active-matter-parser/
├── activematter_parser/
│   ├── __init__.py      # Clean public API exports
│   ├── parser.py        # Storage path discovery, profile & loadout parser
│   ├── slicer.py        # Logic to slice battleResults into individual raid_<id>.json files
│   ├── schema_v2.py     # Canonical JSON Schema 2.0 definition, field transformers & Russian localization
│   └── cli.py           # CLI entry points: slice, profile, loadout, raids
├── examples/
│   └── quickstart.py    # 5-second end-to-end runnable demo
├── tests/
│   ├── test_parser.py   # Unit tests for profile, loadout, and item categorization
│   └── test_slicer.py   # Unit tests for JSON 2.0 schema, slicing, and multi-kill detection
├── pyproject.toml       # Modern PEP 517/518 build metadata
├── setup.py             # pip backward-compatibility
├── .gitignore           # Ignores __pycache__, temp raid dumps, and venvs
├── LICENSE              # MIT License
├── README.md            # English documentation
├── README_RU.md         # Russian documentation
└── FOR_AI.md            # This brief for AI assistants
```

---

## 📋 4. Dagor Engine / Gaijin Data Model Reference

The game saves account state to:
`%LOCALAPPDATA%\active_matter\downloads\online_storage\<UID>\active_matter\am-production\global.json`

Key internal structures:
- **`battleStat.isSuccessRaid`**: `1` = Extracted (survived), `0` = KIA / MIA.
- **`battleAreaInfo.raidName`**: Location code formatted as `raid+<sector>+<mode>` (e.g. `raid+dalniy_factory+hive`, `raid+africa_airport+ordinary`).
- **`debriefingStatsV2`**: Server-verified match statistics:
  - `playTime`: match duration in seconds.
  - `playerPathLen`: distance traveled in meters.
  - `dealtDamage`: total damage dealt (PvP + PvE).
  - `receivedDamage`: total damage taken.
  - `medicineUsed`: count of medkits, bandages, injectors used.
  - `lootedCommonContainers`, `lootedSecretContainers`, `lootedBodies`.
- **`trackPoints`**: Chronological array of telemetry events:
  - `position`: `{x, y, z}` in engine world coordinates.
  - `timestamp`: seconds since player spawn.
  - `eventType`:
    - `"positionPoint"`: routine trajectory point.
    - `"kill"`: player eliminated an entity. If `victimType == "militant"` -> PvP (real player). Else -> PvE creature. Contains `damagedParts` (`head`, `body`, limbs).
    - `"died"`: player death event (`offenderType`, `murderWeaponName`, `deathCause`, `killDistance`).
    - `"metPlayerBattle"`: confrontation engagement with an enemy player.
    - `"transPortalFrom"` / `"transPortalTo"`: quantum anomaly portal traversal.
- **`loadout`**: Array of items in player inventory at match conclusion:
  - `isFoundInRaid`: `True` = looted in this match (FIR status). `False` = starting equipment brought from stash.
  - `isCorrupted`: quantum active matter anomaly radiation status.
  - `ammoCount`: current ammunition loaded into magazine/box.
- **`player_presets.playerPreset_lastUsed`**: Equipped stash loadout:
  - `weapons`: array of weapons with `attachments` slots (`scope`, `muzzle`, `magazine`, `stock`, `pistolgrip`).
  - `chronogene_primary_1`: equipped armor suit with `equipment_mod_*` ballistic plates.
  - `inventories.pouch`: secure pouch contents (saved on death).

---

## 🧪 5. Testing & Verification

Run the full unit test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
*All tests must pass (`Ran 20 tests ... OK`).*

Run the CLI:
```bash
activematter-parser slice --output-dir ./my_raids
activematter-parser profile
activematter-parser loadout
activematter-parser raids --limit 5
```
