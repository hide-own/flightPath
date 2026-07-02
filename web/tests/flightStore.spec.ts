import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFlightStore } from '../src/stores/flight'

describe('flight store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('validates missing log file before parsing', async () => {
    const store = useFlightStore()

    await expect(store.parseSelectedLog()).rejects.toThrow('请选择 .bin 飞行日志')
    expect(store.error).toBe('请选择 .bin 飞行日志')
  })

  it('uploads selected bin file and stores returned job id', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ schemaVersion: 'job.v1', jobId: 'job-123', status: 'queued' })
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useFlightStore()
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))

    await store.parseSelectedLog()

    expect(fetchMock).toHaveBeenCalledWith('/api/logs/parse-file', expect.objectContaining({ method: 'POST' }))
    expect(fetchMock.mock.calls[0][1].body).toBeInstanceOf(FormData)
    expect(store.parseJobId).toBe('job-123')
    expect(store.status).toBe('queued')
    expect(store.error).toBeNull()
  })

  it('loads completed parse job summary', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        schemaVersion: 'job.v1',
        jobId: 'job-123',
        status: 'completed',
        result: {
          schemaVersion: 'flight-log.v1',
          summary: {
            gpsCount: 42,
            selectedDurationS: 18.5,
            maxRelativeAltitudeM: 36.2,
            maxSpeedMS: 9.1,
            waypointCount: 4
          },
          points: [],
          waypoints: []
        }
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useFlightStore()
    store.parseJobId = 'job-123'

    await store.refreshParseJob()

    expect(fetchMock).toHaveBeenCalledWith('/api/jobs/job-123')
    expect(store.status).toBe('completed')
    expect(store.summary?.gpsCount).toBe(42)
    expect(store.summary?.waypointCount).toBe(4)
  })

  it('stores parsed track data and moves the timeline by log timestamp percentage', async () => {
    mockCompletedJob()
    const store = useFlightStore()
    store.parseJobId = 'job-123'

    await store.refreshParseJob()
    store.setTimelineProgress(50)

    expect(store.activePoints).toHaveLength(3)
    expect(store.currentTimeS).toBe(11)
    expect(store.currentPoint?.lat).toBeCloseTo(30.00018)
    expect(store.currentPoint?.relAltM).toBeCloseTo(5.15)
  })

  it('validates preview and export actions before required data is available', () => {
    const store = useFlightStore()

    expect(() => store.validateCanPreview()).toThrow('请先选择 .bin 飞行日志')
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))
    expect(() => store.validateCanPreview()).toThrow('请先解析飞行日志')
    expect(() => store.validateCanExport()).toThrow('请先解析飞行日志')
  })

  it('preserves preview state for the same log and resets it for a different log', () => {
    const store = useFlightStore()
    const firstLog = new File(['BIN'], 'flight.bin', { type: 'application/octet-stream', lastModified: 100 })
    const secondLog = new File(['BIN2'], 'other.bin', { type: 'application/octet-stream', lastModified: 200 })

    store.setLogFile(firstLog)
    store.preview.currentTimeS = 42
    store.summary = {
      gpsCount: 10,
      selectedDurationS: 5,
      maxRelativeAltitudeM: 20,
      maxSpeedMS: 4,
      waypointCount: 1
    }
    store.setLogFile(firstLog)

    expect(store.preview.currentTimeS).toBe(42)
    expect(store.summary?.gpsCount).toBe(10)

    store.setLogFile(secondLog)

    expect(store.preview.currentTimeS).toBe(0)
    expect(store.summary).toBeNull()
    expect(store.activePoints).toHaveLength(0)
  })

  it('advances preview playback using elapsed real time and pauses at the current point', async () => {
    mockCompletedJob()
    const store = useFlightStore()
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))
    store.parseJobId = 'job-123'
    await store.refreshParseJob()

    store.playPreview(1000)
    store.advancePreview(3500)

    expect(store.currentTimeS).toBe(4.5)
    expect(store.currentPoint?.lat).toBe(30.00005)

    store.pausePreview()
    expect(store.preview.isPlaying).toBe(false)
  })

  it('throttles preview playback updates to reduce render churn', async () => {
    mockCompletedJob()
    const store = useFlightStore()
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))
    store.parseJobId = 'job-123'
    await store.refreshParseJob()

    store.playPreview(1000)
    store.advancePreview(1010)

    expect(store.currentTimeS).toBe(2)

    store.advancePreview(1040)

    expect(store.currentTimeS).toBeCloseTo(2.04)
  })

  it('continues playback from scrubbed timeline progress while playing', async () => {
    mockCompletedJob()
    const store = useFlightStore()
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))
    store.parseJobId = 'job-123'
    await store.refreshParseJob()

    store.playPreview(1000)
    store.advancePreview(3500)
    store.setTimelineProgress(50, 3500)
    store.advancePreview(4500)

    expect(store.currentTimeS).toBe(12)
  })

  it('advances preview playback by the selected playback speed', async () => {
    mockCompletedJob()
    const store = useFlightStore()
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))
    store.parseJobId = 'job-123'
    await store.refreshParseJob()

    store.setPlaybackSpeed(2)
    store.playPreview(1000)
    store.advancePreview(2000)

    expect(store.currentTimeS).toBe(4)
  })

  it('uses compressed duration for preview playback timing and displayed time', async () => {
    mockCompletedJob()
    const store = useFlightStore()
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))
    store.parseJobId = 'job-123'
    await store.refreshParseJob()

    store.exportOptions.timeMode = 'compressed'
    store.exportOptions.compressedDurationS = 9

    expect(store.previewDurationS).toBe(9)

    store.playPreview(1000)
    store.advancePreview(5500)

    expect(store.currentTimeS).toBe(11)
    expect(store.previewElapsedS).toBe(4.5)
  })

  it('creates an export job from the parsed log path and preview state', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ schemaVersion: 'job.v1', jobId: 'export-123', status: 'queued' })
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useFlightStore()
    store.setLogFile(new File(['BIN'], 'flight.bin', { type: 'application/octet-stream' }))
    store.logPath = 'cache/uploads/flight.bin'
    store.selectedPoints = [
      { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
      { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 }
    ]
    store.preview.renderMode = '3d'
    store.exportOptions.viewMode = 'current'

    await store.startExport()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/exports',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"renderMode":"3d"')
      })
    )
    expect(fetchMock.mock.calls[0][1].body).toContain('"logPath":"cache/uploads/flight.bin"')
    expect(store.exportJobId).toBe('export-123')
    expect(store.exportStatus).toBe('queued')
  })

  it('loads completed export download url', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        schemaVersion: 'job.v1',
        jobId: 'export-123',
        kind: 'export',
        status: 'completed',
        progress: 100,
        result: {
          schemaVersion: 'export.v1',
          downloadUrl: '/api/exports/export-123/download',
          filename: 'track.mp4',
          renderMode: '2d',
          viewMode: 'auto-fit'
        }
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const store = useFlightStore()
    store.exportJobId = 'export-123'

    await store.refreshExportJob()

    expect(store.exportStatus).toBe('completed')
    expect(store.exportProgress).toBe(100)
    expect(store.exportDownloadUrl).toBe('/api/exports/export-123/download')
  })
})

