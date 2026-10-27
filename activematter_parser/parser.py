"""Active Matter Local Storage Parser.

Parses local profile, equipped loadout, active quests, and raid results
from Active Matter game storage (%LOCALAPPDATA%\\active_matter\\downloads\\online_storage).

100% passive, read-only file parsing. Zero process memory access or hooks.

================================================================================
СТРУКТУРА ЛОКАЛЬНОГО ХРАНИЛИЩА (online_storage / global.json):
================================================================================
• online_storage/<UID>/active_matter/am-production/global.json:
  Основной файл профиля, куда клиент игры сохраняет:
    - player_presets:
        * playerPreset_lastUsed: Текущий экипированный пресет (снаряжение в руках).
        * weapons: Массив оружия со слотами обвесов (scope, muzzle, magazine, stock, pistolgrip).
        * chronogene_primary_1: Активный бронекостюм со слотами плит (equipment_mod_*).
        * inventories.pouch: Защищенный подсумок (сохраняется при гибели).
    - battleResults: Массив последних отчетов о рейдах (история матчей).
    - selectedMetaquests: Список активных контрактов/заданий.
================================================================================
"""
import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Windows console UTF-8 safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .schema_v2 import (
    prettify_item_name,
    categorize_template,
    parse_location_info,
    transform_to_schema_v2,
    safe_int,
    safe_float,
    KNOWN_ITEM_NAMES_RU,
)


def format_epoch_dt(epoch_val: Any) -> str:
    """Convert unix epoch timestamp to readable YYYY-MM-DD HH:MM:SS string."""
    try:
        val = int(epoch_val)
        return datetime.fromtimestamp(val).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(epoch_val or "Неизвестно")


def get_online_storage_root() -> Optional[Path]:
    """Find the root path of Active Matter online storage on Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    candidate = Path(local_app_data) / "active_matter" / "downloads" / "online_storage"
    return candidate if candidate.exists() else None


def get_active_player_uid() -> Optional[str]:
    """Retrieve the current active player's UID from online_storage."""
    root = get_online_storage_root()
    if not root:
        return None

    last_uid_file = root / "last" / "lastUid"
    if last_uid_file.exists():
        try:
            val = last_uid_file.read_text(encoding="utf-8", errors="replace").strip().strip("\x00").strip()
            if val:
                return val
        except Exception:
            pass

    # Fallback: scan for any numeric directory
    for entry in root.iterdir():
        clean_name = entry.name.strip().strip("\x00").strip()
        if entry.is_dir() and clean_name.isdigit():
            return clean_name
    return None


