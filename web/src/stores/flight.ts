import { defineStore } from 'pinia'
import {
  getJob,
  startExport as createExportJob,
  startParseUpload,
  type ExportResult,
  type FlightLogResult,
  type FlightSummary,
  type TrackPoint,
  type Waypoint
} from '../api'
import { interpolateTrackPoint } from '../timeline'

export type PlaybackRange = 'true-flight' | 'full-log'
export type RenderMode = '2d' | '3d'
export type WaypointMode = 'hidden' | 'points' | 'compact' | 'all'
export type ExportViewMode = 'current' | 'auto-fit' | 'follow'
export type TimeMode = 'realtime' | 'compressed'
export type AltitudeScaleMode = 'auto' | 'real-ratio' | 'enhanced'

export interface CameraState {
  center: [number, number]
  zoom: number
  pitch: number
  bearing: number
}

export interface OverlayState {
  route: boolean
  marker: boolean
  waypoints: boolean
  altitude: boolean
  speed: boolean
  progress: boolean
}

export interface PreviewState {
  camera: CameraState
  renderMode: RenderMode
  waypointMode: WaypointMode
  altitudeScaleMode: AltitudeScaleMode
  overlays: OverlayState
  currentTimeS: number
  isPlaying: boolean
  playbackStartedAtMs: number | null
  playbackStartTimeS: number
}

export interface ExportOptions {
  viewMode: ExportViewMode
  timeMode: TimeMode
  compressedDurationS: number
  resolution: string
  fps: string
}

interface FlightState {
  logFile: File | null
  logSignature: string | null
  logPath: string | null
  parseJobId: string | null
  exportJobId: string | null
  exportStatus: string
  exportProgress: number
  exportDownloadUrl: string | null
  status: string
  error: string | null
  summary: FlightSummary | null
  points: TrackPoint[]
  selectedPoints: TrackPoint[]
  waypoints: Waypoint[]
  playbackRange: PlaybackRange
  preview: PreviewState
  exportOptions: ExportOptions
}

