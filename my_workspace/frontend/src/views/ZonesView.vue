<template>
  <AppLayout>
    <template #header>
      <h1 class="text-xl font-bold tracking-tight">Zones & Rules</h1>
      <p class="text-sm text-base-content/50 mt-0.5">Manage detection zones and alert rules per camera</p>
    </template>

    <div class="p-4 space-y-4 max-w-5xl mx-auto">

      <!-- Camera selector + Draw Zone in one toolbar row -->
      <div class="flex items-center gap-3 flex-wrap">
        <div class="tabs tabs-boxed bg-base-200 p-0.5 flex-1">
          <button
            v-for="cam in cameras.cameras"
            :key="cam.id"
            class="tab font-mono text-xs gap-1.5"
            :class="selectedCamId === cam.id ? 'tab-active' : ''"
            @click="selectCamera(cam.id)">
            {{ cam.name }}
            <span class="w-1.5 h-1.5 rounded-full"
              :class="cameras.statusOf(cam.id)?.state === 'ONLINE'       ? 'bg-success' :
                      cameras.statusOf(cam.id)?.state === 'ERROR'        ? 'bg-error' :
                      cameras.statusOf(cam.id)?.state === 'RECONNECTING' ? 'bg-warning' :
                      'bg-base-content/20'"></span>
          </button>
          <span v-if="cameras.cameras.length === 0" class="tab opacity-40 font-mono cursor-default">NO CAMERAS</span>
        </div>
        <button v-if="selectedCam" class="btn btn-sm btn-primary gap-1.5 shrink-0" @click="openDrawing">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Draw Zone
        </button>
      </div>

      <template v-if="selectedCam">
        <div v-if="loading" class="flex justify-center py-12">
          <span class="loading loading-spinner loading-md opacity-30"></span>
        </div>

        <!-- Empty state -->
        <div v-else-if="zones.length === 0"
          class="card bg-base-100 border border-base-300 border-dashed">
          <div class="card-body items-center py-16 gap-3 opacity-40">
            <svg class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
            </svg>
            <p class="font-mono text-sm tracking-widest">NO ZONES DEFINED</p>
            <p class="font-mono text-xs">Click "Draw Zone" to define a detection area</p>
          </div>
        </div>

        <!-- Zone list -->
        <div v-else class="space-y-3">
          <div v-for="zone in zones" :key="zone.id"
            class="card bg-base-100 border border-base-300 overflow-hidden"
            :style="`border-left: 3px solid ${zone.color}`">

            <!-- Zone header -->
            <div class="flex items-center gap-3 px-4 py-3 border-b border-base-300 bg-base-200/40">
              <!-- Color swatch -->
              <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="`background:${zone.color}`"></span>
              <span class="font-mono font-semibold text-sm flex-1 truncate tracking-wide">{{ zone.name.toUpperCase() }}</span>

              <!-- Rule count chip -->
              <span class="badge badge-ghost badge-xs font-mono gap-1">
                <svg class="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                {{ rules.filter(r => r.zone_id === zone.id).length }} RULES
              </span>

              <div class="tooltip tooltip-left" :data-tip="zone.is_active ? 'Disable zone' : 'Enable zone'">
                <button class="btn btn-xs btn-ghost btn-square"
                  :class="zone.is_active ? 'text-success' : 'opacity-20 hover:opacity-60'"
                  @click="toggleZone(zone)">
                  <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>
                </button>
              </div>

              <div class="tooltip tooltip-left" data-tip="Delete zone">
                <button class="btn btn-xs btn-ghost btn-square text-error opacity-40 hover:opacity-100"
                  @click="deleteZone(zone.id)">
                  <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Rules list -->
            <div class="divide-y divide-base-200">
              <div v-for="rule in rules.filter(r => r.zone_id === zone.id)" :key="rule.id"
                class="group flex items-center gap-3 px-4 py-2.5 hover:bg-base-200/50 transition-colors">

                <!-- Behavior icon -->
                <span class="shrink-0 opacity-50 group-hover:opacity-80 transition-opacity" v-html="behaviorIcon(rule.behavior)"></span>

                <!-- Severity badge -->
                <span class="badge badge-xs font-mono shrink-0" :class="sevBadge(rule.severity)">
                  {{ rule.severity.slice(0,4).toUpperCase() }}
                </span>

                <!-- Name + summary -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-1.5">
                    <span class="text-xs font-semibold truncate">{{ rule.name || rule.behavior }}</span>
                    <span v-if="rule.logic" class="badge badge-primary badge-outline badge-xs gap-0.5">
                      <svg class="h-2 w-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                      </svg>
                      POLICY
                    </span>
                  </div>
                  <p class="font-mono text-[10px] opacity-40 mt-0.5">
                    {{ ruleBehaviorLabel(rule) }} ·
                    {{ (rule.confidence_threshold * 100).toFixed(0) }}% conf ·
                    cd {{ rule.cooldown_seconds }}s
                    <span v-if="ruleBehaviorLabel(rule).includes('loitering') || ruleBehaviorLabel(rule).includes('abandoned')"> · dw {{ ruleDwellSeconds(rule) }}s</span>
                    <span v-if="ruleBehaviorLabel(rule).includes('crowd')"> · max {{ ruleMaxPersons(rule) }} persons</span>
                  </p>
                </div>

                <!-- Active toggle (always visible) -->
                <div class="tooltip tooltip-left" :data-tip="rule.is_active ? 'Disable rule' : 'Enable rule'">
                  <button class="btn btn-xs btn-ghost btn-square"
                    :class="rule.is_active ? 'text-success' : 'opacity-20 hover:opacity-60'"
                    @click="toggleRule(rule)">
                    <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>
                  </button>
                </div>

                <!-- Edit / Delete — hover reveal -->
                <div class="flex items-center gap-0.5">
                  <div class="tooltip tooltip-left" data-tip="Edit rule">
                    <button class="btn btn-xs btn-ghost btn-square text-primary" @click="openEditRule(rule)">
                      <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
                      </svg>
                    </button>
                  </div>
                  <div class="tooltip tooltip-left" data-tip="Delete rule">
                    <button class="btn btn-xs btn-ghost btn-square text-error" @click="confirmDeleteRule(rule.id)">
                      <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Add rule row -->
              <div class="px-4 py-2">
                <button class="btn btn-xs btn-ghost w-full border border-dashed border-base-300
                               text-primary opacity-50 hover:opacity-100 gap-1"
                  @click="openAddRule(zone.id)">
                  <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                  </svg>
                  ADD RULE
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Zone Canvas Modal -->
    <ZoneCanvas
      v-if="drawing && selectedCam"
      :camera-id="selectedCam.id"
      :camera-name="selectedCam.name"
      :stream-url="streamUrl(selectedCam.id)"
      @cancel="drawing = false"
      @save="onZoneSaved"
    />

    <!-- Add / Edit Rule Modal -->
    <div v-if="addRuleZoneId !== null" class="modal modal-open">
      <div class="modal-box scrollbar-thin flex flex-col max-h-[90vh]"
           :class="useAdvancedLogic ? 'max-w-2xl' : 'max-w-lg'">
        <h3 class="font-bold font-mono tracking-wide mb-4 flex items-center justify-between shrink-0">
          {{ editingRuleId ? 'EDIT RULE' : 'ADD RULE' }}
          <div class="flex items-center gap-2">
            <span class="text-[10px] opacity-50 uppercase font-normal">Advanced Logic</span>
            <input type="checkbox" v-model="useAdvancedLogic" class="toggle toggle-xs toggle-primary" />
          </div>
        </h3>

        <form @submit.prevent="submitRule" class="space-y-4 overflow-y-auto flex-1 pr-1">
          <!-- Basic Info -->
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Rule Name</label>
              <input v-model="ruleForm.name" class="input input-bordered input-sm" required placeholder="e.g. Night Intrusion" />
            </div>
            <div class="form-control">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Severity</label>
              <select v-model="ruleForm.severity" class="select select-bordered select-sm">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <!-- Schedule -->
          <SchedulePicker v-model="ruleSchedule" />

          <!-- Logic Builder or Basic Behavior -->
          <div v-if="useAdvancedLogic" class="p-3 bg-base-300/30 rounded-lg border border-base-content/10">
            <div class="flex items-center justify-between mb-2">
              <label class="label label-text py-0 text-[10px] opacity-60 uppercase font-bold">Policy Logic Tree</label>
              <span v-if="!(logicTree?.conditions?.length)" class="text-[10px] text-warning font-mono flex items-center gap-1">
                <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
                Tree ว่าง — เพิ่มเงื่อนไข
              </span>
            </div>
            <RuleLogicBuilder v-model="logicTree" :zones="zones" />
          </div>

          <div v-else class="p-3 bg-base-200/50 rounded-lg">
            <div class="form-control">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Primary Behavior</label>
              <select v-model="ruleForm.behavior" class="select select-bordered select-sm"
                :class="!ruleForm.behavior ? 'select-error' : ''"
                required @change="onBehaviorChange">
                <option value="" disabled>— เลือก Behavior —</option>
                <optgroup label="— พื้นฐาน —">
                  <option value="intrusion">บุกรุก (Intrusion)</option>
                  <option value="loitering">ซุ่มรอ (Loitering)</option>
                  <option value="line_crossing">ข้ามเส้น (Line Crossing)</option>
                  <option value="crowd_density">ความหนาแน่นฝูงชน (Crowd Density)</option>
                  <option value="abandoned_object">วัตถุถูกทิ้ง (Abandoned Object)</option>
                </optgroup>
                <optgroup label="— น่าสงสัย / อันตราย —">
                  <option value="running">วิ่ง/เคลื่อนที่เร็ว (Running)</option>
                  <option value="fall_detection">ล้ม (Fall Detection)</option>
                  <option value="crouching">หมอบ/ซ่อนตัว (Crouching)</option>
                  <option value="repeated_entry">เข้าโซนซ้ำ (Repeated Entry)</option>
                  <option value="pacing">เดินวนซ้ำ (Pacing)</option>
                  <option value="sudden_gathering">รวมกลุ่มกะทันหัน (Sudden Gathering)</option>
                </optgroup>
              </select>
            </div>
          </div>

          <!-- Behavior params — Basic mode only. In Advanced Logic mode, params live inside each behavior node in the tree. -->
          <div v-if="!useAdvancedLogic && activeBehavior && !['intrusion','line_crossing','loitering'].includes(activeBehavior)"
               class="space-y-2 p-3 bg-base-200/30 rounded-lg border border-base-content/10">
            <label class="label label-text py-0 text-[10px] opacity-60 uppercase font-bold tracking-wider">
              ⚙ Behavior Parameters
              <span class="ml-2 badge badge-primary badge-outline badge-xs font-mono">{{ activeBehavior }}</span>
            </label>

            <!-- running params -->
            <div v-if="activeBehavior === 'running'" class="grid grid-cols-2 gap-3 pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">ความเร็วขั้นต่ำ (0.01–0.15)</label>
                <input type="number" v-model.number="behaviorParams.speed_threshold" step="0.005" min="0.01" max="0.15" placeholder="0.04" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">เฟรมขั้นต่ำ</label>
                <input type="number" v-model.number="behaviorParams.min_frames" min="1" max="10" placeholder="3" class="input input-bordered input-xs" />
              </div>
            </div>

            <!-- fall_detection params -->
            <div v-if="activeBehavior === 'fall_detection'" class="grid grid-cols-2 gap-3 pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Aspect Ratio ขั้นต่ำ</label>
                <input type="number" v-model.number="behaviorParams.aspect_ratio_threshold" step="0.1" min="1.0" max="3.0" placeholder="1.5" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">เฟรมขั้นต่ำ</label>
                <input type="number" v-model.number="behaviorParams.min_frames" min="1" max="10" placeholder="2" class="input input-bordered input-xs" />
              </div>
            </div>

            <!-- crouching params -->
            <div v-if="activeBehavior === 'crouching'" class="grid grid-cols-3 gap-3 pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Height Ratio ขั้นต่ำ</label>
                <input type="number" v-model.number="behaviorParams.height_ratio_threshold" step="0.05" min="0.2" max="0.9" placeholder="0.6" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">เฟรมขั้นต่ำ</label>
                <input type="number" v-model.number="behaviorParams.min_frames" min="1" max="10" placeholder="3" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Baseline Frames</label>
                <input type="number" v-model.number="behaviorParams.baseline_frames" min="5" max="60" placeholder="15" class="input input-bordered input-xs" />
              </div>
            </div>

            <!-- repeated_entry params -->
            <div v-if="activeBehavior === 'repeated_entry'" class="grid grid-cols-2 gap-3 pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">จำนวนครั้งสูงสุด</label>
                <input type="number" v-model.number="behaviorParams.max_entries" min="2" max="10" placeholder="3" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">ช่วงเวลา (วินาที)</label>
                <input type="number" v-model.number="behaviorParams.time_window_seconds" min="30" max="3600" placeholder="300" class="input input-bordered input-xs" />
              </div>
            </div>

            <!-- pacing params -->
            <div v-if="activeBehavior === 'pacing'" class="grid grid-cols-3 gap-3 pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">จำนวนการกลับทิศ</label>
                <input type="number" v-model.number="behaviorParams.reversal_threshold" min="2" max="10" placeholder="4" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">ขนาด History</label>
                <input type="number" v-model.number="behaviorParams.history_size" min="10" max="100" placeholder="40" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Min Displacement</label>
                <input type="number" v-model.number="behaviorParams.min_displacement" step="0.005" min="0.005" max="0.1" placeholder="0.01" class="input input-bordered input-xs" />
              </div>
            </div>

            <!-- abandoned_object params -->
            <div v-if="activeBehavior === 'abandoned_object'" class="pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">
                  Movement Threshold
                  <span class="ml-1 opacity-40 font-normal normal-case">ขยับเกินนี้ถือว่าเคลื่อนที่ (0.005–0.1)</span>
                </label>
                <input type="number" v-model.number="behaviorParams.movement_threshold" step="0.005" min="0.005" max="0.1" placeholder="0.02" class="input input-bordered input-xs w-40" />
              </div>
            </div>

            <!-- crowd_density params -->
            <div v-if="activeBehavior === 'crowd_density'" class="pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">จำนวนคนสูงสุด (max_persons)</label>
                <input type="number" v-model.number="behaviorParams.max_persons" min="1" max="100" placeholder="5" class="input input-bordered input-xs w-40" />
              </div>
            </div>

            <!-- sudden_gathering params -->
            <div v-if="activeBehavior === 'sudden_gathering'" class="grid grid-cols-3 gap-3 pl-3 border-l-2 border-primary/30">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">จำนวนคนขั้นต่ำ</label>
                <input type="number" v-model.number="behaviorParams.min_persons" min="2" max="20" placeholder="3" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">ช่วงเวลา (s)</label>
                <input type="number" v-model.number="behaviorParams.rate_window_seconds" min="5" max="60" placeholder="10" class="input input-bordered input-xs" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">เพิ่มขึ้นขั้นต่ำ</label>
                <input type="number" v-model.number="behaviorParams.min_increase" min="1" max="10" placeholder="2" class="input input-bordered input-xs" />
              </div>
            </div>
          </div>

          <!-- Rule Settings -->
          <div class="p-3 bg-base-200/50 rounded-lg space-y-3">
            <label class="label label-text py-0 text-[10px] opacity-60 uppercase font-bold tracking-wider">Rule Settings</label>

            <!-- Cooldown + Confidence — always 2 cols -->
            <div class="grid grid-cols-2 gap-3">
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">
                  Cooldown (s)
                  <span class="ml-1 opacity-40 font-normal normal-case">หน่วงเวลาระหว่าง alert</span>
                </label>
                <input type="number" v-model.number="ruleForm.cooldown_seconds" min="10" class="input input-bordered input-sm" />
              </div>
              <div class="form-control">
                <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Confidence (%)</label>
                <input type="number" v-model.number="ruleFormConfidencePct" min="10" max="99" class="input input-bordered input-sm" />
              </div>
            </div>

            <!-- Dwell — only for loitering / abandoned_object in Basic mode -->
            <div class="form-control" v-if="!useAdvancedLogic && (activeBehavior === 'loitering' || activeBehavior === 'abandoned_object')">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">
                Dwell (s)
                <span class="ml-1 opacity-40 font-normal normal-case">{{ activeBehavior === 'abandoned_object' ? 'ต้องนิ่งนานเท่าไร' : 'ต้องซุ่มรอนานเท่าไร' }}</span>
              </label>
              <input type="number" v-model.number="ruleForm.dwell_threshold_seconds" min="5" max="3600" class="input input-bordered input-sm w-40" />
            </div>
          </div>

        </form>

        <!-- Sticky footer -->
        <div class="flex gap-2 pt-4 mt-2 border-t border-base-300 shrink-0">
          <button type="button" class="btn btn-ghost btn-sm flex-1 font-mono"
            @click="addRuleZoneId = null; editingRuleId = null">CANCEL</button>
          <button type="button" class="btn btn-primary flex-[2] font-mono" :disabled="submitting"
            @click="submitRule">
            <span v-if="submitting" class="loading loading-spinner loading-xs"></span>
            {{ submitting ? 'SAVING…' : (editingRuleId ? 'UPDATE RULE' : 'SAVE RULE') }}
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="addRuleZoneId = null; editingRuleId = null"></div>
    </div>

    <!-- Name Zone Modal -->
    <div v-if="pendingZone" class="modal modal-open">
      <div class="modal-box max-w-sm">
        <h3 class="font-bold font-mono mb-3">NAME THIS ZONE</h3>
        <input v-model="pendingZoneName" class="input input-bordered w-full" placeholder="e.g. Front Door, Lobby"
          autofocus @keydown.enter="confirmZone" />
        <div class="modal-action">
          <button class="btn btn-ghost btn-sm" @click="pendingZone = null">Cancel</button>
          <button class="btn btn-primary btn-sm" @click="confirmZone" :disabled="!pendingZoneName.trim()">Create</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="pendingZone = null"></div>
    </div>

    <!-- Delete Zone Confirm -->
    <dialog class="modal" :class="deleteZoneModalOpen && 'modal-open'">
      <div class="modal-box max-w-sm">
        <h3 class="font-bold font-mono text-base text-error">DELETE ZONE?</h3>
        <p class="text-sm opacity-70 mt-2">This zone and all its rules will be permanently removed.</p>
        <div class="modal-action">
          <button class="btn btn-sm btn-ghost font-mono"
            @click="deleteZoneModalOpen = false; deleteTargetZoneId = null">CANCEL</button>
          <button class="btn btn-sm btn-error font-mono" @click="confirmDeleteZone">DELETE</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="deleteZoneModalOpen = false; deleteTargetZoneId = null">
        <button>close</button>
      </form>
    </dialog>

    <!-- Delete Rule Confirm -->
    <dialog class="modal" :class="deleteRuleModalOpen && 'modal-open'">
      <div class="modal-box max-w-sm">
        <h3 class="font-bold font-mono text-base text-error">DELETE RULE?</h3>
        <p class="text-sm opacity-70 mt-2">This rule will be permanently removed and will stop triggering alerts.</p>
        <div class="modal-action">
          <button class="btn btn-sm btn-ghost font-mono"
            @click="deleteRuleModalOpen = false; deleteTargetRuleId = null">CANCEL</button>
          <button class="btn btn-sm btn-error font-mono" @click="executeDeleteRule">DELETE</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="deleteRuleModalOpen = false; deleteTargetRuleId = null">
        <button>close</button>
      </form>
    </dialog>

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import ZoneCanvas from '@/components/ZoneCanvas.vue'
import RuleLogicBuilder from '@/components/RuleLogicBuilder.vue'
import SchedulePicker from '@/components/SchedulePicker.vue'
import { useCamerasStore } from '@/stores/cameras'
import { useToastStore } from '@/stores/toast'

