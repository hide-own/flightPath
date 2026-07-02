<script setup lang="ts">
import { computed, onBeforeUnmount } from 'vue'
import { Download, FileUp, Map, Pause, Play } from 'lucide-vue-next'
import { darkTheme, NButton, NConfigProvider, NProgress } from 'naive-ui'
import MapPreview from './components/MapPreview.vue'
import {
  useFlightStore,
  type AltitudeScaleMode,
  type ExportViewMode,
  type OverlayState,
  type PlaybackRange,
  type RenderMode,
  type WaypointMode
} from './stores/flight'

const flightStore = useFlightStore()
let animationFrame: number | null = null

const compressedDisabled = computed(() => flightStore.exportOptions.timeMode === 'realtime')
const progressPercentage = computed(() => (flightStore.exportJobId ? flightStore.exportProgress : flightStore.timelineProgressPercent))
const statusText = computed(() => {
  if (flightStore.error) return `状态：${flightStore.error}`
  if (flightStore.exportStatus === 'queued') return '状态：导出任务已排队'
  if (flightStore.exportStatus === 'running') return `状态：正在导出 ${flightStore.exportProgress}%`
  if (flightStore.exportStatus === 'completed') return '状态：视频已生成，可以下载'
  if (flightStore.status === 'queued') return '状态：解析任务已排队'
  if (flightStore.status === 'parsing' || flightStore.status === 'running') return '状态：正在解析日志'
  if (flightStore.status === 'completed') return '状态：日志解析完成，可以预览轨迹'
  return '状态：等待选择日志'
})

function onLogFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  flightStore.setLogFile(input.files?.[0] ?? null)
}

async function startParse() {
  try {
    await flightStore.parseSelectedLog()
    await flightStore.waitForParseJob()
  } catch {
    // Store owns the localized validation message.
  }
}

async function startExport() {
  try {
    if (flightStore.exportDownloadUrl) {
      window.location.href = flightStore.exportDownloadUrl
      return
    }
    await flightStore.startExport()
    await flightStore.waitForExportJob()
  } catch {
    // Store owns the localized validation message.
  }
}

function setPlaybackRange(range: PlaybackRange) {
  flightStore.setPlaybackRange(range)
}

function setRenderMode(mode: RenderMode) {
  flightStore.preview.renderMode = mode
}

function setWaypointMode(mode: WaypointMode) {
  flightStore.preview.waypointMode = mode
}

function setAltitudeScaleMode(mode: AltitudeScaleMode) {
  flightStore.preview.altitudeScaleMode = mode
}

function setExportView(mode: ExportViewMode) {
  flightStore.exportOptions.viewMode = mode
}

function onPlaybackSpeedChange(event: Event) {
  const input = event.target as HTMLSelectElement
  flightStore.setPlaybackSpeed(Number(input.value))
}

function toggleOverlay(name: keyof OverlayState) {
  flightStore.setOverlay(name, !flightStore.preview.overlays[name])
}

function onTimelineInput(event: Event) {
  const input = event.target as HTMLInputElement
  flightStore.setTimelineProgress(Number(input.value))
}

function onTimelinePercentChange(percent: number) {
  flightStore.setTimelineProgress(percent)
}

function togglePlayback() {
  try {
    if (flightStore.preview.isPlaying) {
      stopPlayback()
      return
    }
    flightStore.playPreview()
    schedulePlayback()
  } catch {
    // Store owns the localized validation message.
  }
}

function schedulePlayback() {
  cancelScheduledPlayback()
  animationFrame = requestAnimationFrame((now) => {
    flightStore.advancePreview(now)
    if (flightStore.preview.isPlaying) {
      schedulePlayback()
    }
  })
}

function stopPlayback() {
  flightStore.pausePreview()
  cancelScheduledPlayback()
}

function cancelScheduledPlayback() {
  if (animationFrame !== null) {
    cancelAnimationFrame(animationFrame)
    animationFrame = null
  }
}

onBeforeUnmount(cancelScheduledPlayback)
</script>

