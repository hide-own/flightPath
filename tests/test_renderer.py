from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import pytest
from PIL import Image, ImageDraw

from flightpath_video.models import FlightLogData, TrackPoint, Waypoint
from flightpath_video.renderer import (
    RenderCancelled,
    RenderOptions,
    _draw_waypoints,
    _interpolate_point,
    format_seconds,
    render_preview_image,
    render_video,
)


class SolidProvider:
    def get_tile(self, zoom: int, x: int, y: int) -> Image.Image:
        return Image.new("RGB", (256, 256), (40, 60, 80))


class FixedProjection:
    def project(self, lat: float, lon: float) -> tuple[float, float]:
        return (50.0, 50.0)


def synthetic_log() -> FlightLogData:
    return FlightLogData(
        path=Path("synthetic.bin"),
        points=[
            TrackPoint(0, 30.0, 104.0, 0, speed_m_s=0),
            TrackPoint(1, 30.0, 104.0001, 3, speed_m_s=1),
            TrackPoint(11, 30.0, 104.0002, 4, speed_m_s=2),
        ],
    )


def test_interpolation_uses_log_time_not_point_index() -> None:
    points = synthetic_log().points
    times = [point.time_s for point in points]

    early, _ = _interpolate_point(points, times, 0.5)
    late, _ = _interpolate_point(points, times, 6.0)

    assert early.lon == pytest.approx(104.00005)
    assert late.lon == pytest.approx(104.00015)


def test_preview_contains_required_layers() -> None:
    image = render_preview_image(
        synthetic_log(),
        RenderOptions(output_path=Path("unused.mp4"), width=320, height=180, fps=2),
        tile_provider=SolidProvider(),  # type: ignore[arg-type]
    )

    assert image.size == (320, 180)
    assert image.convert("RGB").getbbox() is not None


def test_waypoint_number_marker_is_compact_enough_for_dense_routes() -> None:
    image = Image.new("RGB", (100, 100), (0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")

    _draw_waypoints(draw, FixedProjection(), [Waypoint(26, 0, 0)])

    yellow_pixels = [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y))[0] > 200 and image.getpixel((x, y))[1] > 150 and image.getpixel((x, y))[2] < 100
    ]
    xs, ys = zip(*yellow_pixels)
    assert max(xs) - min(xs) + 1 <= 28
    assert max(ys) - min(ys) + 1 <= 28


def test_render_video_writes_playable_mp4_with_metadata(tmp_path: Path) -> None:
    output = tmp_path / "track.mp4"

    render_video(
        synthetic_log(),
        RenderOptions(output_path=output, width=320, height=176, fps=2, compressed_duration_s=2),
        tile_provider=SolidProvider(),  # type: ignore[arg-type]
    )

    assert output.exists()
    reader = imageio.get_reader(str(output))
    try:
        meta = reader.get_meta_data()
    finally:
        reader.close()
    assert meta["fps"] == pytest.approx(2)
    assert meta["size"] == (320, 176)


def test_render_cancellation_removes_partial_file(tmp_path: Path) -> None:
    output = tmp_path / "cancelled.mp4"

    with pytest.raises(RenderCancelled):
        render_video(
            synthetic_log(),
            RenderOptions(output_path=output, width=320, height=176, fps=2, compressed_duration_s=2),
            tile_provider=SolidProvider(),  # type: ignore[arg-type]
            cancel_check=lambda: True,
        )

    assert not output.exists()


def test_format_seconds() -> None:
    assert format_seconds(65) == "01:05"
    assert format_seconds(3661) == "01:01:01"