def resolve_effective_uid(
    source: Optional[Union[str, Path, Dict[str, Any]]] = None,
    content: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Resolve player UID from source path/content, falling back to local account only if source is None."""
    if source is None and content is None:
        return get_active_player_uid()

    if isinstance(source, (str, Path)):
        p = Path(source)
        # Check if path contains a numeric UID folder (e.g. online_storage/240872112/...)
        # Gaijin UIDs are typically 6-12 digits. Require >= 6 digits (or >= 5 if inside 'online_storage')
        # to prevent 4-digit backup year folders like '2026' from being mistaken for a player UID.
        is_in_online_storage = any(part.lower() == "online_storage" for part in p.parts)
        min_len = 5 if is_in_online_storage else 6

        for part in p.parts:
            clean_part = part.strip().strip("\x00").strip()
            if clean_part.isdigit() and len(clean_part) >= min_len:
                return clean_part

        # Check adjacent lastUid
        check_dirs = [p.parent, p.parent.parent] if not p.is_dir() else [p, p.parent]
        for d in check_dirs:
            l_file = d / "last" / "lastUid"
            if l_file.exists():
                try:
                    uid_val = l_file.read_text(encoding="utf-8", errors="replace").strip().strip("\x00").strip()
                    if uid_val:
                        return uid_val
                except Exception:
                    pass

    # Inspect content battleResults teamInfo for player UID (re-using pre-loaded content to prevent duplicate disk I/O)
    c_data = content if content is not None else (source if isinstance(source, dict) else load_global_content(source))
    results = c_data.get("battleResults", []) if isinstance(c_data, dict) else []
    if isinstance(results, list):
        # 1. Prefer explicit local operative marker if available
        for r in results:
            if isinstance(r, dict):
                for p in r.get("teamInfo", []):
                    if isinstance(p, dict) and (p.get("isLocal") or p.get("isMe")):
                        cand = p.get("userId") or p.get("uid") or p.get("playerId") or p.get("id")
                        if cand and str(cand).isdigit():
                            return str(cand)

        # 2. Fallback to any valid numeric player ID
        for r in results:
            if isinstance(r, dict):
                for p in r.get("teamInfo", []):
                    if isinstance(p, dict):
                        cand = p.get("userId") or p.get("uid") or p.get("playerId") or p.get("id")
                        if cand and str(cand).isdigit():
                            return str(cand)

    return None


def find_global_json(
    source: Optional[Union[str, Path]] = None,
    uid: Optional[str] = None
) -> Optional[Path]:
    """Locate the global.json file from explicit path, UID, or auto-detection."""
    if source is not None:
        p = Path(source)
        if p.is_file() and p.exists():
            return p
        if p.is_dir():
            # 1. Direct global.json in directory
            candidate = p / "global.json"
            if candidate.exists():
                return candidate
            # 2. Standard nested client structure: active_matter/am-production/global.json
            sub = p / "active_matter" / "am-production" / "global.json"
            if sub.exists():
                return sub
            # 3. Source is an online_storage root: resolve via lastUid or UID subdirectories
            last_uid_file = p / "last" / "lastUid"
            if last_uid_file.exists():
                try:
                    uid_val = last_uid_file.read_text(encoding="utf-8", errors="replace").strip().strip("\x00").strip()
                    if uid_val:
                        cand_uid = p / uid_val / "active_matter" / "am-production" / "global.json"
                        if cand_uid.exists():
                            return cand_uid
                except Exception:
                    pass
            # 4. Check last directory fallback
            cand_last = p / "last" / "active_matter" / "am-production" / "global.json"
            if cand_last.exists():
                return cand_last
            # 5. Scan any numeric UID directory inside source
            try:
                for sub_entry in p.iterdir():
                    clean_name = sub_entry.name.strip().strip("\x00").strip()
                    if sub_entry.is_dir() and clean_name.isdigit():
                        cand_num = sub_entry / "active_matter" / "am-production" / "global.json"
                        if cand_num.exists():
                            return cand_num
            except Exception:
                pass

    root = get_online_storage_root()
    if not root:
        return None

    eff_uid = uid or get_active_player_uid()
    if eff_uid:
        p_uid = root / eff_uid / "active_matter" / "am-production" / "global.json"
        if p_uid.exists():
            return p_uid

    p_last = root / "last" / "active_matter" / "am-production" / "global.json"
    if p_last.exists():
        return p_last

    return None


def load_global_content(source: Optional[Union[str, Path, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Load and return the content dictionary of global.json.
    
    Accepts:
        - dict: returns the dict directly or its 'content' child.
        - Path/str: loads JSON from the given file or directory path.
        - None: auto-detects from local game installation.
    """
    if isinstance(source, dict):
        return source.get("content", source)

    json_path = find_global_json(source)
    if not json_path or not json_path.exists():
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("content", data)
            return {}
    except Exception as e:
        sys.stderr.write(f"[activematter-parser WARNING] Failed to read/parse {json_path}: {e}\n")
        return {}


def get_player_profile(source: Optional[Union[str, Path, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Extract operative profile, career summary, and survival stats."""
    content = load_global_content(source)
    if not content:
        return {}

    eff_uid = resolve_effective_uid(source, content=content) or "unknown"
    results = content.get("battleResults", [])
    raids_list = results if isinstance(results, list) else []

    total_raids = len(raids_list)
    # isSuccessRaid == 1 означает успешную эвакуацию (Выжил)
    survived_raids = sum(
        1 for r in raids_list
        if isinstance(r, dict) and safe_int((r.get("battleStat") or {}).get("isSuccessRaid")) == 1
    )
    kia_raids = total_raids - survived_raids
    survival_rate = round((survived_raids / total_raids * 100), 1) if total_raids > 0 else 0.0

    operative_name = "Оперативник"
    suit_name = "Без костюма"
    if raids_list:
        r0 = raids_list[0]
        if isinstance(r0, dict):
            teams = r0.get("teamInfo", [])
            if isinstance(teams, list) and teams:
                player_entry = None
                # Search for player matching eff_uid or local marker
                for p in teams:
                    if isinstance(p, dict):
                        cand_id = str(p.get("userId") or p.get("uid") or p.get("playerId") or p.get("id") or "").strip()
                        if cand_id and cand_id == eff_uid:
                            player_entry = p
                            break
                        if p.get("isLocal") or p.get("isMe"):
                            player_entry = p
                            break
                if not player_entry:
                    player_entry = teams[0] if isinstance(teams[0], dict) else None

                if player_entry:
                    operative_name = player_entry.get("name") or operative_name
                    st = player_entry.get("suitTemplate")
                    if st:
                        suit_name = prettify_item_name(st)

    # Re-use already loaded content dictionary to avoid duplicate disk I/O
    loadout = get_current_loadout(content)
    if loadout.get("armor", {}).get("suit_name"):
        suit_name = loadout["armor"]["suit_name"]

    return {
        "uid": eff_uid,
        "operative_name": operative_name,
        "total_raids": total_raids,
        "survived_raids": survived_raids,
        "kia_raids": kia_raids,
        "survival_rate_pct": survival_rate,
        "current_suit": suit_name,
        "active_preset": loadout.get("preset_name", "Текущий комплект"),
        "selected_metaquests": content.get("selectedMetaquests", []),
    }


def get_current_loadout(source: Optional[Union[str, Path, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Extract currently equipped weapons, attachments, armor, and pouch items."""
    content = load_global_content(source)
    presets = content.get("player_presets", {})
    if not isinstance(presets, dict):
        return {}

    # playerPreset_lastUsed: последний выбранный игроком комплект
    last_used = presets.get("playerPreset_lastUsed", {})
    if not last_used:
        for k, v in presets.items():
            if isinstance(v, dict) and ("weapons" in v or "suit" in v):
                last_used = v
                break

    if not last_used:
        return {}

    def _extract_tmpl(val):
        if isinstance(val, dict):
            return val.get("itemTemplate") or val.get("template")
        elif isinstance(val, str):
            return val
        return None

    # 1. Оружие и установленные оружейные модификации (scope, muzzle, mag, etc.)
    weapons = []
    for w in last_used.get("weapons", []):
        if not isinstance(w, dict):
            continue
        tmpl = _extract_tmpl(w)
        if not tmpl:
            continue
        attachments = []
        att_data = w.get("attachments", {})
        if isinstance(att_data, dict):
            for att_slot, item in att_data.items():
                if isinstance(item, dict):
                    t = _extract_tmpl(item)
                    if t:
                        attachments.append({
                            "slot": att_slot,
                            "template": t,
                            "name": prettify_item_name(t)
                        })
        elif isinstance(att_data, list):
            for item in att_data:
                if isinstance(item, dict):
                    t = _extract_tmpl(item)
                    if t:
                        attachments.append({
                            "slot": item.get("slot", "mod"),
                            "template": t,
                            "name": prettify_item_name(t)
                        })
        ammo = w.get("ammoCount")
        if ammo is None:
            ammo = w.get("ammo_count")
        charges = w.get("charges")

        weapons.append({
            "template": tmpl,
            "name": prettify_item_name(tmpl),
            "ammo_count": safe_int(ammo) if ammo is not None else None,
            "charges": safe_int(charges) if charges is not None else None,
            "attachments": attachments
        })

    # 2. Защищенный подсумок (pouch) - патроны, медицина, ценности
    inventories = last_used.get("inventories", {})
    pouch_data = inventories.get("pouch", {}) if isinstance(inventories, dict) else {}
    raw_pouch_items = pouch_data.get("items", []) if isinstance(pouch_data, dict) else []
    if not raw_pouch_items and "pouch_items" in last_used:
        raw_pouch_items = last_used.get("pouch_items", [])

    pouch_items = []
    for it in raw_pouch_items:
        if isinstance(it, dict):
            t = _extract_tmpl(it)
            if t:
                # Explicit check for None to avoid treating 0 rounds / 0 charges as falsy
                ammo = it.get("ammoCount")
                if ammo is None:
                    ammo = it.get("ammo_count")
                charges = it.get("charges")

                pouch_items.append({
                    "template": t,
                    "name": prettify_item_name(t),
                    "count": safe_int(it.get("count"), 1),
                    "ammo_count": safe_int(ammo) if ammo is not None else None,
                    "charges": safe_int(charges) if charges is not None else None,
                    "is_boxed": bool(it.get("isBoxedItem", False))
                })

    # 3. Броня: экзокостюм (chronogene_primary_1) и установленные бронеплиты (equipment_mod_*)
    armor = {}
    primary_chrono = last_used.get("chronogene_primary_1", {})
    if isinstance(primary_chrono, dict):
        suit_template = primary_chrono.get("itemTemplate")
        plates = []
        for mod_k, mod_v in primary_chrono.items():
            if mod_k.startswith("equipment_mod_") and isinstance(mod_v, dict):
                t = mod_v.get("itemTemplate")
                plates.append({
                    "slot": mod_v.get("slotTemplateName", mod_k),
                    "template": t,
                    "name": prettify_item_name(t)
                })
        armor = {
            "suit": suit_template,
            "suit_name": prettify_item_name(suit_template) if suit_template else "Без костюма",
            "plates": plates
        }
    if not armor.get("suit") and last_used.get("suit"):
        s_tmpl = _extract_tmpl(last_used.get("suit"))
        if s_tmpl:
            armor = {
                "suit": s_tmpl,
                "suit_name": prettify_item_name(s_tmpl),
                "plates": []
            }

    # 4. Шлем, рюкзак и сейфпак
    helmet_tmpl = _extract_tmpl(last_used.get("helmet"))
    backpack_tmpl = _extract_tmpl(last_used.get("backpack"))
    safepack_tmpl = _extract_tmpl(last_used.get("safepack"))

    return {
        "preset_name": last_used.get("presetName") or last_used.get("name", "Текущий комплект"),
        "weapons": weapons,
        "helmet": helmet_tmpl,
        "helmet_name": prettify_item_name(helmet_tmpl) if helmet_tmpl else "Без шлема",
        "armor": armor,
        "backpack": backpack_tmpl,
        "backpack_name": prettify_item_name(backpack_tmpl) if backpack_tmpl else "Без рюкзака",
        "safepack": safepack_tmpl,
        "safepack_name": prettify_item_name(safepack_tmpl) if safepack_tmpl else "Без защищенного кармана",
        "pouch_capacity": safe_int(pouch_data.get("capacity")) if pouch_data.get("capacity") is not None else None,
        "pouch_items": pouch_items,
    }


def get_raids(
    source: Optional[Union[str, Path, Dict[str, Any]]] = None,
    limit: Optional[int] = None,
    include_raw: bool = False
) -> List[Dict[str, Any]]:
    """Return parsed raid history transformed into Schema 2.0 format."""
    content = load_global_content(source)
    results = content.get("battleResults", [])
    if not isinstance(results, list):
        return []

    eff_uid = resolve_effective_uid(source, content=content)
    parsed: List[Dict[str, Any]] = []

    for r in results:
        if isinstance(r, dict):
            parsed.append(transform_to_schema_v2(r, player_uid=eff_uid, include_raw=include_raw))
            if limit is not None and len(parsed) >= limit:
                break

    return parsed


# Aliases for backwards compatibility
get_raid_history = get_raids
get_player_career_summary = get_player_profile
