"""Shared deterministic planner contract used by Daily and Ad-hoc.

This module is intentionally upstream of private promotion. Planner-time validation
must never import production workflow/publishing modules. Production promotion may
import this module, but not vice versa.
"""
from __future__ import annotations

import copy
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from common.workflow_common import CONTENT_ID_RE
from planning.planner_profiles import ADHOC, DAILY, PlannerProfile
from planning.planning_config import TITLE_WEIGHTS
from validation.publication import validate_upload_contract
from validation.validate_content import SCHEMA_VERSION, validate_request_data

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "youtube-shorts-bot"
POOL_SCHEMA_VERSION = 1
CANDIDATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
DAILY_POOL_RE = re.compile(
    r"^youtube-shorts-bot/content/planning-pools/daily/"
    r"(\d{4}-\d{2}-\d{2})/(dp-[A-Za-z0-9-]{8,96})\.json$"
)
ADHOC_POOL_RE = re.compile(
    r"^youtube-shorts-bot/content/planning-pools/adhoc/(ap-[A-Za-z0-9-]{8,96})\.json$"
)
CATCH_UP_MIN_LEAD_MINUTES = 30
SGT = ZoneInfo("Asia/Singapore")


class PlannerContractError(RuntimeError):
    pass


def fail(message):
    raise PlannerContractError(message)


def parse_date(raw, label):
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        fail(f"{label} must be YYYY-MM-DD")


def parse_slot(raw, plan_date):
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        fail(f"invalid publication slot {raw!r}")
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        fail("daily publication slots must be UTC timestamps")
    local = parsed.astimezone(SGT)
    if local.date().isoformat() != plan_date:
        fail("daily publication slot must fall on the plan date in Asia/Singapore")
    if any((local.minute, local.second, local.microsecond)):
        fail("daily publication slots must be exact top-of-hour timestamps")
    return parsed


def canonical_normal_slots(plan_date):
    local_midnight = datetime.fromisoformat(plan_date).replace(tzinfo=SGT)
    return [
        local_midnight.replace(hour=hour)
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
        for hour in range(24)
    ]


def validate_ranked_candidates(pool, expected_count):
    candidates = pool.get("ranked_candidates")
    if not isinstance(candidates, list) or len(candidates) != expected_count:
        fail(f"ranked_candidates must contain exactly {expected_count} candidates")
    candidate_ids = []
    content_ids = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict) or set(item) != {"rank", "candidate_id", "request"}:
            fail("each ranked candidate must contain exactly rank, candidate_id and request")
        if item.get("rank") != index:
            fail("candidate ranks must be contiguous and start at 1")
        candidate_id = item.get("candidate_id")
        if not isinstance(candidate_id, str) or not CANDIDATE_ID_RE.fullmatch(candidate_id):
            fail(f"candidate rank {index} has invalid candidate_id")
        request = item.get("request")
        if not isinstance(request, dict):
            fail(f"candidate rank {index} request must be an object")
        content_id = request.get("content_id")
        if not isinstance(content_id, str) or not CONTENT_ID_RE.fullmatch(content_id):
            fail(f"candidate rank {index} request has invalid content_id")
        candidate_ids.append(candidate_id)
        content_ids.append(content_id)
    if len(candidate_ids) != len(set(candidate_ids)):
        fail("ranked candidate IDs must be unique")
    if len(content_ids) != len(set(content_ids)):
        fail("ranked candidate request content IDs must be unique")
    return candidates, candidate_ids


def validate_planning_execution(pool, candidate_ids, rules_source_sha):
    execution = pool.get("planning_execution")
    expected_keys = {
        "editorial_selection_owner",
        "planning_method",
        "rules_source_sha",
        "ranked_candidate_ids",
    }
    errors = []
    if not isinstance(execution, dict) or set(execution) != expected_keys:
        return ["planning_execution must contain ranked-pool ChatGPT provenance"]
    if execution.get("editorial_selection_owner") != "chatgpt":
        errors.append("ranked planning requires editorial_selection_owner=chatgpt")
    if execution.get("planning_method") != "chatgpt_ranked_pool":
        errors.append("ranked planning requires planning_method=chatgpt_ranked_pool")
    if execution.get("rules_source_sha") != rules_source_sha:
        errors.append(
            "planning_execution.rules_source_sha must equal the exact "
            "rules_source_sha supplied to the validator"
        )
    if execution.get("ranked_candidate_ids") != candidate_ids:
        errors.append(
            "planning_execution.ranked_candidate_ids must exactly match frozen rank order"
        )
    if not HEX40_RE.fullmatch(str(rules_source_sha or "")):
        errors.append("rules_source_sha must be a lowercase full 40-character commit SHA")
    return errors


