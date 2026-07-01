from __future__ import annotations

import time
from pathlib import Path
from threading import Event

from fastapi.testclient import TestClient

from flightpath_video.local_api import create_app
from flightpath_video.models import FlightLogData, TrackPoint, Waypoint


def _sample_log(path: str | Path) -> FlightLogData:
    return FlightLogData(
        path=Path(path),
        points=[
            TrackPoint(time_s=0.0, lat=30.0, lon=120.0, rel_alt_m=0.0, speed_m_s=0.0),
            TrackPoint(time_s=2.0, lat=30.0001, lon=120.0001, rel_alt_m=3.0, speed_m_s=4.0),
            TrackPoint(time_s=5.0, lat=30.0003, lon=120.0002, rel_alt_m=8.0, speed_m_s=6.0),
        ],
        waypoints=[Waypoint(seq=1, lat=30.0001, lon=120.0001, alt_m=20.0, command=16)],
        message_counts={"GPS": 3, "CMD": 1},
    )


def test_parse_job_returns_immediately_and_completes_with_normalized_summary(tmp_path: Path) -> None:
    started = Event()
    release = Event()

    def parse_func(path: str, cancel_token):
        started.set()
        assert path == str(tmp_path / "flight.bin")
        assert not cancel_token.is_cancelled()
        release.wait(timeout=2)
        return _sample_log(path)

    app = create_app(parse_func=parse_func)
    client = TestClient(app)

    response = client.post("/api/logs/parse", json={"path": str(tmp_path / "flight.bin")})

    assert response.status_code == 202
    payload = response.json()
    assert payload["schemaVersion"] == "job.v1"
    assert payload["status"] in {"queued", "running"}
    assert payload["jobId"]
    assert started.wait(timeout=1)

    release.set()
    job = _wait_for_job(client, payload["jobId"])
    assert job["status"] == "completed"
    assert job["result"]["schemaVersion"] == "flight-log.v1"
    assert job["result"]["summary"] == {
        "gpsCount": 3,
        "totalDurationS": 5.0,
        "selectedDurationS": 5.0,
        "maxRelativeAltitudeM": 8.0,
        "maxSpeedMS": 6.0,
        "waypointCount": 1,
        "trueFlightDetected": True,
    }
    assert len(job["result"]["points"]) == 3
    assert job["result"]["waypoints"][0]["seq"] == 1


def test_uploaded_bin_file_starts_parse_job_from_local_temp_copy() -> None:
    received_path: list[str] = []

    def parse_func(path: str, cancel_token):
        received_path.append(path)
        assert Path(path).suffix == ".bin"
        assert Path(path).read_bytes() == b"BINLOG"
        return _sample_log(path)

    client = TestClient(create_app(parse_func=parse_func))
    response = client.post(
        "/api/logs/parse-file",
        files={"file": ("flight.bin", b"BINLOG", "application/octet-stream")},
    )

    assert response.status_code == 202
    job = _wait_for_job(client, response.json()["jobId"])
    assert job["status"] == "completed"
    assert received_path


def test_parse_job_failure_uses_structured_error(tmp_path: Path) -> None:
    def parse_func(path: str, cancel_token):
        raise RuntimeError("bad log")

    client = TestClient(create_app(parse_func=parse_func))
    created = client.post("/api/logs/parse", json={"path": str(tmp_path / "bad.bin")})

    job = _wait_for_job(client, created.json()["jobId"])

    assert job["status"] == "failed"
    assert job["error"]["code"] == "PARSE_FAILED"
    assert "bad log" in job["error"]["message"]


def test_upload_rejects_non_bin_file() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/logs/parse-file",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_LOG_FILE"


def test_job_can_be_cancelled(tmp_path: Path) -> None:
    started = Event()

    def parse_func(path: str, cancel_token):
        started.set()
        while not cancel_token.is_cancelled():
            time.sleep(0.01)
        return _sample_log(path)

    client = TestClient(create_app(parse_func=parse_func))
    created = client.post("/api/logs/parse", json={"path": str(tmp_path / "slow.bin")})
    job_id = created.json()["jobId"]
    assert started.wait(timeout=1)

    cancel_response = client.post(f"/api/jobs/{job_id}/cancel")

    assert cancel_response.status_code == 202
    job = _wait_for_job(client, job_id)
    assert job["status"] == "cancelled"
    assert job["error"]["code"] == "CANCELLED"


def test_job_events_stream_contains_progress_and_terminal_state(tmp_path: Path) -> None:
    def parse_func(path: str, cancel_token):
        return _sample_log(path)

    client = TestClient(create_app(parse_func=parse_func))
    created = client.post("/api/logs/parse", json={"path": str(tmp_path / "flight.bin")})
    job_id = created.json()["jobId"]
    _wait_for_job(client, job_id)

    response = client.get(f"/api/jobs/{job_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: progress" in body
    assert '"phase":"completed"' in body


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
