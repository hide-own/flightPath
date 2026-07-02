<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { LayersList } from '@deck.gl/core'
import type { Feature, FeatureCollection, LineString, Point } from 'geojson'
import type { TrackPoint, Waypoint } from '../api'
import type { AltitudeScaleMode, CameraState, OverlayState, RenderMode, WaypointMode } from '../stores/flight'
import { findTrackSegmentIndex } from '../timeline'

const props = withDefaults(
  defineProps<{
    points?: TrackPoint[]
    waypoints?: Waypoint[]
    currentPoint?: TrackPoint | null
    elapsedS?: number
    durationS?: number
    overlays?: OverlayState
    renderMode?: RenderMode
    altitudeScaleMode?: AltitudeScaleMode
    waypointMode?: WaypointMode
    camera?: CameraState
  }>(),
  {
    points: () => [],
    waypoints: () => [],
    currentPoint: null,
    elapsedS: 0,
    durationS: 0,
    overlays: () => ({
      route: true,
      marker: true,
      waypoints: true,
      altitude: true,
      speed: true,
      progress: true
    }),
    renderMode: '2d',
    altitudeScaleMode: 'auto',
    waypointMode: 'compact',
    camera: () => ({
      center: [120, 30],
      zoom: 12,
      pitch: 0,
      bearing: 0
    })
  }
)

const emit = defineEmits<{
  'camera-change': [camera: CameraState]
  'timeline-change': [percent: number]
}>()

const mapContainer = ref<HTMLDivElement | null>(null)
const mapReady = ref(false)
let map: maplibregl.Map | null = null
let deckOverlay: DeckOverlay | null = null
let deckModules: DeckModules | null = null
let deckModulesPromise: Promise<DeckModules> | null = null
let fittedPointCount = 0

type DeckLayerConstructor = new (props: Record<string, unknown>) => unknown
type DeckOverlay = {
  setProps: (props: { layers: LayersList }) => void
  finalize: () => void
}
type DeckOverlayConstructor = new (props: { interleaved: boolean; layers: LayersList }) => DeckOverlay
type DeckModules = {
  MapboxOverlay: DeckOverlayConstructor
  PathLayer: DeckLayerConstructor
  ScatterplotLayer: DeckLayerConstructor
}

const progressPercent = computed(() => {
  if (props.durationS <= 0) return 0
  return Math.min(100, Math.max(0, (props.elapsedS / props.durationS) * 100))
})

const hudTime = computed(() => `${formatTime(props.elapsedS)} / ${formatTime(props.durationS)}`)

onMounted(() => {
  if (!mapContainer.value) return
  map = new maplibregl.Map({
    container: mapContainer.value,
    center: props.camera.center,
    zoom: props.camera.zoom,
    pitch: props.renderMode === '3d' ? Math.max(props.camera.pitch, 55) : props.camera.pitch,
    bearing: props.camera.bearing,
    scrollZoom: true,
    dragPan: true,
    style: {
      version: 8,
      sources: {
        esriWorldImagery: {
          type: 'raster',
          tiles: ['/tiles/esri/{z}/{x}/{y}'],
          tileSize: 256,
          attribution: 'Tiles (c) Esri'
        }
      },
      layers: [
        {
          id: 'esri-world-imagery',
          type: 'raster',
          source: 'esriWorldImagery'
        }
      ]
    }
  })
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')
  map.on('load', () => {
    mapReady.value = true
    syncStaticMapData()
    fitRouteIfNeeded()
  })
  map.on('moveend', emitCameraState)
})

watch(
  () => [
    props.points,
    props.waypoints,
    props.overlays.route,
    props.overlays.waypoints,
    props.renderMode,
    props.altitudeScaleMode,
    props.waypointMode
  ],
  () => {
    syncStaticMapData()
    fitRouteIfNeeded()
  }
)

watch(
  () => [props.currentPoint, props.elapsedS, props.durationS, props.overlays.marker, props.overlays.progress],
  () => {
    syncCurrentTimeMapData()
  }
)

