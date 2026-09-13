"""Resilient ingestion for reviewed Pexels readiness manifests.

A readiness manifest may intentionally contain reserve candidates. Each reviewed
candidate is tried in manifest order. Source/rendition failures are reported and
skipped so later reserves can still satisfy shared media readiness in the same run.
Identity collisions remain hard failures because they indicate immutable-state
ambiguity rather than an unsuitable media candidate.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from media import pexels_registry
from media.replenishment_state import DECISIONS_ROOT, validate_manifest_against_decisions


HARD_FAILURE_MARKERS = (
    "Background sourcing identity collision",
    "logical_id must be",
    "duplicate logical_id",
    "duplicate provider_asset_id",
)
RECOVERABLE_CANDIDATE_ERRORS = (OSError, RuntimeError, ValueError)


def _single_candidate_manifest(manifest, candidate):
    result = {
        "schema_version": manifest["schema_version"],
        "plan_date": manifest["plan_date"],
        "provider": manifest["provider"],
        "candidates": [candidate],
    }
    if manifest["schema_version"] == 2:
        result.update({
            "replenishment_session_id": manifest["replenishment_session_id"],
            "planner_invocation": manifest["planner_invocation"],
            "attempt": manifest["attempt"],
            "discovery_request_id": manifest["discovery_request_id"],
            "review_decision_ids": [candidate["review_decision_id"]],
        })
    return result


def ingest_resilient(
    manifest_path,
    registry_path=pexels_registry.REGISTRY_PATH,
    key=None,
    review_decisions_root=DECISIONS_ROOT,
):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = pexels_registry.validate_sourcing_manifest(manifest)
    if errors:
        raise ValueError("Background sourcing manifest invalid:\n- " + "\n- ".join(errors))
    if manifest["schema_version"] == 2:
        decisions = []
        for path in sorted(Path(review_decisions_root).glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("replenishment_session_id") == manifest["replenishment_session_id"]:
                decisions.append(document)
        binding_errors = validate_manifest_against_decisions(manifest, decisions)
        if binding_errors:
            raise ValueError(
                "Background sourcing manifest review binding invalid:\n- "
                + "\n- ".join(binding_errors)
            )

    added = []
    cached = []
    rejected = []

    for candidate in manifest["candidates"]:
        logical_id = str(candidate.get("logical_id") or "")
        provider_id = str(candidate.get("provider_asset_id") or "")
        payload = _single_candidate_manifest(manifest, candidate)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            candidate_manifest = Path(handle.name)
        try:
            result = pexels_registry.ingest_manifest(
                candidate_manifest,
                path=Path(registry_path),
                key=key,
            )
        except RECOVERABLE_CANDIDATE_ERRORS as exc:
            message = str(exc)
            if any(marker in message for marker in HARD_FAILURE_MARKERS):
                raise
            rejected.append(
                {
                    "logical_id": logical_id,
                    "provider_asset_id": provider_id,
                    "error": message or type(exc).__name__,
                }
            )
        else:
            added.extend(result.get("added", []))
            cached.extend(result.get("already_cached", []))
        finally:
            candidate_manifest.unlink(missing_ok=True)

    return {
        "manifest": str(manifest_path),
        "candidate_count": len(manifest["candidates"]),
        "accepted_count": len(added) + len(cached),
        "added": added,
        "already_cached": cached,
        "rejected_count": len(rejected),
        "rejected": rejected,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Ingest reviewed Pexels readiness candidates with reserve fallback"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--registry", default=str(pexels_registry.REGISTRY_PATH))
    parser.add_argument("--review-decisions-root", default=str(DECISIONS_ROOT))
    args = parser.parse_args()

    try:
        result = ingest_resilient(
            args.manifest,
            args.registry,
            review_decisions_root=args.review_decisions_root,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc))
        raise SystemExit(1)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
