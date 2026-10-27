# Active Matter Parser & Raid Slicer (JSON 2.0)

<p align="center">
  <a href="README.md"><b>English</b></a> •
  <a href="README_RU.md"><b>Русский</b></a>
</p>

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![BattlEye Safe](https://img.shields.io/badge/BattlEye-100%25%20Safe%20(Passive)-brightgreen)](#-безопасность-для-античита-battleye)
[![Zero External Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-success)](#)

**activematter-parser** — чистый, легковесный парсер локальных файлов **Active Matter** (Dagor Engine / Gaijin Network) и утилита для нарезки истории матчей в отдельные стандартизированные JSON-файлы формата **Schema 2.0**.

Zero dependencies — работает **только** на стандартной библиотеке Python 3.9+ без OpenCV, Torch, Pillow или сторонних пакетов.

---

## 🛡️ Безопасность для античита BattlEye

> **Полная безопасность для аккаунта**:
> - **НЕ** внедряется в память игры (`ReadProcessMemory`).
> - **НЕ** использует DLL injection, хуки API или фоновые потоки, прикрепленные к игре.
> - **НЕ** модифицирует исполняемые файлы или ресурсы игры.
> - Читает исключительно открытый JSON-кэш, который официальный клиент игры сам сохраняет на локальный диск:  
>   `%LOCALAPPDATA%\active_matter\downloads\online_storage\<UID>\active_matter\am-production\global.json`
> - На 100% пассивный режим работы.

---

## ⚡ Возможности (Features)

1. **Парсинг профиля игрока (`get_player_profile`)**:
   - Авто-детект активного UID игрока и путей локального хранилища.
   - Имя оперативника, активный пресет снаряжения, количество рейдов, процент выживаемости.

2. **Парсинг текущего комплекта (`get_current_loadout`)**:
   - Надетый костюм (экзокостюм «Жнец», легкие костюмы) и установленные бронеплиты (`equipment_mod_*`).
   - Шлем, рюкзак, защищенный карман (сейфпак).
   - Все экипированные пушки с прикрепленными обвесами (прицелы, глушители, ЛЦУ, приклады, рукоятки, магазины).
   - Содержимое подсумка с точным подсчетом патронов и зарядов артефактов/стимуляторов.

3. **Нарезка рейдов по одному в JSON 2.0 (`slice_raids`)**:
   - Извлекает монолитный массив `battleResults` из `global.json` и нарезает каждый матч в отдельный файл `raid_<id>.json`.
   - Приводит каждый рейд к стандарту **JSON Schema 2.0** с нормализацией локаций, исходов, мульти-киллов и телеметрии.

4. **Боевая аналитика и GPS-телеметрия**:
   - **Мульти-киллы**: авто-детект быстрых серий фрагов с плавающим окном в 15 секунд.
   - Разделение урона: **PvP** (по живым игрокам) и **PvE** (по ботам/аномалиям).
   - Посекундные 3D-координаты перемещения игрока по карте (`track_points`) с метками событий (убийства, ранения, аптечки, лутание ящиков).
   - Строгое разделение найденного лута (**Found in Raid / FIR**) от собственного снаряжения, взятого со склада.

---

## 📋 Стандарт JSON Schema 2.0

Каждый нарезанный рейд сохраняется в едином самодостаточном формате:

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

## 📖 Справочник внутриигровых полей (Game Data Dictionary)

Для разработчиков, работающих с сырым `global.json` или создающих свои тулы, ниже приведена расшифровка внутренних полей движка Dagor / Gaijin:

| Сырое поле в `global.json` | Тип | Что означает в игре | Как преобразуется в Schema 2.0 |
| :--- | :--- | :--- | :--- |
| **`battleStat.isSuccessRaid`** | `int` | `1` — эвакуация (Выжил), `0` — погиб (KIA) или пропал без вести | `outcome.survived` (`bool`), `outcome.status` (`EXTRACTED` / `KIA`) |
| **`battleAreaInfo.raidName`** | `str` | Код локации: `raid+<сектор>+<режим>` (например `raid+dalniy_factory+hive`) | `location.region`, `location.sublocation`, `location.mode` |
| **`debriefingStatsV2.playTime`** | `int` | Длительность рейда в секундах | `outcome.play_time_seconds` и `play_time_formatted` (`MM:SS`) |
| **`debriefingStatsV2.playerPathLen`**| `float` | Пройденная дистанция пешком/бегом в метрах | `telemetry.path_length_m` |
| **`debriefingStatsV2.dealtDamage`** | `int` | Суммарный нанесенный урон (PvP + PvE) | `combat.damage_dealt`, разделяется на `pvp_damage` и `pve_damage` |
| **`debriefingStatsV2.receivedDamage`**| `int` | Суммарный полученный урон игроком | `combat.damage_received` |
| **`debriefingStatsV2.medicineUsed`** | `int` | Количество использованных аптечек, бинтов и стимуляторов | `activity.medicine_used` |
| **`debriefingStatsV2.lootedCommonContainers`** | `int` | Обыскано обычных ящиков и шкафов | `activity.common_containers` |
| **`debriefingStatsV2.lootedSecretContainers`** | `int` | Найдено и обыскано скрытых аномальных схронов | `activity.secret_containers` |
| **`debriefingStatsV2.lootedBodies`** | `int` | Обыскано трупов (игроков или монстров) | `activity.bodies_looted` |
| **`trackPoints[].eventType`** | `str` | Тип события: `positionPoint` (шаг), `kill` (фраг), `died` (смерть), `metPlayerBattle` (перестрелка), `transPortalFrom/To` (портал) | `telemetry.track_points[].event`, `combat.kills`, `combat.death` |
| **`trackPoints[].victimType`** | `str` | **`militant` = реальный игрок (PvP)**, `monster_*` = мутанты/криперы (PvE) | `combat.kills[].is_pvp` (`true`/`false`), `combat.pvp_kills` |
| **`trackPoints[].damagedParts`** | `dict` | Анатомический урон по жертве (`head`, `body`, `left_hand`, `right_hand`, `left_leg`, `right_leg`) | `combat.kills[].damaged_parts` |
| **`loadout[].isFoundInRaid`** | `bool` | **Критический флаг (FIR)**: `True` — добыто в этом рейде (лут). `False` — снаряжение, взятое со склада | Делит предметы на `loot.found_in_raid` и `loot.brought_in_gear` |
| **`loadout[].isCorrupted`** | `bool` | Предмет заражен активной материей (требует очистки) | `loot.found_in_raid[].is_corrupted` |
| **`player_presets`** | `dict` | Пресеты убежища: оружие с обвесами, экзокостюм (`chronogene_primary_1`), защищенный подсумок (`inventories.pouch`) | `get_current_loadout()` |

---

## 🚀 Установка

```bash
git clone https://github.com/Bathert/active-matter-parser.git
cd active-matter-parser
pip install -e .
```

---

## 💻 CLI Утилита

После установки доступна команда `activematter-parser`:

### 1. Нарезать все рейды в отдельные JSON 2.0 файлы
```bash
# Нарезать рейды из локального хранилища в папку ./raids_v2
activematter-parser slice

# Или указать свою папку назначения
activematter-parser slice --output-dir ./my_raids

# Или нарезать конкретный файл global.json
activematter-parser slice --input path/to/global.json --output-dir ./my_raids

# Нарезать только один рейд по ID
activematter-parser slice --raid-id 7397945507
```

### 2. Посмотреть профиль игрока
```bash
activematter-parser profile
```

### 3. Посмотреть текущее снаряжение и подсумок
```bash
activematter-parser loadout
```

### 4. Список последних рейдов
```bash
activematter-parser raids --limit 10
```

---

## 🐍 Python API

```python
from activematter_parser import (
    load_global_content,
    get_player_profile,
    get_current_loadout,
    get_raids,
    slice_raids,
)

# 1. Профиль игрока
profile = get_player_profile()
print(f"Оперативник: {profile['operative_name']}, Винрейт: {profile['survival_rate_pct']}%")

# 2. Текущее снаряжение
loadout = get_current_loadout()
print(f"Костюм: {loadout['armor']['suit_name']}")
for w in loadout['weapons']:
    print(f"Оружие: {w['name']}, обвесов: {len(w['attachments'])}")

# 3. Список рейдов в Schema 2.0
raids = get_raids(limit=5)
for r in raids:
    status = "ВЫЖИЛ" if r["outcome"]["survived"] else "ПОГИБ"
    print(f"[{status}] {r['location']['full_name']} | Киллы: {r['combat']['kills_total']}")

# 4. Нарезать все рейды в файлы на диск
saved_files = slice_raids(output_dir="./sliced_raids")
print(f"Нарезано файлов: {len(saved_files)}")
```

---

## 📂 Структура репозитория

```text
active-matter-parser/
├── activematter_parser/
│   ├── __init__.py      # Экспорт публичного API
│   ├── parser.py        # Автопоиск хранилища, парсер профиля и экипировки
│   ├── slicer.py        # Нарезка рейдов по отдельным JSON 2.0 файлам
│   ├── schema_v2.py     # Нормализация структуры и логика Schema 2.0
│   └── cli.py           # Консольный интерфейс (slice, profile, loadout, raids)
├── examples/
│   └── quickstart.py    # Пример использования
├── tests/
│   ├── test_parser.py   # Модульные тесты парсера
│   └── test_slicer.py   # Модульные тесты нарезчика и Schema 2.0
├── pyproject.toml       # Метаданные сборки PEP 517/518
├── setup.py             # Обратная совместимость для pip
├── .gitignore           # Исключение кэша, venv и дампов рейдов
├── LICENSE              # Лицензия MIT
├── README.md            # Документация на английском языке
├── README_RU.md         # Документация на русском языке
└── FOR_AI.md            # Архитектурный контекст для AI-ассистентов
```

---

## 🧪 Запуск тестов

```bash
python -m unittest discover -s tests -p "test_*.py"
```

```text
Ran 20 tests in 0.022s

OK
```

---

## 📤 Публикация на GitHub

```bash
git init
git add .
git commit -m "Initial commit: Active Matter Parser & Raid Slicer (JSON 2.0)"
git branch -M main
git remote add origin https://github.com/<твой-ник>/active-matter-parser.git
git push -u origin main
```

---

## 📄 Лицензия

MIT License. См. файл [LICENSE](LICENSE).  
Active Matter является товарным знаком Gaijin Network Ltd. Проект является независимым инструментом сообщества и не аффилирован с разработчиками игры.
