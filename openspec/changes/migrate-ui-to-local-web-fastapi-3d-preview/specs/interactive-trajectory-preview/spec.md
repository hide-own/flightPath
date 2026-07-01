## ADDED Requirements

### Requirement: Interactive Satellite Map Preview
The system SHALL provide an interactive satellite map preview for the selected log and selected playback range.

#### Scenario: Log is parsed successfully
- **WHEN** valid flight log data is available
- **THEN** the right map workspace displays a satellite map centered on the selected flight region
- **AND** the full selected route is visible using an automatically computed initial camera

#### Scenario: User manipulates the map
- **WHEN** the user scrolls the mouse wheel over the map
- **THEN** the map zoom level changes
- **AND** the route and overlays remain aligned with the satellite background

#### Scenario: User drags the map
- **WHEN** the user drags inside the map workspace
- **THEN** the map pans
- **AND** the route and overlays remain aligned with the satellite background

### Requirement: Timeline Scrubbing And Playback
The system SHALL provide timeline controls for previewing marker motion using real log timestamps.

#### Scenario: User drags timeline
- **WHEN** the user drags the timeline thumb to a different time
- **THEN** the current marker moves to the interpolated position for that log timestamp
- **AND** the altitude, speed, elapsed time, and progress displays update to match the selected time

#### Scenario: User plays preview
- **WHEN** the user starts preview playback
- **THEN** the current marker advances according to real log timestamps in real-time mode
- **AND** uneven timestamp gaps are reflected by proportionally uneven marker motion

#### Scenario: User pauses preview
- **WHEN** the user pauses preview playback
- **THEN** the marker remains at the current timeline position
- **AND** the user can resume or scrub from that position

### Requirement: Display Overlay Controls
The system SHALL allow users to control visible map and video overlays.

#### Scenario: User toggles overlay options
- **WHEN** the user changes altitude, speed, progress, route, current marker, or waypoint visibility options
- **THEN** the preview updates to reflect the selected overlay state
- **AND** subsequent video export uses the same selected overlay state by default

### Requirement: Waypoint Display Modes
The system SHALL provide waypoint display modes for hidden, points only, compact, and all-number rendering.

#### Scenario: Hidden waypoint mode is selected
- **WHEN** the user selects hidden waypoint mode
- **THEN** waypoint markers and waypoint labels are not displayed

#### Scenario: Points-only waypoint mode is selected
- **WHEN** the user selects points-only waypoint mode
- **THEN** waypoint locations are displayed as compact markers without numeric labels

#### Scenario: Compact waypoint mode is selected
- **WHEN** the user selects compact waypoint mode
- **THEN** the preview labels only important waypoints such as start, end, current, next, or key turn points
- **AND** dense labels are avoided when they would clutter the map

#### Scenario: All-number waypoint mode is selected
- **WHEN** the user selects all-number waypoint mode
- **THEN** every extracted waypoint number is displayed with compact styling
- **AND** labels remain smaller than the current marker and do not dominate the route

### Requirement: Preview State Persistence During Session
The system SHALL preserve preview camera and display state while the same log remains loaded.

#### Scenario: User changes preview view
- **WHEN** the user zooms, pans, changes pitch or bearing, switches waypoint mode, or changes overlays
- **THEN** the preview state is stored in application state
- **AND** the state remains active until the user resets the view or loads a different log

### Requirement: Auto-Fit Preview Camera
The system SHALL compute an initial preview camera that fits the selected trajectory and waypoints.

#### Scenario: Initial camera is computed
- **WHEN** a log is parsed and a playback range is selected
- **THEN** the system computes a map center and zoom that fit the selected route and available waypoints
- **AND** the computed view includes padding for map edges, HUD overlays, and timeline/progress display

#### Scenario: Track is very short
- **WHEN** the selected route covers a very small geographic area
- **THEN** the system limits maximum zoom to avoid over-magnifying the map

#### Scenario: Track is very large
- **WHEN** the selected route covers a large geographic area
- **THEN** the system lowers zoom enough to keep the route visible
- **AND** the route remains visually distinguishable
