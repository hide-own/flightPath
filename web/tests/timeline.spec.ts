import { describe, expect, it } from 'vitest'
import { interpolateTrackPoint, playbackTimeToLogTime } from '../src/timeline'

const points = [
  { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
  { timeS: 1, lat: 31, lon: 121, relAltM: 10, speedMS: 2 },
  { timeS: 11, lat: 41, lon: 131, relAltM: 110, speedMS: 12 }
]

describe('timeline interpolation', () => {
  it('interpolates by timestamp rather than point index', () => {
    const current = interpolateTrackPoint(points, 6)

    expect(current.lat).toBe(36)
    expect(current.lon).toBe(126)
    expect(current.relAltM).toBe(60)
    expect(current.speedMS).toBe(7)
  })

  it('maps compressed playback time to proportional log time', () => {
    expect(playbackTimeToLogTime({ playbackTimeS: 5, logStartS: 0, logEndS: 100, outputDurationS: 10 })).toBe(50)
  })
})
