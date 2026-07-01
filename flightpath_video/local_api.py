from __future__ import annotations

from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .job_manager import CancellationToken, JobManager
from .map_tiles import MapDownloadError, TileProvider
from .models import FlightLogData, TrackPoint, Waypoint
from .parser import parse_bin_log
from .renderer import RenderCancelled, RenderOptions, render_video


ParseFunction = Callable[[str, CancellationToken], FlightLogData]
ProgressFunction = Callable[[str, int, str], None]
RenderFunction = Callable[[str, "ExportOptionsRequest", Path, CancellationToken, ProgressFunction], dict]


class ParseLogRequest(BaseModel):
    path: str = Field(min_length=1)


class ExportOptionsRequest(BaseModel):
    width: int = Field(default=1280, ge=16, le=7680)
    height: int = Field(default=720, ge=16, le=4320)
    fps: int = Field(default=24, ge=1, le=120)
    range: str = "true-flight"
    renderMode: str = "2d"
    viewMode: str = "auto-fit"
    timeMode: str = "realtime"
    compressedDurationS: int | None = Field(default=None, ge=1, le=7200)
    waypointMode: str = "compact"
    altitudeScaleMode: str = "auto"
    camera: dict = Field(default_factory=dict)
    overlays: dict[str, bool] = Field(default_factory=dict)

    @property
    def render_mode(self) -> str:
        return self.renderMode

    @property
    def view_mode(self) -> str:
        return self.viewMode

    @property
    def time_mode(self) -> str:
        return self.timeMode

    @property
    def compressed_duration_s(self) -> int | None:
        return self.compressedDurationS

    @property
    def waypoint_mode(self) -> str:
        return self.waypointMode

    @property
    def altitude_scale_mode(self) -> str:
        return self.altitudeScaleMode


class ExportRequest(BaseModel):
    logPath: str = Field(min_length=1)
    options: ExportOptionsRequest = Field(default_factory=ExportOptionsRequest)

    @property
    def log_path(self) -> str:
        return self.logPath


