## Context

The tool targets Windows users who fly ArduPilot vehicles, export Mission Planner `.bin` logs, and want a simple desktop workflow for producing trajectory videos. The current project has no approved OpenSpec baseline; this change establishes the requirements and implementation plan for a Python desktop application.

The application must combine four concerns that should remain independently testable: DataFlash log ingestion, map tile retrieval/caching, frame/video rendering, and UI orchestration. The supplied sample log demonstrates older ArduPilot DataFlash fields such as `GPS.Lat`, `GPS.Lng`, `GPS.RelAlt`, `GPS.Spd`, `GPS.T`, and `CMD` waypoint records, so parsing must tolerate field-name and unit differences across ArduPilot versions.

## Goals / Non-Goals

**Goals:**

- Provide a Windows GUI that lets users select a `.bin` log, choose an output `.mp4`, preview the trajectory, and generate the video with progress feedback.
- Provide a one-click Windows launch path so normal users can start the GUI by double-clicking a shortcut or executable, without opening a terminal or seeing a command prompt window.
- Make the UI visually polished and comfortable for repeated use, with a clear Chinese interface, a professional flight/mission-control visual direction, strong visual hierarchy, balanced spacing, and reliable layout at common Windows scaling settings.
- Parse GPS track, mission waypoints, altitude, speed, and log timestamps from Mission Planner / ArduPilot DataFlash logs.
- Default to the true flight phase using `RelAlt > 2m`, while preserving an option to render the full log.
- Render an MP4 with Esri World Imagery satellite background, route, waypoint numbers, current red marker, altitude, speed, elapsed time, and progress bar.
- Preserve real log timing for marker movement; compressed-duration output may scale the whole timeline but must not make point-to-point movement uniformly spaced.
- Cache downloaded map tiles, show cache behavior clearly, and give a clear failure state when network download is unavailable and required tiles are missing.
- Allow users to cancel long-running video generation without leaving a successful-looking partial output behind.

**Non-Goals:**

- Support for PX4, DJI, `.tlog`, `.log`, or non-ArduPilot formats in the initial change.
- Editing mission plans, uploading to vehicles, or replacing Mission Planner.
- Advanced video editing features such as music, multiple camera views, 3D terrain, or user-defined map providers.
- A packaging requirement for a signed installer; packaging can be planned after the MVP is validated.

## Decisions

### Python Desktop Stack

Use Python with PySide6 for the desktop UI, `pymavlink` for `.bin` parsing, Pillow for frame drawing, and `imageio` with `imageio-ffmpeg` for MP4 output.

Alternatives considered:

- Native C# / WPF would integrate well with Windows, but it would require more work to parse ArduPilot DataFlash logs and render frames.
- A web app would simplify preview UI, but it would complicate local file access, ffmpeg availability, and offline use.

### Log Data Model

Normalize parsed logs into `TrackPoint` and `Waypoint` records before rendering. `TrackPoint` should include timestamp seconds, latitude, longitude, relative altitude, optional absolute altitude, speed, and optional heading. Waypoints should include sequence number, coordinates, altitude, and command when available.

This keeps rendering independent from raw MAVLink message variations and allows tests to use synthetic tracks without reading `.bin` files.

### Timing Model

Use log timestamps as the authoritative timeline. For each output frame, convert video time to a log time, find surrounding track points, and interpolate position, altitude, and speed. In compressed mode, scale the full log-time interval into the requested output duration while preserving relative gaps between timestamps.

This directly prevents the failure mode where the red marker moves uniformly through all GPS points regardless of real flight speed or pauses.

Timing behavior should be validated with a synthetic track that has intentionally uneven timestamp gaps, so tests can prove the renderer is not using point-index spacing.

### Flight Range Selection

Default range selection uses the first through last GPS point whose relative altitude exceeds 2 meters, with a default 3 second buffer before the first threshold-crossing point and after the last threshold-crossing point, clipped to the valid GPS range. If no point exceeds the threshold, the application should report that no true-flight phase was detected and offer the full valid GPS range as the explicit fallback selection instead of silently switching ranges or producing an empty video.

The threshold should be represented as a configuration value so later UI work can expose it without changing the parser or renderer contracts.

### Satellite Map Background

Use Esri World Imagery XYZ tiles and cache them under a deterministic local cache directory. The renderer chooses a Web Mercator zoom level that fits the selected track and waypoints within the output resolution, downloads or reads the needed tiles, then crops the composed map to the video frame.

If all required tiles are cached, generation works offline. If any required tile is missing and download fails, the UI reports "地图下载失败" and does not silently render a wrong or blank map. Rendered videos should include visible map attribution, and the UI or documentation should expose where the cache is stored and how to clear it.

### Launch Experience

Provide a normal-user launch artifact in addition to any developer command. The preferred delivery is a Windows shortcut backed by `pythonw` or a packaged executable that starts the GUI without requiring the user to type a command and without leaving a command prompt window open. During development, a script may exist, but the user-facing path should avoid leaving users inside a command-line workflow.

The launch path should either open the main window within 5 seconds on a ready environment or show a localized dependency/startup error that explains what is missing.

This keeps the tool aligned with the requirement that it is a desktop utility, not a command-line utility with a thin wrapper.

### UI Visual Quality

Use a restrained, modern desktop layout with a professional flight/mission-control feel: a clear title, grouped file and generation controls, a readable log-summary/status area, an emphasized primary generate action, status colors that are easy to understand, and consistent spacing. The interface should be localized in Chinese for user-facing labels and messages. It should avoid crowded controls, clipped text, overlapping widgets, and default-looking unstyled layouts.

Visual quality should be checked at minimum at 1280x720 and 1920x1080 windows, and at common Windows display scaling such as 100%, 125%, and 150%. Acceptance should include saved screenshots for normal, parsing-complete, rendering, failure, and completed states.

### UI and Worker Boundary

Keep long-running parse, preview, map download, and rendering work off the UI thread. Worker progress messages should be surfaced as percentages and human-readable states such as parsing, loading map, rendering frame time, cancelling, completed, and failed.

The UI should validate required inputs before starting generation and should not freeze while the video is being rendered. Cancellation should ask the renderer to stop at a safe frame boundary, close the video writer, and delete or clearly mark any incomplete output file.

## Risks / Trade-offs

- ArduPilot log field drift -> Use tolerant field extraction and unit normalization, and add tests using both real and synthetic log samples.
- Satellite map network failure -> Cache tiles by provider/zoom/x/y and fail with an explicit localized message when missing tiles cannot be fetched.
- Long logs can render slowly -> Stream frames directly to the video writer, report progress regularly, and avoid holding all video frames in memory.
- Old logs may lack complete waypoint records -> Render the trajectory even when waypoint extraction returns zero valid waypoints; report the count in the summary.
- `imageio-ffmpeg` codec availability may vary -> Use bundled ffmpeg from the dependency and include a startup or generation-time error that tells the user video encoding failed.
- High-resolution videos increase tile and rendering cost -> Provide default 1280x720 at 24 fps and allow users to choose higher resolution only when needed.
- One-click launch may differ between development and packaged delivery -> Specify the user-facing launch artifact separately from developer commands and test it by double-clicking.
- "Good-looking UI" can be subjective -> Convert it into a visual acceptance checklist covering hierarchy, spacing, Chinese text, scaling, and absence of clipping or overlap.
- Cancellation can corrupt an MP4 if the writer is not closed cleanly -> Handle cancellation through the render loop, close ffmpeg/imageio resources, and prevent partial files from being reported as successful output.
