"""Live shared planner contract with sequence-background policy."""
import json
from media.continuous_background import (CONCATENATED_FIT_TO_SHORT_MODE,FIT_PLAYBACK_RATE_MAX,FIT_PLAYBACK_RATE_MIN,MAX_SEQUENCE_CLIPS,MAX_SEQUENCE_SOURCE_SECONDS,MIN_SEQUENCE_CLIP_SECONDS,MIN_SEQUENCE_CLIPS,MIN_SEQUENCE_SOURCE_SECONDS,PREFERRED_SEQUENCE_CLIPS,PREFERRED_SEQUENCE_SOURCE_SECONDS)
from planning import planner_contract_base as base
from planning.planner_contract_base import *

MAX_REPLENISH_ATTEMPTS=5

def build_contract():
 contract=base.build_contract(); readiness=dict(contract.get("media_readiness") or {})
 readiness.pop("retired_asset_flag",None)
 readiness.update({
  "active_registry":"media-library/backgrounds.json","hard_reset_active_registry":True,"empty_registry_is_valid_replenish_state":True,
  "automatic_continuation_required":True,"replenish_is_terminal":False,"max_replenishment_attempts":MAX_REPLENISH_ATTEMPTS,
  "replenishment_session_prefix":"content/background-sourcing/review-decisions/","discovery_request_schema_version":2,
  "target_only_current_deficits":True,"exclude_previously_reviewed_provider_assets":True,"preserve_original_planner_invocation":True,
  "exhausted_error_code":"E_MEDIA_REPLENISH_EXHAUSTED","atomic_clip_minimum_seconds":MIN_SEQUENCE_CLIP_SECONDS,"normal_looping_allowed":False,
  "replenishment_manifest_is_allowed_prerequisite_commit":True,"pool_only_commit_rule_applies_after_readiness_pass":True,
  "replenishment_sequence":["audit returns REPLENISH","resume or create one stable replenishment session for the current planner invocation","create a schema-v2 targeted discovery request for current deficits excluding all provider IDs already reviewed in this session","run Background Management for deterministic discovery and visual-evidence transport","ChatGPT reviews exact-source evidence and persists immutable approve/reject decisions","ingest only approved category-matching candidates and rerun media.media_readiness","if still REPLENISH increment the same session attempt and repeat, up to 5 attempts","on PASS resume Daily or Ad-hoc ranked-pool authorship in the original planner invocation"],
  "rules":["Treat REPLENISH as resumable prerequisite state, never as the successful end of a planning invocation.","Do not end a planning invocation after an individual candidate rejection while bounded replenishment attempts remain.","Persist every visual decision so rejected/provider IDs are excluded from later attempts in the same session.","A discovery category is search provenance only; approval for a deficit requires the visually reviewed category to match the requested category.","Never weaken visual, duration, rendition, safety or readability requirements to obtain PASS.","After readiness PASS, commit only the ranked-pool JSON under the normal planner commit boundary."],
  "preview_review":{"required_before_verified_preview":True,"full_video_playback_required":False,"metadata_only_sufficient":False,"acceptable_visual_evidence":["provider_page_visual_preview","representative_preview_frames","short_preview_clip"],"review_goal":"Confirm the exact source is visually suitable and semantically matches the requested retention category; reject watermarks, embedded text, unsafe/static/weak footage or misleading metadata.","verified_preview_semantics":"verified_preview=true means ChatGPT/Work reviewed actual visual preview evidence for the exact provider source.","downstream_verification":"Background Management remains responsible for official Pexels identity, duration and rendition enrichment plus hard registry validation.","failure_rule":"Reject an individual candidate when exact-source visual evidence is unavailable or unsuitable and continue the bounded replenishment session."}
 })
 contract["media_readiness"]=readiness
 contract["background_treatment"]={"mode":CONCATENATED_FIT_TO_SHORT_MODE,"request_schema_version":contract["request_schema_version"],"planner_freezes_clip_order":True,"planner_freezes_segment_ranges":True,"planner_freezes_playback_rate":False,"runtime_derives_playback_rate_after_tts":True,"playback_rate_min":FIT_PLAYBACK_RATE_MIN,"playback_rate_max":FIT_PLAYBACK_RATE_MAX,"minimum_atomic_clip_seconds":MIN_SEQUENCE_CLIP_SECONDS,"sequence_clip_count_min":MIN_SEQUENCE_CLIPS,"sequence_clip_count_preferred":PREFERRED_SEQUENCE_CLIPS,"sequence_clip_count_max":MAX_SEQUENCE_CLIPS,"minimum_sequence_source_seconds":MIN_SEQUENCE_SOURCE_SECONDS,"preferred_sequence_source_seconds":PREFERRED_SEQUENCE_SOURCE_SECONDS,"maximum_sequence_source_seconds":MAX_SEQUENCE_SOURCE_SECONDS,"normal_looping_allowed":False,"primary_and_backup_required":True,"primary_and_backup_must_be_disjoint":True}
 return contract

def main():print(json.dumps(build_contract(),indent=2,sort_keys=True))
if __name__=="__main__":main()
