import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MapPreview from '../src/components/MapPreview.vue'

const deckMocks = vi.hoisted(() => {
  const mapboxOverlay = vi.fn(function (options: unknown) {
    return { options, setProps: vi.fn() }
  })
  const pathLayer = vi.fn(function (props: unknown) {
    return { kind: 'PathLayer', props }
  })
  const scatterplotLayer = vi.fn(function (props: unknown) {
    return { kind: 'ScatterplotLayer', props }
  })

  return { mapboxOverlay, pathLayer, scatterplotLayer }
})

const maplibreMocks = vi.hoisted(() => {
  const remove = vi.fn()
  const addControl = vi.fn()
  const addSource = vi.fn()
  const addLayer = vi.fn()
  const fitBounds = vi.fn()
  const getLayer = vi.fn(() => undefined)
  const setLayoutProperty = vi.fn()
  const sourceData = new globalThis.Map<string, { setData: ReturnType<typeof vi.fn> }>()
  const getSource = vi.fn((id: string) => sourceData.get(id))
  const on = vi.fn((event: string, callback: () => void) => {
    if (event === 'load') callback()
  })
  const mapConstructor = vi.fn(function (_options: unknown) {
    return {
      addControl,
      addLayer,
      addSource: (id: string, source: unknown) => {
        const storedSource = { setData: vi.fn() }
        sourceData.set(id, storedSource)
        addSource(id, source)
      },
      fitBounds,
      getBearing: () => 0,
      getCenter: () => ({ lng: 120, lat: 30 }),
      getLayer,
      getPitch: () => 0,
      getSource,
      getZoom: () => 12,
      easeTo: vi.fn(),
      on,
      remove,
      setLayoutProperty
    }
  })
  const navigationControl = vi.fn(function (_options?: unknown) {
    return {}
  })

  return {
    addControl,
    addLayer,
    addSource,
    fitBounds,
    getLayer,
    getSource,
    mapConstructor,
    navigationControl,
    on,
    remove,
    setLayoutProperty,
    sourceData
  }
})

vi.mock('maplibre-gl', () => ({
  default: {
    Map: maplibreMocks.mapConstructor,
    NavigationControl: maplibreMocks.navigationControl
  }
}))

vi.mock('@deck.gl/mapbox', () => ({
  MapboxOverlay: deckMocks.mapboxOverlay
}))

vi.mock('@deck.gl/layers', () => ({
  PathLayer: deckMocks.pathLayer,
  ScatterplotLayer: deckMocks.scatterplotLayer
}))

