import hashlib
import json
import subprocess

from planning import ranked_promotion
from planning.snapshot_checkout import bootstrap_snapshot
from planning.snapshot_precommit import _git_blob_sha, verify_snapshot_manifest


SOURCE_SHA = "1" * 40


def _blob_sha(data):
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


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


def test_snapshot_manifest_fails_when_materialized_bytes_change(
    tmp_path, monkeypatch
):
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
                "files": [
                    {"path": "rule.txt", "blob_sha": _blob_sha(original)}
                ],
            }
        ),
        encoding="utf-8",
    )
    errors = verify_snapshot_manifest(manifest, SOURCE_SHA)
    assert any("snapshot blob mismatch" in error for error in errors)


def test_bootstrap_refuses_to_create_synthetic_git_metadata(
    tmp_path, monkeypatch
):
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
    assert result["status"] == "FAIL"
    assert not (tmp_path / ".git").exists()
    assert any("synthetic Git metadata is prohibited" in error for error in result["errors"])


def test_bootstrap_accepts_clean_real_checkout_at_exact_sha(
    tmp_path, monkeypatch
):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    monkeypatch.setattr(ranked_promotion, "REPO_ROOT", checkout)
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=checkout,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=checkout,
        check=True,
    )
    path = checkout / "file.txt"
    path.write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-qm", "test"], cwd=checkout, check=True)
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
    ).strip()
    data = path.read_bytes()
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha": source_sha,
                "files": [{"path": "file.txt", "blob_sha": _blob_sha(data)}],
            }
        ),
        encoding="utf-8",
    )

    result = bootstrap_snapshot(source_sha, str(manifest))
    assert result["status"] == "PASS"
    assert result["source_mode"] == "checkout"
    assert result["resolved_head"] == source_sha


def test_bootstrap_refuses_dirty_real_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(ranked_promotion, "REPO_ROOT", tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=tmp_path,
        check=True,
    )
    path = tmp_path / "file.txt"
    path.write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "test"], cwd=tmp_path, check=True)
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    data = path.read_bytes()
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha": source_sha,
                "files": [{"path": "file.txt", "blob_sha": _blob_sha(data)}],
            }
        ),
        encoding="utf-8",
    )
    path.write_text("dirty\n", encoding="utf-8")

    result = bootstrap_snapshot(source_sha, str(manifest))
    # Manifest check catches changed tracked bytes before checkout cleanliness.
    assert result["status"] == "FAIL"


def test_bootstrap_refuses_mismatched_existing_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(ranked_promotion, "REPO_ROOT", tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=tmp_path,
        check=True,
    )
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
