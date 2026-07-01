from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
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


def test_tile_endpoint_reports_map_download_failure() -> None:
    class FailingProvider:
        def get_tile(self, zoom: int, x: int, y: int):
            raise MapDownloadError("no cached tile")

    client = TestClient(create_app(tile_provider=FailingProvider()))
    response = client.get("/tiles/esri/3/4/2")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MAP_DOWNLOAD_FAILED"
    assert "no cached tile" in response.json()["detail"]["message"]


def test_tile_endpoint_rejects_invalid_tile_range() -> None:
    client = TestClient(create_app())
    response = client.get("/tiles/esri/0/0/0")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_TILE"
