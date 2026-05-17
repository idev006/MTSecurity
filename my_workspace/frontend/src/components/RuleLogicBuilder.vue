<script lang="ts">
export default {
  name: 'RuleLogicBuilder'
}
</script>

<script setup lang="ts">
import { nextTick } from 'vue'

interface LogicNode {
  id?: string
  operator?: 'AND' | 'OR' | 'NOT'
  conditions?: LogicNode[]
  type?: 'time' | 'space' | 'object' | 'behavior'
  params?: Record<string, any>
}

const props = defineProps<{
  modelValue: LogicNode
  zones?: { id: number, name: string }[]
}>()

const emit = defineEmits(['update:modelValue'])

// Helper to create deep copy and avoid prop mutation
const updateModel = (newValue: LogicNode) => {
  emit('update:modelValue', JSON.parse(JSON.stringify(newValue)))
}

function generateId() {
  return Math.random().toString(36).substring(2, 9)
}

function addCondition(node: LogicNode) {
  const newNode = { ...node }
  if (!newNode.conditions) newNode.conditions = []
  newNode.conditions.push({
    id: generateId(),
    type: 'object',
    params: { class: 'person', confidence: 0.7 }
  })
  updateModel(newNode)
}

function addGroup(node: LogicNode) {
  const newNode = { ...node }
  if (!newNode.conditions) newNode.conditions = []
  newNode.conditions.push({
    id: generateId(),
    operator: 'AND',
    conditions: []
  })
  updateModel(newNode)
}

function removeNode(index: number) {
  const newNode = { ...props.modelValue }
  newNode.conditions?.splice(index, 1)
  updateModel(newNode)
}

function onTypeChange(cond: LogicNode) {
  // Initialize params based on type
  if (cond.type === 'object') {
    cond.params = { class: 'person', confidence: 0.7 }
  } else if (cond.type === 'space') {
    cond.params = { zone_id: 0 }
  } else if (cond.type === 'behavior') {
    cond.params = { type: 'intrusion' }
  } else {
    cond.params = {}
  }
  updateModel(props.modelValue)
}

/** When behavior type changes inside a node, keep only `type` (new value) and reset all other params.
 *  Takes newType as explicit arg because @change fires before v-model updates cond.params.type. */
function onBehaviorTypeChange(cond: LogicNode, newType: string) {
  cond.params = { type: newType }
  updateModel(props.modelValue)
}

function updateChild(index: number, childValue: LogicNode) {
  const newNode = { ...props.modelValue }
  if (newNode.conditions) {
    newNode.conditions[index] = childValue
    updateModel(newNode)
  }
}

const objectClasses = [
  'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
  'dog', 'cat', 'bird', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe',
  'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard',
  'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
  'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl'
]
const behaviorTypes = [
  { value: 'intrusion',         label: 'บุกรุก (Intrusion)' },
  { value: 'loitering',         label: 'ซุ่มรอ (Loitering)' },
  { value: 'line_crossing',     label: 'ข้ามเส้น (Line Crossing)' },
  { value: 'crowd_density',     label: 'ความหนาแน่นฝูงชน (Crowd Density)' },
  { value: 'abandoned_object',  label: 'วัตถุถูกทิ้ง (Abandoned Object)' },
  { value: 'running',           label: 'วิ่ง/เคลื่อนที่เร็ว (Running)' },
  { value: 'fall_detection',    label: 'ล้ม (Fall Detection)' },
  { value: 'crouching',         label: 'หมอบ/ซ่อนตัว (Crouching)' },
  { value: 'repeated_entry',    label: 'เข้าโซนซ้ำ (Repeated Entry)' },
  { value: 'pacing',            label: 'เดินวนซ้ำ (Pacing)' },
  { value: 'sudden_gathering',  label: 'รวมกลุ่มกะทันหัน (Sudden Gathering)' },
]

</script>

