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
