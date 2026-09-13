from media import pexels_discovery as discovery


def _video(video_id, duration, width=1080, height=1920, file_width=1080, file_height=1920):
    return {
        "id": video_id,
        "duration": duration,
        "width": width,
        "height": height,
        "url": f"https://www.pexels.com/video/example-{video_id}/",
        "image": f"https://images.pexels.com/videos/{video_id}/preview.jpg",
        "user": {"name": "Tester"},
        "video_files": [
            {
                "id": video_id * 10,
                "width": file_width,
                "height": file_height,
                "fps": 30,
                "file_type": "video/mp4",
                "quality": "hd",
                "link": f"https://videos.pexels.com/video-files/{video_id}/preview.mp4",
            }
        ],
    }


def test_discover_filters_short_and_unsuitable_renditions(monkeypatch):
    payload = {
        "videos": [
            _video(101, 59),
            _video(102, 75, file_width=1920, file_height=1080),
            _video(103, 90),
        ]
    }
    monkeypatch.setattr(discovery, "api_get", lambda *args, **kwargs: payload)
    candidates, diagnostics = discovery.discover(max_candidates=1, key="test")
    assert [item["provider_asset_id"] for item in candidates] == ["103"]
    assert candidates[0]["duration_seconds"] == 90
    assert candidates[0]["preview_image_url"].endswith("preview.jpg")
    assert candidates[0]["preview_video_url"].endswith("preview.mp4")
    assert diagnostics[0]["new_eligible"] == 1


def test_request_validation_rejects_oversized_pool(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(
        '{"schema_version":1,"plan_date":"2026-09-13","request_id":"dr-20260913-manual","max_candidates":81}',
        encoding="utf-8",
    )
    try:
        discovery._load_request(request)
    except ValueError as exc:
        assert "max_candidates must be 1-80" in str(exc)
    else:
        raise AssertionError("expected invalid max_candidates to fail")


def test_review_preview_prefers_small_exact_rendition():
    video = _video(201, 90, width=3840, height=2160, file_width=3840, file_height=2160)
    video["video_files"].insert(
        0,
        {
            "id": 2011,
            "width": 640,
            "height": 360,
            "fps": 30,
            "file_type": "video/mp4",
            "quality": "sd",
            "link": "https://videos.pexels.com/video-files/201/review-640.mp4",
        },
    )
    candidate = discovery._eligible_candidate(video, "city_motion", "city traffic")
    assert candidate is not None
    assert candidate["production_suitable_rendition_count"] == 1
    assert candidate["preview_video_width"] == 640
    assert candidate["preview_video_height"] == 360
    assert candidate["preview_video_url"].endswith("review-640.mp4")


def test_schema_v2_targets_only_remaining_category_and_rotates_query(tmp_path, monkeypatch):
    request = tmp_path / "request.json"
    request.write_text(
        """{
  "schema_version": 2,
  "plan_date": "2026-09-14",
  "request_id": "dr-20260914-manual-0230-a03",
  "max_candidates": 3,
  "target_categories": ["cleaning"],
  "exclude_provider_asset_ids": [],
  "replenishment_session_id": "rs-20260914-manual-0230",
  "attempt": 3
}""",
        encoding="utf-8",
    )
    data = discovery._load_request(request)
    calls = []

    def fake_api_get(path, key=None):
        calls.append(path)
        return {"videos": [_video(301, 90)]}

    monkeypatch.setattr(discovery, "api_get", fake_api_get)
    report = discovery.build_report(
        data,
        key="test",
        review_decisions_dir=tmp_path / "review-decisions",
    )
    assert report["category_targets"] == {"cleaning": 3}
    assert report["candidates"][0]["discovery_category"] == "cleaning"
    assert "deep+cleaning" in calls[0]
    assert all(item["category"] == "cleaning" for item in report["query_diagnostics"])


def test_same_session_review_state_is_automatically_excluded(tmp_path, monkeypatch):
    decisions = tmp_path / "review-decisions"
    decisions.mkdir()
    (decisions / "dr-old.json").write_text(
        """{
  "schema_version": 1,
  "replenishment_session_id": "rs-20260914-manual-0230",
  "request_id": "dr-20260914-manual-0230-a02",
  "attempt": 2,
  "decisions": [
    {
      "provider_asset_id": "401",
      "decision": "reject",
      "discovery_category": "cleaning",
      "reviewed_category": null,
      "category_match": false,
      "reason_code": "SEMANTIC_CATEGORY_MISMATCH"
    }
  ]
}""",
        encoding="utf-8",
    )
    request = {
        "schema_version": 2,
        "plan_date": "2026-09-14",
        "request_id": "dr-20260914-manual-0230-a03",
        "max_candidates": 3,
        "target_categories": ["cleaning"],
        "exclude_provider_asset_ids": [],
        "replenishment_session_id": "rs-20260914-manual-0230",
        "attempt": 3,
    }

    payload = {"videos": [_video(401, 90), _video(402, 90)]}
    monkeypatch.setattr(discovery, "api_get", lambda *args, **kwargs: payload)
    report = discovery.build_report(
        request,
        key="test",
        review_decisions_dir=decisions,
    )
    assert "401" in report["durably_reviewed_provider_asset_ids"]
    assert "401" in report["effective_excluded_provider_asset_ids"]
    assert [item["provider_asset_id"] for item in report["candidates"]] == ["402"]


def test_review_exclusion_is_scoped_to_replenishment_session(tmp_path):
    decisions = tmp_path / "review-decisions"
    decisions.mkdir()
    (decisions / "dr-old.json").write_text(
        """{
  "schema_version": 1,
  "replenishment_session_id": "rs-20260914-manual-0230",
  "request_id": "dr-20260914-manual-0230-a02",
  "attempt": 2,
  "decisions": [
    {
      "provider_asset_id": "501",
      "decision": "reject",
      "discovery_category": "cleaning",
      "reviewed_category": null,
      "category_match": false,
      "reason_code": "SEMANTIC_CATEGORY_MISMATCH"
    }
  ]
}""",
        encoding="utf-8",
    )
    assert discovery._load_reviewed_provider_ids(
        "rs-20260914-manual-0230", decisions
    ) == {"501"}
    assert discovery._load_reviewed_provider_ids(
        "rs-20260914-manual-0999", decisions
    ) == set()
