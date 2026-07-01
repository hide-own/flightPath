## Why

The current PySide6 MVP proves the flight-log-to-video workflow, but the next product step needs a more interactive and polished UI, timeline scrubbing, map manipulation, 3D altitude preview, and a simpler delivery path than a full Electron shell. A local Web application with a browser UI and localhost FastAPI service keeps user data on the machine, reuses the existing Python/pymavlink engine, and avoids Electron packaging complexity while still feeling like a one-click desktop tool.

## What Changes

- Replace the PySide6 user-facing workflow with a local Web UI built with Vue3 + TypeScript + Vite + Naive UI, opened in the user's browser by a one-click launcher.
- Provide a localhost FastAPI service as the app backend for `.bin` parsing, map tile cache access, long-running job management, progress streaming, cancellation, and MP4 export.
- Keep Python as the first-version backend implementation because the existing ArduPilot DataFlash parser uses `pymavlink`; Java API service options were considered but are deferred unless a future requirement justifies Java + Python worker packaging.
- Add a bounded concurrent job model: API handlers remain responsive, parsing runs in background jobs, map tile downloads use a small worker pool, and video export is limited to a controlled number of simultaneous jobs by default.
- Add an interactive right-side satellite map preview with mouse wheel zoom, drag pan, timeline scrubbing, play/pause, 2D/3D trajectory modes, and waypoint display modes.
- Add a first-version 3D trajectory view where the route and current marker are lifted by `RelAlt`, with altitude line/shadow treatment, current altitude/speed/time HUD, and an explicit note that this is relative-altitude visualization rather than DEM terrain.
- Make video export default to the current preview camera/view, with alternate export view modes for auto-fit full route and optional follow-vehicle framing.
- Preserve existing core workflow requirements: select `.bin`, choose or download `.mp4`, detect true-flight range with `RelAlt > 2m`, use real log timestamps, cache satellite map tiles, show progress/status, and generate playable MP4 output.
- Defer real DEM terrain, 3D buildings, accounts/cloud features, Java service migration, Electron packaging, and professional video editing tools from this first version.

## Capabilities

### New Capabilities

- `local-web-vue-ui`: Browser-based local Vue3 + Naive UI application structure, launcher behavior, layout, visual style, and UI state handling.
- `local-fastapi-service`: Localhost FastAPI service, API boundaries, background job management, progress streaming, cancellation, tile cache access, and export/download endpoints.
- `interactive-trajectory-preview`: Interactive satellite map preview, timeline controls, real-time marker scrubbing, map controls, overlay toggles, and waypoint display modes.
- `three-dimensional-trajectory-view`: 3D trajectory visualization using relative altitude, including altitude scaling, marker elevation, height guide/shadow, and 2D/3D mode switching.
- `preview-aligned-video-export`: MP4 export behavior that preserves real timestamp motion and uses the selected preview/export view mode.

### Modified Capabilities

- None. The project does not currently have accepted baseline specs under `openspec/specs/`; the completed MVP change remains historical context.

## Impact

- Adds a Vue3 browser frontend with dependencies such as Vite, TypeScript, Naive UI, Pinia, lucide-vue-next, MapLibre GL JS, and a WebGL trajectory layer such as deck.gl or Three.js.
- Adds local API dependencies such as FastAPI, an ASGI server, background task/executor utilities, and progress streaming support.
- Introduces stable JSON contracts for parsed flight logs, job creation, job status, progress events, errors, cancellation, tile requests, render options, and export results.
- Keeps existing Python modules available for DataFlash parsing, map tile caching, timing interpolation, and MP4 generation while exposing them through local HTTP APIs.
- Requires new tests across the FastAPI contracts, job concurrency/cancellation behavior, Vue state/components, map preview behavior, export view selection, and end-to-end generation with representative `.bin` logs.
