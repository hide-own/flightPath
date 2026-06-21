## 1. Project Setup

- [x] 1.1 Confirm Python runtime version and create an isolated virtual environment for the desktop tool.
- [x] 1.2 Add runtime dependencies for PySide6, pymavlink, Pillow, imageio, imageio-ffmpeg, requests, and test tooling.
- [x] 1.3 Define the application package structure for log ingestion, map tiles, rendering, UI, and launch artifacts.

## 2. Flight Log Ingestion

- [x] 2.1 Implement `.bin` file validation and user-facing parse errors.
- [x] 2.2 Implement ArduPilot DataFlash GPS parsing with timestamp, latitude, longitude, relative altitude, optional absolute altitude, speed, and heading normalization.
- [x] 2.3 Implement mission waypoint extraction with duplicate waypoint suppression.
- [x] 2.4 Implement true-flight range selection using `RelAlt > 2m`, a default 3 second pre/post buffer, clipped buffer edges, and explicit full-log fallback when no true-flight phase is detected.
- [x] 2.5 Implement summary metrics for GPS point count, selected duration, maximum relative altitude, maximum speed, and waypoint count.
- [x] 2.6 Add parser tests using synthetic records and at least one real Mission Planner / ArduPilot `.bin` log.

## 3. Satellite Map Background

- [x] 3.1 Implement Web Mercator projection helpers for lat/lon, tile coordinates, and frame coordinates.
- [x] 3.2 Implement Esri World Imagery tile retrieval and deterministic local tile caching.
- [x] 3.3 Implement map zoom selection and centering so selected tracks and waypoints fit inside the configured video frame.
- [x] 3.4 Implement offline behavior that uses cached tiles when available and reports "地图下载失败" when required missing tiles cannot be downloaded.
- [x] 3.5 Expose the tile cache location in documentation or UI and document how cached tiles can be cleared.
- [x] 3.6 Render readable Esri World Imagery attribution in previews and videos without covering required overlays.
- [x] 3.7 Add tests for projection, cache hits, cache misses, attribution placement, and download failure handling.

## 4. Video Rendering

- [x] 4.1 Implement static frame composition with satellite background, full route line, waypoint labels, and map attribution.
- [x] 4.2 Implement real-timestamp frame interpolation so marker motion follows log time instead of equal GPS point spacing.
- [x] 4.3 Implement compressed-duration mode that scales the log timeline while preserving relative timestamp gaps.
- [x] 4.4 Implement overlays for current red marker, altitude, speed, elapsed time, and progress bar with user-selectable visibility.
- [x] 4.5 Implement MP4 writing through imageio and imageio-ffmpeg at selected resolution and frame rate.
- [x] 4.6 Implement cancellation support in the renderer, including safe writer cleanup and deletion or marking of incomplete output files.
- [x] 4.7 Add rendering tests or golden-frame checks for synthetic uneven timestamp interpolation, compressed-duration one-frame tolerance, overlay toggles, MP4 metadata, cancellation cleanup, and MP4 output creation.

## 5. Desktop UI

- [x] 5.1 Implement the main PySide6 window with Chinese labels for log selection, output selection, map mode, playback range, time mode, compressed duration, display toggles, resolution, frame rate, preview, generate, progress, and status.
- [x] 5.2 Implement log file selection and automatic summary refresh after parsing.
- [x] 5.3 Implement output `.mp4` path selection and extension enforcement.
- [x] 5.4 Implement preview generation that shows the satellite background, route, waypoints, and initial marker without rendering the full video.
- [x] 5.5 Run parsing, preview, map loading, and rendering work outside the UI thread and stream progress/status updates back to the UI.
- [x] 5.6 Implement input validation and localized error messages for missing log file, missing output path, parse failure, map failure, encoding failure, and write failure.
- [x] 5.7 Implement a visible cancel control during preview or generation and return the UI to an operable idle state after cancellation completes.

## 6. Launch And Visual Polish

- [x] 6.1 Provide a one-click Windows launch entry such as a desktop shortcut backed by `pythonw` or a packaged executable that starts the GUI without typing a command or leaving a command prompt window open.
- [x] 6.2 Verify the one-click launch entry by double-clicking it on Windows and confirming the main window opens within 5 seconds on a ready environment.
- [x] 6.3 Implement a localized startup error path for missing runtime dependencies or launch failures.
- [x] 6.4 Apply a polished professional flight/mission-control visual style with clear grouping, spacing, typography, status colors, and an emphasized primary generate action.
- [x] 6.5 Verify the UI at common sizes including 1280x720 and 1920x1080.
- [x] 6.6 Verify the UI at Windows display scaling settings including 100%, 125%, and 150% with no clipped or overlapping important text.
- [x] 6.7 Capture acceptance screenshots for initial, parsing-complete, rendering, failure, and completed states.

## 7. End-To-End Acceptance

- [x] 7.1 Generate a preview from a real Mission Planner / ArduPilot `.bin` log and confirm summary metrics are displayed.
- [x] 7.2 Generate a real-time MP4 from the same log and confirm the output file plays in Windows Media Player or another standard MP4 player with the selected resolution and frame rate.
- [x] 7.3 Verify red marker motion against uneven log timestamp gaps using a synthetic 0s/1s/11s track so it is not uniform by point index.
- [x] 7.4 Verify the satellite map is centered on the flight area and waypoints are shown when available.
- [x] 7.5 Verify cached-map offline behavior or the required "地图下载失败" message when tiles are missing.
- [x] 7.6 Verify cancellation during map loading and rendering does not report success and does not leave a successful-looking partial MP4.
- [x] 7.7 Document installation, one-click launch, cache behavior, cache clearing, cancellation behavior, and troubleshooting steps for users.
