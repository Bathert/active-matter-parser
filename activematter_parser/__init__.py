"""Active Matter Data Parser & Raid Slicer (Schema 2.0).

Pure Python library for reading Active Matter local storage, extracting operative profiles,
equipped loadouts, and slicing battleResults into individual normalized JSON 2.0 files.

Zero external dependencies. 100% passive, file-based, BattlEye safe.
"""

__version__ = "2.0.0"
__author__ = "Active Matter Community"
__license__ = "MIT"

from .parser import (
    get_online_storage_root,
    get_active_player_uid,
    resolve_effective_uid,
    find_global_json,
    load_global_content,
    get_player_profile,
    get_current_loadout,
    get_raids,
    get_raid_history,
    get_player_career_summary,
    format_epoch_dt,
)

from .schema_v2 import (
    transform_to_schema_v2,
    prettify_item_name,
    categorize_template,
    parse_location_info,
)

from .slicer import (
    slice_raids,
    slice_single_raid_by_id,
    sanitize_filename,
)

__all__ = [
    "get_online_storage_root",
    "get_active_player_uid",
    "resolve_effective_uid",
    "find_global_json",
    "load_global_content",
    "get_player_profile",
    "get_current_loadout",
    "get_raids",
    "get_raid_history",
    "get_player_career_summary",
    "format_epoch_dt",
    "transform_to_schema_v2",
    "prettify_item_name",
    "categorize_template",
    "parse_location_info",
    "slice_raids",
    "slice_single_raid_by_id",
    "sanitize_filename",
]
