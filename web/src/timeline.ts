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

  const previousIndex = findTrackSegmentIndex(points, logTimeS)
  if (previousIndex >= points.length - 1) {
    return last
  }
  const previous = points[previousIndex]
  const next = points[previousIndex + 1]
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

export function findTrackSegmentIndex(points: TrackPoint[], logTimeS: number): number {
  if (points.length <= 1 || logTimeS <= points[0].timeS) {
    return 0
  }
  if (logTimeS >= points[points.length - 1].timeS) {
    return points.length - 1
  }

  let low = 0
  let high = points.length - 1
  while (low <= high) {
    const mid = Math.floor((low + high) / 2)
    if (points[mid].timeS <= logTimeS) {
      low = mid + 1
    } else {
      high = mid - 1
    }
  }
  return Math.max(0, high)
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
