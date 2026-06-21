from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from flightpath_video.map_tiles import (
    MapDownloadError,
    TileProvider,
    UnavailableTileError,
    build_satellite_background,
    choose_zoom,
)
from flightpath_video.models import TrackPoint, Waypoint


class FakeProvider(TileProvider):
    def __init__(self, cache_dir: Path, fail: bool = False) -> None:
        super().__init__(cache_dir=cache_dir)
        self.fail = fail
        self.requests: list[tuple[int, int, int]] = []

    def get_tile(self, zoom: int, x: int, y: int) -> Image.Image:
        self.requests.append((zoom, x, y))
        if self.fail:
            raise MapDownloadError("地图下载失败，且本地没有缓存瓦片")
        return Image.new("RGB", (256, 256), (32, 64, 96))


class ZoomFallbackProvider(TileProvider):
    def __init__(self, cache_dir: Path, unavailable_at_or_above: int) -> None:
        super().__init__(cache_dir=cache_dir)
        self.unavailable_at_or_above = unavailable_at_or_above
        self.requests: list[tuple[int, int, int]] = []

    def get_tile(self, zoom: int, x: int, y: int) -> Image.Image:
        self.requests.append((zoom, x, y))
        if zoom >= self.unavailable_at_or_above:
            raise UnavailableTileError("地图下载失败：地图服务返回占位瓦片")
        return Image.new("RGB", (256, 256), (30, 95, 55))


def test_background_is_centered_and_uses_provider_cache(tmp_path: Path) -> None:
    points = [
        TrackPoint(0, 30.7152, 104.1867, 0),
        TrackPoint(1, 30.7155, 104.1869, 3),
    ]
    waypoints = [Waypoint(1, 30.7154, 104.1868)]
    provider = FakeProvider(tmp_path)

    background, projection = build_satellite_background(points, waypoints, 640, 360, provider)

    assert background.size == (640, 360)
    assert provider.requests
    for point in points:
        x, y = projection.project(point.lat, point.lon)
        assert 0 <= x <= 640
        assert 0 <= y <= 360


def test_missing_uncached_tile_reports_map_download_failure(tmp_path: Path) -> None:
    points = [
        TrackPoint(0, 30.7152, 104.1867, 0),
        TrackPoint(1, 30.7155, 104.1869, 3),
    ]

    with pytest.raises(MapDownloadError, match="地图下载失败"):
        build_satellite_background(points, [], 320, 180, FakeProvider(tmp_path, fail=True))


def test_cache_path_is_exposed(tmp_path: Path) -> None:
    provider = TileProvider(cache_dir=tmp_path)

    assert provider.provider_cache_dir == tmp_path / "esri_world_imagery"
    assert provider.cache_path_for(3, 9, 4).as_posix().endswith("esri_world_imagery/3/1/4.jpg")


def test_esri_unavailable_placeholder_tiles_are_rejected(tmp_path: Path) -> None:
    provider = TileProvider(cache_dir=tmp_path)
    tile_path = provider.cache_path_for(8, 1, 1)
    tile_path.parent.mkdir(parents=True)
    placeholder = Image.new("RGB", (256, 256), (199, 199, 199))
    tile_path.unlink(missing_ok=True)
    placeholder.save(tile_path)

    with pytest.raises(UnavailableTileError, match="占位瓦片"):
        provider.get_tile(8, 1, 1)
    assert not tile_path.exists()


def test_background_retries_lower_zoom_when_provider_returns_placeholder(tmp_path: Path) -> None:
    points = [
        TrackPoint(0, 30.7152, 104.1867, 0),
        TrackPoint(1, 30.7155, 104.1869, 3),
    ]
    initial_zoom = choose_zoom(points, [], 640, 360)
    provider = ZoomFallbackProvider(tmp_path, unavailable_at_or_above=initial_zoom)

    background, projection = build_satellite_background(points, [], 640, 360, provider)

    assert background.getpixel((10, 10)) == (30, 95, 55)
    assert projection.zoom < initial_zoom
    requested_zooms = {request[0] for request in provider.requests}
    assert initial_zoom in requested_zooms
    assert projection.zoom in requested_zooms
