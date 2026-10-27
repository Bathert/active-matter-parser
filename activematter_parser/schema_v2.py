"""Active Matter Standard JSON Schema 2.0 for Single Raid Telemetry.

Transforms raw Active Matter game battleResults entries into normalized,
self-describing JSON Schema 2.0 format.

================================================================================
СПРАВОЧНИК ВНУТРИИГРОВЫХ ПОЛЕЙ GAIJIN / DAGOR ENGINE:
================================================================================
• dateTime: Unix timestamp (в секундах) завершения рейда и формирования отчета.
• sessionId: Уникальный ID сетевой игровой сессии на сервере Gaijin.
• version: Внутренняя версия сетевого протокола/дебрифинга игры.
• battleStat:
    - isSuccessRaid: 1 = Успешная эвакуация (Выжил / EXTRACTED).
                     0 = Погиб в бою (KIA) или пропал без вести (MIA).
• battleAreaInfo:
    - raidName: Код локации и режима игры. Формат: "raid+<сектор>+<режим>".
      Примеры: "raid+dalniy_factory+hive" (Завод на Дальнем, режим Улей),
               "raid+africa_airport+ordinary" (Африка, Аэропорт, обычный).
• debriefingStatsV2: Итоговая статистика матча:
    - playTime: Время выживания в рейде (в секундах).
    - playerPathLen: Пройденное расстояние по карте (в метрах).
    - dealtDamage: Суммарный урон, нанесенный игроком (PvP + PvE).
    - receivedDamage: Урон, полученный игроком от пуль, аномалий и монстров.
    - medicineUsed: Количество использованных аптечек/бинтов/стимуляторов.
    - lootedCommonContainers: Обыскано обычных ящиков/контейнеров с лутом.
    - lootedSecretContainers: Обыскано скрытых тайников и аномальных схронов.
    - lootedBodies: Обыскано трупов (оперативников или монстров).
• trackPoints: Массив посекундных точек маршрута и боевых событий:
    - position: 3D-координаты игрока (x - восток/запад, y - высота, z - север/юг).
    - timestamp: Время от начала рейда (в секундах), когда произошло событие.
    - eventType:
        * "positionPoint": Промежуточная точка траектории движения (GPS-трек).
        * "respawned" / "spawn": Точка высадки / респауна оперативника.
        * "kill": Убийство противника игроком.
            - victimType: "militant" = Живой игрок-оперативник (PvP).
                          "monster_*" / "zombie_*" = Мутанты и аномалии (PvE).
            - weaponName: Внутриигровой идентификатор оружия ("items/m4a1_gun").
            - killDistance: Дистанция до жертвы в метрах в момент выстрела.
            - damagedParts: Распределение урона по частям тела жертвы:
              "head" (голова), "body" (торс), "left_hand" / "right_hand" (руки),
              "left_leg" / "right_leg" (ноги).
        * "died": Гибель игрока.
            - offenderType: "militant" = Убит живым игроком (PvP).
            - murderWeaponName: Оружие, которым нанесен смертельный удар.
            - deathCause: Причина ("снаряд", "взрыв", "аномалия").
            - killDistance: Дистанция убийцы.
        * "metPlayerBattle": Боевой контакт (перестрелка) с другим игроком.
        * "transPortalFrom" / "transPortalTo": Вход/выход из квантового портала.
• loadout: Инвентарь игрока на момент окончания рейда:
    - templateName: Идентификатор предмета (например "active_matter_item").
    - count: Количество предметов в стаке.
    - isFoundInRaid: КРИТИЧЕСКИЙ ФЛАГ (FIR):
        * True: Предмет найден и вынесен из этого рейда (добытый лут).
        * False: Собственное снаряжение, взятое в рейд со склада перед стартом.
    - isCorrupted: Флаг заражения активной материей (аномальная порча).
    - charges: Оставшиеся заряды (для стимуляторов и артефактов).
    - ammoCount: Количество патронов, заряженных в магазин.
================================================================================
"""
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


CANONICAL_BODYPARTS = ("head", "body", "left_hand", "right_hand", "left_leg", "right_leg")
MULTI_KILL_WINDOW_SEC = 15.0


def safe_int(val: Any, default: int = 0) -> int:
    """Safely convert string/float/int to integer, handling decimals and nulls without throwing."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isfinite(f):
            return int(f)
    except (ValueError, TypeError, OverflowError):
        pass
    return default


def safe_float(val: Any, default: float = 0.0, ndigits: Optional[int] = None) -> float:
    """Safely convert to finite float, guarding against NaN, Inf and malformed strings."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isfinite(f):
            return round(f, ndigits) if ndigits is not None else f
    except (ValueError, TypeError, OverflowError):
        pass
    return default


