export interface JobCreatedResponse {
  schemaVersion: 'job.v1'
  jobId: string
  status: string
}

export interface FlightSummary {
  gpsCount: number
  totalDurationS?: number
  selectedDurationS: number
  maxRelativeAltitudeM: number
  maxSpeedMS: number
  waypointCount: number
  trueFlightDetected?: boolean
}

export interface TrackPoint {
  timeS: number
  lat: number
  lon: number
  relAltM: number
  speedMS: number
  altM?: number | null
  headingDeg?: number | null
}

export interface Waypoint {
  seq: number
  lat: number
  lon: number
  altM?: number | null
  command?: number | null
}

export interface FlightLogResult {
  schemaVersion: 'flight-log.v1'
  path?: string
  summary: FlightSummary
  points: TrackPoint[]
  selectedPoints?: TrackPoint[]
  waypoints: Waypoint[]
}

export interface ExportResult {
  schemaVersion: 'export.v1'
  filename: string
  downloadUrl: string
  renderMode: string
  viewMode: string
}

export interface JobStatusResponse {
  schemaVersion: 'job.v1'
  jobId: string
  kind?: string
  status: string
  progress?: number
  result?: FlightLogResult | ExportResult
}

export interface ExportRequestPayload {
  logPath: string
  options: {
    width: number
    height: number
    fps: number
    range: string
    renderMode: string
    viewMode: string
    timeMode: string
    compressedDurationS?: number | null
    waypointMode: string
    altitudeScaleMode: string
    camera: {
      center: [number, number]
      zoom: number
      pitch: number
      bearing: number
    }
    overlays: Record<string, boolean>
  }
}

export async function startParseUpload(file: File): Promise<JobCreatedResponse> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/logs/parse-file', {
    method: 'POST',
    body: form
  })
  if (!response.ok) {
    throw new Error(await readApiError(response))
  }
  return (await response.json()) as JobCreatedResponse
}

export async function getJob(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`/api/jobs/${jobId}`)
  if (!response.ok) {
    throw new Error(await readApiError(response))
  }
  return (await response.json()) as JobStatusResponse
}

export async function startExport(payload: ExportRequestPayload): Promise<JobCreatedResponse> {
  const response = await fetch('/api/exports', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  if (!response.ok) {
    throw new Error(await readApiError(response))
  }
  return (await response.json()) as JobCreatedResponse
}

async function readApiError(response: Response): Promise<string> {
  try {
    const payload = await response.json()
    return payload?.detail?.message ?? '请求失败'
  } catch {
    return '请求失败'
  }
}
