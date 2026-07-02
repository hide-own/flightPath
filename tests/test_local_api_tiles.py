from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from io import BytesIO

from PIL import Image

from flightpath_video.local_api import create_app
from flightpath_video.map_tiles import MapDownloadError, TileProvider


def test_tile_endpoint_serves_cached_esri_tile(tmp_path: Path) -> None:
    provider = TileProvider(cache_dir=tmp_path)
    tile_path = provider.cache_path_for(3, 4, 2)
    tile_path.parent.mkdir(parents=True)
    Image.new("RGB", (256, 256), (20, 80, 120)).save(tile_path, format="JPEG")

    client = TestClient(create_app(tile_provider=provider))
    response = client.get("/tiles/esri/3/4/2")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8")


def test_tile_endpoint_uses_lower_zoom_fallback_when_exact_tile_fails() -> None:
    class ParentFallbackProvider:
        def get_tile(self, zoom: int, x: int, y: int):
            if zoom == 2 and x == 1 and y == 1:
                tile = Image.new("RGB", (256, 256), (0, 0, 0))
                colors = [
                    ((0, 0, 128, 128), (255, 0, 0)),
                    ((128, 0, 256, 128), (0, 255, 0)),
                    ((0, 128, 128, 256), (0, 0, 255)),
                    ((128, 128, 256, 256), (255, 255, 0)),
                ]
                for box, color in colors:
                    tile.paste(color, box)
                return tile
            raise MapDownloadError("exact tile unavailable")

    client = TestClient(create_app(tile_provider=ParentFallbackProvider()))
    response = client.get("/tiles/esri/3/2/2")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    returned = Image.open(BytesIO(response.content)).convert("RGB")
    red, green, blue = returned.getpixel((128, 128))
    assert red > 180
    assert green < 80
    assert blue < 80


def test_tile_endpoint_returns_placeholder_when_map_download_fails() -> None:
    class FailingProvider:
        def get_tile(self, zoom: int, x: int, y: int):
            raise MapDownloadError("no cached tile")

    client = TestClient(create_app(tile_provider=FailingProvider()))
    response = client.get("/tiles/esri/3/4/2")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8")


def test_tile_endpoint_rejects_invalid_tile_range() -> None:
    client = TestClient(create_app())
    response = client.get("/tiles/esri/0/0/0")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_TILE"
