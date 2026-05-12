<template>
  <!-- Full-screen overlay modal for drawing zone polygons on live camera feed -->
  <teleport to="body">
    <div class="fixed inset-0 z-50 flex flex-col bg-black" @keydown.esc="$emit('cancel')">
      <!-- Header bar -->
      <div class="flex items-center gap-3 px-4 py-3 bg-base-900/90 border-b border-white/10">
        <span class="text-white font-semibold">Draw Zone — {{ cameraName }}</span>
        <span class="text-xs text-white/50 ml-2">
          Click to add points &nbsp;·&nbsp; Double-click or press Enter to save &nbsp;·&nbsp; ESC to cancel
        </span>
        <div class="ml-auto flex gap-2">
          <button class="btn btn-xs btn-ghost text-white/70" @click="undo" :disabled="points.length === 0">Undo</button>
          <button class="btn btn-xs btn-ghost text-white/70" @click="reset">Clear</button>
          <button class="btn btn-xs btn-error" @click="$emit('cancel')">Cancel</button>
          <button class="btn btn-xs btn-success" :disabled="points.length < 3" @click="save">
            Save Zone ({{ points.length }} pts)
          </button>
        </div>
      </div>

      <!-- Canvas area -->
      <div class="flex-1 relative flex items-center justify-center overflow-hidden bg-black">
        <!-- Live MJPEG stream as background -->
        <img
          ref="imgEl"
          :src="streamUrl"
          class="max-h-full max-w-full object-contain"
          @load="syncCanvas"
          alt="camera feed"
        />
        <!-- SVG canvas overlay — pointer-events active -->
        <svg
          ref="svgEl"
          class="absolute"
          :style="svgStyle"
          @click="onCanvasClick"
          @dblclick.prevent="save"
          style="cursor: crosshair;"
        >
          <!-- Filled polygon preview -->
          <polygon
            v-if="points.length >= 3"
            :points="svgPoints"
            :fill="fillColor"
            fill-opacity="0.25"
            :stroke="color"
            stroke-width="2"
            stroke-linejoin="round"
          />
          <!-- Polyline for in-progress edges -->
          <polyline
            :points="svgPoints + (points.length >= 1 ? '' : '')"
            fill="none"
            :stroke="color"
            stroke-width="2"
            stroke-dasharray="6 3"
          />
          <!-- Vertex dots -->
          <circle
            v-for="(pt, i) in points"
            :key="i"
            :cx="pt.x"
            :cy="pt.y"
            r="6"
            :fill="i === 0 ? color : 'white'"
            :stroke="color"
            stroke-width="2"
          />
          <!-- Point labels -->
          <text
            v-for="(pt, i) in points"
            :key="'lbl-'+i"
            :x="pt.x + 8"
            :y="pt.y - 6"
            font-size="11"
            fill="white"
            paint-order="stroke"
            stroke="black"
            stroke-width="3"
          >{{ i + 1 }}</text>
        </svg>
      </div>

      <!-- Bottom instruction bar -->
      <div class="flex items-center gap-4 px-4 py-2 bg-base-900/80 border-t border-white/10 text-xs text-white/50">
        <span>Points: <b class="text-white">{{ points.length }}</b></span>
        <span v-if="points.length < 3" class="text-warning">Need at least 3 points to form a zone</span>
        <span v-else class="text-success">Ready to save</span>
        <div class="ml-auto flex items-center gap-2">
          <label class="text-white/60">Color:</label>
          <input type="color" v-model="color" class="h-6 w-10 rounded cursor-pointer" />
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps<{
  cameraId: number
  cameraName: string
  streamUrl: string
}>()

const emit = defineEmits<{
  cancel: []
  save: [payload: { coordinates: [number, number][], color: string }]
}>()

const imgEl = ref<HTMLImageElement | null>(null)
const svgEl = ref<SVGSVGElement | null>(null)
const points = ref<{ x: number; y: number }[]>([])
const color = ref('#FF6B6B')
const svgRect = ref({ left: 0, top: 0, width: 0, height: 0 })

const fillColor = computed(() => color.value)
const svgPoints = computed(() =>
  points.value.map(p => `${p.x},${p.y}`).join(' ')
)
const svgStyle = computed(() => ({
  left: `${svgRect.value.left}px`,
  top: `${svgRect.value.top}px`,
  width: `${svgRect.value.width}px`,
  height: `${svgRect.value.height}px`,
}))

function syncCanvas() {
  if (!imgEl.value) return
  const r = imgEl.value.getBoundingClientRect()
  const container = imgEl.value.parentElement!.getBoundingClientRect()
  svgRect.value = {
    left: r.left - container.left,
    top: r.top - container.top,
    width: r.width,
    height: r.height,
  }
}

function onCanvasClick(e: MouseEvent) {
  const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
  points.value.push({
    x: Math.round(e.clientX - rect.left),
    y: Math.round(e.clientY - rect.top),
  })
}

function undo() {
  points.value.pop()
}
function reset() {
  points.value = []
}

function save() {
  if (points.value.length < 3) return
  const w = svgRect.value.width
  const h = svgRect.value.height
  // Normalise to 0.0–1.0
  const normalized: [number, number][] = points.value.map(p => [
    parseFloat((p.x / w).toFixed(4)),
    parseFloat((p.y / h).toFixed(4)),
  ])
  emit('save', { coordinates: normalized, color: color.value })
}

function onResize() {
  nextTick(syncCanvas)
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKeydown)
  nextTick(syncCanvas)
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKeydown)
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') save()
  if (e.key === 'Escape') emit('cancel')
  if ((e.key === 'z' && (e.ctrlKey || e.metaKey)) || e.key === 'Backspace') undo()
}
</script>
