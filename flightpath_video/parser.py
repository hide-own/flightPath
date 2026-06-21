from __future__ import annotations

import contextlib
import io
from collections import Counter
from pathlib import Path

from pymavlink import mavutil

from .geo import haversine_m
from .models import FlightLogData, TrackPoint, Waypoint


class LogParseError(RuntimeError):
    pass


GPS_MESSAGE_TYPES = {"GPS", "GPS2", "GPSU", "GPSB"}
WAYPOINT_MESSAGE_TYPES = {"CMD", "MISSION_ITEM", "MISSION_ITEM_INT"}


def parse_bin_log(path: str | Path) -> FlightLogData:
    log_path = Path(path)
    if not log_path.exists():
        raise LogParseError(f"日志文件不存在: {log_path}")
    if log_path.suffix.lower() != ".bin":
        raise LogParseError("请选择 Mission Planner / ArduPilot 的 .bin 日志文件。")

    message_counts: Counter[str] = Counter()
    raw_points: list[TrackPoint] = []
    raw_waypoints: list[Waypoint] = []

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            mlog = mavutil.mavlink_connection(str(log_path), robust_parsing=True, dialect="ardupilotmega")
        except Exception as exc:
            raise LogParseError(f"无法打开日志: {exc}") from exc

        while True:
            try:
                msg = mlog.recv_match(blocking=False)
            except Exception:
                continue
            if msg is None:
                break

            msg_type = msg.get_type()
            if msg_type == "BAD_DATA":
                continue
            message_counts[msg_type] += 1
            data = msg.to_dict()

            if msg_type in GPS_MESSAGE_TYPES:
                point = _parse_gps_message(data)
                if point is not None:
                    raw_points.append(point)
            elif msg_type in WAYPOINT_MESSAGE_TYPES:
                waypoint = _parse_waypoint_message(data)
                if waypoint is not None:
                    raw_waypoints.append(waypoint)

    points = _postprocess_points(raw_points)
    waypoints = _dedupe_waypoints(raw_waypoints)

    if not points:
        raise LogParseError("没有解析到有效 GPS 轨迹点。请确认这是 Mission Planner / ArduPilot 的 .bin 日志。")

    return FlightLogData(path=log_path, points=points, waypoints=waypoints, message_counts=dict(message_counts))


def _parse_gps_message(data: dict) -> TrackPoint | None:
    lat = _normalize_lat_lon(_first_present(data, ("Lat", "lat")), is_lon=False)
    lon = _normalize_lat_lon(_first_present(data, ("Lng", "Lon", "lon")), is_lon=True)
    if lat is None or lon is None or lat == 0.0 or lon == 0.0:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None

    status = _first_present(data, ("Status", "FixType", "fix_type"))
    if status is not None and float(status) < 2:
        return None

    time_s = _message_time_s(data, prefer_gps_t=True)
    if time_s is None:
        return None

    alt_m = _normalize_altitude(_first_present(data, ("Alt", "AMSL", "MSL")))
    rel_alt = _normalize_altitude(_first_present(data, ("RelAlt", "RAlt", "relative_alt")))
    if rel_alt is None:
        rel_alt = 0.0

    speed = _normalize_speed(_first_present(data, ("Spd", "Speed", "Vel", "GSpd", "groundspeed")))
    heading = _normalize_heading(_first_present(data, ("GCrs", "Yaw", "Hdg", "Cog")))

    return TrackPoint(
        time_s=time_s,
        lat=lat,
        lon=lon,
        rel_alt_m=rel_alt,
        alt_m=alt_m,
        speed_m_s=speed if speed is not None else 0.0,
        heading_deg=heading,
    )


def _parse_waypoint_message(data: dict) -> Waypoint | None:
    lat = _normalize_lat_lon(_first_present(data, ("Lat", "X", "x")), is_lon=False)
    lon = _normalize_lat_lon(_first_present(data, ("Lng", "Lon", "Y", "y")), is_lon=True)
    if lat is None or lon is None or lat == 0.0 or lon == 0.0:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None

    seq_raw = _first_present(data, ("CNum", "Seq", "seq", "current"))
    command_raw = _first_present(data, ("CId", "Command", "command"))
    alt = _normalize_altitude(_first_present(data, ("Alt", "Z", "z")))

    seq = int(seq_raw) if seq_raw is not None else 0
    command = int(command_raw) if command_raw is not None else None
    return Waypoint(seq=seq, lat=lat, lon=lon, alt_m=alt, command=command)


