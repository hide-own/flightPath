from __future__ import annotations

import math
from dataclasses import dataclass

WEB_MERCATOR_MAX_LAT = 85.05112878
EARTH_RADIUS_M = 6371008.8
TILE_SIZE = 256


def clamp_lat(lat: float) -> float:
    return max(-WEB_MERCATOR_MAX_LAT, min(WEB_MERCATOR_MAX_LAT, lat))


def latlon_to_world_px(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    lat = clamp_lat(lat)
    scale = TILE_SIZE * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale
    sin_lat = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def world_px_to_tile(x: float, y: float) -> tuple[int, int]:
    return int(math.floor(x / TILE_SIZE)), int(math.floor(y / TILE_SIZE))


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass(frozen=True)
class MapProjection:
    zoom: int
    top_left_x: float
    top_left_y: float
    width: int
    height: int

    def project(self, lat: float, lon: float) -> tuple[float, float]:
        x, y = latlon_to_world_px(lat, lon, self.zoom)
        return x - self.top_left_x, y - self.top_left_y
