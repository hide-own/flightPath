## Context

The project currently has a working Python/PySide6 MVP that parses Mission Planner / ArduPilot `.bin` logs, downloads and caches Esri satellite tiles, renders a 2D trajectory with Pillow, and writes MP4 output. That MVP validated the core data path, but the UI is limited for interactive preview, timeline scrubbing, modern visual states, map manipulation, and 3D altitude visualization.

This change upgrades the product to a local Web application: a Vue3 browser UI opened by a Windows launcher, backed by a FastAPI service bound to localhost. User data stays local. The browser provides an excellent WebGL map environment without Electron packaging, while Python remains the best first-version backend because the existing parser already depends on `pymavlink`.

## Goals / Non-Goals

**Goals:**

- Build a Vue3 + TypeScript + Vite browser UI using Naive UI, Pinia, and lucide-vue-next.
- Provide a one-click Windows launch path that starts the local FastAPI service and opens the browser UI.
- Reuse and stabilize the Python `.bin` parsing engine through local HTTP APIs.
- Keep the FastAPI service responsive through explicit job management, bounded worker pools, progress streaming, and cancellation.
- Provide an interactive satellite map preview with zoom, pan, pitch/bearing where applicable, play/pause, and draggable timeline scrubbing.
- Add a first-version 3D trajectory mode that visualizes `RelAlt` by elevating the route and marker above the satellite map.
- Make export framing predictable: default to the current preview view, with auto-fit and follow-vehicle alternatives.
- Generate playable MP4 output with marker motion based on real log timestamps or proportionally scaled compressed time.
- Retain offline map cache behavior and explicit map download failure reporting.

**Non-Goals:**

- Electron shell, Electron packaging, or Electron IPC for this version.
- Java backend implementation for this version; Java remains an evaluated alternative.
- Pure Java DataFlash parsing or replacement of `pymavlink`.
- Real DEM terrain, terrain mesh, terrain-aware altitude, 3D buildings, or Cesium-like globe rendering.
- Replacing Mission Planner, editing missions, or uploading plans to aircraft.
- Cloud sync, accounts, collaboration, or remote project storage.
- Professional video editing features such as music, transitions, subtitles, or multi-camera editing.
- Supporting PX4, DJI, `.tlog`, or non-ArduPilot formats in this change.

## Decisions

### Local Web + FastAPI Instead Of Electron

Use the user's browser for the Vue3 UI and a localhost FastAPI service for backend work. A Windows launcher starts the backend on an available local port, opens the browser, and reports startup failures in Chinese.

Alternatives considered:

- Electron + Vue3 provides desktop file-system access and app-like packaging, but adds Chromium packaging, main/preload/IPC complexity, and a larger distribution.
- Java Spring Boot/Quarkus can provide strong concurrency, but pure Java DataFlash parsing is risky and Java + Python worker packaging would add another runtime. It may be revisited later if enterprise deployment or Java ecosystem integration becomes important.
- A cloud Web service is not appropriate for the first version because flight logs are local files and users expect offline/private operation.

### Vue3 + Naive UI Browser Interface

Use Vue3 + TypeScript + Vite for the frontend. Use Naive UI as the main component library, Pinia for state, and lucide-vue-next for icons.

The UI still follows the product layout already chosen: a left operation panel and a right map workspace. Running in a browser must not make the tool feel like a marketing website; it should be a focused local flight-analysis workspace.

### Local API Boundaries

Expose backend behavior through versioned local APIs:

- `POST /api/logs/parse` starts a parse job and returns a job id.
- `GET /api/jobs/{job_id}` returns job state and result summary when available.
- `GET /api/jobs/{job_id}/events` streams progress through Server-Sent Events.
- `POST /api/jobs/{job_id}/cancel` requests cancellation.
- `GET /tiles/esri/{z}/{x}/{y}` serves cached/downloaded satellite tiles.
- `POST /api/exports` starts an export job.
- `GET /api/exports/{job_id}/download` downloads the completed MP4.

The API should be bound to `127.0.0.1` by default. CORS should allow only the local frontend origin used by the launcher/dev server.

### Background Job Manager

API handlers must not perform heavy work inline. Add a job manager that owns job ids, status, progress, cancellation tokens, and results.

Recommended first-version concurrency:

- Parse worker pool: 1-2 workers because DataFlash parsing is CPU and I/O heavy but usually short enough.
- Tile worker pool: 4-8 workers for network-bound tile fetch/cache operations.
- Export worker pool: default 1 concurrent export to avoid CPU/GPU/ffmpeg contention.
- Progress channel: SSE event stream backed by an in-memory event queue per job.

The job manager should survive normal request lifetimes but does not need persistent database storage in the first version.

### File Selection And Output Strategy

The browser cannot write arbitrary paths without user consent. Support two first-version output flows:

- Browser download: export creates an MP4 on the local service and the browser downloads it from `/api/exports/{job_id}/download`.
- Optional save path: if the frontend uses supported browser APIs or the user supplies an allowed output directory/path through the launcher/API, the service may write to that path.

The default acceptance path should be browser download because it is reliable across local Web deployment.

