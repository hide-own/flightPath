## ADDED Requirements

### Requirement: Preview-Aligned Export View
The system SHALL use the current preview view as the default video export view.

#### Scenario: User exports after adjusting preview
- **WHEN** the user zooms, pans, changes pitch, changes bearing, switches 2D/3D mode, changes altitude scale, or changes overlays before export
- **THEN** the export uses those current preview settings by default
- **AND** the exported video framing substantially matches the preview framing

### Requirement: Export View Modes
The system SHALL provide export view modes for current preview view, auto-fit full route, and follow-vehicle view.

#### Scenario: Current preview view is selected
- **WHEN** the user exports with current preview view mode selected
- **THEN** the video uses the stored preview center, zoom, pitch, bearing, render mode, altitude scale, overlay options, and waypoint mode

#### Scenario: Auto-fit full route is selected
- **WHEN** the user exports with auto-fit full route mode selected
- **THEN** the system computes a camera that keeps the selected route and relevant waypoints visible
- **AND** the computed view reserves padding for HUD, progress, and frame edges

#### Scenario: Follow-vehicle view is selected
- **WHEN** the user exports with follow-vehicle view mode selected
- **THEN** the video camera follows the current marker over time
- **AND** camera movement is smoothed enough to avoid abrupt jumps during normal GPS updates

### Requirement: Real Timestamp Export Motion
The system SHALL move the exported current-position marker according to parsed log timestamps rather than uniform GPS point spacing.

#### Scenario: Uneven timestamp gaps exist
- **WHEN** consecutive GPS points have uneven timestamp gaps
- **THEN** the exported marker spends proportionally more video time across longer log-time gaps
- **AND** the exported marker spends proportionally less video time across shorter log-time gaps

#### Scenario: Vehicle pauses in the log
- **WHEN** the log contains multiple seconds where position changes very little
- **THEN** the exported marker remains near that position for the corresponding log-time duration in real-time mode

### Requirement: Compressed Duration Export
The system SHALL support exporting the selected log range to a specified compressed duration while preserving relative timestamp spacing.

#### Scenario: Compressed duration is selected
- **WHEN** the user selects compressed duration mode and enters a valid target duration
- **THEN** the output video duration matches the target duration within one output frame interval
- **AND** marker motion is based on scaled log timestamps rather than equal point spacing

### Requirement: MP4 Output And Download
The system SHALL generate a playable `.mp4` video and make it available through the local Web application.

#### Scenario: Export succeeds
- **WHEN** the user exports with a valid log, valid map background, and valid export view
- **THEN** the system creates an `.mp4` result for the export job
- **AND** the browser can download the completed video from the local API service
- **AND** the downloaded file opens in a standard MP4 player
- **AND** the video uses the selected resolution and frame rate

#### Scenario: Optional save path is provided
- **WHEN** the user or launcher provides a supported local save path for export
- **THEN** the system writes the `.mp4` file to that path if it is writable
- **AND** the completed video remains downloadable through the browser UI

#### Scenario: Optional save path is not writable
- **WHEN** an optional save path is provided but cannot be written
- **THEN** export fails with a clear localized error
- **AND** the system does not report success

### Requirement: Export Progress And Status
The system SHALL display export progress, status, cancellation, and failure information in the UI.

#### Scenario: Export is running
- **WHEN** video export is in progress
- **THEN** the UI displays progress
- **AND** the UI displays a status phase such as preparing map, rendering frames, encoding video, completed, cancelling, cancelled, or failed

#### Scenario: User cancels export
- **WHEN** the user cancels while export is active
- **THEN** export stops at a safe boundary as soon as practical
- **AND** incomplete output is deleted or clearly marked incomplete
- **AND** the UI reports cancelled rather than completed

#### Scenario: Export fails
- **WHEN** map loading, frame rendering, encoding, or file writing fails
- **THEN** export stops
- **AND** the UI displays the failure reason
- **AND** no partial file is presented as a successful video

### Requirement: Map Availability For Export
The system SHALL verify required map tiles are available before or during export and fail clearly when they are not.

#### Scenario: Tiles are cached
- **WHEN** all required map tiles for the selected export view are already cached
- **THEN** export can proceed without network access

#### Scenario: Tiles are missing and cannot be downloaded
- **WHEN** required export map tiles are missing and download fails
- **THEN** export fails with a map download failure message
- **AND** the video is not rendered with blank placeholder map areas

### Requirement: 3D Export Parity
The system SHALL support exporting the first-version 3D trajectory view.

#### Scenario: 3D mode is exported
- **WHEN** the user exports while 3D trajectory mode is active
- **THEN** the output video includes the elevated route, elevated current marker, height guide or shadow, satellite map ground reference, and selected HUD overlays
- **AND** the exported 3D scene uses the selected altitude scale mode
