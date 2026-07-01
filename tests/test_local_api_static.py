from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from flightpath_video.local_api import create_app


def test_root_serves_built_web_index(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html><body>flight ui</body></html>", encoding="utf-8")

    client = TestClient(create_app(static_dir=tmp_path))
    response = client.get("/")

    assert response.status_code == 200
    assert "flight ui" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_static_asset_is_served_from_built_web_dir(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")

    client = TestClient(create_app(static_dir=tmp_path))
    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "console.log" in response.text
