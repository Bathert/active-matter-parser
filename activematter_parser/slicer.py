"""Active Matter Raid Slicer & Exporter (JSON 2.0).

Slices monolithic battleResults from global.json into individual, normalized
raid JSON files following Schema 2.0 specification.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from .parser import load_global_content, resolve_effective_uid, get_active_player_uid, find_global_json
from .schema_v2 import transform_to_schema_v2


def sanitize_filename(name: Any) -> str:
    """Sanitize raid ID or filename component to prevent path traversal and invalid Windows chars."""
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(name)).strip(' ._')
    return cleaned if cleaned else "unknown_raid"


def slice_raids(
    source: Optional[Union[str, Path, Dict[str, Any]]] = None,
    output_dir: Union[str, Path] = "./raids_v2",
    include_raw: bool = False,
    overwrite: bool = True,
    player_uid: Optional[str] = None,
) -> List[Path]:
    """Slice all raids from game storage into individual JSON 2.0 files.
    
    Args:
        source: Path to global.json, directory, or parsed dictionary.
                If None, auto-detects from local game installation.
        output_dir: Target directory to write individual raid JSON files.
        include_raw: Whether to include original raw game payload inside 'raw_game_data'.
        overwrite: Overwrite existing JSON files with matching raid IDs.
        player_uid: Player UID string for metadata enrichment.
        
    Returns:
        List of Path objects for all successfully written raid JSON files.
    """
    content = load_global_content(source)
    if not content:
        return []

    eff_uid = player_uid or resolve_effective_uid(source, content=content)
    results = content.get("battleResults", [])
    if not isinstance(results, list) or not results:
        return []

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    saved_files: List[Path] = []

    for idx, raw_raid in enumerate(results):
        if not isinstance(raw_raid, dict):
            continue

        raid_id = str(raw_raid.get("id") or f"index_{idx}")
        safe_id = sanitize_filename(raid_id)
        file_path = out_path / f"raid_{safe_id}.json"

        if file_path.exists() and not overwrite:
            saved_files.append(file_path)
            continue

        v2_data = transform_to_schema_v2(raw_raid, player_uid=eff_uid, include_raw=include_raw)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(v2_data, f, indent=2, ensure_ascii=False)

        saved_files.append(file_path)

    return saved_files


def slice_single_raid_by_id(
    raid_id: str,
    source: Optional[Union[str, Path, Dict[str, Any]]] = None,
    output_dir: Union[str, Path] = "./raids_v2",
    include_raw: bool = False,
    player_uid: Optional[str] = None,
) -> Optional[Path]:
    """Find a specific raid by ID and slice it into a single JSON 2.0 file."""
    content = load_global_content(source)
    if not content:
        return None

    eff_uid = player_uid or resolve_effective_uid(source, content=content)
    results = content.get("battleResults", [])
    if not isinstance(results, list):
        return None

    target = None
    for r in results:
        if isinstance(r, dict) and str(r.get("id")) == str(raid_id):
            target = r
            break

    if not target:
        return None

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    safe_id = sanitize_filename(raid_id)
    file_path = out_path / f"raid_{safe_id}.json"
    v2_data = transform_to_schema_v2(target, player_uid=eff_uid, include_raw=include_raw)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(v2_data, f, indent=2, ensure_ascii=False)

    return file_path