def create_app(
    parse_func: ParseFunction | None = None,
    render_func: RenderFunction | None = None,
    job_manager: JobManager | None = None,
    tile_provider: TileProvider | None = None,
    static_dir: Path | None = None,
    upload_dir: Path | None = None,
    export_dir: Path | None = None,
) -> FastAPI:
    manager = job_manager or JobManager()
    parser = parse_func or _parse_log
    renderer = render_func or (lambda path, options, output_path, token, progress: _render_export(path, options, output_path, token, progress, parser, tile_provider))
    tiles = tile_provider or TileProvider()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            manager.shutdown()

    app = FastAPI(title="FlightPath Local API", version="0.1.0", lifespan=lifespan)
    app.state.job_manager = manager

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1", "http://localhost"],
        allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/api/logs/parse", status_code=202)
    def create_parse_job(request: ParseLogRequest) -> dict:
        job = manager.submit_parse(request.path, lambda path, token: _serialize_log(parser(path, token)))
        return job.to_dict()

    @app.post("/api/logs/parse-file", status_code=202)
    async def create_uploaded_parse_job(file: UploadFile = File(...)) -> dict:
        filename = file.filename or ""
        if not filename.lower().endswith(".bin"):
            raise HTTPException(status_code=400, detail={"code": "INVALID_LOG_FILE", "message": "Please select an ArduPilot .bin log"})
        target_dir = upload_dir or Path("cache") / "uploads"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{uuid4().hex}.bin"
        target.write_bytes(await file.read())
        job = manager.submit_parse(str(target), lambda path, token: _serialize_log(parser(path, token)))
        return job.to_dict()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": f"Job not found: {job_id}"})
        return job.to_dict()

    @app.post("/api/jobs/{job_id}/cancel", status_code=202)
    def cancel_job(job_id: str) -> dict:
        job = manager.cancel(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": f"Job not found: {job_id}"})
        return job.to_dict()

    @app.get("/api/jobs/{job_id}/events")
    def job_events(job_id: str) -> StreamingResponse:
        return StreamingResponse(manager.iter_sse_events(job_id), media_type="text/event-stream")

    @app.post("/api/exports", status_code=202)
    def create_export_job(request: ExportRequest) -> dict:
        target_dir = export_dir or Path("cache") / "exports"
        target_dir.mkdir(parents=True, exist_ok=True)
        output_path = target_dir / f"{uuid4().hex}.mp4"

        def work(job_id: str, token: CancellationToken, progress: ProgressFunction) -> dict:
            progress("preparing_map", 2, "正在准备导出")
            extra = renderer(request.log_path, request.options, output_path, token, progress) or {}
            return {
                "schemaVersion": "export.v1",
                "filename": output_path.name,
                "outputPath": str(output_path),
                "downloadUrl": f"/api/exports/{job_id}/download",
                "renderMode": request.options.render_mode,
                "viewMode": request.options.view_mode,
                **extra,
            }

        job = manager.submit_export(work)
        return job.to_dict()

    @app.get("/api/exports/{job_id}/download")
    def download_export(job_id: str) -> FileResponse:
        job = manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": f"Job not found: {job_id}"})
        if job.status != "completed" or not job.result:
            raise HTTPException(status_code=409, detail={"code": "EXPORT_NOT_READY", "message": "Export is not complete"})

        output_path = Path(str(job.result.get("outputPath", "")))
        if not output_path.exists():
            raise HTTPException(status_code=404, detail={"code": "EXPORT_FILE_NOT_FOUND", "message": "Export file was not found"})
        filename = str(job.result.get("filename") or output_path.name)
        return FileResponse(output_path, media_type="video/mp4", filename=filename)

    @app.get("/tiles/esri/{z}/{x}/{y}")
    def get_esri_tile(z: int, x: int, y: int) -> Response:
        if z < 1 or z > 22 or x < 0 or y < 0:
            raise HTTPException(status_code=422, detail={"code": "INVALID_TILE", "message": "Invalid tile coordinates"})
        try:
            tile = tiles.get_tile(z, x, y)
        except MapDownloadError as exc:
            raise HTTPException(status_code=503, detail={"code": "MAP_DOWNLOAD_FAILED", "message": str(exc)}) from exc

        buffer = BytesIO()
        tile.save(buffer, format="JPEG", quality=90)
        return Response(content=buffer.getvalue(), media_type="image/jpeg")

    resolved_static_dir = static_dir or _default_static_dir()
    if resolved_static_dir is not None and resolved_static_dir.exists():
        index_path = resolved_static_dir / "index.html"

        @app.get("/")
        def index() -> Response:
            if not index_path.exists():
                raise HTTPException(status_code=404, detail={"code": "WEB_UI_NOT_BUILT", "message": "Web UI is not built"})
            return Response(content=index_path.read_text(encoding="utf-8"), media_type="text/html")

        assets_dir = resolved_static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    return app


def _parse_log(path: str, cancel_token: CancellationToken) -> FlightLogData:
    if cancel_token.is_cancelled():
        raise RuntimeError("Job cancelled before parsing started")
    return parse_bin_log(path)


def _render_export(
    path: str,
    options: ExportOptionsRequest,
    output_path: Path,
    cancel_token: CancellationToken,
    progress: ProgressFunction,
    parser: ParseFunction,
    tile_provider: TileProvider | None,
) -> dict:
    if cancel_token.is_cancelled():
        raise RenderCancelled("Export cancelled before rendering started")

    log_data = parser(path, cancel_token)
    compressed_duration = options.compressed_duration_s if options.time_mode == "compressed" else None
    overlays = options.overlays

    def render_progress(percent: int, status: str) -> None:
        phase = "encoding" if percent >= 98 else "rendering"
        progress(phase, percent, status)

    render_video(
        log_data,
        RenderOptions(
            output_path=output_path,
            width=options.width,
            height=options.height,
            fps=options.fps,
            render_mode=options.render_mode,
            altitude_scale_mode=options.altitude_scale_mode,
            export_view_mode=options.view_mode,
            true_flight_only=options.range != "full-log",
            compressed_duration_s=compressed_duration,
            show_waypoints=overlays.get("waypoints", True) and options.waypoint_mode != "hidden",
            show_altitude=overlays.get("altitude", True),
            show_speed=overlays.get("speed", True),
            show_progress=overlays.get("progress", True),
        ),
        progress_callback=render_progress,
        tile_provider=tile_provider,
        cancel_check=cancel_token.is_cancelled,
    )
    return {
        "width": options.width,
        "height": options.height,
        "fps": options.fps,
        "timeMode": options.time_mode,
    }


def _serialize_log(log_data: FlightLogData) -> dict:
    selected_points = log_data.selected_points(true_flight_only=True)
    return {
        "schemaVersion": "flight-log.v1",
        "path": str(log_data.path),
        "summary": {
            "gpsCount": log_data.gps_count,
            "totalDurationS": log_data.total_duration_s,
            "selectedDurationS": _duration(selected_points),
            "maxRelativeAltitudeM": log_data.max_altitude_m,
            "maxSpeedMS": log_data.max_speed_m_s,
            "waypointCount": len(log_data.waypoints),
            "trueFlightDetected": log_data.true_flight_detected(),
        },
        "points": [_track_point_to_dict(point) for point in log_data.points],
        "selectedPoints": [_track_point_to_dict(point) for point in selected_points],
        "waypoints": [_waypoint_to_dict(waypoint) for waypoint in log_data.waypoints],
        "messageCounts": dict(log_data.message_counts),
    }


def _track_point_to_dict(point: TrackPoint) -> dict:
    return {
        "timeS": point.time_s,
        "lat": point.lat,
        "lon": point.lon,
        "relAltM": point.rel_alt_m,
        "altM": point.alt_m,
        "speedMS": point.speed_m_s,
        "headingDeg": point.heading_deg,
    }


def _waypoint_to_dict(waypoint: Waypoint) -> dict:
    return {
        "seq": waypoint.seq,
        "lat": waypoint.lat,
        "lon": waypoint.lon,
        "altM": waypoint.alt_m,
        "command": waypoint.command,
    }


def _duration(points: list[TrackPoint]) -> float:
    if len(points) < 2:
        return 0.0
    return max(0.0, points[-1].time_s - points[0].time_s)


def _default_static_dir() -> Path | None:
    return Path(__file__).resolve().parents[1] / "web" / "dist"


app = create_app()