export const useFlightStore = defineStore('flight', {
  state: (): FlightState => ({
    logFile: null,
    logSignature: null,
    logPath: null,
    parseJobId: null,
    exportJobId: null,
    exportStatus: 'idle',
    exportProgress: 0,
    exportDownloadUrl: null,
    status: 'idle',
    error: null,
    summary: null,
    points: [],
    selectedPoints: [],
    waypoints: [],
    playbackRange: 'true-flight',
    preview: createDefaultPreviewState(),
    exportOptions: createDefaultExportOptions()
  }),
  getters: {
    activePoints(state): TrackPoint[] {
      return state.playbackRange === 'full-log' ? state.points : state.selectedPoints
    },
    currentTimeS(state): number {
      return state.preview.currentTimeS
    },
    durationS(): number {
      return getDuration(this.activePoints)
    },
    elapsedS(): number {
      const first = this.activePoints[0]
      if (!first) return 0
      return Math.max(0, this.preview.currentTimeS - first.timeS)
    },
    timelineProgressPercent(): number {
      const first = this.activePoints[0]
      const duration = this.durationS
      if (!first || duration <= 0) return 0
      return clamp(((this.preview.currentTimeS - first.timeS) / duration) * 100, 0, 100)
    },
    currentPoint(): TrackPoint | null {
      if (this.activePoints.length === 0) return null
      return interpolateTrackPoint(this.activePoints, this.preview.currentTimeS)
    }
  },
  actions: {
    setLogFile(file: File | null) {
      const nextSignature = file ? fileSignature(file) : null
      const isSameLog = nextSignature !== null && nextSignature === this.logSignature

      this.logFile = file
      this.error = null

      if (isSameLog) {
        return
      }

      this.logSignature = nextSignature
      this.logPath = null
      this.parseJobId = null
      this.exportJobId = null
      this.exportStatus = 'idle'
      this.exportProgress = 0
      this.exportDownloadUrl = null
      this.status = file ? 'idle' : 'idle'
      this.summary = null
      this.points = []
      this.selectedPoints = []
      this.waypoints = []
      this.preview = createDefaultPreviewState()
    },
    async parseSelectedLog() {
      if (!this.logFile || !this.logFile.name.toLowerCase().endsWith('.bin')) {
        throw this.setErrorAndCreateException('请选择 .bin 飞行日志')
      }

      this.status = 'parsing'
      this.error = null
      const job = await startParseUpload(this.logFile)
      this.parseJobId = job.jobId
      this.status = job.status
      return job
    },
    async refreshParseJob() {
      if (!this.parseJobId) {
        return null
      }
      const job = await getJob(this.parseJobId)
      this.status = job.status
      if (job.result?.schemaVersion === 'flight-log.v1') {
        this.applyLogResult(job.result)
      }
      return job
    },
    async waitForParseJob(delayMs = 250, maxAttempts = 240) {
      return this.waitForJob(() => this.refreshParseJob(), delayMs, maxAttempts)
    },
    applyLogResult(result: FlightLogResult) {
      this.logPath = result.path ?? this.logPath
      this.summary = result.summary
      this.points = result.points
      this.selectedPoints = result.selectedPoints?.length ? result.selectedPoints : result.points
      this.waypoints = result.waypoints
      this.resetTimelineToStart()
    },
    setPlaybackRange(range: PlaybackRange) {
      this.playbackRange = range
      this.resetTimelineToStart()
    },
    setTimelineProgress(percent: number) {
      const points = this.activePoints
      if (points.length === 0) return
      const first = points[0]
      this.setCurrentTimeS(first.timeS + getDuration(points) * clamp(percent / 100, 0, 1))
    },
    setCurrentTimeS(timeS: number) {
      const points = this.activePoints
      if (points.length === 0) {
        this.preview.currentTimeS = 0
        return
      }
      this.preview.currentTimeS = clamp(timeS, points[0].timeS, points[points.length - 1].timeS)
    },
    playPreview(nowMs = performance.now()) {
      this.validateCanPreview()
      this.preview.isPlaying = true
      this.preview.playbackStartedAtMs = nowMs
      this.preview.playbackStartTimeS = this.preview.currentTimeS
    },
    advancePreview(nowMs = performance.now()) {
      if (!this.preview.isPlaying || this.preview.playbackStartedAtMs === null) {
        return
      }
      const elapsedS = (nowMs - this.preview.playbackStartedAtMs) / 1000
      this.setCurrentTimeS(this.preview.playbackStartTimeS + elapsedS)
      const last = this.activePoints[this.activePoints.length - 1]
      if (last && this.preview.currentTimeS >= last.timeS) {
        this.pausePreview()
      }
    },
    pausePreview() {
      this.preview.isPlaying = false
      this.preview.playbackStartedAtMs = null
      this.preview.playbackStartTimeS = this.preview.currentTimeS
    },
    updateCamera(camera: Partial<CameraState>) {
      this.preview.camera = { ...this.preview.camera, ...camera }
    },
    setOverlay(name: keyof OverlayState, enabled: boolean) {
      this.preview.overlays[name] = enabled
    },
    validateCanPreview() {
      if (!this.logFile) {
        throw this.setErrorAndCreateException('请先选择 .bin 飞行日志')
      }
      if (this.activePoints.length < 2) {
        throw this.setErrorAndCreateException('请先解析飞行日志')
      }
      this.error = null
      return true
    },
    validateCanExport() {
      this.validateCanPreview()
      if (!this.logPath) {
        throw this.setErrorAndCreateException('请先解析飞行日志')
      }
      if (this.exportOptions.timeMode === 'compressed' && this.exportOptions.compressedDurationS <= 0) {
        throw this.setErrorAndCreateException('请输入有效的压缩时长')
      }
      return true
    },
    async startExport() {
      this.validateCanExport()
      const [width, height] = parseResolution(this.exportOptions.resolution)
      this.exportStatus = 'running'
      this.exportProgress = 0
      this.exportDownloadUrl = null
      const job = await createExportJob({
        logPath: this.logPath!,
        options: {
          width,
          height,
          fps: Number(this.exportOptions.fps),
          range: this.playbackRange,
          renderMode: this.preview.renderMode,
          viewMode: this.exportOptions.viewMode,
          timeMode: this.exportOptions.timeMode,
          compressedDurationS:
            this.exportOptions.timeMode === 'compressed' ? this.exportOptions.compressedDurationS : null,
          waypointMode: this.preview.waypointMode,
          altitudeScaleMode: this.preview.altitudeScaleMode,
          camera: { ...this.preview.camera },
          overlays: { ...this.preview.overlays }
        }
      })
      this.exportJobId = job.jobId
      this.exportStatus = job.status
      return job
    },
    async refreshExportJob() {
      if (!this.exportJobId) {
        return null
      }
      const job = await getJob(this.exportJobId)
      this.exportStatus = job.status
      this.exportProgress = job.progress ?? this.exportProgress
      if (job.result?.schemaVersion === 'export.v1') {
        this.applyExportResult(job.result)
      }
      return job
    },
    async waitForExportJob(delayMs = 250, maxAttempts = 720) {
      return this.waitForJob(() => this.refreshExportJob(), delayMs, maxAttempts)
    },
    applyExportResult(result: ExportResult) {
      this.exportDownloadUrl = result.downloadUrl
    },
    async waitForJob(refresh: () => Promise<{ status: string } | null>, delayMs: number, maxAttempts: number) {
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        const job = await refresh()
        if (job && ['completed', 'failed', 'cancelled'].includes(job.status)) {
          return job
        }
        await sleep(delayMs)
      }
      throw this.setErrorAndCreateException('任务等待超时')
    },
    resetTimelineToStart() {
      const first = this.activePoints[0]
      this.pausePreview()
      this.preview.currentTimeS = first?.timeS ?? 0
    },
    setErrorAndCreateException(message: string) {
      this.error = message
      return new Error(message)
    }
  }
})

function createDefaultPreviewState(): PreviewState {
  return {
    camera: {
      center: [120, 30],
      zoom: 12,
      pitch: 0,
      bearing: 0
    },
    renderMode: '2d',
    waypointMode: 'compact',
    altitudeScaleMode: 'auto',
    overlays: {
      route: true,
      marker: true,
      waypoints: true,
      altitude: true,
      speed: true,
      progress: true
    },
    currentTimeS: 0,
    isPlaying: false,
    playbackStartedAtMs: null,
    playbackStartTimeS: 0
  }
}

function createDefaultExportOptions(): ExportOptions {
  return {
    viewMode: 'current',
    timeMode: 'realtime',
    compressedDurationS: 360,
    resolution: '1280x720',
    fps: '24'
  }
}

function getDuration(points: TrackPoint[]): number {
  if (points.length < 2) return 0
  return Math.max(0, points[points.length - 1].timeS - points[0].timeS)
}

function fileSignature(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`
}

function parseResolution(resolution: string): [number, number] {
  const [widthText, heightText] = resolution.split('x')
  const width = Number(widthText)
  const height = Number(heightText)
  if (!Number.isFinite(width) || !Number.isFinite(height)) {
    return [1280, 720]
  }
  return [width, height]
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
