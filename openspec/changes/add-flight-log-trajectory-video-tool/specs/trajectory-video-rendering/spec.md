## ADDED Requirements

### Requirement: MP4 Video Output
The system SHALL generate a playable `.mp4` video at the user-selected output path.

#### Scenario: Generation succeeds
- **WHEN** the user starts generation with a valid log, valid map background, and writable output path
- **THEN** the system writes an `.mp4` file to the selected output path
- **AND** the resulting file can be opened by Windows Media Player or another standard MP4 player
- **AND** the video metadata reports the selected resolution and frame rate

#### Scenario: Output path is not writable
- **WHEN** the selected output path cannot be written
- **THEN** generation fails with a clear error message
- **AND** the system does not report success

### Requirement: Real Timestamp Marker Motion
The system SHALL move the current-position red marker according to parsed log timestamps rather than uniform GPS point spacing.

#### Scenario: Uneven timestamp gaps exist
- **WHEN** consecutive GPS points have uneven timestamp gaps
- **THEN** the red marker spends proportionally more video time across longer log-time gaps
- **AND** the red marker spends proportionally less video time across shorter log-time gaps

#### Scenario: Vehicle pauses in the log
- **WHEN** the log contains multiple seconds where the vehicle position changes very little
- **THEN** the rendered red marker remains near that position for the corresponding log-time duration in real-time mode

#### Scenario: Synthetic uneven timing verification
- **WHEN** a synthetic track contains points at 0 seconds, 1 second, and 11 seconds
- **THEN** the rendered frame count spent between the second and third points is 10 times the frame count spent between the first and second points in real-time mode
- **AND** the timing error is no more than one output frame interval

### Requirement: Compressed Timeline Mode
The system SHALL support compressing the selected log timeline to a user-specified output duration while preserving relative timing within the selected range.

#### Scenario: User selects compressed duration
- **WHEN** the user selects compressed mode and enters a target duration
- **THEN** the output video duration differs from the requested duration by no more than one output frame interval
- **AND** marker motion is based on scaled log timestamps rather than equal spacing across GPS points

### Requirement: Real-Time Timeline Mode
The system SHALL default to real-time mode where one second of selected log time maps to one second of video time within one output frame interval.

#### Scenario: User keeps default time mode
- **WHEN** the user generates a video without enabling compressed duration
- **THEN** the output timeline follows the selected log duration at real-time speed

### Requirement: Required Visual Overlays
The system SHALL render the satellite background, full route line, current red marker, waypoint numbers, altitude, speed, elapsed time, and progress bar when their display options are enabled.

#### Scenario: All display options enabled
- **WHEN** the user generates a video with all default display options enabled
- **THEN** each frame includes the satellite map background
- **AND** each frame includes the flight route line
- **AND** each frame includes the current red marker
- **AND** frames display waypoint numbers for extracted waypoints
- **AND** frames display current altitude, current speed, elapsed time, and progress bar

#### Scenario: Optional overlay disabled
- **WHEN** the user disables a supported overlay option before generation
- **THEN** the disabled overlay is omitted from the rendered frames
- **AND** required map and marker rendering still occurs

#### Scenario: Dense waypoint labels are rendered
- **WHEN** multiple waypoint labels appear close together
- **THEN** waypoint number markers remain compact enough to avoid dominating the map
- **AND** waypoint labels remain readable without unnecessarily covering the route or satellite background

### Requirement: Resolution And Frame Rate
The system SHALL render using the selected output resolution and frame rate, defaulting to 1280x720 at 24 fps.

#### Scenario: Default render settings are used
- **WHEN** the user does not change video settings
- **THEN** the generated video uses 1280x720 resolution
- **AND** the generated video uses 24 frames per second

#### Scenario: User changes render settings
- **WHEN** the user selects a supported resolution or frame rate
- **THEN** the generated video uses the selected settings

### Requirement: Static Preview
The system SHALL provide a preview of the selected trajectory before video generation.

#### Scenario: User requests preview
- **WHEN** a valid log has been parsed and the user clicks preview
- **THEN** the system renders a static preview showing the satellite background, route, waypoints when available, and an initial marker
- **AND** the preview does not require generating the full MP4

### Requirement: Cancelable Rendering
The system SHALL allow an active video render to be cancelled without reporting a successful output.

#### Scenario: User cancels rendering
- **WHEN** the user cancels while video rendering is in progress
- **THEN** the renderer stops at a safe frame boundary
- **AND** video writer resources are closed
- **AND** any incomplete output file is deleted or clearly marked as incomplete
- **AND** the UI reports that generation was cancelled rather than completed

#### Scenario: User cancels during map loading
- **WHEN** the user cancels while map tiles are being loaded or downloaded
- **THEN** pending work stops as soon as practical
- **AND** generation does not proceed to video encoding