watch(
  () => props.renderMode,
  () => {
    if (!map) return
    map.easeTo({
      pitch: props.renderMode === '3d' ? Math.max(props.camera.pitch, 55) : 0,
      duration: 250
    })
  }
)

watch(
  () => props.camera,
  () => {
    if (!map) return
    if (cameraMatchesMap(props.camera)) return
    map.easeTo({
      center: props.camera.center,
      zoom: props.camera.zoom,
      pitch: props.renderMode === '3d' ? props.camera.pitch : 0,
      bearing: props.camera.bearing,
      duration: 200
    })
  },
  { deep: true }
)

onBeforeUnmount(() => {
  deckOverlay?.finalize()
  deckOverlay = null
  map?.remove()
  map = null
})

function syncStaticMapData() {
  if (!map || !mapReady.value) return

  ensureGeoJsonSource('flight-route', createRouteFeature(optimizeDisplayPoints(props.points)))
  ensureGeoJsonSource('flight-waypoints', createWaypointFeatures())

  const showGroundRoute = props.renderMode !== '3d'
  const showGroundWaypoints = props.renderMode !== '3d'
  ensureLineLayer('flight-route-line', 'flight-route', '#56d6ff', 4, props.overlays.route && showGroundRoute)
  ensureCircleLayer(
    'flight-waypoint-circles',
    'flight-waypoints',
    '#ffd166',
    props.waypointMode === 'points' ? 5 : 7,
    props.overlays.waypoints && props.waypointMode !== 'hidden' && showGroundWaypoints
  )
  ensureSymbolLayer(
    'flight-waypoint-labels',
    'flight-waypoints',
    props.overlays.waypoints && ['compact', 'all'].includes(props.waypointMode) && showGroundWaypoints
  )
  syncCurrentTimeMapData()
  void syncDeckOverlay()
}

function syncCurrentTimeMapData() {
  if (!map || !mapReady.value) return

  ensureGeoJsonSource('flight-flown-route', createRouteFeature(optimizeDisplayPoints(createFlownPoints(), 1000)))
  ensureGeoJsonSource('flight-current-marker', createPointFeature(props.currentPoint))
  const showGroundRoute = props.renderMode !== '3d'
  ensureLineLayer('flight-flown-line', 'flight-flown-route', '#ff3864', 5, props.overlays.progress && showGroundRoute)
  ensureCircleLayer('flight-current-circle', 'flight-current-marker', '#ef233c', 8, props.overlays.marker && showGroundRoute)
  if (props.renderMode === '3d') {
    void syncDeckOverlay()
  }
}

function fitRouteIfNeeded() {
  if (!map || !mapReady.value || props.points.length < 1 || fittedPointCount === props.points.length) return

  const coordinates = [...props.points.map(toCoordinate), ...props.waypoints.map(toCoordinate)]
  const bounds = calculateBounds(coordinates)
  map.fitBounds(bounds, {
    padding: { top: 84, right: 84, bottom: 96, left: 84 },
    maxZoom: 17,
    duration: 0
  })
  fittedPointCount = props.points.length
}

async function syncDeckOverlay() {
  if (!map) return
  if (props.renderMode !== '3d') {
    deckOverlay?.setProps({ layers: [] })
    return
  }

  const modules = await loadDeckModules()
  if (!map || props.renderMode !== '3d') return

  if (!deckOverlay) {
    deckOverlay = new modules.MapboxOverlay({ interleaved: false, layers: [] })
    map.addControl(deckOverlay as unknown as maplibregl.IControl)
  }

  deckOverlay.setProps({
    layers: create3dLayers(modules) as LayersList
  })
}

