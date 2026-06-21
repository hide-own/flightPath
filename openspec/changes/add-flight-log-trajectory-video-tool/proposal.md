## Why

Pilots who use Mission Planner / ArduPilot currently need several manual steps to turn a `.bin` flight log into a shareable route video with a satellite map background. This change defines a Windows desktop tool that lets a user select a log, inspect the parsed flight summary, and generate an MP4 video whose moving marker follows the log's real timing.

## What Changes

- Add a Windows graphical desktop application for creating flight trajectory videos from Mission Planner / ArduPilot `.bin` logs.
- Parse GPS track points, relative altitude, absolute altitude when available, ground speed, and mission waypoint records from ArduPilot DataFlash logs.
- Show log summary after file selection, including GPS point count, selected flight duration, maximum relative altitude, maximum speed, and waypoint count.
- Default the playback range to the true flight phase, identified by `RelAlt > 2m`, with a 3 second pre/post buffer and an explicit fallback path when no true-flight phase is detected.
- Generate a satellite map background centered on the flight area using Esri World Imagery tiles, with local tile caching, map attribution, cache management visibility, and a clear failure message when missing tiles cannot be downloaded.
- Render a trajectory video with route line, waypoint numbers, current red marker, altitude, speed, elapsed time, and progress bar.
- Move the red marker according to real log timestamps; compressed-duration output must preserve relative timing instead of playing points at uniform spacing.
- Let users choose output `.mp4` path, resolution, frame rate, display overlays, and real-time versus compressed-duration timing mode.
- Display generation progress and status in the UI, including map loading, rendering progress, cancellation, completion, and failure states.
- Provide a one-click Windows launch entry so the user can start the GUI without typing commands or seeing a command prompt window.
- Deliver a polished, modern, Chinese desktop UI with a professional flight/mission-control visual direction, clear visual hierarchy, attractive spacing, and no clipped or overlapping controls.

## Capabilities

### New Capabilities

- `flight-log-ingestion`: Select and parse ArduPilot `.bin` logs, extract flight data, identify true flight ranges, and expose summary metrics.
- `satellite-map-background`: Build a centered satellite map background from cached or downloaded Esri World Imagery tiles.
- `trajectory-video-rendering`: Generate MP4 trajectory videos that use log timestamps for marker motion and display required overlays.
- `desktop-generation-ui`: Provide a polished Windows desktop GUI for one-click launch, file selection, configuration, preview, generation progress, and error reporting.

### Modified Capabilities

None.

## Impact

- Adds a Python desktop application using PySide6 for the GUI.
- Uses `pymavlink` for ArduPilot DataFlash `.bin` parsing.
- Uses Pillow for frame composition, `imageio` with `imageio-ffmpeg` for MP4 output, and `requests` for map tile downloads.
- Adds local cache storage for satellite tiles and output video selection through the Windows file dialog.
- Adds a Windows launch artifact such as a desktop shortcut backed by `pythonw` or a packaged executable entry point.
- Adds visual QA expectations for layout, typography, spacing, localization, common Windows display scaling, and saved acceptance screenshots.
- Requires validation against at least one real Mission Planner / ArduPilot `.bin` log and a playable generated MP4.
