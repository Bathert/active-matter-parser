"""Quickstart example for activematter-parser (Raw Parser & Raid Slicer)."""
import json
from pathlib import Path
from activematter_parser import (
    get_active_player_uid,
    get_player_profile,
    get_current_loadout,
    get_raids,
    slice_raids,
)


def main():
    print("=" * 60)
    print(" Active Matter Parser & Raid Slicer — Quickstart")
    print("=" * 60)

    # 1. Player Profile & Career
    uid = get_active_player_uid()
    profile = get_player_profile()
    print(f"\n[1] Operative Profile:")
    print(f"    UID:           {profile.get('uid') or uid or 'Not detected'}")
    print(f"    Operative:     {profile.get('operative_name', 'Unknown')}")
    print(f"    Total Raids:   {profile.get('total_raids', 0)} (Survived: {profile.get('survived_raids', 0)})")
    print(f"    Survival Rate: {profile.get('survival_rate_pct', 0.0)}%")

    # 2. Currently Equipped Gear
    loadout = get_current_loadout()
    if loadout:
        print(f"\n[2] Current Loadout:")
        print(f"    Preset:    {loadout.get('preset_name')}")
        print(f"    Suit:      {loadout.get('armor', {}).get('suit_name')}")
        print(f"    Helmet:    {loadout.get('helmet_name')}")
        print(f"    Weapons:   {len(loadout.get('weapons', []))}")
        for w in loadout.get("weapons", []):
            atts_str = ", ".join(a["name"] for a in w.get("attachments", []))
            print(f"      - {w['name']} [{atts_str}]")
        print(f"    Pouch Items: {len(loadout.get('pouch_items', []))}")

    # 3. Recent Raids in Schema 2.0
    raids = get_raids(limit=3)
    print(f"\n[3] Recent Raids ({len(raids)} in Schema 2.0):")
    for r in raids:
        outcome = r["outcome"]["status"]
        dur = r["outcome"]["play_time_formatted"]
        loc = r["location"]["full_name"]
        dmg = r["combat"]["damage_dealt"]
        kills = r["combat"]["kills_total"]
        print(f"    - [{outcome}] #{r['raid_id']} | {loc} ({dur}) | Dmg: {dmg} | Kills: {kills}")

    # 4. Slicing Raids into individual JSON 2.0 files
    temp_out = Path("./demo_sliced_raids")
    sliced_paths = slice_raids(output_dir=temp_out)
    print(f"\n[4] Sliced {len(sliced_paths)} raids into individual JSON 2.0 files in {temp_out.name}/")
    if sliced_paths:
        sample = json.loads(sliced_paths[0].read_text(encoding="utf-8"))
        print(f"    Sample: {sliced_paths[0].name} (Schema: {sample.get('schema_version')}, ID: {sample.get('raid_id')})")

    # Clean up demo folder
    for p in sliced_paths:
        p.unlink()
    if temp_out.exists():
        temp_out.rmdir()

    print("\nQuickstart finished successfully.")


if __name__ == "__main__":
    main()
