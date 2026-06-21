from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TrackPoint:
    time_s: float
    lat: float
    lon: float
    rel_alt_m: float
    alt_m: float | None = None
    speed_m_s: float = 0.0
    heading_deg: float | None = None


@dataclass(frozen=True)
class Waypoint:
    seq: int
    lat: float
    lon: float
    alt_m: float | None = None
    command: int | None = None


@dataclass
class FlightLogData:
    path: Path
    points: list[TrackPoint] = field(default_factory=list)
    waypoints: list[Waypoint] = field(default_factory=list)
    message_counts: dict[str, int] = field(default_factory=dict)

    @property
    def gps_count(self) -> int:
        return len(self.points)

    @property
    def total_duration_s(self) -> float:
        return duration_s(self.points)

    @property
    def max_altitude_m(self) -> float:
        if not self.points:
            return 0.0
        return max(point.rel_alt_m for point in self.points)

    @property
    def max_speed_m_s(self) -> float:
        if not self.points:
            return 0.0
        return max(point.speed_m_s for point in self.points)

    def true_flight_detected(self, rel_alt_threshold_m: float = 2.0) -> bool:
        return any(point.rel_alt_m > rel_alt_threshold_m for point in self.points)

    def selected_points(
        self,
        true_flight_only: bool = True,
        rel_alt_threshold_m: float = 2.0,
        buffer_s: float = 3.0,
    ) -> list[TrackPoint]:
        if not true_flight_only or not self.points:
            return list(self.points)

        above = [index for index, point in enumerate(self.points) if point.rel_alt_m > rel_alt_threshold_m]
        if not above:
            return list(self.points)

        start_time = self.points[above[0]].time_s - buffer_s
        end_time = self.points[above[-1]].time_s + buffer_s
        return [point for point in self.points if start_time <= point.time_s <= end_time]

    def selected_duration_s(
        self,
        true_flight_only: bool = True,
        rel_alt_threshold_m: float = 2.0,
        buffer_s: float = 3.0,
    ) -> float:
        return duration_s(self.selected_points(true_flight_only, rel_alt_threshold_m, buffer_s))


def duration_s(points: Iterable[TrackPoint]) -> float:
    items = list(points)
    if len(items) < 2:
        return 0.0
    return max(0.0, items[-1].time_s - items[0].time_s)