ITEM_PRETTY_NAMES: Dict[str, str] = {
    "hellhound_remains_item": "Останки адской гончей",
    "invisible_remains_pristine_item": "Редкие останки невидимки",
    "invisible_remains_item": "Останки невидимки",
    "distorted_remains_item": "Останки искаженного",
    "turned_soldier_remains_item": "Останки обращенного бойца",
    "monster_hunter_artifact_inactive_item": "Неактивный артефакт охотника",
    "active_matter_item": "Активная материя",
    "m4a1_gun": "Штурмовая винтовка M4A1",
    "m4a1_magazine": "Магазин M4A1 (30 патр.)",
    "sv98_gun": "Снайперская винтовка СВ-98",
    "sv98_magazine": "Магазин СВ-98 (10 патр.)",
    "winchester_civil_gun": "Винтовка Winchester Civil",
    "m45a1_gun": "Пистолет M45A1",
    "m1911_colt_magazine": "Магазин M1911 Colt (7 патр.)",
    "pp_91_kedr_20_magazine": "Магазин ПП-91 «Кедр» (20 патр.)",
    "banish_45_ext_suppressor": "Глушитель Banish .45",
    "scope_sig_tango_6": "Оптический прицел SIG Tango 6",
    "item_painkiller": "Обезболивающее",
    "item_healkit": "Аптечка первой помощи",
    "loot_item_healkit_magazine_small": "Малая походная аптечка",
    "loot_item_healkit_magazine_avg": "Средняя походная аптечка",
    "item_injector_streaming": "Стимулятор «Поток»",
    "box_12_gauge_magazine": "Патроны 12 калибра (пачка)",
    "box_45_acp_magazine": "Патроны .45 ACP (пачка)",
    "box_9mm_magazine": "Патроны 9x19 мм (пачка)",
    "box_7_62x54_magazine": "Патроны 7.62x54 мм (пачка)",
    "medium_pouch": "Средний разгрузочный подсумок",
    "small_safepack": "Малый защищенный контейнер",
    "small_backpack": "Малый рюкзак выжившего",
    "helmet_pasgt_tactical": "Тактический шлем PASGT",
    "sm_reaper_item": "Тяжелый экзокостюм «Жнец»",
    "scout_suit": "Костюм разведчика",
    "armorplate_big_uhmwpe": "Большая бронеплита UHMWPE",
    "armorplate_small_uhmwpe": "Малая бронеплита UHMWPE",
    "dash_speed_mult_chronogene_t3": "Хроноген: Скорость рывка III",
    "dash_speed_mult_chronogene_t2": "Хроноген: Скорость рывка II",
}

KNOWN_ITEM_NAMES_RU = ITEM_PRETTY_NAMES

# Семантический порядок категорий: от узких/специфичных к общим
# ВАЖНО: healkit стоит ПЕРЕД magazine, чтобы "healkit_magazine" определялся как медицина
ITEM_CATEGORIES: Dict[str, str] = {
    # 1. Медицина и стимуляторы (высокий приоритет)
    "healkit": "Медицина и стимуляторы",
    "painkiller": "Медицина и стимуляторы",
    "injector": "Медицина и стимуляторы",
    "bandage": "Медицина и стимуляторы",
    "stim": "Медицина и стимуляторы",
    # 2. Останки и аномальные артефакты
    "active_matter": "Останки и артефакты аномалий",
    "hunter_artifact": "Останки и артефакты аномалий",
    "remains": "Останки и артефакты аномалий",
    "artifact": "Останки и артефакты аномалий",
    # 3. Хроногены
    "chronogene": "Хроногены",
    "chrono": "Хроногены",
    # 4. Броня и экипировка
    "helmet": "Броня и защита",
    "armorplate": "Броня и защита",
    "suit": "Броня и защита",
    "armor": "Броня и защита",
    "reaper": "Броня и защита",
    # 5. Оружие и обвесы
    "gun": "Оружие и модификации",
    "rifle": "Оружие и модификации",
    "shotgun": "Оружие и модификации",
    "pistol": "Оружие и модификации",
    "suppressor": "Оружие и модификации",
    "scope": "Оружие и модификации",
    # 6. Контейнеры и подсумки
    "safepack": "Снаряжение и контейнеры",
    "backpack": "Снаряжение и контейнеры",
    "pouch": "Снаряжение и контейнеры",
    # 7. Боеприпасы и магазины (общие ключевые слова в самом конце)
    "magazine": "Боеприпасы и магазины",
    "ammo": "Боеприпасы и магазины",
    "box_": "Боеприпасы и магазины",
    "box": "Боеприпасы и магазины",
    "gauge": "Боеприпасы и магазины",
    "round": "Боеприпасы и магазины",
}

