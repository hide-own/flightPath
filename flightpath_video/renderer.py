from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .map_tiles import MapCancelled, TileProvider, build_satellite_background
from .models import FlightLogData, TrackPoint, Waypoint

ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]


@dataclass(frozen=True)
class RenderOptions:
    output_path: Path
    width: int = 1280
    height: int = 720
    fps: int = 24
    true_flight_only: bool = True
    rel_alt_threshold_m: float = 2.0
    compressed_duration_s: int | None = None
    show_waypoints: bool = True
    show_altitude: bool = True
    show_speed: bool = True
    show_progress: bool = True


class RenderError(RuntimeError):
    pass


class RenderCancelled(RuntimeError):
    pass


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled


def render_video(
    log_data: FlightLogData,
    options: RenderOptions,
    progress_callback: ProgressCallback | None = None,
    tile_provider: TileProvider | None = None,
    cancel_check: CancelCheck | None = None,
) -> None:
    points = log_data.selected_points(options.true_flight_only, options.rel_alt_threshold_m)
    if len(points) < 2:
        raise RenderError("有效轨迹点不足，无法生成视频。")

    _emit(progress_callback, 2, "正在下载/读取卫星地图瓦片")
    try:
        background, projection = build_satellite_background(
            points, log_data.waypoints, options.width, options.height, tile_provider, cancel_check
        )
    except MapCancelled as exc:
        raise RenderCancelled(str(exc)) from exc
    static_frame = _draw_static_layers(background, projection, points, log_data.waypoints, options)

    log_start = points[0].time_s
    log_duration = max(0.001, points[-1].time_s - log_start)
    output_duration = float(options.compressed_duration_s) if options.compressed_duration_s else log_duration
    frame_count = max(2, int(math.ceil(output_duration * options.fps)) + 1)
    times = [point.time_s for point in points]

    output_path = Path(options.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _emit(progress_callback, 5, f"正在渲染 0s / {output_duration:.0f}s")
    writer = None
    completed = False
    try:
        writer = imageio.get_writer(
            str(output_path),
            fps=options.fps,
            codec="libx264",
            quality=8,
            pixelformat="yuv420p",
            macro_block_size=16,
        )
        for frame_index in range(frame_count):
            if cancel_check is not None and cancel_check():
                _emit(progress_callback, min(99, max(1, progress_bar_percent(frame_index, frame_count))), "正在取消生成...")
                raise RenderCancelled("视频生成已取消。")
            if options.compressed_duration_s:
                ratio = frame_index / max(1, frame_count - 1)
                log_time = log_start + ratio * log_duration
                display_elapsed = ratio * log_duration
                video_elapsed = ratio * output_duration
            else:
                video_elapsed = frame_index / options.fps
                log_time = min(points[-1].time_s, log_start + video_elapsed)
                display_elapsed = log_time - log_start

            current, point_index = _interpolate_point(points, times, log_time)
            frame = static_frame.copy()
            draw = ImageDraw.Draw(frame, "RGBA")
            _draw_progress_track(draw, projection, points, point_index, current)
            _draw_current_marker(draw, projection, current)
            _draw_hud(draw, frame.size, current, display_elapsed, log_duration, options)
            writer.append_data(np.asarray(frame))

            if frame_index % max(1, options.fps // 2) == 0 or frame_index == frame_count - 1:
                percent = 5 + int((frame_index + 1) / frame_count * 95)
                _emit(progress_callback, min(100, percent), f"正在渲染 {video_elapsed:.0f}s / {output_duration:.0f}s")
        completed = True
    except Exception:
        raise
    finally:
        if writer is not None:
            writer.close()
        if not completed and output_path.exists():
            try:
                output_path.unlink()
            except OSError:
                incomplete_path = output_path.with_suffix(output_path.suffix + ".incomplete")
                try:
                    output_path.replace(incomplete_path)
                except OSError:
                    pass

    _emit(progress_callback, 100, f"完成: {output_path}")


def render_preview_image(
    log_data: FlightLogData,
    options: RenderOptions,
    tile_provider: TileProvider | None = None,
    cancel_check: CancelCheck | None = None,
) -> Image.Image:
    points = log_data.selected_points(options.true_flight_only, options.rel_alt_threshold_m)
    if len(points) < 2:
        raise RenderError("有效轨迹点不足，无法预览。")

    try:
        background, projection = build_satellite_background(
            points, log_data.waypoints, options.width, options.height, tile_provider, cancel_check
        )
    except MapCancelled as exc:
        raise RenderCancelled(str(exc)) from exc
    frame = _draw_static_layers(background, projection, points, log_data.waypoints, options)
    current = points[0]
    draw = ImageDraw.Draw(frame, "RGBA")
    _draw_current_marker(draw, projection, current)
    _draw_hud(draw, frame.size, current, 0.0, max(0.001, points[-1].time_s - points[0].time_s), options)
    return frame


def _draw_static_layers(
    background: Image.Image,
    projection,
    points: list[TrackPoint],
    waypoints: list[Waypoint],
    options: RenderOptions,
) -> Image.Image:
    frame = background.copy()
    draw = ImageDraw.Draw(frame, "RGBA")
    route = [_project_point(projection, point) for point in points]
    if len(route) >= 2:
        draw.line(route, fill=(0, 0, 0, 150), width=7, joint="curve")
        draw.line(route, fill=(75, 214, 255, 230), width=4, joint="curve")

    if options.show_waypoints:
        _draw_waypoints(draw, projection, waypoints)

    _draw_map_credit(draw, frame.size)
    return frame


def _draw_progress_track(draw: ImageDraw.ImageDraw, projection, points: list[TrackPoint], index: int, current: TrackPoint) -> None:
    flown = [_project_point(projection, point) for point in points[: max(1, index + 1)]]
    flown.append(_project_point(projection, current))
    if len(flown) >= 2:
        draw.line(flown, fill=(255, 255, 255, 185), width=8, joint="curve")
        draw.line(flown, fill=(255, 63, 63, 240), width=4, joint="curve")


def _draw_current_marker(draw: ImageDraw.ImageDraw, projection, point: TrackPoint) -> None:
    x, y = _project_point(projection, point)
    radius = 10
    draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(255, 0, 0, 50))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(232, 26, 36, 255))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(255, 255, 255, 245), width=3)


