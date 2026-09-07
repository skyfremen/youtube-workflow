# CI validator for the reusable Wacky Insights media cache.
import json
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).parent
MEDIA_DIR = BASE / 'media-library'

ALLOWED_STATUS = {'active', 'inactive'}


def nonempty(value):
    return bool(str(value or '').strip())


def valid_http_url(value):
    try:
        parsed = urlparse(str(value or '').strip())
    except Exception:
        return False
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def require_bool(asset, field, label, errors, required=True):
    if field not in asset:
        if required:
            errors.append(f'{label}: missing {field}')
        return None
    value = asset.get(field)
    if not isinstance(value, bool):
        errors.append(f'{label}: {field} must be boolean')
        return None
    return value


def require_list(asset, field, label, errors):
    value = asset.get(field)
    if not isinstance(value, list):
        errors.append(f'{label}: {field} must be a list')
        return []
    return value


def validate_common(asset, idx, kind, seen_ids, seen_direct, seen_source, errors):
    label = f'{kind} asset {idx}'
    if not isinstance(asset, dict):
        errors.append(f'{label}: must be an object')
        return None

    required = ('id', 'type', 'title', 'direct_url', 'source_page', 'source', 'license', 'status')
    for field in required:
        if not nonempty(asset.get(field)):
            errors.append(f'{label}: missing/non-empty {field}')

    asset_id = str(asset.get('id', '')).strip()
    direct = str(asset.get('direct_url', '')).strip()
    source_page = str(asset.get('source_page', '')).strip()

    if asset_id:
        if asset_id in seen_ids:
            errors.append(f'{label}: duplicate id {asset_id}')
        seen_ids.add(asset_id)
    if direct:
        if direct in seen_direct:
            errors.append(f'{label}: duplicate direct_url {direct}')
        seen_direct.add(direct)
        if not valid_http_url(direct):
            errors.append(f'{label}: direct_url must be http(s)')
    if source_page:
        if source_page in seen_source:
            errors.append(f'{label}: duplicate source_page {source_page}')
        seen_source.add(source_page)
        if not valid_http_url(source_page):
            errors.append(f'{label}: source_page must be http(s)')

    expected_type = 'video' if kind == 'background' else 'music'
    if asset.get('type') != expected_type:
        errors.append(f'{label}: type must be {expected_type!r}')

    status = asset.get('status')
    if status not in ALLOWED_STATUS:
        errors.append(f'{label}: status must be one of {sorted(ALLOWED_STATUS)}')

    verified = require_bool(asset, 'verified', label, errors)
    require_bool(asset, 'commercial_use', label, errors)
    require_bool(asset, 'attribution_required', label, errors)

    if verified is True and not nonempty(asset.get('last_verified_at')):
        errors.append(f'{label}: verified=true requires last_verified_at')
    if status == 'active' and verified is not True:
        errors.append(f'{label}: active assets must have verified=true')

    usage_count = asset.get('usage_count')
    if isinstance(usage_count, bool) or not isinstance(usage_count, int) or usage_count < 0:
        errors.append(f'{label}: usage_count must be an integer >= 0')

    plan_ready = asset.get('plan_ready', False)
    if not isinstance(plan_ready, bool):
        errors.append(f'{label}: plan_ready must be boolean when present')
        plan_ready = False
    if plan_ready and (verified is not True or status != 'active'):
        errors.append(f'{label}: plan_ready=true requires verified=true and status=active')

    return label, plan_ready


def validate_backgrounds(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    errors = []
    if not isinstance(data, dict):
        raise SystemExit('Background library root must be an object.')
    if not isinstance(data.get('schema_version'), int):
        errors.append('background library: schema_version must be an integer')
    assets = data.get('assets')
    if not isinstance(assets, list) or not assets:
        errors.append('background library: assets must be a non-empty list')
        assets = []

    seen_ids, seen_direct, seen_source = set(), set(), set()
    ready = 0
    for idx, asset in enumerate(assets, 1):
        result = validate_common(asset, idx, 'background', seen_ids, seen_direct, seen_source, errors)
        if result is None:
            continue
        label, plan_ready = result
        for field in ('scene_tags', 'categories', 'actions', 'setting', 'people_context', 'time_context',
                      'visual_tone', 'camera_style', 'usable_for_hooks', 'avoid_for'):
            require_list(asset, field, label, errors)
        if not nonempty(asset.get('semantic_description')):
            errors.append(f'{label}: semantic_description is required')

        if plan_ready:
            ready += 1
            for field in ('creator', 'direct_url', 'source_page', 'license', 'semantic_description'):
                if not nonempty(asset.get(field)):
                    errors.append(f'{label}: plan_ready=true requires {field}')

    if errors:
        raise SystemExit('Background media library validation failed:\n- ' + '\n- '.join(errors))
    return len(assets), ready


def validate_music(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    errors = []
    if not isinstance(data, dict):
        raise SystemExit('Music library root must be an object.')
    if not isinstance(data.get('schema_version'), int):
        errors.append('music library: schema_version must be an integer')
    assets = data.get('assets')
    if not isinstance(assets, list) or not assets:
        errors.append('music library: assets must be a non-empty list')
        assets = []

    seen_ids, seen_direct, seen_source = set(), set(), set()
    ready = 0
    for idx, asset in enumerate(assets, 1):
        result = validate_common(asset, idx, 'music', seen_ids, seen_direct, seen_source, errors)
        if result is None:
            continue
        label, plan_ready = result
        for field in ('mood_tags', 'suitable_for', 'suitable_for_mechanisms', 'suitable_for_scenes', 'avoid_for'):
            require_list(asset, field, label, errors)
        for field in ('monetization_allowed', 'content_id_safe', 'instrumental', 'has_vocals'):
            require_bool(asset, field, label, errors)
        if not nonempty(asset.get('artist')):
            errors.append(f'{label}: artist is required')
        if not nonempty(asset.get('semantic_description')):
            errors.append(f'{label}: semantic_description is required')

        if plan_ready:
            ready += 1
            for field in ('artist', 'direct_url', 'source_page', 'license', 'semantic_description'):
                if not nonempty(asset.get(field)):
                    errors.append(f'{label}: plan_ready=true requires {field}')

    if errors:
        raise SystemExit('Music media library validation failed:\n- ' + '\n- '.join(errors))
    return len(assets), ready


def main():
    bg_count, bg_ready = validate_backgrounds(MEDIA_DIR / 'backgrounds.json')
    music_count, music_ready = validate_music(MEDIA_DIR / 'music.json')
    print(
        f'Media libraries valid: {bg_count} backgrounds ({bg_ready} explicit plan_ready), '
        f'{music_count} music tracks ({music_ready} explicit plan_ready). '
        'Assets without plan_ready are conservatively treated as not immediately reusable.'
    )


if __name__ == '__main__':
    main()
