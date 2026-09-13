"""Shared background timing policy for Wacky Dramas production.

Schema v6 retains the original one-long-source ``fit_to_short`` contract for
immutable recovery. New schema-v7 production composes two or three distinct
atomic clips once, then derives one playback rate for the concatenated sequence
after exact narration/render duration is known.
"""

FIT_TO_SHORT_MODE = "fit_to_short"
CONCATENATED_FIT_TO_SHORT_MODE = "concatenated_fit_to_short"
FIT_PLAYBACK_RATE_MIN = 1.0
FIT_PLAYBACK_RATE_MAX = 2.5

# Historical schema-v6 single-source policy. Keep these values stable so old
# immutable requests remain executable exactly as authored.
MIN_CONTINUOUS_SOURCE_SECONDS = 180.0
PREFERRED_CONTINUOUS_RANGE_SECONDS = 300.0

# Schema-v7 atomic/sequence policy. Pexels clips are reusable atomic assets; the
# immutable request freezes 2-3 distinct ranges whose total coverage is consumed
# once. No source is repeated to fill time.
MIN_SEQUENCE_CLIP_SECONDS = 60.0
MIN_SEQUENCE_CLIPS = 2
MAX_SEQUENCE_CLIPS = 3
PREFERRED_SEQUENCE_CLIPS = 3
MIN_SEQUENCE_SOURCE_SECONDS = 210.0
PREFERRED_SEQUENCE_SOURCE_SECONDS = 240.0
MAX_SEQUENCE_SOURCE_SECONDS = 300.0
DURATION_EPSILON_SECONDS = 0.05


def trusted_duration_seconds(asset):
    try:
        value = float(asset.get("duration_seconds"))
    except (AttributeError, TypeError, ValueError):
        return None
    return value if value > 0 else None


def continuous_source_eligible(asset):
    """Historical schema-v6 single-source eligibility."""
    duration = trusted_duration_seconds(asset)
    return duration is not None and duration + DURATION_EPSILON_SECONDS >= MIN_CONTINUOUS_SOURCE_SECONDS


def sequence_clip_eligible(asset):
    """Return whether an atomic registry asset can participate in a v7 sequence."""
    duration = trusted_duration_seconds(asset)
    return duration is not None and duration + DURATION_EPSILON_SECONDS >= MIN_SEQUENCE_CLIP_SECONDS


def preferred_range_duration(asset):
    """Historical schema-v6 preferred range helper."""
    duration = trusted_duration_seconds(asset)
    if duration is None or duration + DURATION_EPSILON_SECONDS < MIN_CONTINUOUS_SOURCE_SECONDS:
        raise ValueError("background source duration is insufficient for continuous fit-to-short")
    return round(min(duration, PREFERRED_CONTINUOUS_RANGE_SECONDS), 3)


def sequence_total_duration(segments):
    total = 0.0
    for segment in segments or []:
        try:
            duration = float(segment.get("segment_duration_seconds"))
        except (AttributeError, TypeError, ValueError):
            raise ValueError("sequence segment duration must be numeric") from None
        if duration <= 0:
            raise ValueError("sequence segment duration must be positive")
        total += duration
    return total


def sequence_source_duration_eligible(total_seconds):
    try:
        total = float(total_seconds)
    except (TypeError, ValueError):
        return False
    return (
        MIN_SEQUENCE_SOURCE_SECONDS - DURATION_EPSILON_SECONDS
        <= total
        <= MAX_SEQUENCE_SOURCE_SECONDS + DURATION_EPSILON_SECONDS
    )


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


def derived_sequence_playback_rate(segments, output_seconds):
    """Derive one no-loop playback rate for the complete frozen v7 sequence."""
    total = sequence_total_duration(segments)
    if not sequence_source_duration_eligible(total):
        raise ValueError(
            f"sequence source duration {total:.3f}s is outside "
            f"{MIN_SEQUENCE_SOURCE_SECONDS:.0f}-{MAX_SEQUENCE_SOURCE_SECONDS:.0f}s"
        )
    return derived_playback_rate(total, output_seconds)
