"""Active background-registry validator.

The active registry may be empty after a hard reset. Soft-retired entries are not
permitted: historical definitions live only in the separate legacy recovery snapshot.
"""
import json
from pathlib import Path

from media import validate_media_library_v3 as legacy
from media.validate_media_library_v3 import *

REGISTRY_PATH = legacy.REGISTRY_PATH


def validate_registry_data(data):
    errors = legacy.validate_registry_data(data)
    if isinstance(data, dict) and isinstance(data.get("assets"), list):
        for index, asset in enumerate(data["assets"], 1):
            if isinstance(asset, dict) and "selection_enabled" in asset:
                errors.append(f"asset {index}: selection_enabled is obsolete in the active registry")
    return errors


def load_registry(path=REGISTRY_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_registry_data(data)
    if errors:
        raise ValueError("Background registry validation failed:\n- " + "\n- ".join(errors))
    return data


def asset_map(data):
    return {asset["id"]: asset for asset in data.get("assets", [])}


def validate_request_backgrounds(request_data, registry_data):
    mapping = asset_map(registry_data)
    visual = request_data["visual"]
    primary = visual["background_primary_id"]
    backup = visual["background_backup_id"]
    if primary == backup:
        raise ValueError("Primary and backup background IDs must differ")
    missing = [value for value in (primary, backup) if value not in mapping]
    if missing:
        raise ValueError("Unknown background IDs: " + ", ".join(missing))
    for asset_id in (primary, backup):
        asset = mapping[asset_id]
        if asset.get("status") != "active" or asset.get("verified") is not True:
            raise ValueError(f"Background {asset_id} must be active and verified")
    return mapping[primary], mapping[backup]


def main():
    try:
        data = load_registry()
    except ValueError as exc:
        raise SystemExit(str(exc))
    active = sum(1 for item in data["assets"] if item.get("status") == "active")
    print(f"Active background registry valid: {len(data['assets'])} assets, {active} active.")


if __name__ == "__main__":
    main()
