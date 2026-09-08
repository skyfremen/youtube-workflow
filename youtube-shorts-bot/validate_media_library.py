import json
import re
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).parent
REGISTRY_PATH = BASE / "media-library" / "backgrounds.json"
ID_RE = re.compile(r"^satisfying-\d{3}$")
ALLOWED_STATUS = {"active", "inactive"}
ALLOWED_INTENSITY = {"low", "medium", "high"}
ALLOWED_ORIENTATION = {"vertical", "horizontal", "square", "unknown"}


def _url(value):
    try:
        parsed = urlparse(str(value or "").strip())
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _score(value, field, label, errors):
    if isinstance(value, bool):
        errors.append(f"{label}: {field} must be numeric")
        return
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label}: {field} must be numeric")
        return
    if not 0 <= number <= 100:
        errors.append(f"{label}: {field} must be between 0 and 100")


def validate_registry_data(data):
    errors = []
    if not isinstance(data, dict):
        return ["background registry root must be an object"]
    if data.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        return errors + ["assets must be a non-empty list"]

    seen_ids, seen_direct = set(), set()
    for idx, asset in enumerate(assets, 1):
        label = f"asset {idx}"
        if not isinstance(asset, dict):
            errors.append(f"{label}: must be an object")
            continue
        required = (
            "id", "type", "title", "source", "source_page", "direct_url", "license",
            "commercial_use", "attribution_required", "verified", "last_verified_at",
            "status", "orientation", "visual_tags", "motion_type", "motion_intensity",
            "loopability_score", "visual_satisfaction_score", "caption_readability_score",
            "has_embedded_text", "has_watermark",
        )
        missing = [k for k in required if k not in asset]
        if missing:
            errors.append(f"{label}: missing fields: {', '.join(missing)}")
            continue
        asset_id = str(asset["id"]).strip()
        if not ID_RE.fullmatch(asset_id):
            errors.append(f"{label}: id must match satisfying-NNN")
        elif asset_id in seen_ids:
            errors.append(f"{label}: duplicate id {asset_id}")
        seen_ids.add(asset_id)
        if asset.get("type") != "video":
            errors.append(f"{label}: type must be video")
        for key in ("title", "source", "license", "last_verified_at", "motion_type"):
            if not str(asset.get(key, "")).strip():
                errors.append(f"{label}: {key} must be non-empty")
        for key in ("source_page", "direct_url"):
            if not _url(asset.get(key)):
                errors.append(f"{label}: {key} must be an http(s) URL")
        direct = str(asset.get("direct_url", "")).strip()
        if direct:
            if direct in seen_direct:
                errors.append(f"{label}: duplicate direct_url {direct}")
            seen_direct.add(direct)
        for key in (
            "commercial_use", "attribution_required", "verified",
            "has_embedded_text", "has_watermark",
        ):
            if not isinstance(asset.get(key), bool):
                errors.append(f"{label}: {key} must be boolean")
        if asset.get("status") not in ALLOWED_STATUS:
            errors.append(f"{label}: invalid status")
        if asset.get("orientation") not in ALLOWED_ORIENTATION:
            errors.append(f"{label}: invalid orientation")
        if asset.get("motion_intensity") not in ALLOWED_INTENSITY:
            errors.append(f"{label}: invalid motion_intensity")
        if not isinstance(asset.get("visual_tags"), list) or not asset["visual_tags"]:
            errors.append(f"{label}: visual_tags must be a non-empty list")
        for field in (
            "loopability_score", "visual_satisfaction_score", "caption_readability_score"
        ):
            _score(asset.get(field), field, label, errors)
        for field in ("width", "height"):
            if field in asset and asset[field] is not None:
                if isinstance(asset[field], bool) or not isinstance(asset[field], int) or asset[field] <= 0:
                    errors.append(f"{label}: {field} must be a positive integer when present")
        if "duration_seconds" in asset and asset["duration_seconds"] is not None:
            try:
                if float(asset["duration_seconds"]) <= 0:
                    errors.append(f"{label}: duration_seconds must be positive when present")
            except (TypeError, ValueError):
                errors.append(f"{label}: duration_seconds must be numeric when present")
        if any(k in asset for k in ("usage_count", "last_used_at", "last_used_short_id")):
            errors.append(f"{label}: usage history belongs in result receipts, not the registry")
        if asset.get("status") == "active":
            if asset.get("verified") is not True:
                errors.append(f"{label}: active assets must be verified")
            if asset.get("commercial_use") is not True:
                errors.append(f"{label}: active assets must allow commercial use")
            if asset.get("has_watermark") is not False:
                errors.append(f"{label}: active assets may not have a watermark")
            if asset.get("has_embedded_text") is not False:
                errors.append(f"{label}: active assets may not have embedded text")
    return errors


def load_registry(path=REGISTRY_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_registry_data(data)
    if errors:
        raise ValueError("Background registry validation failed:\n- " + "\n- ".join(errors))
    return data


def asset_map(data):
    return {asset["id"]: asset for asset in data["assets"]}


def validate_request_backgrounds(request_data, registry_data):
    mapping = asset_map(registry_data)
    visual = request_data["visual"]
    primary = visual["background_primary_id"]
    backup = visual["background_backup_id"]
    if primary == backup:
        raise ValueError("Primary and backup background IDs must differ")
    missing = [x for x in (primary, backup) if x not in mapping]
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
    active = sum(1 for x in data["assets"] if x.get("status") == "active")
    print(f"Satisfying background registry valid: {len(data['assets'])} assets, {active} active.")


if __name__ == "__main__":
    main()
