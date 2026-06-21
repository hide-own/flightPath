from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable

import requests
from PIL import Image, ImageStat

from .geo import TILE_SIZE, MapProjection, latlon_to_world_px, world_px_to_tile
from .models import TrackPoint, Waypoint


class MapDownloadError(RuntimeError):
    pass


class UnavailableTileError(MapDownloadError):
    pass


ESRI_WORLD_IMAGERY_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
CancelCheck = Callable[[], bool]


class MapCancelled(RuntimeError):
    pass


@dataclass
class TileProvider:
    cache_dir: Path = Path("cache") / "tiles"
    timeout_s: float = 15.0

    @property
    def provider_cache_dir(self) -> Path:
        return self.cache_dir / "esri_world_imagery"

    def cache_path_for(self, zoom: int, x: int, y: int) -> Path:
        tile_count = 2**zoom
        return self.provider_cache_dir / str(zoom) / str(x % tile_count) / f"{y}.jpg"

    def get_tile(self, zoom: int, x: int, y: int) -> Image.Image:
        tile_count = 2**zoom
        if y < 0 or y >= tile_count:
            raise MapDownloadError(f"地图瓦片超出范围 z={zoom} x={x} y={y}")

        wrapped_x = x % tile_count
        tile_path = self.cache_path_for(zoom, wrapped_x, y)
        if tile_path.exists():
            tile = Image.open(tile_path).convert("RGB")
            if is_unavailable_esri_tile(tile):
                tile.close()
                tile_path.unlink(missing_ok=True)
                raise UnavailableTileError(f"地图下载失败：地图服务返回占位瓦片 z={zoom} x={wrapped_x} y={y}")
            return tile

        url = ESRI_WORLD_IMAGERY_URL.format(z=zoom, x=wrapped_x, y=y)
        try:
            response = requests.get(
                url,
                timeout=self.timeout_s,
                headers={"User-Agent": "FlightPathVideo/0.1"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MapDownloadError(f"地图下载失败，且本地没有缓存瓦片: {exc}") from exc

        tile = Image.open(BytesIO(response.content)).convert("RGB")
        if is_unavailable_esri_tile(tile):
            tile.close()
            raise UnavailableTileError(f"地图下载失败：地图服务返回占位瓦片 z={zoom} x={wrapped_x} y={y}")

        tile_path.parent.mkdir(parents=True, exist_ok=True)
        tile_path.write_bytes(response.content)
        return tile


def build_satellite_background(
    points: list[TrackPoint],
    waypoints: list[Waypoint],
    width: int,
    height: int,
    provider: TileProvider | None = None,
    cancel_check: CancelCheck | None = None,
) -> tuple[Image.Image, MapProjection]:
    if not points:
        raise MapDownloadError("没有可用于定位地图的轨迹点。")

    provider = provider or TileProvider()
    start_zoom = choose_zoom(points, waypoints, width, height)
    unavailable_error: UnavailableTileError | None = None

    for zoom in range(start_zoom, 1, -1):
        try:
            return _build_background_at_zoom(points, waypoints, width, height, provider, zoom, cancel_check)
        except UnavailableTileError as exc:
            unavailable_error = exc
            continue

    if unavailable_error is not None:
        raise MapDownloadError(str(unavailable_error)) from unavailable_error
    raise MapDownloadError("地图下载失败：没有可用的卫星地图缩放级别")


def _build_background_at_zoom(
    points: list[TrackPoint],
    waypoints: list[Waypoint],
    width: int,
    height: int,
    provider: TileProvider,
    zoom: int,
    cancel_check: CancelCheck | None = None,
) -> tuple[Image.Image, MapProjection]:
    projection = make_projection(points, waypoints, width, height, zoom)
    background = Image.new("RGB", (width, height), (35, 42, 48))

    min_tile_x, min_tile_y = world_px_to_tile(projection.top_left_x, projection.top_left_y)
    max_tile_x, max_tile_y = world_px_to_tile(
        projection.top_left_x + width + TILE_SIZE,
        projection.top_left_y + height + TILE_SIZE,
    )

    failures: list[str] = []
    for tile_x in range(min_tile_x, max_tile_x + 1):
        for tile_y in range(min_tile_y, max_tile_y + 1):
            if cancel_check is not None and cancel_check():
                raise MapCancelled("地图加载已取消。")
            try:
                tile = provider.get_tile(zoom, tile_x, tile_y)
            except UnavailableTileError:
                raise
            except MapDownloadError as exc:
                failures.append(str(exc))
                continue
            paste_x = round(tile_x * TILE_SIZE - projection.top_left_x)
            paste_y = round(tile_y * TILE_SIZE - projection.top_left_y)
            background.paste(tile, (paste_x, paste_y))

    if failures:
        raise MapDownloadError(failures[0])

    return background, projection


def is_unavailable_esri_tile(tile: Image.Image) -> bool:
    rgb_tile = tile.convert("RGB")
    resized = rgb_tile.resize((32, 32))
    stat = ImageStat.Stat(resized)
    mean_r, mean_g, mean_b = stat.mean
    std_r, std_g, std_b = stat.stddev
    channels_close = max(abs(mean_r - mean_g), abs(mean_g - mean_b), abs(mean_r - mean_b)) <= 4
    mid_gray = 165 <= mean_r <= 225 and 165 <= mean_g <= 225 and 165 <= mean_b <= 225
    low_detail = max(std_r, std_g, std_b) <= 18
    return channels_close and mid_gray and low_detail


def choose_zoom(points: list[TrackPoint], waypoints: list[Waypoint], width: int, height: int) -> int:
    geo_items = _geo_items(points, waypoints)
    for zoom in range(20, 1, -1):
        xs, ys = zip(*(latlon_to_world_px(lat, lon, zoom) for lat, lon in geo_items))
        extent_w = max(xs) - min(xs)
        extent_h = max(ys) - min(ys)
        if extent_w <= width * 0.72 and extent_h <= height * 0.62:
            return zoom
    return 2


def make_projection(
    points: list[TrackPoint],
    waypoints: list[Waypoint],
    width: int,
    height: int,
    zoom: int,
) -> MapProjection:
    geo_items = _geo_items(points, waypoints)
    xs, ys = zip(*(latlon_to_world_px(lat, lon, zoom) for lat, lon in geo_items))
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    if math.isclose(min_x, max_x):
        min_x -= TILE_SIZE / 4
        max_x += TILE_SIZE / 4
    if math.isclose(min_y, max_y):
        min_y -= TILE_SIZE / 4
        max_y += TILE_SIZE / 4

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    top_left_x = center_x - width / 2.0
    top_left_y = center_y - height / 2.0
    return MapProjection(zoom=zoom, top_left_x=top_left_x, top_left_y=top_left_y, width=width, height=height)


def _geo_items(points: Iterable[TrackPoint], waypoints: Iterable[Waypoint]) -> list[tuple[float, float]]:
    items = [(point.lat, point.lon) for point in points]
    items.extend((waypoint.lat, waypoint.lon) for waypoint in waypoints)
    return items
