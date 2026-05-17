<script setup lang="ts">
import { computed } from 'vue'

interface Schedule {
  start: string
  end: string
  days: number[]
}

const props = defineProps<{
  modelValue: Schedule | null
}>()

const emit = defineEmits(['update:modelValue'])

const defaultSchedule: Schedule = {
  start: '00:00',
  end: '23:59',
  days: [0, 1, 2, 3, 4, 5, 6]
}

const schedule = computed({
  get: () => props.modelValue || defaultSchedule,
  set: (val) => emit('update:modelValue', val)
})

const daysOfWeek = [
  { label: 'M', value: 1 },
  { label: 'T', value: 2 },
  { label: 'W', value: 3 },
  { label: 'T', value: 4 },
  { label: 'F', value: 5 },
  { label: 'S', value: 6 },
  { label: 'S', value: 0 },
]

function toggleDay(day: number) {
  const newDays = [...schedule.value.days]
  const index = newDays.indexOf(day)
  if (index === -1) {
    newDays.push(day)
  } else {
    newDays.splice(index, 1)
  }
  schedule.value = { ...schedule.value, days: newDays.sort() }
}

function updateTime(field: 'start' | 'end', val: string) {
  schedule.value = { ...schedule.value, [field]: val }
}
</script>

<template>
  <div class="p-4 bg-base-300/20 rounded-xl border border-base-300 space-y-4">
    <div class="flex items-center justify-between">
      <span class="text-xs font-black uppercase tracking-widest opacity-60">Primary Schedule</span>
      <div class="tooltip tooltip-left" data-tip="Rule fires only within this time window and on selected days">
        <span class="badge badge-outline badge-xs opacity-50 cursor-help">Active Control</span>
      </div>
    </div>

    <!-- Time Range Selection -->
    <div class="grid grid-cols-2 gap-4">
      <div class="form-control">
        <label class="label pt-0">
          <span class="label-text text-[10px] uppercase font-bold opacity-70">Start Time</span>
        </label>
        <input 
          type="time" 
          :value="schedule.start"
          @input="e => updateTime('start', (e.target as HTMLInputElement).value)"
          class="input input-sm input-bordered bg-base-100 font-mono focus:border-primary" 
        />
      </div>
      <div class="form-control">
        <label class="label pt-0">
          <span class="label-text text-[10px] uppercase font-bold opacity-70">End Time</span>
        </label>
        <input 
          type="time" 
          :value="schedule.end"
          @input="e => updateTime('end', (e.target as HTMLInputElement).value)"
          class="input input-sm input-bordered bg-base-100 font-mono focus:border-primary" 
        />
      </div>
    </div>

    <!-- Day Selection -->
    <div class="space-y-2">
      <label class="label py-0">
        <span class="label-text text-[10px] uppercase font-bold opacity-70">Operating Days</span>
      </label>
      <div class="flex justify-between gap-1">
        <button
          v-for="day in daysOfWeek"
          :key="day.value"
          type="button"
          @click="toggleDay(day.value)"
          :class="[
            'btn btn-circle btn-xs w-7 h-7 text-[11px] font-bold transition-all duration-200',
            schedule.days.includes(day.value)
              ? 'btn-primary shadow-sm shadow-primary/20'
              : 'btn-ghost bg-base-200 opacity-40 hover:opacity-70'
          ]"
        >
          {{ day.label }}
        </button>
      </div>
    </div>

    <div class="pt-2 flex items-center gap-2">
      <div class="w-2 h-2 rounded-full bg-success animate-pulse"></div>
      <p class="text-[10px] opacity-60 italic">
        Rule will only trigger during these selected periods.
      </p>
    </div>
  </div>
</template>

<style scoped>
input[type="time"]::-webkit-calendar-picker-indicator {
  filter: invert(0.5);
  cursor: pointer;
}
</style>
