<template>
  <AppLayout>
    <div class="flex flex-col gap-4 max-w-5xl">

      <!-- ── Header ──────────────────────────────────────────────────────── -->
      <div class="flex items-center justify-between">
        <h2 class="font-mono font-semibold tracking-wide text-sm">จัดการผู้ใช้งาน</h2>
        <button class="btn btn-primary btn-sm font-mono gap-1.5" @click="openCreate">
          <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          เพิ่มผู้ใช้
        </button>
      </div>

      <!-- ── User table ──────────────────────────────────────────────────── -->
      <div class="card bg-base-100 border border-base-300 shadow-none overflow-hidden">
        <div v-if="loading" class="flex justify-center py-12">
          <span class="loading loading-spinner loading-md opacity-40"></span>
        </div>

        <div v-else-if="users.length === 0" class="flex flex-col items-center gap-3 py-12 opacity-40">
          <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <p class="font-mono text-sm">ไม่มีผู้ใช้งาน</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="table table-sm font-mono">
            <thead>
              <tr class="border-b border-base-300 text-xs opacity-50">
                <th class="w-10">ID</th>
                <th>ชื่อผู้ใช้</th>
                <th>ชื่อแสดง</th>
                <th>สิทธิ์</th>
                <th>ขอบเขตกล้อง</th>
                <th>สถานะ</th>
                <th>สร้างเมื่อ</th>
                <th class="text-right">จัดการ</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id"
                class="border-b border-base-300/50 hover:bg-base-200/40 transition-colors">
                <td class="opacity-40 text-xs">{{ u.id }}</td>
                <td>
                  <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                      :class="avatarClass(u.role)">
                      {{ (u.display_name || u.username)[0].toUpperCase() }}
                    </div>
                    <span class="font-semibold">{{ u.username }}</span>
                    <span v-if="u.id === auth.user?.id"
                      class="badge badge-xs badge-ghost">คุณ</span>
                  </div>
                </td>
                <td class="opacity-70">{{ u.display_name || '—' }}</td>
                <td>
                  <span class="badge badge-xs font-mono" :class="roleBadge(u.role)">{{ u.role }}</span>
                </td>
                <td class="opacity-60 text-xs max-w-[120px] truncate">{{ u.camera_scope || 'ทั้งหมด' }}</td>
                <td>
                  <span class="badge badge-xs font-mono"
                    :class="u.is_active ? 'badge-success' : 'badge-error'">
                    {{ u.is_active ? 'ใช้งาน' : 'ปิดใช้' }}
                  </span>
                </td>
                <td class="opacity-50 text-xs">{{ fmtDate(u.created_at) }}</td>
                <td>
                  <div class="flex items-center justify-end gap-1">
                    <button class="btn btn-ghost btn-xs font-mono" title="แก้ไข"
                      @click="openEdit(u)">
                      ✎
                    </button>
                    <button
                      class="btn btn-ghost btn-xs text-error font-mono"
                      title="ลบ"
                      :disabled="u.id === auth.user?.id"
                      @click="confirmDelete(u)">
                      ✕
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- ── Create / Edit Modal ─────────────────────────────────────────────── -->
    <dialog ref="modalRef" class="modal">
      <div class="modal-box max-w-md">
        <h3 class="font-bold font-mono text-sm mb-4">
          {{ editTarget ? 'แก้ไขผู้ใช้' : 'เพิ่มผู้ใช้ใหม่' }}
        </h3>

        <div class="flex flex-col gap-3">

          <!-- username (create only) -->
          <template v-if="!editTarget">
            <label class="form-control w-full">
              <div class="label py-0.5">
                <span class="label-text font-mono text-xs">ชื่อผู้ใช้ <span class="text-error">*</span></span>
              </div>
              <input v-model="form.username" type="text" placeholder="alphanumeric, _ . -"
                class="input input-bordered input-sm font-mono"
                :class="formErrors.username ? 'input-error' : ''" />
              <div v-if="formErrors.username" class="label py-0.5">
                <span class="label-text-alt text-error font-mono text-xs">{{ formErrors.username }}</span>
              </div>
            </label>

            <label class="form-control w-full">
              <div class="label py-0.5">
                <span class="label-text font-mono text-xs">รหัสผ่าน <span class="text-error">*</span></span>
              </div>
              <input v-model="form.password" type="password" placeholder="อย่างน้อย 8 ตัวอักษร"
                class="input input-bordered input-sm font-mono"
                :class="formErrors.password ? 'input-error' : ''" />
              <div v-if="formErrors.password" class="label py-0.5">
                <span class="label-text-alt text-error font-mono text-xs">{{ formErrors.password }}</span>
              </div>
            </label>

            <label class="form-control w-full">
              <div class="label py-0.5">
                <span class="label-text font-mono text-xs">สิทธิ์ <span class="text-error">*</span></span>
              </div>
              <select v-model="form.role" class="select select-bordered select-sm font-mono">
                <option value="OPERATOR">OPERATOR</option>
                <option value="AUDITOR">AUDITOR</option>
                <option value="ADMIN">ADMIN</option>
                <option v-if="auth.role === 'SUPERADMIN'" value="SUPERADMIN">SUPERADMIN</option>
                <option value="EXTERNAL_SYSTEM">EXTERNAL_SYSTEM</option>
              </select>
            </label>
          </template>

          <!-- display_name (both) -->
          <label class="form-control w-full">
            <div class="label py-0.5">
              <span class="label-text font-mono text-xs">ชื่อแสดง</span>
            </div>
            <input v-model="form.display_name" type="text" placeholder="ชื่อ-นามสกุล หรือตำแหน่ง"
              class="input input-bordered input-sm font-mono" />
          </label>

          <!-- camera_scope (both) -->
          <label class="form-control w-full">
            <div class="label py-0.5">
              <span class="label-text font-mono text-xs">ขอบเขตกล้อง</span>
              <span class="label-text-alt font-mono text-xs opacity-50">เว้นว่าง = ทั้งหมด</span>
            </div>
            <input v-model="form.camera_scope" type="text" placeholder="1,2,5 หรือเว้นว่าง"
              class="input input-bordered input-sm font-mono" />
          </label>

          <!-- is_active (edit only) -->
          <template v-if="editTarget">
            <label class="label cursor-pointer justify-start gap-3 py-1">
              <input v-model="form.is_active" type="checkbox" class="toggle toggle-sm toggle-success" />
              <span class="font-mono text-sm">เปิดใช้งานบัญชี</span>
            </label>
          </template>

          <!-- error -->
          <div v-if="submitError" class="alert alert-error py-2 text-xs font-mono">
            {{ submitError }}
          </div>
        </div>

        <div class="modal-action mt-5">
          <button class="btn btn-ghost btn-sm font-mono" @click="closeModal">ยกเลิก</button>
          <button class="btn btn-primary btn-sm font-mono" :class="saving ? 'loading' : ''"
            :disabled="saving" @click="handleSubmit">
            {{ editTarget ? 'บันทึก' : 'สร้างผู้ใช้' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ── Delete confirmation ─────────────────────────────────────────────── -->
    <dialog ref="deleteRef" class="modal">
      <div class="modal-box max-w-sm">
        <h3 class="font-bold font-mono text-sm">ยืนยันการลบ</h3>
        <p class="py-4 font-mono text-sm opacity-70">
          ลบผู้ใช้ <span class="font-bold text-error">{{ deleteTarget?.username }}</span> ?
          การกระทำนี้ไม่สามารถย้อนกลับได้
        </p>
        <div class="modal-action">
          <button class="btn btn-ghost btn-sm font-mono" @click="deleteRef?.close()">ยกเลิก</button>
          <button class="btn btn-error btn-sm font-mono" :class="deleting ? 'loading' : ''"
            :disabled="deleting" @click="handleDelete">
            ลบ
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { usersApi, type UserRead } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const auth  = useAuthStore()
const toast = useToastStore()

// ── Data ──────────────────────────────────────────────────────────────────────
const users   = ref<UserRead[]>([])
const loading = ref(false)

async function fetchUsers() {
  loading.value = true
  try {
    users.value = await usersApi.list()
  } catch (e: any) {
    toast.error('โหลดข้อมูลผู้ใช้ล้มเหลว', e?.message)
  } finally {
    loading.value = false
  }
}

onMounted(fetchUsers)

// ── Create / Edit ─────────────────────────────────────────────────────────────
const modalRef   = ref<HTMLDialogElement | null>(null)
const editTarget = ref<UserRead | null>(null)
const saving     = ref(false)
const submitError = ref('')

const form = ref({
  username: '',
  password: '',
  role: 'OPERATOR',
  display_name: '',
  camera_scope: '',
  is_active: true,
})

const formErrors = ref<Record<string, string>>({})

function openCreate() {
  editTarget.value = null
  form.value = { username: '', password: '', role: 'OPERATOR', display_name: '', camera_scope: '', is_active: true }
  formErrors.value = {}
  submitError.value = ''
  modalRef.value?.showModal()
}

function openEdit(u: UserRead) {
  editTarget.value = u
  form.value = {
    username: u.username,
    password: '',
    role: u.role,
    display_name: u.display_name ?? '',
    camera_scope: u.camera_scope ?? '',
    is_active: u.is_active,
  }
  formErrors.value = {}
  submitError.value = ''
  modalRef.value?.showModal()
}

function closeModal() {
  modalRef.value?.close()
}

function validateCreate(): boolean {
  const errs: Record<string, string> = {}
  if (!form.value.username.match(/^[a-zA-Z0-9_.-]{3,64}$/)) {
    errs.username = 'ชื่อผู้ใช้ต้องมี 3-64 ตัว (a-z, 0-9, _ . -)'
  }
  if (form.value.password.length < 8) {
    errs.password = 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร'
  }
  formErrors.value = errs
  return Object.keys(errs).length === 0
}

async function handleSubmit() {
  submitError.value = ''
  if (!editTarget.value && !validateCreate()) return

  saving.value = true
  try {
    if (editTarget.value) {
      await usersApi.update(editTarget.value.id, {
        display_name: form.value.display_name || null,
        camera_scope: form.value.camera_scope || null,
        is_active: form.value.is_active,
      })
      toast.success('บันทึกแล้ว', `อัปเดต ${editTarget.value.username} เรียบร้อย`)
    } else {
      await usersApi.create({
        username: form.value.username,
        password: form.value.password,
        role: form.value.role,
        display_name: form.value.display_name || null,
        camera_scope: form.value.camera_scope || null,
      })
      toast.success('สร้างแล้ว', `ผู้ใช้ ${form.value.username} ถูกสร้างเรียบร้อย`)
    }
    closeModal()
    await fetchUsers()
  } catch (e: any) {
    submitError.value = e?.message ?? 'เกิดข้อผิดพลาด'
  } finally {
    saving.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────
const deleteRef    = ref<HTMLDialogElement | null>(null)
const deleteTarget = ref<UserRead | null>(null)
const deleting     = ref(false)

function confirmDelete(u: UserRead) {
  deleteTarget.value = u
  deleteRef.value?.showModal()
}

async function handleDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await usersApi.delete(deleteTarget.value.id)
    toast.success('ลบแล้ว', `ลบผู้ใช้ ${deleteTarget.value.username} เรียบร้อย`)
    deleteRef.value?.close()
    await fetchUsers()
  } catch (e: any) {
    toast.error('ลบไม่สำเร็จ', e?.message)
  } finally {
    deleting.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function avatarClass(role: string) {
  const map: Record<string, string> = {
    SUPERADMIN: 'bg-error text-error-content',
    ADMIN:      'bg-warning text-warning-content',
    OPERATOR:   'bg-primary text-primary-content',
    AUDITOR:    'bg-secondary text-secondary-content',
    EXTERNAL_SYSTEM: 'bg-neutral text-neutral-content',
  }
  return map[role] ?? 'bg-neutral text-neutral-content'
}

function roleBadge(role: string) {
  const map: Record<string, string> = {
    SUPERADMIN: 'badge-error',
    ADMIN:      'badge-warning',
    OPERATOR:   'badge-primary',
    AUDITOR:    'badge-secondary',
    EXTERNAL_SYSTEM: 'badge-ghost',
  }
  return map[role] ?? 'badge-ghost'
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('th-TH', { day: '2-digit', month: 'short', year: '2-digit' })
}
</script>
