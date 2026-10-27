"""Active Matter Parser & Raid Slicer CLI."""
import sys
import argparse
import json
from pathlib import Path

# Windows console UTF-8 safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .parser import (
    find_global_json,
    get_active_player_uid,
    get_player_profile,
    get_current_loadout,
    get_raids,
)
from .slicer import slice_raids, slice_single_raid_by_id


def main():
    parser = argparse.ArgumentParser(
        prog="activematter-parser",
        description="Active Matter Data Parser & Raid Slicer (JSON Schema 2.0)"
    )
    parser.add_argument("--input", "-i", type=str, default=None, help="Custom path to global.json or storage directory")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: slice
    slice_p = subparsers.add_parser("slice", aliases=["split", "dump"], help="Slice raids into individual JSON 2.0 files")
    slice_p.add_argument("--output-dir", "-o", type=str, default="./raids_v2", help="Target output directory (default: ./raids_v2)")
    slice_p.add_argument("--raid-id", type=str, default=None, help="Slice only a specific raid by ID")
    slice_p.add_argument("--raw", action="store_true", help="Include original raw game payload inside 'raw_game_data'")

    # Command: profile
    subparsers.add_parser("profile", help="Show operative profile, UID, and survival stats")

    # Command: loadout
    subparsers.add_parser("loadout", help="Show currently equipped loadout, weapons, armor, and pouch items")

    # Command: raids
    raids_p = subparsers.add_parser("raids", help="List recent raids summary")
    raids_p.add_argument("--limit", type=int, default=10, help="Number of raids to show (default: 10)")

    args = parser.parse_args()

    source = args.input

    if args.command in ("slice", "split", "dump"):
        out_dir = Path(args.output_dir)
        print(f"[*] Target directory: {out_dir.resolve()}")
        json_file = find_global_json(source)
        print(f"[*] Reading source:   {json_file or 'Auto-detecting from local storage'}")

        if args.raid_id:
            res = slice_single_raid_by_id(args.raid_id, source=source, output_dir=out_dir, include_raw=args.raw)
            if res:
                print(f"[+] Successfully sliced raid #{args.raid_id} -> {res.name}")
            else:
                print(f"[-] Raid #{args.raid_id} not found.")
        else:
            files = slice_raids(source=source, output_dir=out_dir, include_raw=args.raw)
            if not files:
                print("[-] No raids found in source.")
            else:
                print(f"[+] Successfully sliced {len(files)} raids into JSON Schema 2.0 files:")
                for f in files[:5]:
                    print(f"    • {f.name}")
                if len(files) > 5:
                    print(f"    ... and {len(files) - 5} more files in {out_dir.name}/")

    elif args.command == "profile":
        json_file = find_global_json(source)
        prof = get_player_profile(source)
        print("=== Active Matter Player Profile ===")
        print(f"Source:        {json_file or 'Not found'}")
        print(f"UID:           {prof.get('uid', 'Unknown')}")
        print(f"Operative:     {prof.get('operative_name', 'Unknown')}")
        print(f"Current Suit:  {prof.get('current_suit', 'None')}")
        print(f"Active Preset: {prof.get('active_preset', 'None')}")
        print(f"Total Raids:   {prof.get('total_raids', 0)} (Survived: {prof.get('survived_raids', 0)}, KIA: {prof.get('kia_raids', 0)})")
        print(f"Survival Rate: {prof.get('survival_rate_pct', 0.0)}%")

    elif args.command == "loadout":
        loadout = get_current_loadout(source)
        print(f"=== Active Matter Equipped Loadout ===")
        if not loadout:
            print("No equipped loadout found.")
            return

        print(f"Preset:   {loadout.get('preset_name', 'Default')}")
        print(f"Helmet:   {loadout.get('helmet_name', 'None')}")
        suit = loadout.get("armor", {}).get("suit_name", "None")
        plates = [p["name"] for p in loadout.get("armor", {}).get("plates", [])]
        plates_s = f" (Плиты: {', '.join(plates)})" if plates else ""
        print(f"Suit:     {suit}{plates_s}")
        print(f"Backpack: {loadout.get('backpack_name', 'None')}")
        print(f"Safepack: {loadout.get('safepack_name', 'None')}")

        print("\nWeapons:")
        for idx, w in enumerate(loadout.get("weapons", []), 1):
            atts = [f"{a['slot']}: {a['name']}" for a in w.get("attachments", [])]
            atts_s = f" [{', '.join(atts)}]" if atts else ""
            print(f"  #{idx}: {w.get('name')}{atts_s}")

        pouch = loadout.get("pouch_items", [])
        print(f"\nPouch Items ({len(pouch)} items):")
        for it in pouch:
            cnt_s = f" x{it['count']}" if it.get("count", 1) > 1 else ""
            ammo_s = f" ({it['ammo_count']} патр.)" if it.get("ammo_count") is not None else ""
            print(f"  • {it.get('name')}{cnt_s}{ammo_s}")

    elif args.command == "raids":
        raids = get_raids(source=source, limit=args.limit)
        print(f"=== Active Matter Raids (Showing {len(raids)}) ===")
        for r in raids:
            status = "ВЫЖИЛ" if r["outcome"]["survived"] else "ПОГИБ"
            loc = r["location"]["full_name"]
            dur = r["outcome"]["play_time_formatted"]
            kills = r["combat"]["kills_total"]
            dmg = r["combat"]["damage_dealt"]
            loot = r["loot"]["found_in_raid_count"]
            print(f"[{status}] #{r['raid_id']} | {loc} ({dur}) | Урон: {dmg} | Киллы: {kills} | Лут: {loot} предм. | {r['date_time_local']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