async function loadDeckModules(): Promise<DeckModules> {
  if (deckModules) return deckModules
  deckModulesPromise ??= Promise.all([import('@deck.gl/mapbox'), import('@deck.gl/layers')]).then(
    ([mapboxModule, layersModule]) => {
      deckModules = {
        MapboxOverlay: mapboxModule.MapboxOverlay as unknown as DeckOverlayConstructor,
        PathLayer: layersModule.PathLayer as unknown as DeckLayerConstructor,
        ScatterplotLayer: layersModule.ScatterplotLayer as unknown as DeckLayerConstructor
      }
      return deckModules
    }
  )
  return deckModulesPromise
}

function create3dLayers(modules: DeckModules) {
  const altitudeScale = resolveAltitudeScale()
  const routePath = optimizeDisplayPoints(props.points).map((point) => toElevatedCoordinate(point, altitudeScale))
  const elevatedWaypoints = create3dWaypointData(altitudeScale)
  const currentPosition = props.currentPoint ? toElevatedCoordinate(props.currentPoint, altitudeScale) : null
  const groundPosition = props.currentPoint ? toGroundCoordinate(props.currentPoint) : null
  const heightGuidePath = currentPosition && groundPosition ? [groundPosition, currentPosition] : []

  return [
    new modules.PathLayer({
      id: 'flight-3d-route',
      data: [{ path: routePath }],
      getPath: (item: { path: number[][] }) => item.path,
      getColor: [86, 214, 255, 235],
      getWidth: 5,
      widthUnits: 'pixels',
      parameters: { depthTest: true }
    }),
    new modules.ScatterplotLayer({
      id: 'flight-3d-waypoints',
      data: elevatedWaypoints,
      getPosition: (item: { position: number[] }) => item.position,
      getFillColor: [255, 209, 102, 240],
      getLineColor: [3, 7, 18, 230],
      getLineWidth: 2,
      getRadius: 7,
      lineWidthUnits: 'pixels',
      radiusUnits: 'pixels',
      stroked: true,
      parameters: { depthTest: false }
    }),
    new modules.ScatterplotLayer({
      id: 'flight-3d-ground-shadow',
      data: groundPosition ? [{ position: groundPosition }] : [],
      getPosition: (item: { position: number[] }) => item.position,
      getFillColor: [3, 7, 18, 130],
      getRadius: 16,
      radiusUnits: 'pixels'
    }),
    new modules.PathLayer({
      id: 'flight-3d-height-guide',
      data: heightGuidePath.length ? [{ path: heightGuidePath }] : [],
      getPath: (item: { path: number[][] }) => item.path,
      getColor: [255, 255, 255, 160],
      getWidth: 2,
      widthUnits: 'pixels',
      parameters: { depthTest: false }
    }),
    new modules.ScatterplotLayer({
      id: 'flight-3d-marker',
      data: currentPosition ? [{ position: currentPosition }] : [],
      getPosition: (item: { position: number[] }) => item.position,
      getFillColor: [239, 35, 60, 240],
      getLineColor: [255, 255, 255, 255],
      getLineWidth: 2,
      getRadius: 9,
      lineWidthUnits: 'pixels',
      radiusUnits: 'pixels',
      stroked: true
    })
  ]
}

function create3dWaypointData(altitudeScale: number) {
  if (!props.overlays.waypoints || props.waypointMode === 'hidden') return []
  const waypoints = props.waypointMode === 'compact' ? compactWaypoints(props.waypoints) : props.waypoints
  return waypoints.map((waypoint) => ({
    position: toElevatedWaypointCoordinate(waypoint, altitudeScale),
    label: String(waypoint.seq)
  }))
}

function resolveAltitudeScale(): number {
  if (props.altitudeScaleMode === 'real-ratio') return 1
  if (props.altitudeScaleMode === 'enhanced') return 6

  const maxAltitude = Math.max(...props.points.map((point) => Math.max(0, point.relAltM)), 0)
  if (maxAltitude <= 0) return 1
  return clamp(90 / maxAltitude, 1.2, 8)
}

function ensureGeoJsonSource(id: string, data: Feature | FeatureCollection) {
  if (!map) return
  const source = map.getSource(id) as maplibregl.GeoJSONSource | undefined
  if (source) {
    source.setData(data)
    return
  }
  map.addSource(id, {
    type: 'geojson',
    data
  })
}

