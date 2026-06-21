## ADDED Requirements

### Requirement: Satellite Map Provider
The system SHALL use Esri World Imagery satellite map tiles as the default map background provider.

#### Scenario: Map generation starts
- **WHEN** the renderer prepares a background for a selected trajectory
- **THEN** the system requests or reads Esri World Imagery tiles for the required Web Mercator zoom and tile coordinates

### Requirement: Flight Area Centering
The system SHALL center the satellite map background on the selected flight trajectory and mission waypoints.

#### Scenario: Track and waypoints fit frame
- **WHEN** the renderer builds the map background
- **THEN** the selected GPS trajectory is visible within the output frame
- **AND** mission waypoints with valid coordinates are visible within the output frame when they are near the selected flight area

#### Scenario: No waypoints are available
- **WHEN** the selected log contains valid GPS trajectory points but no valid mission waypoints
- **THEN** the map background is centered using the GPS trajectory alone

### Requirement: Zoom Selection
The system SHALL choose a map zoom level that fits the selected trajectory and waypoints within the configured video resolution with visible padding.

#### Scenario: Compact flight path
- **WHEN** the selected flight path covers a small geographic area
- **THEN** the system uses a sufficiently detailed zoom level so the route is readable

#### Scenario: Detailed zoom has no imagery
- **WHEN** the chosen detailed zoom level returns provider placeholder tiles such as "Map data not yet available"
- **THEN** the system does not render those placeholder tiles as the satellite map background
- **AND** the system retries with a lower zoom level before failing generation

#### Scenario: Large flight path
- **WHEN** the selected flight path covers a larger geographic area
- **THEN** the system lowers the zoom level enough for the route to fit within the configured frame

### Requirement: Tile Cache
The system SHALL cache downloaded map tiles locally using provider, zoom, x, and y tile coordinates.

#### Scenario: Tile is already cached
- **WHEN** a required map tile exists in the local cache
- **THEN** the system reads the cached tile
- **AND** the system does not require a network request for that tile

#### Scenario: Tile is not cached
- **WHEN** a required map tile is missing from the local cache and network access succeeds
- **THEN** the system downloads the tile
- **AND** the system stores the tile in the local cache for future offline use

#### Scenario: Provider returns an unavailable placeholder tile
- **WHEN** the map provider returns a placeholder tile instead of satellite imagery
- **THEN** the system treats the tile as unavailable
- **AND** the system does not store the placeholder tile in the local cache

#### Scenario: Placeholder tile exists in cache
- **WHEN** a cached tile is identified as a provider unavailable placeholder
- **THEN** the system ignores and removes the cached placeholder tile
- **AND** the system attempts to obtain a usable satellite tile instead

#### Scenario: User needs cache location
- **WHEN** the user opens documentation or cache-related UI
- **THEN** the system exposes the local tile cache location
- **AND** the user can understand how to clear cached tiles

### Requirement: Map Download Failure Handling
The system SHALL report "地图下载失败" when required satellite tiles are unavailable from cache and cannot be downloaded.

#### Scenario: Network is unavailable and tile is missing
- **WHEN** a required tile is not cached
- **AND** the map provider download fails
- **THEN** generation stops before rendering a misleading video
- **AND** the UI displays an error message containing "地图下载失败"

#### Scenario: All required tiles are cached while offline
- **WHEN** all required tiles are present in the local cache
- **AND** network access is unavailable
- **THEN** the system generates the map background from cached tiles
- **AND** generation may continue

### Requirement: Map Attribution
The system SHALL include visible Esri World Imagery attribution in generated previews and videos.

#### Scenario: Preview or video frame is rendered
- **WHEN** the satellite map background is visible
- **THEN** the rendered frame includes readable Esri World Imagery attribution
- **AND** the attribution does not cover the current marker, waypoint labels, or required telemetry overlays
