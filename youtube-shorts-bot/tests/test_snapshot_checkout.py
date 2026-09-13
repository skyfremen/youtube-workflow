import hashlib
import json
import subprocess

from planning import ranked_promotion
from planning.snapshot_checkout import bootstrap_snapshot
from planning.snapshot_precommit import _git_blob_sha, verify_snapshot_manifest


SOURCE_SHA = "1" * 40


def _blob_sha(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def test_git_blob_sha_matches_git_object_format():
    data = b"planner rules\n"
    assert _git_blob_sha(data) == _blob_sha(data)


def test_snapshot_manifest_verifies_materialized_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(ranked_promotion, "REPO_ROOT", tmp_path)
    path = tmp_path / "youtube-shorts-bot" / "planning" / "rule.txt"
    path.parent.mkdir(parents=True)
    data = b"same immutable bytes\n"
    path.write_bytes(data)
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha": SOURCE_SHA,
                "files": [
                    {
                        "path": "youtube-shorts-bot/planning/rule.txt",
                        "blob_sha": _blob_sha(data),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert verify_snapshot_manifest(manifest, SOURCE_SHA) == []


def test_snapshot_manifest_fails_when_materialized_bytes_change(tmp_path, monkeypatch):
    monkeypatch.setattr(ranked_promotion, "REPO_ROOT", tmp_path)
    path = tmp_path / "rule.txt"
    original = b"original\n"
    path.write_bytes(b"changed\n")
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha": SOURCE_SHA,
                "files": [{"path": "rule.txt", "blob_sha": _blob_sha(original)}],
            }
        ),
        encoding="utf-8",
    )
    errors = verify_snapshot_manifest(manifest, SOURCE_SHA)
    assert any("snapshot blob mismatch" in error for error in errors)


def test_bootstrap_makes_rev_parse_head_equal_source_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(ranked_promotion, "REPO_ROOT", tmp_path)
    path = tmp_path / "rule.txt"
    data = b"verified\n"
    path.write_bytes(data)
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha": SOURCE_SHA,
                "files": [{"path": "rule.txt", "blob_sha": _blob_sha(data)}],
            }
        ),
        encoding="utf-8",
    )

    result = bootstrap_snapshot(SOURCE_SHA, str(manifest))
    assert result["status"] == "PASS"
    assert result["source_mode"] == "github_snapshot"
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip() == SOURCE_SHA


def test_bootstrap_refuses_mismatched_existing_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(ranked_promotion, "REPO_ROOT", tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    (tmp_path / "file.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "test"], cwd=tmp_path, check=True)
    data = (tmp_path / "file.txt").read_bytes()
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha": SOURCE_SHA,
                "files": [{"path": "file.txt", "blob_sha": _blob_sha(data)}],
            }
        ),
        encoding="utf-8",
    )

    result = bootstrap_snapshot(SOURCE_SHA, str(manifest))
    assert result["status"] == "FAIL"
    assert any("HEAD does not match" in error for error in result["errors"])
