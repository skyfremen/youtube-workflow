"""Pexels registry facade enforcing long continuous-source eligibility."""
from media import pexels_registry_base as base
from media.pexels_registry_base import *
from media.continuous_background import MIN_CONTINUOUS_SOURCE_SECONDS, continuous_source_eligible

_original_build_asset = base._build_asset


def _build_asset(logical_id, video_id, metadata, video, retrieved_at):
    asset = _original_build_asset(logical_id, video_id, metadata, video, retrieved_at)
    if not continuous_source_eligible(asset):
        raise ValueError(
            f"Pexels video {video_id} duration {asset.get('duration_seconds')}s is below "
            f"the continuous-source minimum {MIN_CONTINUOUS_SOURCE_SECONDS:.0f}s"
        )
    return asset


base._build_asset = _build_asset


if __name__ == "__main__":
    base.main()