// ── API types & calls ────────────────────────────────────────────────────────

interface ZoneRead {
  id: number; camera_id: number; name: string
  coordinates: string; color: string; is_active: boolean
}
interface RuleRead {
  id: number; zone_id: number; name: string; behavior: string
  is_active: boolean; confidence_threshold: number
  dwell_threshold_seconds: number; cooldown_seconds: number; severity: string
  logic?: any; schedule?: any; behavior_params?: any
}

const BASE = '/api/v1'
const h = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}`, 'Content-Type': 'application/json' })

async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path, { headers: h() })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + path, { method: 'POST', headers: h(), body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + path, { method: 'PATCH', headers: h(), body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
async function apiDelete(path: string): Promise<void> {
  const r = await fetch(BASE + path, { method: 'DELETE', headers: h() })
  if (!r.ok && r.status !== 204) throw new Error(await r.text())
}

// ── Store & state ────────────────────────────────────────────────────────────

const cameras    = useCamerasStore()
const toastStore = useToastStore()
const selectedCamId = ref<number | null>(null)
const zones = ref<ZoneRead[]>([])
const rules = ref<RuleRead[]>([])
const loading = ref(false)
const drawing = ref(false)
const addRuleZoneId = ref<number | null>(null)
const editingRuleId = ref<number | null>(null)
const submitting = ref(false)
const pendingZone = ref<{ coordinates: [number, number][], color: string } | null>(null)
const pendingZoneName = ref('')
const deleteZoneModalOpen = ref(false)
const deleteTargetZoneId = ref<number | null>(null)
const deleteRuleModalOpen = ref(false)
const deleteTargetRuleId = ref<number | null>(null)

const useAdvancedLogic = ref(false)
const logicTree = ref<{ operator: 'AND' | 'OR' | 'NOT'; conditions: any[] }>({ operator: 'AND', conditions: [] })
const ruleSchedule = ref({ start: '00:00', end: '23:59', days: [0, 1, 2, 3, 4, 5, 6] })
const behaviorParams = ref<Record<string, any>>({})

const selectedCam = computed(() => cameras.cameras.find(c => c.id === selectedCamId.value) ?? null)

const ruleForm = ref({
  name: '',
  behavior: 'intrusion',
  confidence_threshold: 0.6,
  dwell_threshold_seconds: 30,
  cooldown_seconds: 60,
  severity: 'medium',
})

// Two-way proxy: form stores 0-1 float, input shows 0-100 int
const ruleFormConfidencePct = computed({
  get: () => Math.round(ruleForm.value.confidence_threshold * 100),
  set: (v: number) => { ruleForm.value.confidence_threshold = v / 100 },
})

// Effective behavior for form display — reads from logic tree when Advanced Logic is on
const activeBehavior = computed<string>(() => {
  if (useAdvancedLogic.value) {
    return extractBehaviorFromTree(logicTree.value) ?? ''
  }
  return ruleForm.value.behavior
})

// ── Mode toggle sync ─────────────────────────────────────────────────────────
// Prevent stale state when user switches between Basic ↔ Advanced Logic modes.
watch(useAdvancedLogic, (isAdvanced) => {
  if (!isAdvanced) {
    // Switched back to Basic: reset behavior so user must explicitly reselect.
    // This prevents a stale Advanced-tree behavior leaking into the Basic payload.
    ruleForm.value.behavior = '' as any
    behaviorParams.value = {}
  }
  // Switched to Advanced: logicTree and ruleForm stay untouched.
  // The tree is either empty (new rule) or loaded from the existing rule (edit).
})

// ── Helpers ──────────────────────────────────────────────────────────────────

function streamUrl(cameraId: number) {
  return `/api/v1/cameras/${cameraId}/stream?token=${localStorage.getItem('access_token') ?? ''}`
}

// ── Actions ──────────────────────────────────────────────────────────────────

async function selectCamera(id: number) {
  selectedCamId.value = id
  await loadZonesAndRules()
}

async function loadZonesAndRules() {
  if (!selectedCamId.value) return
  loading.value = true
  try {
    const [z, r] = await Promise.all([
      apiGet<ZoneRead[]>(`/zones?camera_id=${selectedCamId.value}`),
      apiGet<RuleRead[]>('/rules'),
    ])
    zones.value = z
    rules.value = r.map(rule => ({
      ...rule,
      logic:           typeof rule.logic           === 'string' ? JSON.parse(rule.logic)           : rule.logic,
      schedule:        typeof rule.schedule        === 'string' ? JSON.parse(rule.schedule)        : rule.schedule,
      behavior_params: typeof rule.behavior_params === 'string' ? JSON.parse(rule.behavior_params) : rule.behavior_params,
    }))
  } finally {
    loading.value = false
  }
}

function openDrawing() { drawing.value = true }

function onZoneSaved(payload: { coordinates: [number, number][], color: string }) {
  drawing.value = false
  pendingZone.value = payload
  pendingZoneName.value = ''
}

async function confirmZone() {
  if (!pendingZone.value || !selectedCamId.value || !pendingZoneName.value.trim()) return
  try {
    const zone = await apiPost<ZoneRead>('/zones', {
      camera_id:   selectedCamId.value,
      name:        pendingZoneName.value.trim(),
      coordinates: pendingZone.value.coordinates,
      color:       pendingZone.value.color,
    })
    zones.value = [...zones.value, zone]
    pendingZone.value = null
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Save Failed', message: e.message })
  }
}

function deleteZone(id: number) {
  deleteTargetZoneId.value = id
  deleteZoneModalOpen.value = true
}

async function confirmDeleteZone() {
  const id = deleteTargetZoneId.value
  if (!id) return
  deleteZoneModalOpen.value = false
  deleteTargetZoneId.value = null
  try {
    await apiDelete(`/zones/${id}`)
    zones.value = zones.value.filter(z => z.id !== id)
    rules.value = rules.value.filter(r => r.zone_id !== id)
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Delete Failed', message: e.message })
  }
}

function confirmDeleteRule(id: number) {
  deleteTargetRuleId.value = id
  deleteRuleModalOpen.value = true
}

async function executeDeleteRule() {
  const id = deleteTargetRuleId.value
  if (!id) return
  deleteRuleModalOpen.value = false
  deleteTargetRuleId.value = null
  try {
    await apiDelete(`/rules/${id}`)
    rules.value = rules.value.filter(r => r.id !== id)
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Delete Failed', message: e.message })
  }
}

function openAddRule(zoneId: number) {
  addRuleZoneId.value = zoneId
  editingRuleId.value = null
  ruleForm.value = { name: '', behavior: '' as any, confidence_threshold: 0.6, dwell_threshold_seconds: 30, cooldown_seconds: 60, severity: 'medium' }
  useAdvancedLogic.value = false
  logicTree.value = { operator: 'AND', conditions: [] }
  ruleSchedule.value = { start: '00:00', end: '23:59', days: [0, 1, 2, 3, 4, 5, 6] }
  behaviorParams.value = {}
}

function openEditRule(rule: RuleRead) {
  addRuleZoneId.value = rule.zone_id
  editingRuleId.value = rule.id
  ruleForm.value = {
    name: rule.name, behavior: rule.behavior as any,
    confidence_threshold: rule.confidence_threshold,
    dwell_threshold_seconds: rule.dwell_threshold_seconds,
    cooldown_seconds: rule.cooldown_seconds, severity: rule.severity as any,
  }
  useAdvancedLogic.value = !!rule.logic
  logicTree.value      = rule.logic           ? JSON.parse(JSON.stringify(rule.logic))           : { operator: 'AND', conditions: [] }
  ruleSchedule.value   = rule.schedule        ? JSON.parse(JSON.stringify(rule.schedule))        : { start: '00:00', end: '23:59', days: [0, 1, 2, 3, 4, 5, 6] }
  behaviorParams.value = rule.behavior_params ? JSON.parse(JSON.stringify(rule.behavior_params)) : {}
}

/** Reset behavior-specific params and set smart dwell defaults when behavior dropdown changes. */
function onBehaviorChange() {
  behaviorParams.value = {}
  const b = ruleForm.value.behavior
  if (b === 'abandoned_object') {
    ruleForm.value.dwell_threshold_seconds = 60
  } else if (b === 'loitering') {
    ruleForm.value.dwell_threshold_seconds = 30
  }
}

/** Recursively find first behavior node's type in a logic tree. */
function extractBehaviorFromTree(node: any): string | null {
  if (!node) return null
  if (node.type === 'behavior') return node.params?.type ?? null
  for (const child of (node.conditions ?? [])) {
    const found = extractBehaviorFromTree(child)
    if (found) return found
  }
  return null
}

/** Find first behavior node in tree matching any of the given types. */
function findBehaviorNode(node: any, types: string[]): any {
  if (!node) return null
  if (node.type === 'behavior' && types.includes(node.params?.type)) return node
  for (const child of (node.conditions ?? [])) {
    const found = findBehaviorNode(child, types)
    if (found) return found
  }
  return null
}

/** Dwell seconds for card display — reads from tree node if Advanced Logic, else top-level field. */
function ruleDwellSeconds(rule: RuleRead): number {
  if (rule.logic) {
    const node = findBehaviorNode(rule.logic, ['loitering', 'abandoned_object'])
    if (node?.params?.dwell_threshold_seconds) return node.params.dwell_threshold_seconds
  }
  return rule.dwell_threshold_seconds
}

/** Max persons for card display — reads from tree node if Advanced Logic, else top-level behavior_params. */
function ruleMaxPersons(rule: RuleRead): number {
  if (rule.logic) {
    const node = findBehaviorNode(rule.logic, ['crowd_density'])
    if (node?.params?.max_persons) return node.params.max_persons
  }
  return rule.behavior_params?.max_persons ?? 5
}

/** Return the behavior label to display for a rule card. */
function ruleBehaviorLabel(rule: RuleRead): string {
  if (rule.logic) {
    const fromTree = extractBehaviorFromTree(rule.logic)
    if (fromTree) return fromTree.replace(/_/g, ' ')
  }
  return rule.behavior.replace(/_/g, ' ')
}

async function submitRule() {
  if (submitting.value || !addRuleZoneId.value) return
  if (!useAdvancedLogic.value && !ruleForm.value.behavior) {
    toastStore.push({ type: 'error', title: 'กรุณาเลือก Behavior', message: 'โปรดเลือกประเภทพฤติกรรมที่ต้องการตรวจจับ' })
    return
  }
  if (useAdvancedLogic.value && !(logicTree.value?.conditions?.length)) {
    toastStore.push({ type: 'error', title: 'Logic Tree ว่าง', message: 'กรุณาเพิ่มเงื่อนไขอย่างน้อย 1 ข้อใน Policy Logic Tree' })
    return
  }
  submitting.value = true
  try {
    // When Advanced Logic is on, derive behavior from the logic tree's
    // behavior node so rule.behavior stays in sync with the actual policy.
    let effectiveBehavior = ruleForm.value.behavior
    if (useAdvancedLogic.value) {
      const fromTree = extractBehaviorFromTree(logicTree.value)
      if (fromTree) effectiveBehavior = fromTree
    }
    const payload = {
      zone_id: addRuleZoneId.value,
      ...ruleForm.value,
      behavior: effectiveBehavior,
      schedule: ruleSchedule.value,
      logic: useAdvancedLogic.value ? logicTree.value : null,
      // In Advanced Logic mode, behavior params are embedded inside each behavior node
      // in the logic tree — top-level behavior_params is not used.
      behavior_params: useAdvancedLogic.value
        ? null
        : (Object.keys(behaviorParams.value).length > 0 ? behaviorParams.value : null),
    }
    const normalise = (rule: RuleRead): RuleRead => ({
      ...rule,
      logic:           typeof rule.logic           === 'string' ? JSON.parse(rule.logic)           : rule.logic,
      behavior_params: typeof rule.behavior_params === 'string' ? JSON.parse(rule.behavior_params) : rule.behavior_params,
    })
    if (editingRuleId.value) {
      const rule = normalise(await apiPatch<RuleRead>(`/rules/${editingRuleId.value}`, payload))
      rules.value = rules.value.map(r => r.id === rule.id ? rule : r)
    } else {
      const rule = normalise(await apiPost<RuleRead>('/rules', payload))
      rules.value = [...rules.value, rule]
    }
    addRuleZoneId.value = null
    editingRuleId.value = null
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Save Failed', message: e.message })
  } finally {
    submitting.value = false
  }
}

async function toggleZone(zone: ZoneRead) {
  try {
    const endpoint = zone.is_active ? 'disable' : 'enable'
    const updated = await apiPost<ZoneRead>(`/zones/${zone.id}/${endpoint}`, {})
    // Update zone in local list
    zones.value = zones.value.map(z => z.id === updated.id ? updated : z)
    // Cascade: flip is_active on every rule that belongs to this zone
    const newActive = updated.is_active
    rules.value = rules.value.map(r => r.zone_id === zone.id ? { ...r, is_active: newActive } : r)
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Toggle Failed', message: e.message })
  }
}

async function toggleRule(rule: RuleRead) {
  try {
    const endpoint = rule.is_active ? 'disable' : 'enable'
    const updated = await apiPost<RuleRead>(`/rules/${rule.id}/${endpoint}`, {})
    const norm = {
      ...updated,
      logic:           typeof updated.logic           === 'string' ? JSON.parse(updated.logic)           : updated.logic,
      schedule:        typeof updated.schedule        === 'string' ? JSON.parse(updated.schedule)        : updated.schedule,
      behavior_params: typeof updated.behavior_params === 'string' ? JSON.parse(updated.behavior_params) : updated.behavior_params,
    }
    rules.value = rules.value.map(r => r.id === norm.id ? norm : r)
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Toggle Failed', message: e.message })
  }
}

function sevBadge(s: string) {
  return { critical: 'badge-error', high: 'badge-warning', medium: 'badge-info', low: 'badge-ghost' }[s] ?? 'badge-ghost'
}

function behaviorIcon(behavior: string): string {
  const icons: Record<string, string> = {
    intrusion:      `<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`,
    loitering:      `<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
    line_crossing:  `<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>`,
    crowd_density:  `<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`,
    abandoned_object: `<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>`,
  }
  return icons[behavior] ?? `<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
}

// ── Init ─────────────────────────────────────────────────────────────────────

onMounted(async () => {
  await cameras.fetchAll()
  if (cameras.cameras.length > 0) await selectCamera(cameras.cameras[0].id)
})
</script>
