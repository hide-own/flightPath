## 1. Project Structure And Tooling

- [x] 1.1 Add local Web project structure for Vue3 + TypeScript + Vite without removing the existing Python MVP path.
- [x] 1.2 Add frontend dependencies for Naive UI, Pinia, lucide-vue-next, MapLibre GL JS, and the selected WebGL overlay library.
- [x] 1.3 Add backend dependencies for FastAPI, ASGI serving, multipart uploads, and tests.
- [x] 1.4 Configure frontend linting, formatting, TypeScript checks, and unit test runner.
- [x] 1.5 Add development scripts for starting the FastAPI service and browser UI.

## 2. Local FastAPI Service And Job Manager

- [x] 2.1 Add a FastAPI application entry point that can run without starting the PySide6 UI.
- [x] 2.2 Define versioned JSON schemas for job creation, job status, parsed log responses, progress events, cancellation, and errors.
- [x] 2.3 Implement a bounded in-memory job manager with job ids, statuses, results, errors, progress events, and cancellation tokens.
- [x] 2.4 Implement a parse worker path that runs outside the HTTP request handler.
- [x] 2.5 Preserve true-flight range selection using `RelAlt > 2m` with configurable buffer.
- [x] 2.6 Surface structured parse and service errors with stable error codes.
- [x] 2.7 Add cancellation handling for long-running service operations.
- [x] 2.8 Add Server-Sent Events or equivalent streaming for job progress.
- [x] 2.9 Add contract tests for API request/response, job lifecycle, progress, cancellation, and error payloads.

## 3. Tile Cache And Map Access

- [x] 3.1 Expose cached Esri World Imagery tiles to the browser preview through a local FastAPI tile endpoint.
- [x] 3.2 Ensure preview tile requests use the existing cache before network download.
- [x] 3.3 Preserve unavailable/placeholder tile detection and failure behavior.
- [x] 3.4 Report localized map download failures when required tiles cannot be cached or served.
- [x] 3.5 Add tests for cached tile serving, missing tile failure, and offline cache success.

## 4. Browser UI And Naive UI Layout

- [x] 4.1 Implement the main two-pane layout with left operation panel and right map workspace.
- [x] 4.2 Build log file selection and MP4 export/download controls.
- [x] 4.3 Build playback range controls for true-flight phase and full log.
- [x] 4.4 Build time mode controls for real-time and compressed-duration export.
- [x] 4.5 Build display overlay controls for route, marker, waypoints, altitude, speed, and progress.
- [x] 4.6 Build render mode controls for 2D and 3D trajectory preview.
- [x] 4.7 Build export view mode controls for current preview, auto-fit full route, and follow vehicle.
- [x] 4.8 Build resolution and frame rate controls.
- [x] 4.9 Implement polished selected, disabled, loading, success, warning, and error visual states using Naive UI.
- [x] 4.10 Localize normal workflow labels, validation messages, status text, and errors in Chinese.
- [x] 4.11 Add component/state tests for key controls and disabled/selected visual states.

## 5. Flight Data State And Summary

- [x] 5.1 Add Pinia stores for loaded log data, selected range, preview state, export options, progress, and errors.
- [x] 5.2 Display GPS point count, selected flight duration, full log duration, maximum altitude, maximum speed, and waypoint count after parsing.
- [x] 5.3 Validate missing log file and missing export/download settings before preview/export actions.
- [x] 5.4 Reset or preserve preview state correctly when loading a new log versus changing options on the same log.

## 6. Interactive 2D Preview

- [x] 6.1 Render the satellite map in the right workspace using MapLibre GL JS.
- [x] 6.2 Render the selected 2D route, current marker, flown path, HUD, and progress overlays.
- [x] 6.3 Implement mouse wheel zoom and drag pan with overlay alignment.
- [x] 6.4 Implement automatic initial camera fitting with route/waypoint bounds and HUD padding.
- [x] 6.5 Add guardrails for very short and very large routes when computing initial zoom.
- [x] 6.6 Implement timeline thumb scrubbing with timestamp-based interpolation.
- [x] 6.7 Implement play and pause preview behavior using real log timestamps.
- [x] 6.8 Add preview tests for interpolation using uneven timestamp gaps.

