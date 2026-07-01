## ADDED Requirements

### Requirement: Local Browser Vue Application
The system SHALL provide a browser-based local user interface implemented with Vue3, TypeScript, Vite, and Naive UI.

#### Scenario: User opens the local app
- **WHEN** the user starts the one-click launch entry
- **THEN** the local API service starts on localhost
- **AND** the user's browser opens the Vue3 interface

#### Scenario: Required frontend stack is inspected
- **WHEN** the application source dependencies are reviewed
- **THEN** the user-facing UI uses Vue3 and Naive UI as the primary component framework
- **AND** TypeScript is used for frontend application code

### Requirement: Local-Only User Data
The system SHALL keep selected flight logs and generated videos on the user's machine in the first-version local Web architecture.

#### Scenario: User selects a `.bin` log
- **WHEN** the user selects a flight log through the browser UI
- **THEN** the log is sent only to the localhost API service
- **AND** the system does not upload the log to a remote cloud service

### Requirement: Two-Pane Flight Tool Layout
The system SHALL present a left-side operation panel and a right-side map workspace as the primary application layout.

#### Scenario: Main view is displayed
- **WHEN** the browser UI is opened
- **THEN** file selection, output/download options, playback range, time mode, display options, export view, resolution, frame rate, progress, status, and action controls are available in the left panel
- **AND** the satellite map preview and timeline controls are available in the right workspace

#### Scenario: Browser window is resized
- **WHEN** the user resizes the browser window within practical desktop sizes
- **THEN** the left operation panel remains usable
- **AND** the right map workspace receives the remaining available space
- **AND** important controls and status text do not overlap or become clipped

### Requirement: Polished Naive UI Visual States
The system SHALL use a polished dark professional tool visual style with clear selected, disabled, working, success, warning, and error states.

#### Scenario: User selects segmented options
- **WHEN** the user selects playback range, time mode, render mode, waypoint mode, or export view mode
- **THEN** the selected option is visually emphasized beyond a native radio indicator
- **AND** unselected options remain visually secondary

#### Scenario: Compressed duration is disabled
- **WHEN** real-time mode is active
- **THEN** the compressed duration input is disabled
- **AND** the disabled state uses visibly muted background, border, and text treatment

#### Scenario: Long-running work is active
- **WHEN** parsing, map loading, preview preparation, or video export is running
- **THEN** the UI displays a progress or loading state
- **AND** the active primary action state is visually distinct from idle, success, warning, and error states

### Requirement: One-Click Windows Local Web Launch
The system SHALL provide a one-click Windows launch path that starts the local Web service and opens the browser UI.

#### Scenario: User double-clicks launch entry
- **WHEN** the user double-clicks the provided shortcut, script, or executable
- **THEN** the localhost API service starts
- **AND** the browser opens the local app URL
- **AND** no persistent command prompt window remains visible unless the user started a development script

#### Scenario: Startup dependency fails
- **WHEN** a required runtime dependency is missing or cannot start
- **THEN** the system displays or records a localized startup error explaining the missing dependency
- **AND** the user is not left at an unexplained blank browser page

### Requirement: Localized Workflow
The system SHALL present the core workflow labels, status text, validation messages, and errors in Chinese for normal users.

#### Scenario: User operates the main workflow
- **WHEN** the user selects a log, previews the route, and exports video
- **THEN** the visible workflow labels and status messages are in Chinese
- **AND** technical API details are not exposed unless needed for diagnostics
