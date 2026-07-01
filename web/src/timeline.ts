export interface TrackPoint {
  timeS: number
  lat: number
  lon: number
  relAltM: number
  speedMS: number
}

export function interpolateTrackPoint(points: TrackPoint[], logTimeS: number): TrackPoint {
  if (points.length === 0) {
    throw new Error('No track points available')
  }
  if (points.length === 1 || logTimeS <= points[0].timeS) {
    return points[0]
  }
  const last = points[points.length - 1]
  if (logTimeS >= last.timeS) {
    return last
  }

  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1]
    const next = points[index]
    if (logTimeS <= next.timeS) {
      const duration = Math.max(0.001, next.timeS - previous.timeS)
      const ratio = (logTimeS - previous.timeS) / duration
      return {
        timeS: logTimeS,
        lat: lerp(previous.lat, next.lat, ratio),
        lon: lerp(previous.lon, next.lon, ratio),
        relAltM: lerp(previous.relAltM, next.relAltM, ratio),
        speedMS: lerp(previous.speedMS, next.speedMS, ratio)
      }
    }
  }
  return last
}

export function playbackTimeToLogTime(input: {
  playbackTimeS: number
  logStartS: number
  logEndS: number
  outputDurationS: number
}): number {
  const progress = clamp(input.playbackTimeS / Math.max(0.001, input.outputDurationS), 0, 1)
  return lerp(input.logStartS, input.logEndS, progress)
}

function lerp(start: number, end: number, ratio: number): number {
  return start + (end - start) * ratio
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
