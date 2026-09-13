"""Shared long-form background policy for new Wacky Dramas production."""

FIT_TO_SHORT_MODE = "fit_to_short"
FIT_PLAYBACK_RATE_MIN = 1.0
FIT_PLAYBACK_RATE_MAX = 2.5

# New sources should be long enough to cover a full normal Short without looping.
# 180s covers the 175s target at ~1.03x, while the preferred 300s window maps
# cleanly across the 120-175s production target at ~1.71-2.50x.
MIN_CONTINUOUS_SOURCE_SECONDS = 180.0
PREFERRED_CONTINUOUS_RANGE_SECONDS = 300.0
DURATION_EPSILON_SECONDS = 0.05


def trusted_duration_seconds(asset):
    try:
        value = float(asset.get("duration_seconds"))
    except (AttributeError, TypeError, ValueError):
        return None
    return value if value > 0 else None


def continuous_source_eligible(asset):
    duration = trusted_duration_seconds(asset)
    return duration is not None and duration + DURATION_EPSILON_SECONDS >= MIN_CONTINUOUS_SOURCE_SECONDS


def preferred_range_duration(asset):
    duration = trusted_duration_seconds(asset)
    if duration is None or duration + DURATION_EPSILON_SECONDS < MIN_CONTINUOUS_SOURCE_SECONDS:
        raise ValueError("background source duration is insufficient for continuous fit-to-short")
    return round(min(duration, PREFERRED_CONTINUOUS_RANGE_SECONDS), 3)


def derived_playback_rate(source_range_seconds, output_seconds):
    source = float(source_range_seconds)
    output = float(output_seconds)
    if source <= 0 or output <= 0:
        raise ValueError("source/output durations must be positive")
    rate = source / output
    if not FIT_PLAYBACK_RATE_MIN - 1e-9 <= rate <= FIT_PLAYBACK_RATE_MAX + 1e-9:
        raise ValueError(
            f"derived playback rate {rate:.6f}x is outside "
            f"{FIT_PLAYBACK_RATE_MIN:.2f}-{FIT_PLAYBACK_RATE_MAX:.2f}x"
        )
    return rate
