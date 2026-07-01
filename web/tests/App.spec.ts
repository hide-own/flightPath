import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import App from '../src/App.vue'
import { useFlightStore } from '../src/stores/flight'

const mapPreviewStub = {
  template: '<div data-testid="maplibre-host"></div>'
}

describe('App layout', () => {
  it('renders a left control panel and right map workspace', () => {
    const wrapper = mountApp()

    expect(wrapper.get('[data-testid="control-panel"]').text()).toContain('日志文件')
    expect(wrapper.get('[data-testid="map-workspace"]').text()).toContain('卫星地图预览')
    expect(wrapper.get('[data-testid="log-file-input"]').attributes('accept')).toBe('.bin')
    expect(wrapper.get('[data-testid="download-action"]').text()).toContain('下载 MP4')
  })

  it('highlights selected modes and disables compressed duration in realtime mode', async () => {
    const wrapper = mountApp()

    expect(wrapper.get('[data-testid="range-true-flight"]').classes()).toContain('is-selected')
    expect(wrapper.get('[data-testid="time-realtime"]').classes()).toContain('is-selected')
    expect(wrapper.get('[data-testid="compressed-duration"]').attributes('disabled')).toBeDefined()

    await wrapper.get('[data-testid="time-compressed"]').trigger('click')

    expect(wrapper.get('[data-testid="time-compressed"]').classes()).toContain('is-selected')
    expect(wrapper.get('[data-testid="compressed-duration"]').attributes('disabled')).toBeUndefined()
  })

  it('renders and updates display, render, export, resolution and frame-rate controls', async () => {
    const wrapper = mountApp()
    const store = useFlightStore()

    expect(wrapper.get('[data-testid="overlay-altitude"]').classes()).toContain('is-selected')
    await wrapper.get('[data-testid="overlay-altitude"]').trigger('click')
    expect(wrapper.get('[data-testid="overlay-altitude"]').classes()).not.toContain('is-selected')

    expect(wrapper.get('[data-testid="render-2d"]').classes()).toContain('is-selected')
    await wrapper.get('[data-testid="render-3d"]').trigger('click')
    expect(wrapper.get('[data-testid="render-3d"]').classes()).toContain('is-selected')

    expect(wrapper.get('[data-testid="altitude-scale-auto"]').classes()).toContain('is-selected')
    await wrapper.get('[data-testid="altitude-scale-enhanced"]').trigger('click')
    expect(wrapper.get('[data-testid="altitude-scale-enhanced"]').classes()).toContain('is-selected')

    await wrapper.get('[data-testid="camera-pitch"]').setValue(58)
    await wrapper.get('[data-testid="camera-bearing"]').setValue(35)
    expect(store.preview.camera.pitch).toBe(58)
    expect(store.preview.camera.bearing).toBe(35)

    expect(wrapper.get('[data-testid="waypoint-compact"]').classes()).toContain('is-selected')
    await wrapper.get('[data-testid="waypoint-points"]').trigger('click')
    expect(wrapper.get('[data-testid="waypoint-points"]').classes()).toContain('is-selected')

    expect(wrapper.get('[data-testid="export-current"]').classes()).toContain('is-selected')
    await wrapper.get('[data-testid="export-auto-fit"]').trigger('click')
    expect(wrapper.get('[data-testid="export-auto-fit"]').classes()).toContain('is-selected')

    expect((wrapper.get('[data-testid="resolution-select"]').element as HTMLSelectElement).value).toBe('1280x720')
    expect((wrapper.get('[data-testid="fps-select"]').element as HTMLSelectElement).value).toBe('24')
  })

  it('renders parsed log summary when available', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useFlightStore()
    store.summary = {
      gpsCount: 42,
      selectedDurationS: 18.5,
      maxRelativeAltitudeM: 36.2,
      maxSpeedMS: 9.1,
      waypointCount: 4
    }

    const wrapper = mount(App, {
      global: {
        plugins: [pinia],
        stubs: {
          MapPreview: mapPreviewStub
        }
      }
    })

    expect(wrapper.get('[data-testid="log-summary"]').text()).toContain('GPS 点 42')
    expect(wrapper.get('[data-testid="log-summary"]').text()).toContain('最高高度 36.2 m')
  })

  it('scrubs preview timeline through the flight store', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useFlightStore()
    store.selectedPoints = [
      { timeS: 2, lat: 30, lon: 120, relAltM: 2, speedMS: 2 },
      { timeS: 20, lat: 30.0004, lon: 120.0004, relAltM: 10, speedMS: 6 }
    ]
    store.preview.currentTimeS = 2

    const wrapper = mount(App, {
      global: {
        plugins: [pinia],
        stubs: {
          MapPreview: mapPreviewStub
        }
      }
    })

    await wrapper.get('[data-testid="timeline-slider"]').setValue(50)

    expect(store.currentTimeS).toBe(11)
  })
})

function mountApp() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(App, {
    global: {
      plugins: [pinia],
      stubs: {
        MapPreview: mapPreviewStub
      }
    }
  })
}