def _postprocess_points(points: list[TrackPoint]) -> list[TrackPoint]:
    points = sorted(points, key=lambda item: item.time_s)
    if not points:
        return []

    base_alt = next((point.alt_m for point in points if point.alt_m is not None), None)
    processed: list[TrackPoint] = []
    last_time: float | None = None
    for point in points:
        if last_time is not None and point.time_s <= last_time:
            continue
        rel_alt = point.rel_alt_m
        if point.alt_m is not None and base_alt is not None and abs(rel_alt) < 0.001:
            rel_alt = point.alt_m - base_alt
        processed.append(
            TrackPoint(
                time_s=point.time_s,
                lat=point.lat,
                lon=point.lon,
                rel_alt_m=rel_alt,
                alt_m=point.alt_m,
                speed_m_s=point.speed_m_s,
                heading_deg=point.heading_deg,
            )
        )
        last_time = point.time_s

    if all(point.speed_m_s <= 0.01 for point in processed) and len(processed) > 1:
        processed = _estimate_speeds(processed)
    return processed


def _estimate_speeds(points: list[TrackPoint]) -> list[TrackPoint]:
    estimated: list[TrackPoint] = []
    for index, point in enumerate(points):
        if index == 0:
            next_point = points[1]
            dt = max(0.001, next_point.time_s - point.time_s)
            speed = haversine_m(point.lat, point.lon, next_point.lat, next_point.lon) / dt
        else:
            prev = points[index - 1]
            dt = max(0.001, point.time_s - prev.time_s)
            speed = haversine_m(prev.lat, prev.lon, point.lat, point.lon) / dt
        estimated.append(
            TrackPoint(
                time_s=point.time_s,
                lat=point.lat,
                lon=point.lon,
                rel_alt_m=point.rel_alt_m,
                alt_m=point.alt_m,
                speed_m_s=speed,
                heading_deg=point.heading_deg,
            )
        )
    return estimated


def _dedupe_waypoints(waypoints: list[Waypoint]) -> list[Waypoint]:
    deduped: dict[tuple[int, int, int], Waypoint] = {}
    for waypoint in waypoints:
        key = (waypoint.seq, round(waypoint.lat * 1_000_000), round(waypoint.lon * 1_000_000))
        deduped.setdefault(key, waypoint)
    return sorted(deduped.values(), key=lambda item: (item.seq, item.lat, item.lon))


def _message_time_s(data: dict, prefer_gps_t: bool = False) -> float | None:
    if "TimeUS" in data:
        return float(data["TimeUS"]) / 1_000_000.0
    if prefer_gps_t and "T" in data:
        return float(data["T"]) / 1_000.0
    if "TimeMS" in data:
        return float(data["TimeMS"]) / 1_000.0
    if "time_boot_ms" in data:
        return float(data["time_boot_ms"]) / 1_000.0
    if "time_usec" in data:
        return float(data["time_usec"]) / 1_000_000.0
    if "T" in data:
        return float(data["T"]) / 1_000.0
    return None


def _first_present(data: dict, names: tuple[str, ...]) -> object | None:
    for name in names:
        value = data.get(name)
        if value is not None:
            return value
    return None


def _normalize_lat_lon(value: object | None, is_lon: bool) -> float | None:
    if value is None:
        return None
    number = float(value)
    limit = 180.0 if is_lon else 90.0
    if abs(number) > limit and abs(number) > 10_000:
        number /= 10_000_000.0
    return number


def _normalize_altitude(value: object | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if abs(number) > 20_000:
        number /= 1000.0
    return number


def _normalize_speed(value: object | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if number > 500:
        number /= 100.0
    return max(0.0, number)


def _normalize_heading(value: object | None) -> float | None:
    if value is None:
        return None
    return float(value) % 360.0