function ensureLineLayer(id: string, source: string, color: string, width: number, visible: boolean) {
  if (!map) return
  if (!map.getLayer(id)) {
    map.addLayer({
      id,
      type: 'line',
      source,
      paint: {
        'line-color': color,
        'line-width': width,
        'line-opacity': 0.9
      },
      layout: {
        'line-cap': 'round',
        'line-join': 'round',
        visibility: visible ? 'visible' : 'none'
      }
    })
    return
  }
  map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
}

function ensureCircleLayer(id: string, source: string, color: string, radius: number, visible: boolean) {
  if (!map) return
  if (!map.getLayer(id)) {
    map.addLayer({
      id,
      type: 'circle',
      source,
      paint: {
        'circle-color': color,
        'circle-radius': radius,
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': id === 'flight-current-circle' ? 3 : 1.5
      },
      layout: {
        visibility: visible ? 'visible' : 'none'
      }
    })
    return
  }
  map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
}

function ensureSymbolLayer(id: string, source: string, visible: boolean) {
  if (!map) return
  if (!map.getLayer(id)) {
    map.addLayer({
      id,
      type: 'symbol',
      source,
      layout: {
        'text-field': ['get', 'label'],
        'text-size': 11,
        'text-offset': [0, 1.15],
        'text-anchor': 'top',
        visibility: visible ? 'visible' : 'none'
      },
      paint: {
        'text-color': '#f8fafc',
        'text-halo-color': '#020617',
        'text-halo-width': 1.2
      }
    })
    return
  }
  map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
}

function createRouteFeature(points: TrackPoint[]): Feature<LineString> {
  return {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'LineString',
      coordinates: points.map(toCoordinate)
    }
  }
}

function createPointFeature(point: TrackPoint | null): Feature<Point> {
  return {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'Point',
      coordinates: point ? toCoordinate(point) : [0, 0]
    }
  }
}

function createWaypointFeatures(): FeatureCollection<Point> {
  const waypoints = props.waypointMode === 'compact' ? compactWaypoints(props.waypoints) : props.waypoints
  return {
    type: 'FeatureCollection',
    features: waypoints.map((waypoint) => ({
      type: 'Feature',
      properties: {
        label: String(waypoint.seq)
      },
      geometry: {
        type: 'Point',
        coordinates: toCoordinate(waypoint)
      }
    }))
  }
}

function createFlownPoints(): TrackPoint[] {
  if (!props.currentPoint) return []
  const lastFlownIndex = findTrackSegmentIndex(props.points, props.currentPoint.timeS)
  const flown = props.points.slice(0, Math.max(1, lastFlownIndex + 1))
  const last = flown[flown.length - 1]
  if (!last || last.timeS !== props.currentPoint.timeS) {
    flown.push(props.currentPoint)
  }
  return flown
}

function onMapProgressInput(event: Event) {
  const input = event.target as HTMLInputElement
  emit('timeline-change', Number(input.value))
}

function compactWaypoints(waypoints: Waypoint[]): Waypoint[] {
  if (waypoints.length <= 6) return waypoints
  return [
    waypoints[0],
    ...waypoints.slice(1, -1).filter((_, index) => index % 4 === 0),
    waypoints[waypoints.length - 1]
  ]
}

function optimizeDisplayPoints(points: TrackPoint[], maxPoints = 1500): TrackPoint[] {
  if (points.length <= maxPoints) return points
  const result: TrackPoint[] = []
  const seenIndexes = new Set<number>()
  const step = (points.length - 1) / (maxPoints - 1)

  for (let outputIndex = 0; outputIndex < maxPoints; outputIndex += 1) {
    const sourceIndex = Math.round(outputIndex * step)
    if (!seenIndexes.has(sourceIndex)) {
      seenIndexes.add(sourceIndex)
      result.push(points[sourceIndex])
    }
  }

  if (result[0] !== points[0]) {
    result.unshift(points[0])
  }
  if (result[result.length - 1] !== points[points.length - 1]) {
    result.push(points[points.length - 1])
  }
  return result
}