## 7. Waypoint Display Modes

- [x] 7.1 Implement hidden waypoint mode.
- [x] 7.2 Implement points-only waypoint mode.
- [x] 7.3 Implement compact waypoint mode for start, end, current, next, and key waypoints.
- [x] 7.4 Implement all-number waypoint mode with compact labels.
- [x] 7.5 Add collision or density handling so waypoint labels do not dominate the map.
- [x] 7.6 Add visual tests or screenshots for dense waypoint display states.

## 8. 3D Relative-Altitude Preview

- [x] 8.1 Choose and integrate the WebGL overlay implementation for 3D route rendering.
- [x] 8.2 Render the route and current marker elevated by parsed `RelAlt` in 3D mode.
- [x] 8.3 Render a height guide, vertical line, ground shadow, or equivalent marker ground reference.
- [x] 8.4 Implement camera pitch and bearing controls in 3D mode.
- [x] 8.5 Implement altitude scale modes for auto, real-ratio, and enhanced visualization.
- [x] 8.6 Add UI wording that clarifies 3D height uses log relative altitude and not DEM terrain.
- [x] 8.7 Optimize long-route display geometry while preserving timestamp data for interpolation.
- [x] 8.8 Add automated or screenshot-based checks that 3D mode renders a nonblank elevated trajectory.

## 9. Preview-Aligned Video Export

- [x] 9.1 Define the shared preview/export state object containing camera, render mode, altitude scale, overlays, waypoint mode, and timeline settings.
- [x] 9.2 Implement current-preview export mode using the stored preview state.
- [x] 9.3 Implement auto-fit full route export mode with HUD and progress padding.
- [x] 9.4 Implement follow-vehicle export mode with smoothed camera motion.
- [x] 9.5 Implement real-time export duration using log timestamps.
- [x] 9.6 Implement compressed-duration export while preserving relative timestamp gaps.
- [x] 9.7 Render 2D export frames from the selected export view.
- [x] 9.8 Render 3D export frames from the selected export view.
- [x] 9.9 Encode frames to playable `.mp4` with selected resolution and frame rate.
- [x] 9.10 Block export when required map tiles are missing and cannot be downloaded.
- [x] 9.11 Add export cancellation that closes resources and removes or marks incomplete output.
- [x] 9.12 Add progress events for preparing map, rendering frames, encoding video, cancelling, completed, and failed.
- [x] 9.13 Add a local download endpoint for completed MP4 export jobs.

## 10. Launch, Packaging, And Migration

- [x] 10.1 Add a one-click Windows launch artifact for the local Web app.
- [x] 10.2 Ensure startup failures produce localized user-facing or logged errors.
- [x] 10.3 Start the FastAPI service on an available localhost port and open the browser UI.
- [x] 10.4 Keep the existing PySide6 MVP launch available as a temporary fallback until local Web acceptance passes.
- [x] 10.5 Update README and user-facing run instructions for the local Web app.

## 11. Verification And Acceptance

- [x] 11.1 Validate the OpenSpec change with strict validation.
- [x] 11.2 Run Python tests for parsing, range selection, map cache behavior, local API contracts, job concurrency, cancellation, and renderer compatibility.
- [x] 11.3 Run frontend unit/component tests for stores, controls, selected/disabled states, and validation.
- [x] 11.4 Run browser/API integration tests for log selection, parsed summary display, preview loading, and export validation.
- [x] 11.5 Verify with the supplied sample `.bin` logs that GPS count, duration, max altitude, and waypoint count are shown.
- [x] 11.6 Verify map zoom, pan, timeline scrubbing, play/pause, waypoint modes, and 2D/3D switching manually or with browser automation.
- [x] 11.7 Export at least one 2D MP4 and one 3D MP4 and confirm both download and play in a standard MP4 player.
- [x] 11.8 Verify exported marker motion follows uneven real timestamps rather than uniform GPS point index spacing.
- [x] 11.9 Verify offline cached tile success and missing-tile map download failure messaging.
- [x] 11.10 Capture acceptance screenshots for initial, parsed, 2D preview, 3D preview, exporting, failure, and completed states.
