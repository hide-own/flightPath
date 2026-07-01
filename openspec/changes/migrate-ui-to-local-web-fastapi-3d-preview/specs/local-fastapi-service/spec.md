## ADDED Requirements

### Requirement: Localhost FastAPI Service
The system SHALL provide a local FastAPI service for parsing logs, serving tiles, managing jobs, streaming progress, cancelling work, and exporting videos.

#### Scenario: Service starts
- **WHEN** the local launcher starts the backend
- **THEN** the API service binds to `127.0.0.1`
- **AND** it exposes versioned API routes for the browser UI

#### Scenario: Browser calls API
- **WHEN** the local browser UI sends API requests
- **THEN** the FastAPI service accepts requests from the local UI origin
- **AND** the service does not require internet access for local job status operations

### Requirement: Structured API Contracts
The system SHALL expose machine-readable JSON contracts for job creation, job state, parsed log data, progress events, cancellation, and errors.

#### Scenario: Parse job is created
- **WHEN** the browser UI submits a valid `.bin` parse request
- **THEN** the service returns a job id
- **AND** the parse work runs outside the request handler

#### Scenario: API operation fails
- **WHEN** parsing, map loading, export, or file handling fails
- **THEN** the service returns or streams a structured error with a stable error code and diagnostic message
- **AND** the browser UI can present a localized user-facing error

### Requirement: Normalized Flight Data Contract
The system SHALL provide a versioned JSON-compatible data contract for parsed flight logs.

#### Scenario: Log parse succeeds
- **WHEN** a Mission Planner / ArduPilot `.bin` log is parsed
- **THEN** each valid track point includes timestamp seconds, latitude, longitude, relative altitude, optional absolute altitude, speed, and optional heading
- **AND** each valid waypoint includes sequence number, latitude, longitude, optional altitude, and optional command
- **AND** the payload declares a schema version

#### Scenario: Log summary is displayed
- **WHEN** parsed log data is returned through a completed parse job
- **THEN** the payload includes GPS point count, selected flight duration, full log duration, maximum relative altitude, maximum speed, and waypoint count

### Requirement: True Flight Range Selection
The system SHALL support selecting the true flight phase by default using `RelAlt > 2m`.

#### Scenario: True flight phase is detected
- **WHEN** parsed track points include points with relative altitude greater than 2 meters
- **THEN** the default selected range starts near the first threshold crossing
- **AND** the default selected range ends near the last threshold crossing
- **AND** the selected range includes a small configurable buffer around takeoff and landing

#### Scenario: True flight phase is not detected
- **WHEN** no valid track point exceeds the relative altitude threshold
- **THEN** the system reports that true flight was not detected
- **AND** the full valid GPS range is available as an explicit fallback

### Requirement: Bounded Background Job Management
The system SHALL keep API handlers responsive by running heavy work in bounded background jobs.

#### Scenario: Parse request is received
- **WHEN** a parse request is accepted
- **THEN** the HTTP response returns promptly with a job id
- **AND** the actual parsing runs in a background worker

#### Scenario: Export request is received while another export is running
- **WHEN** the maximum number of concurrent export jobs is already active
- **THEN** the new export is queued or rejected with a clear structured status
- **AND** the API service remains responsive

#### Scenario: Tile requests are active
- **WHEN** multiple missing tiles need to be downloaded
- **THEN** the service limits tile download concurrency to a configured worker count
- **AND** cached tile reads remain available while downloads are active

### Requirement: Progress Streaming And Cancellation
The system SHALL stream job progress and support cancellation for long-running parse, tile, and export operations.

#### Scenario: Long operation is running
- **WHEN** the service is parsing, loading map data, rendering frames, or encoding video
- **THEN** the browser can subscribe to progress events for the job
- **AND** progress events include a phase such as queued, parsing, loading map, rendering, encoding, cancelling, complete, cancelled, or failed

#### Scenario: User cancels active work
- **WHEN** the browser sends a cancellation request for an active operation
- **THEN** the service marks the job as cancelling
- **AND** the worker stops at a safe boundary as soon as practical
- **AND** the final job state reports cancelled rather than successful completion

### Requirement: Cached Satellite Tile Endpoint
The system SHALL serve satellite map tiles through the local FastAPI service while preserving app-controlled caching behavior.

#### Scenario: Required tile exists in cache
- **WHEN** the browser preview or export requests a satellite tile that is already cached
- **THEN** the service serves the cached tile without requiring network access

#### Scenario: Required tile is missing and download fails
- **WHEN** a required satellite tile is missing from cache and cannot be downloaded
- **THEN** the service reports a map download failure
- **AND** preview or export does not silently use a blank or incorrect map

### Requirement: MP4 Download Endpoint
The system SHALL allow completed export videos to be downloaded through the local API service.

#### Scenario: Export job completes
- **WHEN** an export job has successfully written an MP4
- **THEN** the browser can download the video from a local API endpoint
- **AND** the downloaded file has an `.mp4` filename

#### Scenario: Export job is incomplete
- **WHEN** the browser requests download for a queued, running, cancelled, or failed export job
- **THEN** the service does not return a successful MP4 download
- **AND** the service returns a clear job-state or error response