function calculateBounds(coordinates: [number, number][]): [[number, number], [number, number]] {
  const longitudes = coordinates.map(([lon]) => lon)
  const latitudes = coordinates.map(([, lat]) => lat)
  let minLon = Math.min(...longitudes)
  let maxLon = Math.max(...longitudes)
  let minLat = Math.min(...latitudes)
  let maxLat = Math.max(...latitudes)

  if (minLon === maxLon) {
    minLon -= 0.0002
    maxLon += 0.0002
  }
  if (minLat === maxLat) {
    minLat -= 0.0002
    maxLat += 0.0002
  }

  return [
    [minLon, minLat],
    [maxLon, maxLat]
  ]
}

function emitCameraState() {
  if (!map) return
  const center = map.getCenter()
  emit('camera-change', {
    center: [center.lng, center.lat],
    zoom: map.getZoom(),
    pitch: map.getPitch(),
    bearing: map.getBearing()
  })
}

function cameraMatchesMap(camera: CameraState): boolean {
  if (!map) return false
  const center = map.getCenter()
  return (
    Math.abs(center.lng - camera.center[0]) < 0.000001 &&
    Math.abs(center.lat - camera.center[1]) < 0.000001 &&
    Math.abs(map.getZoom() - camera.zoom) < 0.001 &&
    Math.abs(map.getPitch() - camera.pitch) < 0.001 &&
    Math.abs(map.getBearing() - camera.bearing) < 0.001
  )
}

function toCoordinate(point: TrackPoint | Waypoint): [number, number] {
  return [point.lon, point.lat]
}

function toGroundCoordinate(point: TrackPoint): [number, number, number] {
  return [point.lon, point.lat, 0]
}

function toElevatedCoordinate(point: TrackPoint, altitudeScale: number): [number, number, number] {
  return [point.lon, point.lat, Math.max(0, point.relAltM) * altitudeScale]
}

function toElevatedWaypointCoordinate(waypoint: Waypoint, altitudeScale: number): [number, number, number] {
  const nearestPoint = findNearestTrackPoint(waypoint)
  const altitudeM = nearestPoint?.relAltM ?? waypoint.altM ?? 0
  return [waypoint.lon, waypoint.lat, Math.max(0, altitudeM) * altitudeScale]
}

function findNearestTrackPoint(waypoint: Waypoint): TrackPoint | null {
  let nearest: TrackPoint | null = null
  let nearestDistance = Number.POSITIVE_INFINITY

  for (const point of props.points) {
    const distance = (point.lon - waypoint.lon) ** 2 + (point.lat - waypoint.lat) ** 2
    if (distance < nearestDistance) {
      nearest = point
      nearestDistance = distance
    }
  }

  return nearest
}

function formatTime(totalSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds))
  const minutes = Math.floor(safeSeconds / 60)
  const seconds = safeSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
</script>

<template>
  <div class="map-canvas">
    <div ref="mapContainer" class="maplibre-host" data-testid="maplibre-host"></div>
    <div class="hud">
      <span v-if="overlays.altitude">高度 {{ (currentPoint?.relAltM ?? 0).toFixed(1) }} m</span>
      <span v-if="overlays.speed">速度 {{ (currentPoint?.speedMS ?? 0).toFixed(1) }} m/s</span>
      <span v-if="overlays.progress">{{ hudTime }}</span>
    </div>
    <div v-if="renderMode === '3d'" class="relative-altitude-note">3D 高度基于日志相对高度</div>
    <input
      v-if="overlays.progress"
      data-testid="map-progress-slider"
      class="map-progress-slider"
      type="range"
      min="0"
      max="100"
      step="0.1"
      :value="progressPercent"
      aria-label="地图预览进度"
      @input="onMapProgressInput"
    />
  </div>
</template>