REGION_NAMES: Dict[str, str] = {
    "dalniy": "Дальний остров",
    "africa": "Африка",
    "america": "Америка",
    "europe": "Европа",
    "nexus": "Nexus",
    "gigaserial": "Гигаструктура",
    "monolyth": "Монолит",
}

SUBLOCATION_NAMES: Dict[str, str] = {
    "shegolskoe": "Щегольское",
    "ozernoe": "Озёрное",
    "factory": "Завод",
    "military_base": "Военная база",
    "cargoport": "Грузовой порт",
    "dam": "Дамба",
    "park": "Парк",
    "ore_quarry": "Карьер руды",
    "quarry": "Карьер",
    "scrapyard": "Свалка",
    "dogorsk": "Догорск",
    "underground": "Подземка",
    "airport": "Аэропорт",
    "headquarters": "Штаб-квартира",
    "abandoned_city": "Заброшенный город",
    "abandoned_breakout": "Зона прорыва",
    "abandoned_collapse": "Коллапс",
    "factory_mir": "Завод МИР",
    "itzal_kutan": "Ицаль-Кутан",
    "underground_depo": "Подземное депо",
    "vanilla_mall": "Торговый центр",
    "gigastructure": "Гигахрущ",
    "samosbor": "Самосбор",
}

MODE_NAMES: Dict[str, str] = {
    "ordinary": "Стандартный",
    "hive": "Улей",
    "distortion": "Искажение",
    "samosbor": "Самосбор",
    "breakout": "Прорыв",
    "xenos": "Ксеносы",
    "collapse": "Коллапс",
}


def prettify_item_name(template: Optional[str]) -> str:
    """Return clean human-readable Russian item title."""
    if not template:
        return "Неизвестный предмет"
    cleaned = str(template).replace("items/", "").strip()
    if cleaned in ITEM_PRETTY_NAMES:
        return ITEM_PRETTY_NAMES[cleaned]
    # Fallback to readable title from snake_case
    words = cleaned.replace("_item", "").replace("_gun", "").replace("_", " ").title()
    return words


def categorize_template(template: Optional[str]) -> str:
    """Classify item template into a canonical category using semantic priority order."""
    if not template:
        return "Разное"
    t_lower = str(template).lower()
    # Preserves insertion order: specific categories (healkit) match before broad (magazine)
    for key, cat in ITEM_CATEGORIES.items():
        if key in t_lower:
            return cat
    return "Разное"


def parse_location_info(raid_code: Optional[str]) -> Dict[str, str]:
    """Parse raw raid code (e.g. 'raid+dalniy_factory+ordinary') into components."""
    if not raid_code:
        return {
            "code": "unknown",
            "region": "Неизвестно",
            "sublocation": "Неизвестно",
            "mode": "Стандартный",
            "full_name": "Неизвестная локация"
        }

    parts = str(raid_code).replace("raid+", "").split("+")
    loc_part = parts[0] if len(parts) > 0 else ""
    mode_part = parts[1] if len(parts) > 1 else "ordinary"

    region = "Дальний остров"
    for r_k, r_name in sorted(REGION_NAMES.items(), key=lambda x: len(x[0]), reverse=True):
        if r_k in loc_part.lower():
            region = r_name
            break

    subloc = loc_part
    # Match longest sublocation identifiers first (e.g. factory_mir before factory, ore_quarry before quarry)
    for s_k, s_name in sorted(SUBLOCATION_NAMES.items(), key=lambda x: len(x[0]), reverse=True):
        if s_k in loc_part.lower():
            subloc = s_name
            break

    mode = MODE_NAMES.get(mode_part.lower(), mode_part.title())
    full_name = f"{subloc} ({region})" if subloc != region else region
    if mode != "Стандартный":
        full_name += f" [{mode}]"

    return {
        "code": raid_code,
        "region": region,
        "sublocation": subloc,
        "mode": mode,
        "full_name": full_name
    }