describe('MapPreview', () => {
  beforeEach(() => {
    maplibreMocks.addControl.mockClear()
    maplibreMocks.addLayer.mockClear()
    maplibreMocks.addSource.mockClear()
    maplibreMocks.fitBounds.mockClear()
    maplibreMocks.getLayer.mockClear()
    maplibreMocks.getSource.mockClear()
    maplibreMocks.mapConstructor.mockClear()
    maplibreMocks.navigationControl.mockClear()
    maplibreMocks.on.mockClear()
    maplibreMocks.remove.mockClear()
    maplibreMocks.setLayoutProperty.mockClear()
    maplibreMocks.sourceData.clear()
    deckMocks.mapboxOverlay.mockClear()
    deckMocks.pathLayer.mockClear()
    deckMocks.scatterplotLayer.mockClear()
  })

  it('creates a MapLibre satellite map using the local tile endpoint', () => {
    mount(MapPreview)

    expect(maplibreMocks.mapConstructor).toHaveBeenCalledOnce()
    const [options] = maplibreMocks.mapConstructor.mock.calls[0] as [
      {
        dragPan: boolean
        scrollZoom: boolean
        style: { sources: { esriWorldImagery: { tiles: string[] } } }
      }
    ]
    expect(options.style.sources.esriWorldImagery.tiles).toEqual(['/tiles/esri/{z}/{x}/{y}'])
    expect(options.scrollZoom).toBe(true)
    expect(options.dragPan).toBe(true)
    expect(maplibreMocks.addControl).toHaveBeenCalled()
  })

  it('renders route, flown path, current marker and waypoint sources from parsed data', () => {
    mount(MapPreview, {
      props: {
        points: [
          { timeS: 2, lat: 30, lon: 120, relAltM: 2, speedMS: 2 },
          { timeS: 12, lat: 30.0002, lon: 120.0002, relAltM: 5.5, speedMS: 4 },
          { timeS: 20, lat: 30.0004, lon: 120.0004, relAltM: 10, speedMS: 6 }
        ],
        currentPoint: { timeS: 12, lat: 30.0002, lon: 120.0002, relAltM: 5.5, speedMS: 4 },
        waypoints: [{ seq: 1, lat: 30, lon: 120, altM: 20, command: 16 }],
        elapsedS: 10,
        durationS: 18
      }
    })

    expect(maplibreMocks.addSource).toHaveBeenCalledWith(
      'flight-route',
      expect.objectContaining({
        data: expect.objectContaining({
          geometry: expect.objectContaining({
            coordinates: [
              [120, 30],
              [120.0002, 30.0002],
              [120.0004, 30.0004]
            ]
          })
        })
      })
    )
    expect(maplibreMocks.addSource).toHaveBeenCalledWith(
      'flight-current-marker',
      expect.objectContaining({
        data: expect.objectContaining({
          geometry: expect.objectContaining({ coordinates: [120.0002, 30.0002] })
        })
      })
    )
    expect(maplibreMocks.addSource).toHaveBeenCalledWith(
      'flight-waypoints',
      expect.objectContaining({
        data: expect.objectContaining({
          features: [expect.objectContaining({ properties: expect.objectContaining({ label: '1' }) })]
        })
      })
    )
    expect(maplibreMocks.fitBounds).toHaveBeenCalledWith(
      [
        [120, 30],
        [120.0004, 30.0004]
      ],
      expect.objectContaining({
        maxZoom: 17,
        padding: expect.objectContaining({ left: 84, top: 84 })
      })
    )
  })

  it('applies waypoint display modes with compact density handling', () => {
    const denseWaypoints = Array.from({ length: 12 }, (_, index) => ({
      seq: index + 1,
      lat: 30 + index * 0.0001,
      lon: 120 + index * 0.0001,
      altM: 20,
      command: 16
    }))

    mount(MapPreview, {
      props: {
        points: [
          { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
          { timeS: 10, lat: 30.0011, lon: 120.0011, relAltM: 10, speedMS: 5 }
        ],
        waypoints: denseWaypoints,
        waypointMode: 'compact'
      }
    })

    const waypointSourceCall = maplibreMocks.addSource.mock.calls.find(([id]) => id === 'flight-waypoints')
    const features = waypointSourceCall?.[1].data.features
    expect(features.length).toBeLessThan(denseWaypoints.length)
    expect(features[0].properties.label).toBe('1')
    expect(features.at(-1).properties.label).toBe('12')
  })

  it('hides waypoint labels in points-only mode and all waypoint layers in hidden mode', () => {
    mount(MapPreview, {
      props: {
        points: [
          { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
          { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 }
        ],
        waypoints: [{ seq: 1, lat: 30, lon: 120, altM: 20, command: 16 }],
        waypointMode: 'points'
      }
    })

    expect(maplibreMocks.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-waypoint-labels',
        layout: expect.objectContaining({ visibility: 'none' })
      })
    )

    maplibreMocks.addLayer.mockClear()
    mount(MapPreview, {
      props: {
        points: [
          { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
          { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 }
        ],
        waypoints: [{ seq: 1, lat: 30, lon: 120, altM: 20, command: 16 }],
        waypointMode: 'hidden'
      }
    })

    expect(maplibreMocks.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-waypoint-circles',
        layout: expect.objectContaining({ visibility: 'none' })
      })
    )
  })

  it('renders elevated route, marker, height guide and ground shadow in 3D mode', async () => {
    mount(MapPreview, {
      props: {
        points: [
          { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
          { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 }
        ],
        currentPoint: { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 },
        renderMode: '3d',
        altitudeScaleMode: 'enhanced'
      }
    })

    await vi.waitFor(() => expect(deckMocks.mapboxOverlay).toHaveBeenCalled())
    expect(deckMocks.pathLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-3d-route',
        data: [
          {
            path: [
              [120, 30, 0],
              [120.001, 30.001, 60]
            ]
          }
        ]
      })
    )
    expect(deckMocks.pathLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-3d-height-guide',
        data: [{ path: [[120.001, 30.001, 0], [120.001, 30.001, 60]] }]
      })
    )
    expect(deckMocks.scatterplotLayer).toHaveBeenCalledWith(expect.objectContaining({ id: 'flight-3d-marker' }))
    expect(deckMocks.scatterplotLayer).toHaveBeenCalledWith(expect.objectContaining({ id: 'flight-3d-ground-shadow' }))
  })

  it('hides 2D ground route layers in 3D mode so only the elevated route remains', async () => {
    mount(MapPreview, {
      props: {
        points: [
          { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
          { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 }
        ],
        currentPoint: { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 },
        renderMode: '3d'
      }
    })

    expect(maplibreMocks.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-route-line',
        layout: expect.objectContaining({ visibility: 'none' })
      })
    )
    expect(maplibreMocks.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-flown-line',
        layout: expect.objectContaining({ visibility: 'none' })
      })
    )
    await vi.waitFor(() => expect(deckMocks.pathLayer).toHaveBeenCalledWith(expect.objectContaining({ id: 'flight-3d-route' })))
  })

  it('renders waypoints on the elevated 3D route instead of the 2D map in 3D mode', async () => {
    mount(MapPreview, {
      props: {
        points: [
          { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
          { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 }
        ],
        waypoints: [{ seq: 1, lat: 30.001, lon: 120.001, altM: 20, command: 16 }],
        renderMode: '3d',
        altitudeScaleMode: 'enhanced'
      }
    })

    expect(maplibreMocks.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-waypoint-circles',
        layout: expect.objectContaining({ visibility: 'none' })
      })
    )
    expect(maplibreMocks.addLayer).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'flight-waypoint-labels',
        layout: expect.objectContaining({ visibility: 'none' })
      })
    )
    await vi.waitFor(() =>
      expect(deckMocks.scatterplotLayer).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'flight-3d-waypoints',
          data: [{ position: [120.001, 30.001, 60], label: '1' }]
        })
      )
    )
  })

  it('downsamples very long display routes while keeping endpoints visible', () => {
    const longPoints = Array.from({ length: 5000 }, (_, index) => ({
      timeS: index,
      lat: 30 + index * 0.00001,
      lon: 120 + index * 0.00001,
      relAltM: index % 80,
      speedMS: 4
    }))

    mount(MapPreview, {
      props: {
        points: longPoints,
        currentPoint: longPoints[2500]
      }
    })

    const routeSourceCall = maplibreMocks.addSource.mock.calls.find(([id]) => id === 'flight-route')
    const coordinates = routeSourceCall?.[1].data.geometry.coordinates

    expect(coordinates.length).toBeLessThanOrEqual(1500)
    expect(coordinates[0]).toEqual([120, 30])
    expect(coordinates.at(-1)).toEqual([120 + 4999 * 0.00001, 30 + 4999 * 0.00001])
  })

  it('exposes the map progress as a draggable timeline control', async () => {
    const wrapper = mount(MapPreview, {
      props: {
        points: [
          { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
          { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 }
        ],
        elapsedS: 2.5,
        durationS: 10
      }
    })

    const slider = wrapper.get('[data-testid="map-progress-slider"]')
    expect((slider.element as HTMLInputElement).value).toBe('25')

    await slider.setValue(40)

    expect(wrapper.emitted('timeline-change')?.[0]).toEqual([40])
  })

  it('updates only current-time map sources when the current point changes', async () => {
    const points = [
      { timeS: 0, lat: 30, lon: 120, relAltM: 0, speedMS: 0 },
      { timeS: 10, lat: 30.001, lon: 120.001, relAltM: 10, speedMS: 5 },
      { timeS: 20, lat: 30.002, lon: 120.002, relAltM: 20, speedMS: 6 }
    ]
    const wrapper = mount(MapPreview, {
      props: {
        points,
        currentPoint: points[0]
      }
    })
    const routeSource = maplibreMocks.sourceData.get('flight-route')
    const flownSource = maplibreMocks.sourceData.get('flight-flown-route')
    const markerSource = maplibreMocks.sourceData.get('flight-current-marker')
    routeSource?.setData.mockClear()
    flownSource?.setData.mockClear()
    markerSource?.setData.mockClear()

    await wrapper.setProps({ currentPoint: points[1], elapsedS: 10 })

    expect(routeSource?.setData).not.toHaveBeenCalled()
    expect(flownSource?.setData).toHaveBeenCalled()
    expect(markerSource?.setData).toHaveBeenCalled()
  })
})