<template>
  <n-config-provider :theme="darkTheme">
    <main class="app-shell">
      <aside class="control-panel" data-testid="control-panel">
        <header class="brand-block">
          <div class="brand-icon">
            <Map :size="22" />
          </div>
          <div>
            <h1>飞行日志轨迹视频生成工具</h1>
            <p>本地 Web 版</p>
          </div>
        </header>

        <section class="control-section">
          <h2>文件</h2>
          <label class="file-picker">
            <input data-testid="log-file-input" type="file" accept=".bin" @change="onLogFileChange" />
            <span>
              <FileUp :size="17" />
              {{ flightStore.logFile?.name ?? '选择 .bin 日志文件' }}
            </span>
          </label>
          <n-button data-testid="download-action" class="full-button" secondary @click="startExport">
            <template #icon>
              <Download :size="17" />
            </template>
            {{ flightStore.exportDownloadUrl ? '下载 MP4' : '生成/下载 MP4' }}
          </n-button>
        </section>

        <section v-if="flightStore.summary" class="control-section summary-grid" data-testid="log-summary">
          <h2>日志信息</h2>
          <div>
            <span>GPS 点 {{ flightStore.summary.gpsCount }}</span>
          </div>
          <div>
            <span>飞行时长 {{ flightStore.summary.selectedDurationS.toFixed(1) }} s</span>
          </div>
          <div>
            <span>最高高度 {{ flightStore.summary.maxRelativeAltitudeM.toFixed(1) }} m</span>
          </div>
          <div>
            <span>航点 {{ flightStore.summary.waypointCount }}</span>
          </div>
        </section>

        <section class="control-section">
          <h2>播放范围</h2>
          <div class="segmented">
            <button
              data-testid="range-true-flight"
              :class="{ 'is-selected': flightStore.playbackRange === 'true-flight' }"
              @click="setPlaybackRange('true-flight')"
            >
              真正飞行阶段
            </button>
            <button
              data-testid="range-full-log"
              :class="{ 'is-selected': flightStore.playbackRange === 'full-log' }"
              @click="setPlaybackRange('full-log')"
            >
              全部日志
            </button>
          </div>
        </section>

        <section class="control-section">
          <h2>时间模式</h2>
          <div class="segmented">
            <button
              data-testid="time-realtime"
              :class="{ 'is-selected': flightStore.exportOptions.timeMode === 'realtime' }"
              @click="flightStore.exportOptions.timeMode = 'realtime'"
            >
              真实时间
            </button>
            <button
              data-testid="time-compressed"
              :class="{ 'is-selected': flightStore.exportOptions.timeMode === 'compressed' }"
              @click="flightStore.exportOptions.timeMode = 'compressed'"
            >
              压缩时长
            </button>
          </div>
          <label class="field-label">
            压缩时长（秒）
            <input
              v-model.number="flightStore.exportOptions.compressedDurationS"
              type="number"
              data-testid="compressed-duration"
              :disabled="compressedDisabled"
              :min="10"
              :max="7200"
              class="duration-input"
            />
          </label>
        </section>

        <section class="control-section">
          <h2>显示</h2>
          <div class="chip-row">
            <button
              data-testid="overlay-route"
              class="chip"
              :class="{ 'is-selected': flightStore.preview.overlays.route }"
              @click="toggleOverlay('route')"
            >
              轨迹
            </button>
            <button
              data-testid="overlay-waypoints"
              class="chip"
              :class="{ 'is-selected': flightStore.preview.overlays.waypoints }"
              @click="toggleOverlay('waypoints')"
            >
              航点
            </button>
            <button
              data-testid="overlay-altitude"
              class="chip"
              :class="{ 'is-selected': flightStore.preview.overlays.altitude }"
              @click="toggleOverlay('altitude')"
            >
              高度
            </button>
            <button
              data-testid="overlay-speed"
              class="chip"
              :class="{ 'is-selected': flightStore.preview.overlays.speed }"
              @click="toggleOverlay('speed')"
            >
              速度
            </button>
            <button
              data-testid="overlay-progress"
              class="chip"
              :class="{ 'is-selected': flightStore.preview.overlays.progress }"
              @click="toggleOverlay('progress')"
            >
              进度条
            </button>
          </div>
        </section>

        <details class="control-section collapsible-section" data-testid="advanced-preview-settings">
          <summary>高级预览</summary>
          <div class="collapsible-content">
        <section class="control-section">
          <h2>航点模式</h2>
          <div class="segmented vertical compact-segmented">
            <button
              data-testid="waypoint-hidden"
              :class="{ 'is-selected': flightStore.preview.waypointMode === 'hidden' }"
              @click="setWaypointMode('hidden')"
            >
              隐藏航点
            </button>
            <button
              data-testid="waypoint-points"
              :class="{ 'is-selected': flightStore.preview.waypointMode === 'points' }"
              @click="setWaypointMode('points')"
            >
              仅显示点
            </button>
            <button
              data-testid="waypoint-compact"
              :class="{ 'is-selected': flightStore.preview.waypointMode === 'compact' }"
              @click="setWaypointMode('compact')"
            >
              简洁编号
            </button>
            <button
              data-testid="waypoint-all"
              :class="{ 'is-selected': flightStore.preview.waypointMode === 'all' }"
              @click="setWaypointMode('all')"
            >
              全部编号
            </button>
          </div>
        </section>

        <section class="control-section">
          <h2>轨迹模式</h2>
          <div class="segmented">
            <button
              data-testid="render-2d"
              :class="{ 'is-selected': flightStore.preview.renderMode === '2d' }"
              @click="setRenderMode('2d')"
            >
              2D
            </button>
            <button
              data-testid="render-3d"
              :class="{ 'is-selected': flightStore.preview.renderMode === '3d' }"
              @click="setRenderMode('3d')"
            >
              3D
            </button>
          </div>
        </section>

        <section class="control-section">
          <h2>3D 高度比例</h2>
          <div class="segmented vertical compact-segmented">
            <button
              data-testid="altitude-scale-auto"
              :class="{ 'is-selected': flightStore.preview.altitudeScaleMode === 'auto' }"
              @click="setAltitudeScaleMode('auto')"
            >
              自动
            </button>
            <button
              data-testid="altitude-scale-real"
              :class="{ 'is-selected': flightStore.preview.altitudeScaleMode === 'real-ratio' }"
              @click="setAltitudeScaleMode('real-ratio')"
            >
              真实比例
            </button>
            <button
              data-testid="altitude-scale-enhanced"
              :class="{ 'is-selected': flightStore.preview.altitudeScaleMode === 'enhanced' }"
              @click="setAltitudeScaleMode('enhanced')"
            >
              增强
            </button>
          </div>
          <label class="field-label">
            俯仰角
            <input
              v-model.number="flightStore.preview.camera.pitch"
              data-testid="camera-pitch"
              type="range"
              min="0"
              max="75"
              class="range-input"
            />
          </label>
          <label class="field-label">
            方位角
            <input
              v-model.number="flightStore.preview.camera.bearing"
              data-testid="camera-bearing"
              type="range"
              min="-180"
              max="180"
              class="range-input"
            />
          </label>
        </section>

          </div>
        </details>

        <details class="control-section collapsible-section" data-testid="advanced-export-settings">
          <summary>导出设置</summary>
          <div class="collapsible-content">
        <section class="control-section">
          <h2>导出</h2>
          <div class="segmented vertical">
            <button
              data-testid="export-current"
              :class="{ 'is-selected': flightStore.exportOptions.viewMode === 'current' }"
              @click="setExportView('current')"
            >
              使用当前预览视角
            </button>
            <button
              data-testid="export-auto-fit"
              :class="{ 'is-selected': flightStore.exportOptions.viewMode === 'auto-fit' }"
              @click="setExportView('auto-fit')"
            >
              自动适配完整轨迹
            </button>
            <button
              data-testid="export-follow"
              :class="{ 'is-selected': flightStore.exportOptions.viewMode === 'follow' }"
              @click="setExportView('follow')"
            >
              跟随飞行器移动
            </button>
          </div>
        </section>

        <section class="control-section settings-grid">
          <label>
            分辨率
            <select v-model="flightStore.exportOptions.resolution" data-testid="resolution-select">
              <option value="1280x720">1280x720</option>
              <option value="1920x1080">1920x1080</option>
            </select>
          </label>
          <label>
            帧率
            <select v-model="flightStore.exportOptions.fps" data-testid="fps-select">
              <option value="24">24fps</option>
              <option value="30">30fps</option>
              <option value="60">60fps</option>
            </select>
          </label>
        </section>

          </div>
        </details>

        <footer class="action-area">
          <n-button data-testid="parse-action" type="primary" class="full-button" @click="startParse">
            <template #icon>
              <Play :size="17" />
            </template>
            生成视频
          </n-button>
          <n-progress type="line" :percentage="progressPercentage" :show-indicator="false" />
          <p>{{ statusText }}</p>
        </footer>
      </aside>

      <section class="map-workspace" data-testid="map-workspace">
        <div class="map-topbar">
          <div>
            <strong>卫星地图预览</strong>
            <span>2D / 3D 相对高度轨迹</span>
          </div>
          <div class="mode-badge">当前预览视角</div>
        </div>
        <MapPreview
          :points="flightStore.activePoints"
          :waypoints="flightStore.waypoints"
          :current-point="flightStore.currentPoint"
          :elapsed-s="flightStore.previewElapsedS"
          :duration-s="flightStore.previewDurationS"
          :overlays="flightStore.preview.overlays"
          :render-mode="flightStore.preview.renderMode"
          :altitude-scale-mode="flightStore.preview.altitudeScaleMode"
          :waypoint-mode="flightStore.preview.waypointMode"
          :camera="flightStore.preview.camera"
          @camera-change="flightStore.updateCamera"
          @timeline-change="onTimelinePercentChange"
        />
        <div class="timeline">
          <button
            type="button"
            :aria-label="flightStore.preview.isPlaying ? '暂停预览' : '播放预览'"
            @click="togglePlayback"
          >
            <Pause v-if="flightStore.preview.isPlaying" :size="16" />
            <Play v-else :size="16" />
          </button>
          <select
            data-testid="playback-speed-select"
            class="playback-speed-select"
            :value="String(flightStore.preview.playbackSpeed)"
            aria-label="播放速度"
            @change="onPlaybackSpeedChange"
          >
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="1.5">1.5x</option>
            <option value="2">2x</option>
            <option value="4">4x</option>
          </select>
          <input
            data-testid="timeline-slider"
            type="range"
            min="0"
            max="100"
            :value="flightStore.timelineProgressPercent"
            aria-label="时间轴"
            @input="onTimelineInput"
          />
        </div>
      </section>
    </main>
  </n-config-provider>
</template>