<template>
  <div class="space-y-4">
    <!-- Logic Node Renderer (Recursive) -->
    <div class="border-l-2 border-primary/30 pl-4 py-2 space-y-3 bg-base-200/20 rounded-r-lg">
      <div class="flex items-center gap-2 mb-2">
        <select
          :value="modelValue.operator"
          @input="e => updateModel({ ...modelValue, operator: (e.target as HTMLSelectElement).value as any })"
          class="select select-xs select-primary font-mono font-bold h-7 w-20"
        >
          <option value="AND">AND</option>
          <option value="OR">OR</option>
          <option value="NOT">NOT</option>
        </select>

        <div class="ml-auto flex gap-1">
          <button type="button" class="btn btn-xs btn-outline btn-primary h-7 gap-0.5" @click="addCondition(modelValue)">
            <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
            Condition
          </button>
          <button type="button" class="btn btn-xs btn-outline btn-primary h-7 gap-0.5 opacity-70" @click="addGroup(modelValue)">
            <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/></svg>
            Group
          </button>
        </div>
      </div>

      <div v-for="(cond, idx) in modelValue.conditions" :key="cond.id || idx" class="relative group/node">
        <!-- Visual Operator Separator (The "Middle" Operator) -->
        <div v-if="idx > 0" class="flex items-center gap-2 my-2 py-1">
          <div class="h-[1px] flex-grow bg-base-content/10"></div>
          <div class="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[9px] font-black border border-primary/20 uppercase tracking-tighter shadow-sm">
            {{ modelValue.operator }}
          </div>
          <div class="h-[1px] flex-grow bg-base-content/10"></div>
        </div>

        <!-- If nested operator (Sub-group) -->
        <div v-if="cond.operator" class="relative">
          <RuleLogicBuilder 
            :modelValue="cond" 
            :zones="zones"
            @update:modelValue="val => updateChild(idx, val)" 
          />
          <!-- Enhanced Group Delete Button -->
          <button 
            type="button"
            title="Remove this group"
            class="absolute -left-7 top-1 btn btn-circle btn-xs btn-error shadow-lg hover:scale-110 z-10"
            @click="removeNode(idx)"
          >
            <svg xmlns="http://www.w3.org/2001/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <!-- If leaf condition -->
        <div v-else class="flex flex-col gap-2 p-3 bg-base-100 rounded-lg border border-base-300 shadow-sm hover:border-primary/50 transition-all hover:shadow-md">
          <div class="flex items-center gap-2">
            <select 
              v-model="cond.type" 
              @change="onTypeChange(cond)"
              class="select select-xs select-bordered font-mono h-7 text-primary font-bold"
            >
              <option value="time">TIME</option>
              <option value="space">SPACE</option>
              <option value="object">OBJECT</option>
              <option value="behavior">BEHAVIOR</option>
            </select>
            
            <!-- Enhanced Condition Delete Button -->
            <button 
              type="button" 
              title="Remove condition"
              class="btn btn-xs btn-circle btn-ghost text-error/40 hover:text-error hover:bg-error/10 ml-auto transition-colors" 
              @click="removeNode(idx)"
            >
              <svg xmlns="http://www.w3.org/2001/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </button>
          </div>

          <!-- Time Params -->
          <div v-if="cond.type === 'time'" class="grid grid-cols-1 gap-1 pl-3 border-l-2 border-base-300">
            <p class="text-[10px] opacity-60 uppercase font-bold">Schedule Reference</p>
            <span class="text-xs italic opacity-80">Uses Rule's Primary Schedule</span>
          </div>

          <!-- Space Params -->
          <div v-if="cond.type === 'space'" class="grid grid-cols-1 gap-1 pl-3 border-l-2 border-base-300">
            <label class="text-[10px] opacity-60 uppercase font-bold">Target Zone</label>
            <select 
              v-if="zones && zones.length"
              v-model.number="cond.params!.zone_id" 
              @change="updateModel(modelValue)"
              class="select select-xs select-bordered w-full h-7"
            >
              <option :value="0">Primary Zone (Current)</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }} (ID: {{ z.id }})</option>
            </select>
            <input 
              v-else
              type="number" 
              v-model.number="cond.params!.zone_id" 
              @input="updateModel(modelValue)"
              class="input input-xs input-bordered w-full h-7" 
              placeholder="Enter Zone ID"
            />
          </div>

          <!-- Object Params -->
          <div v-if="cond.type === 'object'" class="grid grid-cols-2 gap-3 pl-3 border-l-2 border-base-300">
            <div class="flex flex-col gap-1">
              <label class="text-[10px] opacity-60 uppercase font-bold">Class</label>
              <select 
                v-model="cond.params!.class" 
                @change="updateModel(modelValue)"
                class="select select-xs select-bordered h-7 w-full"
              >
                <option v-for="c in objectClasses" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-[10px] opacity-60 uppercase font-bold">Min Confidence</label>
              <input 
                type="number" 
                v-model.number="cond.params!.confidence" 
                step="0.05" min="0" max="1" 
                @input="updateModel(modelValue)"
                class="input input-xs input-bordered h-7 w-full" 
              />
            </div>
          </div>

          <!-- Behavior Params -->
          <div v-if="cond.type === 'behavior'" class="flex flex-col gap-2 pl-3 border-l-2 border-base-300">
            <!-- Behavior type selector -->
            <div class="flex flex-col gap-1">
              <label class="text-[10px] opacity-60 uppercase font-bold">Behavior Type</label>
              <select
                :value="cond.params!.type"
                @change="e => onBehaviorTypeChange(cond, (e.target as HTMLSelectElement).value)"
                class="select select-xs select-bordered h-7 w-full"
              >
                <option v-for="b in behaviorTypes" :key="b.value" :value="b.value">{{ b.label }}</option>
              </select>
            </div>

            <!-- loitering params -->
            <div v-if="cond.params!.type === 'loitering'" class="grid grid-cols-1 gap-1">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Dwell (s) <span class="opacity-50 font-normal normal-case">ซุ่มรอนานเท่าไร</span></label>
                <input type="number" v-model.number="cond.params!.dwell_threshold_seconds"
                  @input="updateModel(modelValue)" min="5" max="3600" placeholder="30"
                  class="input input-xs input-bordered h-7 w-32" />
              </div>
            </div>

            <!-- abandoned_object params -->
            <div v-if="cond.params!.type === 'abandoned_object'" class="grid grid-cols-2 gap-2">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Dwell (s)</label>
                <input type="number" v-model.number="cond.params!.dwell_threshold_seconds"
                  @input="updateModel(modelValue)" min="5" max="3600" placeholder="60"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Move Threshold</label>
                <input type="number" v-model.number="cond.params!.movement_threshold"
                  @input="updateModel(modelValue)" step="0.005" min="0.005" max="0.1" placeholder="0.02"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
            </div>

            <!-- crowd_density params -->
            <div v-if="cond.params!.type === 'crowd_density'" class="flex flex-col gap-1">
              <label class="text-[10px] opacity-60 uppercase font-bold">Max Persons</label>
              <input type="number" v-model.number="cond.params!.max_persons"
                @input="updateModel(modelValue)" min="1" max="100" placeholder="5"
                class="input input-xs input-bordered h-7 w-32" />
            </div>

            <!-- running params -->
            <div v-if="cond.params!.type === 'running'" class="grid grid-cols-2 gap-2">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Speed Threshold</label>
                <input type="number" v-model.number="cond.params!.speed_threshold"
                  @input="updateModel(modelValue)" step="0.005" min="0.01" max="0.15" placeholder="0.04"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Min Frames</label>
                <input type="number" v-model.number="cond.params!.min_frames"
                  @input="updateModel(modelValue)" min="1" max="10" placeholder="3"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
            </div>

            <!-- fall_detection params -->
            <div v-if="cond.params!.type === 'fall_detection'" class="grid grid-cols-2 gap-2">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Aspect Ratio</label>
                <input type="number" v-model.number="cond.params!.aspect_ratio_threshold"
                  @input="updateModel(modelValue)" step="0.1" min="1.0" max="3.0" placeholder="1.5"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Min Frames</label>
                <input type="number" v-model.number="cond.params!.min_frames"
                  @input="updateModel(modelValue)" min="1" max="10" placeholder="2"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
            </div>

            <!-- crouching params -->
            <div v-if="cond.params!.type === 'crouching'" class="grid grid-cols-3 gap-2">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Height Ratio</label>
                <input type="number" v-model.number="cond.params!.height_ratio_threshold"
                  @input="updateModel(modelValue)" step="0.05" min="0.2" max="0.9" placeholder="0.6"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Min Frames</label>
                <input type="number" v-model.number="cond.params!.min_frames"
                  @input="updateModel(modelValue)" min="1" max="10" placeholder="3"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Baseline Frames</label>
                <input type="number" v-model.number="cond.params!.baseline_frames"
                  @input="updateModel(modelValue)" min="5" max="60" placeholder="15"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
            </div>

            <!-- repeated_entry params -->
            <div v-if="cond.params!.type === 'repeated_entry'" class="grid grid-cols-2 gap-2">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Max Entries</label>
                <input type="number" v-model.number="cond.params!.max_entries"
                  @input="updateModel(modelValue)" min="2" max="10" placeholder="3"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Window (s)</label>
                <input type="number" v-model.number="cond.params!.time_window_seconds"
                  @input="updateModel(modelValue)" min="30" max="3600" placeholder="300"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
            </div>

            <!-- pacing params -->
            <div v-if="cond.params!.type === 'pacing'" class="grid grid-cols-3 gap-2">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Reversals</label>
                <input type="number" v-model.number="cond.params!.reversal_threshold"
                  @input="updateModel(modelValue)" min="2" max="10" placeholder="4"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">History Size</label>
                <input type="number" v-model.number="cond.params!.history_size"
                  @input="updateModel(modelValue)" min="10" max="100" placeholder="40"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Min Disp.</label>
                <input type="number" v-model.number="cond.params!.min_displacement"
                  @input="updateModel(modelValue)" step="0.005" min="0.005" max="0.1" placeholder="0.01"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
            </div>

            <!-- sudden_gathering params -->
            <div v-if="cond.params!.type === 'sudden_gathering'" class="grid grid-cols-3 gap-2">
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Min Persons</label>
                <input type="number" v-model.number="cond.params!.min_persons"
                  @input="updateModel(modelValue)" min="2" max="20" placeholder="3"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Window (s)</label>
                <input type="number" v-model.number="cond.params!.rate_window_seconds"
                  @input="updateModel(modelValue)" min="5" max="60" placeholder="10"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[10px] opacity-60 uppercase font-bold">Min Increase</label>
                <input type="number" v-model.number="cond.params!.min_increase"
                  @input="updateModel(modelValue)" min="1" max="10" placeholder="2"
                  class="input input-xs input-bordered h-7 w-full" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.select-xs { padding-top: 0; padding-bottom: 0; font-size: 0.7rem; height: 1.5rem; min-height: 1.5rem; }
.input-xs  { font-size: 0.7rem; height: 1.5rem; min-height: 1.5rem; }
</style>
