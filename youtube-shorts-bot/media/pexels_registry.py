"""Pexels registry facade enforcing long continuous-source eligibility."""
from media import pexels_registry_base as base
from media.pexels_registry_base import *
from media.continuous_background import (
    MIN_CONTINUOUS_SOURCE_SECONDS,
    continuous_source_eligible,
)

_original_build_asset = base._build_asset
_original_register_video = base.register_video
_original_ingest_manifest = base.ingest_manifest
_original_enrich_existing = base.enrich_existing
_original_search = base.search


def _build_asset(logical_id, video_id, metadata, video, retrieved_at):
    asset = _original_build_asset(logical_id, video_id, metadata, video, retrieved_at)
    if not continuous_source_eligible(asset):
        raise ValueError(
            f"Pexels video {video_id} duration {asset.get('duration_seconds')}s is below "
            f"the continuous-source minimum {MIN_CONTINUOUS_SOURCE_SECONDS:.0f}s"
        )
    return asset


def _sync_base_overrides():
    # Preserve the established patchable facade used by tests and callers while
    # retaining the long-source gate in the shared builder.
    base.api_get = globals()["api_get"]
    base._build_asset = _build_asset


def register_video(*args, **kwargs):
    _sync_base_overrides()
    return _original_register_video(*args, **kwargs)


def ingest_manifest(*args, **kwargs):
    _sync_base_overrides()
    return _original_ingest_manifest(*args, **kwargs)


def enrich_existing(*args, **kwargs):
    _sync_base_overrides()
    return _original_enrich_existing(*args, **kwargs)


def search(*args, **kwargs):
    _sync_base_overrides()
    return _original_search(*args, **kwargs)


base._build_asset = _build_asset


if __name__ == "__main__":
    _sync_base_overrides()
    base.main()
