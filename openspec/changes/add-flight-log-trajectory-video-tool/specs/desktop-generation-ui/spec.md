## ADDED Requirements

### Requirement: Graphical Desktop Interface
The system SHALL provide a Windows graphical user interface and SHALL NOT require command-line operation for the core workflow.

#### Scenario: User opens the tool
- **WHEN** the application starts
- **THEN** the user can access controls for log selection, output selection, playback range, timing mode, display overlays, resolution, frame rate, preview, and video generation

### Requirement: One-Click Windows Launch
The system SHALL provide a one-click Windows launch entry for starting the GUI without typing a command or leaving a command prompt window open.

#### Scenario: User double-clicks launch entry
- **WHEN** the user double-clicks the provided shortcut, launcher, or executable
- **THEN** the graphical application opens
- **AND** the user does not need to type a terminal command
- **AND** no persistent command prompt window remains visible
- **AND** the main window appears within 5 seconds on a ready environment

#### Scenario: Startup dependency is missing
- **WHEN** the launch entry is double-clicked and a required runtime dependency is missing
- **THEN** the system displays or records a localized startup error explaining what is missing
- **AND** the failure does not leave the user at an unexplained blank screen

#### Scenario: Launch entry is missing or broken
- **WHEN** the release or local deliverable is checked
- **THEN** a missing or non-working one-click launch entry is treated as a failed acceptance condition

### Requirement: Output Path Selection
The system SHALL allow the user to choose the `.mp4` output file path through the desktop UI.

#### Scenario: User chooses save location
- **WHEN** the user selects a save path
- **THEN** the system stores the path as the active output path
- **AND** generation uses that path

#### Scenario: Output extension omitted
- **WHEN** the user selects or enters an output path without `.mp4`
- **THEN** the system appends or enforces the `.mp4` output extension

### Requirement: Default Configuration
The system SHALL default to satellite map background, true-flight range, real-time mode, 1280x720 resolution, 24 fps, and MP4 output.

#### Scenario: Application opens with defaults
- **WHEN** the user opens the application
- **THEN** the map background is set to satellite map
- **AND** playback range is set to true-flight phase
- **AND** time mode is set to real time
- **AND** resolution is set to 1280x720
- **AND** frame rate is set to 24 fps
- **AND** output format is MP4

### Requirement: Polished Visual Design
The system SHALL present a polished, modern, Chinese desktop interface with a professional flight/mission-control visual direction, clear hierarchy, consistent spacing, and visually distinct primary actions.

#### Scenario: Main window is viewed
- **WHEN** the user opens the main window
- **THEN** the title, file controls, generation settings, log summary, action buttons, progress, and status areas are visually grouped and easy to scan
- **AND** the primary generation action is visually emphasized over secondary actions
- **AND** user-facing labels and status messages are in Chinese
- **AND** status colors consistently distinguish idle, working, success, warning, and error states

#### Scenario: Common window sizes and scaling are checked
- **WHEN** the UI is viewed at common Windows display scaling settings such as 100%, 125%, and 150%
- **AND** the window is viewed at practical sizes including 1280x720 and 1920x1080
- **THEN** text does not overlap other controls
- **AND** important labels, buttons, and status messages are not clipped
- **AND** the initial generation settings rows are not squeezed or visually overlapping
- **AND** the layout remains balanced and usable

#### Scenario: Visual style is reviewed
- **WHEN** the UI is compared with an unstyled default widget layout
- **THEN** the delivered UI uses deliberate spacing, typography, grouping, and color treatment
- **AND** the interface looks like a finished desktop utility rather than a raw prototype

#### Scenario: Acceptance screenshots are captured
- **WHEN** visual QA is performed
- **THEN** screenshots are captured for the initial, parsing-complete, rendering, failure, and completed states
- **AND** the screenshots show no clipped text, overlapping controls, or visually broken layout

### Requirement: Display Options
The system SHALL allow users to enable or disable waypoint labels, altitude, speed, and progress bar overlays.

#### Scenario: User changes display options
- **WHEN** the user toggles an overlay option
- **THEN** subsequent preview or video generation reflects the selected option state

### Requirement: Clear Selection And Disabled States
The system SHALL make selected options and disabled controls visually obvious in the desktop UI.

#### Scenario: User changes playback range or time mode
- **WHEN** the user selects a playback range or time mode option
- **THEN** the selected option is visually emphasized beyond the native radio indicator
- **AND** the selected option uses distinct background, border, and text treatment
- **AND** unselected options remain visually secondary
- **AND** playback range, time mode, and display overlay selections use a consistent selected-state visual language

#### Scenario: User toggles display overlays
- **WHEN** the user enables or disables waypoint labels, altitude, speed, or progress overlays
- **THEN** each checked display option is visually recognizable at a glance
- **AND** unchecked display options remain visually secondary

#### Scenario: Real-time mode disables compressed duration
- **WHEN** real-time mode is selected
- **THEN** the compressed duration input is disabled
- **AND** the disabled input is visually distinct from active inputs through muted background, border, and text treatment

### Requirement: Generation Progress
The system SHALL display video generation progress and human-readable status messages in the UI.

#### Scenario: Generation is running
- **WHEN** video generation is in progress
- **THEN** the UI displays a progress indicator
- **AND** the UI displays a status message such as map loading, rendering progress, or completion state

#### Scenario: Generation fails
- **WHEN** parsing, map loading, encoding, or file writing fails during generation
- **THEN** the UI stops the progress state
- **AND** the UI displays the failure reason

### Requirement: Generation Cancellation Control
The system SHALL provide a visible cancellation control while preview or video generation is running.

#### Scenario: User cancels generation
- **WHEN** generation is running
- **AND** the user activates the cancellation control
- **THEN** the UI requests cancellation from the active worker
- **AND** the UI displays a cancelling or cancelled state
- **AND** the UI returns to an operable idle state after cancellation completes

#### Scenario: No generation is running
- **WHEN** no preview or video generation work is active
- **THEN** the cancellation control is hidden or disabled

### Requirement: Responsive UI During Long Work
The system SHALL keep long-running parsing, map loading, preview, and rendering operations from freezing the UI.

#### Scenario: Rendering takes multiple seconds
- **WHEN** the renderer is generating a video
- **THEN** the UI remains responsive enough to repaint progress and status updates

### Requirement: Input Validation Before Generation
The system SHALL validate that a log file and output path are selected before starting video generation.

#### Scenario: Missing log file
- **WHEN** the user clicks generate without selecting a valid log file
- **THEN** generation does not start
- **AND** the UI asks the user to select a valid `.bin` log

#### Scenario: Missing output path
- **WHEN** the user clicks generate without choosing an output path
- **THEN** generation does not start
- **AND** the UI asks the user to choose an output `.mp4` path
