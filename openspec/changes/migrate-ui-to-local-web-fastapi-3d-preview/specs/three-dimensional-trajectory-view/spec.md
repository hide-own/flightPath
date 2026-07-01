## ADDED Requirements

### Requirement: 2D And 3D Trajectory Modes
The system SHALL allow users to switch between 2D trajectory preview and 3D relative-altitude trajectory preview.

#### Scenario: User selects 2D mode
- **WHEN** the user selects 2D trajectory mode
- **THEN** the route, marker, and waypoint overlays are drawn on the satellite map plane

#### Scenario: User selects 3D mode
- **WHEN** the user selects 3D trajectory mode
- **THEN** the route and current marker are elevated using parsed relative altitude
- **AND** the satellite map remains visible as the ground reference

### Requirement: Relative-Altitude 3D Rendering
The system SHALL render first-version 3D trajectory height from log relative altitude rather than DEM terrain.

#### Scenario: 3D route is displayed
- **WHEN** 3D mode is active and valid `RelAlt` values are available
- **THEN** higher relative altitude points appear visually higher than lower relative altitude points
- **AND** the 3D route preserves the same horizontal GPS path as the 2D route

#### Scenario: User views 3D mode note
- **WHEN** 3D mode is active
- **THEN** the UI communicates that height is based on log relative altitude
- **AND** the UI does not imply that real terrain elevation or DEM terrain is being shown

### Requirement: Current Marker Height Guide
The system SHALL provide a visual ground reference for the current marker in 3D mode.

#### Scenario: Marker is above map plane
- **WHEN** the current marker has positive relative altitude in 3D mode
- **THEN** the marker is displayed at its elevated position
- **AND** a height guide, vertical line, ground shadow, or equivalent visual reference connects the marker to the ground plane

### Requirement: Altitude Scale Controls
The system SHALL provide altitude scale options for 3D trajectory readability.

#### Scenario: Auto altitude scale is selected
- **WHEN** auto altitude scale mode is active
- **THEN** the system chooses a scale that keeps the 3D trajectory readable within the current map view
- **AND** the highest selected altitude does not routinely render outside the visible scene

#### Scenario: Real-ratio altitude scale is selected
- **WHEN** real-ratio altitude scale mode is active
- **THEN** altitude is displayed as close as practical to the map projection scale
- **AND** the UI indicates that visual effect may be subtle for low-altitude flights

#### Scenario: Enhanced altitude scale is selected
- **WHEN** enhanced altitude scale mode is active
- **THEN** altitude differences are visually exaggerated for readability
- **AND** the UI treats the mode as visual enhancement rather than physical terrain accuracy

### Requirement: 3D Camera Interaction
The system SHALL support camera pitch and bearing control in 3D trajectory mode.

#### Scenario: User adjusts 3D camera
- **WHEN** the user changes pitch or bearing in 3D mode
- **THEN** the map camera updates
- **AND** the 3D route, marker, height guide, and waypoints remain aligned with the satellite map

#### Scenario: User resets 3D camera
- **WHEN** the user activates reset view
- **THEN** the camera returns to an automatically fitted view for the selected route
- **AND** the altitude scale and overlay settings remain unchanged unless the user resets them separately

### Requirement: 3D Performance Guardrails
The system SHALL keep 3D preview responsive for long logs by separating display geometry from timestamp interpolation data.

#### Scenario: Long route is loaded
- **WHEN** the selected track contains many GPS points
- **THEN** the preview may use optimized or downsampled display geometry for route drawing
- **AND** marker interpolation and export timing still use the timestamped track data needed for accurate motion