def _draw_waypoints(draw: ImageDraw.ImageDraw, projection, waypoints: list[Waypoint]) -> None:
    font = _font(15, bold=True)
    for waypoint in waypoints:
        x, y = projection.project(waypoint.lat, waypoint.lon)
        label = str(waypoint.seq)
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        radius = max(9, math.ceil(text_w / 2) + 4)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 208, 66, 225))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(20, 20, 20, 210), width=1)
        draw.text((x - text_w / 2, y - text_h / 2 - 1), label, font=font, fill=(20, 20, 20, 255))


def _draw_hud(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    point: TrackPoint,
    elapsed_s: float,
    duration_s: float,
    options: RenderOptions,
) -> None:
    width, height = size
    font = _font(24)
    small = _font(18)
    padding = 22
    lines: list[str] = [f"时间 {format_seconds(elapsed_s)} / {format_seconds(duration_s)}"]
    if options.show_altitude:
        lines.append(f"高度 {point.rel_alt_m:.1f} m")
    if options.show_speed:
        lines.append(f"速度 {point.speed_m_s:.1f} m/s")

    text_width = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)
    box_w = max(260, text_width + 36)
    box_h = 24 + len(lines) * 34
    draw.rounded_rectangle((padding, padding, padding + box_w, padding + box_h), radius=8, fill=(0, 0, 0, 150))
    for index, line in enumerate(lines):
        draw.text((padding + 18, padding + 14 + index * 34), line, font=font, fill=(255, 255, 255, 245))

    if options.show_progress:
        progress = max(0.0, min(1.0, elapsed_s / max(0.001, duration_s)))
        bar_w = min(620, width - padding * 2)
        bar_h = 14
        x0 = (width - bar_w) / 2
        y0 = height - 38
        draw.rounded_rectangle((x0, y0, x0 + bar_w, y0 + bar_h), radius=7, fill=(0, 0, 0, 150))
        draw.rounded_rectangle((x0, y0, x0 + bar_w * progress, y0 + bar_h), radius=7, fill=(255, 64, 64, 235))
        draw.text((x0, y0 - 24), f"{progress * 100:.0f}%", font=small, fill=(255, 255, 255, 235))


def _draw_map_credit(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    text = "Esri World Imagery"
    font = _font(14)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = size[0] - (bbox[2] - bbox[0]) - 12
    y = size[1] - (bbox[3] - bbox[1]) - 10
    draw.rectangle((x - 6, y - 4, size[0] - 6, size[1] - 6), fill=(0, 0, 0, 105))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 210))


def _interpolate_point(points: list[TrackPoint], times: list[float], time_s: float) -> tuple[TrackPoint, int]:
    index = bisect.bisect_right(times, time_s)
    if index <= 0:
        return points[0], 0
    if index >= len(points):
        return points[-1], len(points) - 1

    prev = points[index - 1]
    next_point = points[index]
    dt = next_point.time_s - prev.time_s
    ratio = 0.0 if dt <= 0 else (time_s - prev.time_s) / dt
    ratio = max(0.0, min(1.0, ratio))
    return (
        TrackPoint(
            time_s=time_s,
            lat=prev.lat + (next_point.lat - prev.lat) * ratio,
            lon=prev.lon + (next_point.lon - prev.lon) * ratio,
            rel_alt_m=prev.rel_alt_m + (next_point.rel_alt_m - prev.rel_alt_m) * ratio,
            alt_m=None
            if prev.alt_m is None or next_point.alt_m is None
            else prev.alt_m + (next_point.alt_m - prev.alt_m) * ratio,
            speed_m_s=prev.speed_m_s + (next_point.speed_m_s - prev.speed_m_s) * ratio,
            heading_deg=prev.heading_deg,
        ),
        index - 1,
    )


def progress_bar_percent(frame_index: int, frame_count: int) -> int:
    return 5 + int((frame_index + 1) / max(1, frame_count) * 95)


def _project_point(projection, point: TrackPoint) -> tuple[float, float]:
    return projection.project(point.lat, point.lon)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return ImageFont.load_default()


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def _emit(callback: ProgressCallback | None, percent: int, status: str) -> None:
    if callback is not None:
        callback(percent, status)
