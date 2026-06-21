## ADDED Requirements

### Requirement: Bin Log File Selection
The system SHALL allow the user to select a Mission Planner / ArduPilot `.bin` flight log file from the Windows desktop UI.

#### Scenario: User selects a bin log
- **WHEN** the user chooses an existing `.bin` file
- **THEN** the system stores that path as the active input log
- **AND** the system begins parsing or makes parsing available without requiring command-line input

#### Scenario: User selects a non-existent file
- **WHEN** the selected path does not exist
- **THEN** the system rejects the selection
- **AND** the system displays a clear error message

### Requirement: ArduPilot Flight Data Parsing
The system SHALL parse valid ArduPilot DataFlash `.bin` logs for GPS trajectory points, mission waypoints, relative altitude, available absolute altitude, ground speed, and timestamps.

#### Scenario: Valid GPS records are present
- **WHEN** a selected log contains valid GPS latitude, longitude, timestamp, relative altitude, and speed fields
- **THEN** the system produces ordered track points with time, latitude, longitude, altitude, and speed values

#### Scenario: Mission waypoint records are present
- **WHEN** a selected log contains valid mission command or waypoint records with coordinates
- **THEN** the system extracts waypoint sequence numbers and coordinates
- **AND** duplicate waypoint records do not create duplicate labels for the same sequence and coordinate

#### Scenario: Required GPS records are missing
- **WHEN** a selected log does not contain enough valid GPS points to form a trajectory
- **THEN** the system reports that no valid GPS trajectory was found
- **AND** the system does not start video generation

### Requirement: Log Summary Metrics
The system SHALL display log summary information after parsing, including GPS point count, selected flight duration, maximum relative altitude, maximum speed, and waypoint count.

#### Scenario: Parsing succeeds
- **WHEN** the system finishes parsing a selected log
- **THEN** the UI displays the GPS point count
- **AND** the UI displays the selected flight duration
- **AND** the UI displays the maximum relative altitude
- **AND** the UI displays the maximum speed
- **AND** the UI displays the waypoint count

### Requirement: True Flight Phase Detection
The system SHALL default to a true-flight playback range identified by `RelAlt > 2m` and include a default 3 second buffer before takeoff and after landing when those surrounding GPS points are available.

#### Scenario: Relative altitude crosses threshold
- **WHEN** parsed track points include one or more points where relative altitude is greater than 2 meters
- **THEN** the default playback range starts up to 3 seconds before the first threshold-crossing point, clipped to the first valid GPS point
- **AND** the default playback range ends up to 3 seconds after the last threshold-crossing point, clipped to the last valid GPS point

#### Scenario: Relative altitude never crosses threshold
- **WHEN** no parsed track point has relative altitude greater than 2 meters
- **THEN** the system reports that no true-flight phase was detected
- **AND** the system offers the full valid GPS range as the explicit fallback selection
- **AND** the system does not silently create an empty playback range

#### Scenario: Buffer extends outside valid range
- **WHEN** applying the 3 second pre/post buffer would extend outside the valid GPS range
- **THEN** the system clips the buffer to the available valid GPS range
- **AND** the selected range still includes every threshold-crossing point

### Requirement: Full Log Range Option
The system SHALL allow the user to choose the full valid log trajectory instead of the default true-flight phase.

#### Scenario: User selects full log range
- **WHEN** the user chooses the full log playback range
- **THEN** video generation uses all valid parsed GPS points in timestamp order
- **AND** the log summary distinguishes the full duration from the true-flight duration when both are available
