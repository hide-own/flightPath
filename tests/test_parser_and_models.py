from __future__ import annotations

from pathlib import Path

import pytest

from flightpath_video.models import FlightLogData, TrackPoint, Waypoint
from flightpath_video.parser import LogParseError, parse_bin_log

from .conftest import REAL_LOGS


def test_true_flight_selection_uses_three_second_buffer() -> None:
    data = FlightLogData(
        path=Path("synthetic.bin"),
        points=[
            TrackPoint(0, 30.0, 104.0, 0),
            TrackPoint(5, 30.0, 104.0001, 1.9),
            TrackPoint(10, 30.0, 104.0002, 2.1),
            TrackPoint(20, 30.0, 104.0003, 2.2),
            TrackPoint(25, 30.0, 104.0004, 1.0),
        ],
    )

    selected = data.selected_points(true_flight_only=True, rel_alt_threshold_m=2.0, buffer_s=3.0)

    assert [point.time_s for point in selected] == [10, 20]
    assert data.true_flight_detected()


def test_true_flight_selection_falls_back_to_full_track_when_missing() -> None:
    points = [
        TrackPoint(0, 30.0, 104.0, 0),
        TrackPoint(5, 30.0, 104.0001, 1.5),
    ]
    data = FlightLogData(path=Path("synthetic.bin"), points=points)

    assert data.selected_points(true_flight_only=True) == points
    assert not data.true_flight_detected()


def test_waypoint_duplicate_records_are_suppressed() -> None:
    for path in REAL_LOGS:
        if not path.exists():
            pytest.skip(f"missing real log {path}")
        data = parse_bin_log(path)
        unique_keys = {(wp.seq, round(wp.lat, 6), round(wp.lon, 6)) for wp in data.waypoints}
        assert len(unique_keys) == len(data.waypoints)
        assert data.gps_count > 100
        assert data.max_altitude_m > 2.0
        assert data.max_speed_m_s > 0.0


def test_parse_bin_log_rejects_missing_or_non_bin_file(tmp_path: Path) -> None:
    with pytest.raises(LogParseError):
        parse_bin_log(tmp_path / "missing.bin")

    text_file = tmp_path / "not_a_log.txt"
    text_file.write_text("not a log", encoding="utf-8")
    with pytest.raises(LogParseError):
        parse_bin_log(text_file)