def title_component_key_errors(request):
    errors = []
    planning = request.get("planning")
    titles = planning.get("title_candidates") if isinstance(planning, dict) else None
    if not isinstance(titles, list):
        return errors
    expected = set(TITLE_WEIGHTS)
    for index, item in enumerate(titles):
        components = item.get("score_components") if isinstance(item, dict) else None
        if not isinstance(components, dict):
            continue
        actual = set(components)
        if actual == expected:
            continue
        errors.append(
            f"planning.title_candidates[{index}].score_components keys mismatch; "
            f"missing={sorted(expected - actual)}; unexpected={sorted(actual - expected)}"
        )
    return errors


def candidate_errors(
    request,
    *,
    registry,
    request_path,
    profile: PlannerProfile,
    publish_at_override=None,
):
    """Validate one frozen candidate without mutating the authored request."""
    content_id = str(request.get("content_id", ""))
    errors = []
    if not CONTENT_ID_RE.fullmatch(content_id):
        errors.append(f"content_id must match canonical pattern {CONTENT_ID_RE.pattern}")
    if profile is ADHOC and "-adhoc-" not in content_id.lower():
        errors.append("Ad-hoc content_id must contain -adhoc-")
    if request.get("publication") != profile.publication_template:
        errors.append(
            f"{profile.name} publication must exactly equal its canonical planner template"
        )
    errors.extend(title_component_key_errors(request))

    candidate = copy.deepcopy(request)
    if publish_at_override is not None:
        candidate["publication"]["publish_at"] = publish_at_override
    errors.extend(
        validate_request_data(
            candidate,
            request_path=request_path,
            enforce_registry=True,
            registry=registry,
        )
    )
    if candidate.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"new production request must use schema-v{SCHEMA_VERSION}")
    if not errors:
        try:
            validate_upload_contract(candidate, require_future=False)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"final publication payload is invalid: {exc}")
    return list(dict.fromkeys(errors))


def scheduled_adhoc_matches(singapore_date, *, exclude_content_id=None):
    prefix = f"wd-{singapore_date.replace('-', '')}T010000-adhoc-"
    request_dir = BOT_ROOT / "content" / "requests"
    matches = []
    if request_dir.is_dir():
        for path in request_dir.glob(f"{prefix}*.json"):
            if exclude_content_id and path.stem == exclude_content_id:
                continue
            matches.append(path)
    return sorted(matches)


def validate_daily_slots(mode, target, slots, plan_date, *, now_utc=None):
    errors = []
    parsed_slots = []
    if (
        not isinstance(slots, list)
        or target is None
        or len(slots) != target
        or len(slots) != len(set(slots))
    ):
        return [], ["publication_slots must contain exactly target_count unique slots"]
    for raw in slots:
        try:
            parsed_slots.append(parse_slot(raw, plan_date))
        except PlannerContractError as exc:
            errors.append(str(exc))
    if len(parsed_slots) != len(slots):
        return parsed_slots, errors
    if parsed_slots != sorted(parsed_slots):
        errors.append("publication_slots must be chronological")
    if mode == DAILY.normal_mode and slots != canonical_normal_slots(plan_date):
        errors.append("normal_next_day publication_slots must be the canonical 24 hourly slots")
    if mode == "same_day_catch_up":
        current = now_utc or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        threshold = current.astimezone(timezone.utc) + timedelta(
            minutes=CATCH_UP_MIN_LEAD_MINUTES
        )
        if any(slot < threshold for slot in parsed_slots):
            errors.append(
                "same_day_catch_up publication slots must remain at least "
                f"{CATCH_UP_MIN_LEAD_MINUTES} minutes in the future"
            )
    return parsed_slots, errors