def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    s = max(0, safe_int(seconds, 0))
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def transform_to_schema_v2(
    raw_raid: Dict[str, Any],
    player_uid: Optional[str] = None,
    include_raw: bool = False
) -> Dict[str, Any]:
    """Transform a single raw game battleResults object into Schema 2.0 format."""
    # 1. Основные метаданные матча
    raid_id = str(raw_raid.get("id") or "")
    session_id = str(raw_raid.get("sessionId") or "")
    version = str(raw_raid.get("version") or "")
    dt_epoch = safe_int(raw_raid.get("dateTime"), 0)

    # 2. Временные метки (UTC ISO 8601 и человекочитаемое локальное время)
    dt_iso = ""
    dt_local = ""
    if dt_epoch > 0:
        try:
            dt_utc_obj = datetime.fromtimestamp(dt_epoch, tz=timezone.utc)
            dt_iso = dt_utc_obj.isoformat().replace("+00:00", "Z")
            dt_local = datetime.fromtimestamp(dt_epoch).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    # 3. Локация: сектор, регион и аномальный режим (battleAreaInfo.raidName)
    area_info = raw_raid.get("battleAreaInfo", {}) or {}
    raid_code = area_info.get("raidName", "")
    loc_info = parse_location_info(raid_code)

    # 4. Исход рейда: 1 = эвакуация (EXTRACTED), 0 = погиб в бою (KIA)
    battle_stat = raw_raid.get("battleStat", {}) or {}
    is_success = bool(safe_int(battle_stat.get("isSuccessRaid"), 0) == 1)
    status = "EXTRACTED" if is_success else "KIA"

    # 5. Итоговая статистика рейда (debriefingStatsV2)
    debrief = raw_raid.get("debriefingStatsV2", {}) or {}
    play_time_sec = safe_int(debrief.get("playTime"), 0)
    damage_dealt = safe_int(debrief.get("dealtDamage"), 0)
    damage_received = safe_int(debrief.get("receivedDamage"), 0)
    path_len_m = safe_float(debrief.get("playerPathLen"), 0.0, ndigits=1)
    medicine_used = safe_int(debrief.get("medicineUsed"), 0)
    looted_common = safe_int(debrief.get("lootedCommonContainers"), 0)
    looted_secret = safe_int(debrief.get("lootedSecretContainers"), 0)
    looted_bodies = safe_int(debrief.get("lootedBodies"), 0)

    # 6. Данные оперативника игрока (teamInfo)
    # При игре в скваде ищем игрока с совпадающим player_uid или маркером isLocal/isMe
    team_info = raw_raid.get("teamInfo", []) or []
    operative_name = "Оперативник"
    suit_template = None
    if isinstance(team_info, list) and team_info:
        player_entry = None
        if player_uid:
            p_uid_str = str(player_uid).strip()
            for p in team_info:
                if isinstance(p, dict):
                    cand = str(p.get("userId") or p.get("uid") or p.get("playerId") or "").strip()
                    if cand and cand == p_uid_str:
                        player_entry = p
                        break
                    if p.get("isLocal") or p.get("isMe"):
                        player_entry = p
                        break
        if not player_entry:
            for p in team_info:
                if isinstance(p, dict):
                    player_entry = p
                    break

        if player_entry:
            operative_name = player_entry.get("name") or operative_name
            suit_template = player_entry.get("suitTemplate")

    # 7. GPS-трек и боевая телеметрия (trackPoints)
    raw_track = raw_raid.get("trackPoints", []) or []
    track_points: List[Dict[str, Any]] = []
    kills_list: List[Dict[str, Any]] = []
    multi_kills_count = 0
    last_kill_ts: Optional[float] = None
    longest_shot_m = 0.0
    death_info: Optional[Dict[str, Any]] = None
    player_fights = 0
    portals_used = 0

    pvp_kills_count = 0
    pve_kills_count = 0
    pvp_damage_calc = 0.0

    # Сортируем точки трека по timestamp для предотвращения рассинхрона
    valid_raw_track = [pt for pt in raw_track if isinstance(pt, dict)]
    valid_raw_track.sort(key=lambda pt: safe_float(pt.get("timestamp"), 0.0))

    for pt in valid_raw_track:
        pos = pt.get("position", {}) or {}
        event_type = pt.get("eventType", "positionPoint")
        ts = safe_float(pt.get("timestamp"), 0.0, ndigits=2)

        entry = {
            "x": safe_float(pos.get("x"), 0.0, ndigits=2),
            "y": safe_float(pos.get("y"), 0.0, ndigits=2),
            "z": safe_float(pos.get("z"), 0.0, ndigits=2),
            "timestamp": ts,
            "event": event_type,
        }

        # Обработка убийства врага (eventType == "kill")
        if event_type == "kill":
            victim_type = str(pt.get("victimType") or "bot")
            # "militant" означает реального игрока-оперативника (PvP)
            is_pvp = bool(victim_type == "militant")
            if is_pvp:
                pvp_kills_count += 1
            else:
                pve_kills_count += 1

            # Детектор серии быстрых убийств (мульти-килл в окне 15 сек при монотонном ts)
            if last_kill_ts is not None and 0.0 <= (ts - last_kill_ts) <= MULTI_KILL_WINDOW_SEC:
                multi_kills_count += 1
            last_kill_ts = ts

            # Оружие и дальность выстрела
            raw_w = str(pt.get("weaponName") or "").replace("items/", "")
            kd = safe_float(pt.get("killDistance"), 0.0, ndigits=1)
            if kd > longest_shot_m:
                longest_shot_m = kd

            # Анатомическая раскладка попаданий по частям тела жертвы
            raw_parts = pt.get("damagedParts") or {}
            damaged_parts = {
                str(k): safe_float(v, 0.0, ndigits=1) for k, v in raw_parts.items()
                if isinstance(v, (int, float, str))
            } if isinstance(raw_parts, dict) else {}

            parts_dmg = sum(damaged_parts.values()) if damaged_parts else (280.0 if is_pvp else 0.0)
            if is_pvp:
                pvp_damage_calc += parts_dmg

            kill_item = {
                "victim_name": str(pt.get("name") or ("Игрок" if is_pvp else "Аномалия")),
                "victim_type": victim_type,
                "is_pvp": is_pvp,
                "weapon": prettify_item_name(raw_w) if raw_w else "Оружие",
                "weapon_raw": raw_w,
                "distance_m": kd,
                "timestamp_sec": ts,
                "damaged_parts": damaged_parts,
            }
            kills_list.append(kill_item)
            entry["kill_details"] = kill_item

        elif event_type == "metPlayerBattle":
            # Фиксация перестрелки с живым противником
            player_fights += 1
            entry["opponent_name"] = pt.get("name")
        elif event_type == "transPortalFrom":
            # 1 прыжок генерирует вход (transPortalFrom) и выход (transPortalTo).
            # Считаем только события входа (transPortalFrom), чтобы 1 перемещение считалось как 1 использование портала.
            portals_used += 1
        elif event_type == "transPortalTo" and portals_used == 0:
            # Краевой случай: лог начался уже внутри перемещения портала
            portals_used = 1
        elif event_type == "died" and not death_info:
            # Детали гибели игрока в матче
            raw_mw = str(pt.get("murderWeaponName") or "").replace("items/", "")
            death_info = {
                "killer_name": pt.get("name") or "Неизвестный противник",
                "killer_type": pt.get("offenderType", "militant"),
                "is_pvp": bool(pt.get("offenderType") == "militant"),
                "murder_weapon": prettify_item_name(raw_mw) if raw_mw else "Огнестрельное оружие",
                "death_cause": pt.get("deathCause", "снаряд"),
                "kill_distance_m": safe_float(pt.get("killDistance"), 0.0, ndigits=1),
                "timestamp_sec": ts,
            }
            entry["death_details"] = death_info

        track_points.append(entry)

    # Разделение урона: PvP (по подтвержденным фрагам игроков) и PvE (по мутантам/ботам)
    # Примечание о телеметрии Dagor Engine:
    # Движок игры хранит точный посегментный урон (damagedParts) только в момент ликвидации
    # противника (eventType == "kill"). Если игрок ранил другого оперативника в перестрелке
    # (metPlayerBattle), но не добил его (враг убежал), движок не создает отдельного PvP-эвента,
    # и этот урон входит в общий debriefingStatsV2.dealtDamage. Поэтому pvp_damage отражает
    # подтвержденный урон по ликвидированным целям.
    pvp_damage = min(damage_dealt, round(pvp_damage_calc))
    pve_damage = max(0, damage_dealt - pvp_damage)

    # 8. Лут и экипировка (loadout)
    # isFoundInRaid == True -> вынесенный добытый лут (FIR)
    # isFoundInRaid == False -> снаряжение, взятое с собой из убежища
    raw_loadout = raw_raid.get("loadout", []) or []
    found_in_raid_items: List[Dict[str, Any]] = []
    brought_in_gear_items: List[Dict[str, Any]] = []

    for it in raw_loadout:
        if not isinstance(it, dict):
            continue
        tmpl = it.get("templateName", "")
        if not tmpl:
            continue
        count = safe_int(it.get("count"), 1)
        is_corrupted = bool(it.get("isCorrupted", False))
        is_fir = bool(it.get("isFoundInRaid", False))

        # Explicit check for None to avoid treating 0 rounds as falsy
        ammo = it.get("ammoCount")
        if ammo is None:
            ammo = it.get("ammo_count")
        charges = it.get("charges")

        item_entry = {
            "template": tmpl,
            "name": prettify_item_name(tmpl),
            "category": categorize_template(tmpl),
            "count": count,
            "is_corrupted": is_corrupted,
            "item_id": it.get("itemId"),
            "charges": safe_int(charges) if charges is not None else None,
            "ammo_count": safe_int(ammo) if ammo is not None else None,
        }
        if is_fir:
            found_in_raid_items.append(item_entry)
        else:
            brought_in_gear_items.append(item_entry)

    # 9. Прогресс контрактов и опыт
    contracts = []
    for c in raw_raid.get("contractsVisuals", []) or []:
        if isinstance(c, dict):
            contracts.append({
                "id": c.get("id"),
                "progress": safe_int(c.get("progress")),
                "target": safe_int(c.get("target")),
                "is_completed": bool(c.get("isCompleted", False)),
            })

    exp_block = raw_raid.get("experienceBlock", {}) or {}
    exp_rewards = exp_block.get("expRewards", []) or []
    total_xp = sum(safe_int(r.get("exp")) for r in exp_rewards if isinstance(r, dict))

    # 10. Открытые крафты и заряды хроногенов
    opened_recipes = [
        {"node_id": ocr.get("nodeId")}
        for ocr in raw_raid.get("openedCraftRecipes", []) or []
        if isinstance(ocr, dict)
    ]
    chrono_charges = raw_raid.get("chronogeneCharges", {}) or {}

    # Сборка итогового объекта Schema 2.0
    schema_v2_object: Dict[str, Any] = {
        "schema_version": "2.0",
        "raid_id": raid_id,
        "session_id": session_id,
        "game_version": version,
        "timestamp": dt_epoch,
        "date_time_iso": dt_iso,
        "date_time_local": dt_local,
        "location": loc_info,
        "outcome": {
            "survived": is_success,
            "status": status,
            "play_time_seconds": play_time_sec,
            "play_time_formatted": format_duration(play_time_sec),
        },
        "player": {
            "uid": str(player_uid or ""),
            "operative_name": operative_name,
            "suit": suit_template,
            "suit_name": prettify_item_name(suit_template) if suit_template else "Без костюма",
        },
        "combat": {
            "damage_dealt": damage_dealt,
            "damage_received": damage_received,
            "pvp_damage": pvp_damage,
            "pve_damage": pve_damage,
            "kills_total": len(kills_list),
            "pvp_kills": pvp_kills_count,
            "pve_kills": pve_kills_count,
            "kills": kills_list,
            "multi_kills": multi_kills_count,
            "longest_kill_m": longest_shot_m,
            "death": death_info,
        },
        "activity": {
            "containers_looted": looted_common + looted_secret,
            "common_containers": looted_common,
            "secret_containers": looted_secret,
            "bodies_looted": looted_bodies,
            "medicine_used": medicine_used,
            "player_fights": player_fights,
            "portals_used": portals_used,
        },
        "loot": {
            "found_in_raid_count": len(found_in_raid_items),
            "found_in_raid_units": sum(it["count"] for it in found_in_raid_items),
            "found_in_raid": found_in_raid_items,
            "brought_in_gear": brought_in_gear_items,
        },
        "contracts": contracts,
        "experience": {
            "total_xp": total_xp,
            "rewards": exp_rewards,
        },
        "opened_recipes": opened_recipes,
        "chronogene_charges": chrono_charges,
        "telemetry": {
            "path_length_m": path_len_m,
            "points_count": len(track_points),
            "track_points": track_points,
        },
        "raw_debriefing_stats": debrief,
    }

    if include_raw:
        schema_v2_object["raw_game_data"] = raw_raid

    return schema_v2_object
