"""Private background selector with canonical successful-receipt semantics.

The retention-first ranking implementation is retained in background_selector_base.
This wrapper fixes production-history classification so current immediate-public
Ad-hoc receipts contribute to the same private anti-repetition history as scheduled
successes.
"""

from media import background_selector_base as base
from media.background_selector_base import *  # re-export selector API


def is_successful_receipt(record):
    if not (
        isinstance(record, dict)
        and record.get("background_asset_id")
        and record.get("verification", {}).get("passed") is True
    ):
        return False
    state = record.get("verification_state")
    if state in {"verified_public", "verified_immediate_public"}:
        return bool(
            record.get("privacy_status") == "public"
            and (
                record.get("publish_at_absent") is True
                or (
                    record.get("publication_mode") == "immediate"
                    and record.get("publish_at") is None
                )
            )
        )
    if state == "verified_private":
        return bool(
            record.get("privacy_status") == "private"
            and record.get("publish_at_absent") is True
        )
    if state in {"verified_scheduled", "verified_scheduled_published"}:
        return bool(
            record.get("publication_mode") == "scheduled"
            and record.get("publish_at")
            and record.get("privacy_status") in {"private", "public"}
        )
    return False


# Existing selector helpers resolve this symbol through their defining module's
# globals, so update that one hook rather than duplicating ranking/history logic.
base.is_successful_receipt = is_successful_receipt


if __name__ == "__main__":
    base.main()
