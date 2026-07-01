from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from flightpath_video.local_api import create_app


def test_export_job_completes_and_downloads_mp4(tmp_path: Path) -> None:
    def render_func(log_path, options, output_path, cancel_token, progress):
        assert log_path == str(tmp_path / "flight.bin")
        assert options.render_mode == "3d"
        assert options.view_mode == "current"
        assert options.width == 640
        assert not cancel_token.is_cancelled()
        progress("rendering", 40, "正在渲染")
        output_path.write_bytes(b"fake mp4")
        return {"extra": "ok"}

    client = TestClient(create_app(render_func=render_func, export_dir=tmp_path / "exports"))

    created = client.post(
        "/api/exports",
        json={
            "logPath": str(tmp_path / "flight.bin"),
            "options": {
                "width": 640,
                "height": 360,
                "fps": 24,
                "renderMode": "3d",
                "viewMode": "current",
                "timeMode": "realtime",
                "overlays": {"waypoints": True, "altitude": True, "speed": True, "progress": True},
            },
        },
    )

    assert created.status_code == 202
    job = _wait_for_job(client, created.json()["jobId"])
    assert job["status"] == "completed"
    assert job["result"]["schemaVersion"] == "export.v1"
    assert job["result"]["downloadUrl"] == f"/api/exports/{job['jobId']}/download"
    assert job["result"]["renderMode"] == "3d"
    assert job["result"]["viewMode"] == "current"

    downloaded = client.get(job["result"]["downloadUrl"])

    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("video/mp4")
    assert downloaded.content == b"fake mp4"


def test_export_download_rejects_incomplete_job(tmp_path: Path) -> None:
    def render_func(log_path, options, output_path, cancel_token, progress):
        time.sleep(0.2)
        output_path.write_bytes(b"late mp4")
        return {}

    client = TestClient(create_app(render_func=render_func, export_dir=tmp_path / "exports"))
    created = client.post(
        "/api/exports",
        json={
            "logPath": str(tmp_path / "flight.bin"),
            "options": {"width": 320, "height": 176, "fps": 2},
        },
    )

    response = client.get(f"/api/exports/{created.json()['jobId']}/download")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EXPORT_NOT_READY"


def test_export_job_can_be_cancelled(tmp_path: Path) -> None:
    def render_func(log_path, options, output_path, cancel_token, progress):
        while not cancel_token.is_cancelled():
            time.sleep(0.01)
        return {}

    client = TestClient(create_app(render_func=render_func, export_dir=tmp_path / "exports"))
    created = client.post(
        "/api/exports",
        json={
            "logPath": str(tmp_path / "flight.bin"),
            "options": {"width": 320, "height": 176, "fps": 2},
        },
    )
    job_id = created.json()["jobId"]

    cancelled = client.post(f"/api/jobs/{job_id}/cancel")
    job = _wait_for_job(client, job_id)

    assert cancelled.status_code == 202
    assert job["status"] == "cancelled"
    assert job["error"]["code"] == "CANCELLED"


def _wait_for_job(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not finish")