### Map Tile Access Through FastAPI

The current Python tile cache behavior should remain the offline authority. The browser map preview should request tiles through the local FastAPI service rather than directly from Esri. This keeps preview, export, offline behavior, and failure messages consistent.

### WebGL Preview With Shared Scene State

Use MapLibre GL JS for the satellite map and a WebGL overlay such as deck.gl or Three.js for route, marker, waypoint, and 3D altitude layers. Store all camera and display state in a shared preview state object:

- center longitude/latitude
- zoom
- pitch
- bearing
- render mode: 2D or 3D
- altitude scale mode/value
- overlay visibility
- waypoint display mode
- timeline time

This state is the contract between interactive preview and export.

### First-Version 3D Means Relative-Altitude Visualization

The 3D mode will lift route coordinates by `RelAlt`, not by terrain-following altitude. The UI should make this clear in concise wording: altitude is relative to the takeoff/reference point from the log. Use an altitude scale control with sensible modes:

- auto: fits typical height variation into a readable scene
- real ratio: uses the map projection as closely as practical
- enhanced: exaggerates altitude for visual clarity

Auto should be the default because many flights have small horizontal areas but meaningful vertical change.

### Export Uses Preview State by Default

Export should default to "current preview view": the user adjusts the right map and the exported video uses the same center, zoom, pitch, bearing, render mode, altitude scale, overlays, and waypoint mode.

Alternative view modes:

- Auto-fit full route: recompute camera from selected track and waypoints with padding for HUD and progress overlays.
- Follow vehicle: keep the current marker near a stable screen position while preserving real timestamp motion.

For preview-aligned 3D export, the preferred implementation is to render frames from the same WebGL scene in a deterministic export renderer and encode them with the bundled ffmpeg path. The old Pillow renderer can remain useful for legacy 2D fallback, but it should not be the source of truth for 3D visual output.

### Timing Model Remains Timestamp-Based

For preview playback, scrubbing, and export, map video time to log time using parsed timestamps. Compressed duration mode scales the selected log interval to the requested output duration while preserving relative timestamp gaps. No preview or export path should move the marker by uniform point index spacing.

### Waypoint Display Modes

Replace oversized all-number rendering with explicit modes:

- hidden: no waypoint layer
- points only: compact point markers without labels
- compact: label start/end/current/next/key waypoints and avoid dense collisions
- all numbers: show every waypoint label using small, collision-aware labels

Compact should be the default for polished visuals.

## Risks / Trade-offs

- Browser file-system restrictions can make arbitrary output paths awkward -> Use browser download as the default output flow and add optional save-path support only where reliable.
- WebGL export can be nondeterministic if map tiles or layers are still loading -> Add export readiness checks for tile availability, font/icon readiness, and WebGL layer completion before frame capture.
- Current Python Pillow renderer cannot reproduce 3D preview -> Treat WebGL scene rendering as the source for 3D export and keep Pillow only as a fallback or compatibility path.
- MapLibre direct network requests could bypass cache rules -> Route map tile access through the local FastAPI tile endpoint.
- Long logs can overload preview layers -> Downsample route display for interaction while preserving full timestamp data for interpolation and export.
- Long-running work can make the API appear frozen -> Run parse/tile/export work through bounded background workers and stream progress.
- Multiple exports can saturate CPU/GPU/ffmpeg -> Limit concurrent exports to 1 by default and queue additional requests.
- Altitude visualization can mislead users into thinking terrain is real -> Label the mode as relative-altitude 3D and defer DEM terrain explicitly.
- Local service startup can fail because a port is occupied -> Choose an available localhost port and pass it to the launcher/browser.
- Map service failures can break preview and export -> Preserve tile cache use and surface a clear "map download failed" state when required tiles are missing.

## Migration Plan

1. Keep the existing Python application runnable while adding local API modules in parallel.
2. Add FastAPI dependencies and a local API entry point that can run without starting PySide6.
3. Add the job manager, progress event stream, cancellation tokens, and API contract tests.
4. Expose `.bin` parsing through parse jobs and normalized JSON responses.
5. Expose Esri tile cache through the local tile endpoint.
6. Build the Vue3 browser UI and connect it to parse/status/events APIs.
7. Add 2D preview parity, timeline scrubbing, and real timestamp interpolation.
8. Add 3D trajectory layers and altitude scale controls.
9. Add preview-state export and MP4 download.
10. Update launch scripts to start FastAPI and open the browser UI.
11. Keep the old PySide6 path as a temporary fallback until local Web acceptance passes, then remove or mark it as legacy.

Rollback strategy: if local Web export blocks release, keep the PySide6 MVP as the available stable app and ship the local Web work only after preview/export acceptance is met.

## Open Questions

- Whether the 3D overlay implementation should start with deck.gl or a focused Three.js layer. Both are viable; deck.gl is better integrated with MapLibre, while Three.js gives lower-level control for custom export scenes.
- Whether deterministic 3D frame export should run from a browser-controlled capture page, a headless browser, or a backend-driven rendering process. The preview state object should make this swappable.