function mockCompletedJob() {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      schemaVersion: 'job.v1',
      jobId: 'job-123',
      status: 'completed',
        result: {
          schemaVersion: 'flight-log.v1',
          path: 'cache/uploads/flight.bin',
          summary: {
          gpsCount: 4,
          selectedDurationS: 10,
          maxRelativeAltitudeM: 10,
          maxSpeedMS: 6,
          waypointCount: 2
        },
        points: [
          { timeS: 0, lat: 29.9999, lon: 119.9999, relAltM: 0, speedMS: 0 },
          { timeS: 2, lat: 30, lon: 120, relAltM: 2, speedMS: 2 },
          { timeS: 12, lat: 30.0002, lon: 120.0002, relAltM: 5.5, speedMS: 4 },
          { timeS: 20, lat: 30.0004, lon: 120.0004, relAltM: 10, speedMS: 6 }
        ],
        selectedPoints: [
          { timeS: 2, lat: 30, lon: 120, relAltM: 2, speedMS: 2 },
          { timeS: 12, lat: 30.0002, lon: 120.0002, relAltM: 5.5, speedMS: 4 },
          { timeS: 20, lat: 30.0004, lon: 120.0004, relAltM: 10, speedMS: 6 }
        ],
        waypoints: [
          { seq: 1, lat: 30, lon: 120, altM: 20, command: 16 },
          { seq: 2, lat: 30.0004, lon: 120.0004, altM: 25, command: 16 }
        ]
      }
    })
  })
  vi.stubGlobal('fetch', fetchMock)
}
