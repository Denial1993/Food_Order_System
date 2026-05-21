<script setup lang="ts">
/**
 * 後台系統參數管理（Food_SystemConfig / 參考 tblsysCode 設計）
 *
 * 設計重點：
 *  - 一張表同時承擔「全站環境變數」與「下拉/列舉字典」兩種用途，
 *    用 CodeType 分群（系統參數 / 付款方式 / …）。
 *  - 列表照 CodeType + CodeSeq 排序，並提供 CodeType 篩選 chips。
 *  - 對於布林型參數（Y/N、OPEN/CLOSE）提供一鍵切換按鈕，避免每次都開彈窗。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'

// ── 型別 ─────────────────────────────────────────────────────────
interface SysConfig {
  CodeID:     number
  CodeNo:     string | null
  CodeType:   string | null
  CodeStr:    string | null
  CodeValue:  string | null
  RoleID:     number
  CodeDesc:   string | null
  CodeSeq:    string | null
  StatusCode: string | null
}

// ── 狀態 ─────────────────────────────────────────────────────────
const configs    = ref<SysConfig[]>([])
const loading    = ref(true)
const saving     = ref(false)
const successMsg = ref('')
const errorMsg   = ref('')

// 篩選 + 搜尋
const filterType = ref<string>('全部')
const keyword    = ref('')

// 彈窗
const showModal    = ref(false)
const isEditing    = ref(false)
const editCodeID   = ref<number | null>(null)
const deleteTarget = ref<SysConfig | null>(null)

// 表單
const form = reactive({
  CodeNo:    '',
  CodeType:  '系統參數',
  CodeStr:   '',
  CodeValue: '',
  RoleID:    0,
  CodeDesc:  '',
  CodeSeq:   '',
})
const formError = ref('')

// ── 衍生資料 ─────────────────────────────────────────────────────
/** 從現有資料抓出所有 CodeType，給篩選 chips 用 */
const codeTypes = computed(() => {
  const set = new Set<string>()
  for (const c of configs.value) if (c.CodeType) set.add(c.CodeType)
  return ['全部', ...Array.from(set)]
})

/** 套用篩選 + 搜尋後的列表 */
const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return configs.value.filter(c => {
    if (filterType.value !== '全部' && c.CodeType !== filterType.value) return false
    if (!kw) return true
    return (
      (c.CodeStr   ?? '').toLowerCase().includes(kw) ||
      (c.CodeValue ?? '').toLowerCase().includes(kw) ||
      (c.CodeDesc  ?? '').toLowerCase().includes(kw)
    )
  })
})

/** 判斷此參數是否為「布林型」，是的話就允許一鍵切換 */
function boolToggle(c: SysConfig): { next: string; label: string } | null {
  const v = (c.CodeValue ?? '').toUpperCase()
  if (v === 'Y')     return { next: 'N',     label: '停用' }
  if (v === 'N')     return { next: 'Y',     label: '啟用' }
  if (v === 'OPEN')  return { next: 'CLOSE', label: '打烊' }
  if (v === 'CLOSE') return { next: 'OPEN',  label: '開店' }
  return null
}

// ── API ─────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const res = await api.get<SysConfig[]>('/admin/system-config')
    configs.value = res.data
  } catch {
    errorMsg.value = '載入失敗，請確認後端是否正在運行'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEditing.value = false
  editCodeID.value = null
  Object.assign(form, {
    CodeNo: '', CodeType: filterType.value === '全部' ? '系統參數' : filterType.value,
    CodeStr: '', CodeValue: '', RoleID: 0, CodeDesc: '', CodeSeq: '',
  })
  formError.value = ''
  showModal.value = true
}

function openEdit(c: SysConfig) {
  isEditing.value = true
  editCodeID.value = c.CodeID
  Object.assign(form, {
    CodeNo:    c.CodeNo    ?? '',
    CodeType:  c.CodeType  ?? '',
    CodeStr:   c.CodeStr   ?? '',
    CodeValue: c.CodeValue ?? '',
    RoleID:    c.RoleID    ?? 0,
    CodeDesc:  c.CodeDesc  ?? '',
    CodeSeq:   c.CodeSeq   ?? '',
  })
  formError.value = ''
  showModal.value = true
}

async function submitForm() {
  if (!form.CodeType.trim()) { formError.value = '請填寫 CodeType (分類)'; return }
  if (!form.CodeStr.trim())  { formError.value = '請填寫 CodeStr (參數鍵)'; return }

  saving.value = true
  formError.value = ''

  const payload = {
    CodeNo:    form.CodeNo.trim()   || null,
    CodeType:  form.CodeType.trim(),
    CodeStr:   form.CodeStr.trim(),
    CodeValue: form.CodeValue,
    RoleID:    form.RoleID,
    CodeDesc:  form.CodeDesc.trim() || null,
    CodeSeq:   form.CodeSeq.trim()  || null,
  }

  try {
    if (isEditing.value && editCodeID.value !== null) {
      await api.put(`/admin/system-config/${editCodeID.value}`, payload)
      successMsg.value = `「${form.CodeStr}」已更新`
    } else {
      await api.post('/admin/system-config', payload)
      successMsg.value = `「${form.CodeStr}」已新增`
    }
    showModal.value = false
    await load()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    formError.value = msg ?? '儲存失敗，請再試一次'
  } finally {
    saving.value = false
    setTimeout(() => (successMsg.value = ''), 2500)
  }
}

/** 一鍵切換布林型參數 (Y/N、OPEN/CLOSE) */
async function quickToggle(c: SysConfig) {
  const toggle = boolToggle(c)
  if (!toggle) return
  try {
    await api.put(`/admin/system-config/${c.CodeID}`, {
      CodeNo:    c.CodeNo,
      CodeType:  c.CodeType,
      CodeStr:   c.CodeStr,
      CodeValue: toggle.next,
      RoleID:    c.RoleID,
      CodeDesc:  c.CodeDesc,
      CodeSeq:   c.CodeSeq,
    })
    c.CodeValue = toggle.next
    successMsg.value = `${c.CodeStr} → ${toggle.next}`
  } catch {
    errorMsg.value = '操作失敗'
  }
  setTimeout(() => { successMsg.value = ''; errorMsg.value = '' }, 2500)
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    await api.delete(`/admin/system-config/${deleteTarget.value.CodeID}`)
    successMsg.value = `「${deleteTarget.value.CodeStr}」已刪除`
    deleteTarget.value = null
    await load()
  } catch {
    errorMsg.value = '刪除失敗'
  }
  setTimeout(() => { successMsg.value = ''; errorMsg.value = '' }, 2500)
}

onMounted(load)
</script>

<template>
  <div class="space-y-5">

    <!-- ① 標題列 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">系統參數</h1>
        <p class="text-xs text-slate-400 mt-1">
          管理全站環境變數（如服務費率、營業狀態）與下拉字典（如付款方式）。
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="successMsg" class="text-sm text-emerald-600 font-medium">{{ successMsg }}</span>
        <span v-if="errorMsg"   class="text-sm text-rose-600 font-medium">{{ errorMsg }}</span>
        <button class="btn-ghost text-sm" @click="load">↻ 重整</button>
        <button class="btn-primary text-sm" @click="openCreate">＋ 新增參數</button>
      </div>
    </div>

    <!-- ② 篩選 + 搜尋 -->
    <div class="card flex flex-wrap items-center gap-3">
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="t in codeTypes"
          :key="t"
          class="text-xs px-3 py-1 rounded-full border transition"
          :class="filterType === t
            ? 'bg-brand-600 text-white border-brand-600'
            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'"
          @click="filterType = t"
        >{{ t }}</button>
      </div>
      <div class="flex-1 min-w-48">
        <input
          v-model="keyword"
          type="text"
          placeholder="搜尋 CodeStr / CodeValue / 說明..."
          class="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
        />
      </div>
      <span class="text-xs text-slate-400">{{ filtered.length }} 筆</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-slate-400 text-sm">載入中...</div>

    <!-- ③ 參數表格 -->
    <div v-else class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-slate-400 border-b border-slate-100">
            <th class="pb-2 font-medium w-20">分類</th>
            <th class="pb-2 font-medium">參數鍵 (CodeStr)</th>
            <th class="pb-2 font-medium">當前值 (CodeValue)</th>
            <th class="pb-2 font-medium">說明</th>
            <th class="pb-2 font-medium text-center w-16">排序</th>
            <th class="pb-2 font-medium text-center w-32">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
            v-for="c in filtered"
            :key="c.CodeID"
            class="hover:bg-slate-50"
          >
            <td class="py-3">
              <span class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {{ c.CodeType }}
              </span>
            </td>
            <td class="py-3 font-mono text-xs text-slate-700">{{ c.CodeStr }}</td>
            <td class="py-3">
              <span class="font-semibold text-slate-800">{{ c.CodeValue }}</span>
            </td>
            <td class="py-3 text-slate-500 text-xs">{{ c.CodeDesc ?? '—' }}</td>
            <td class="py-3 text-center text-slate-400 text-xs font-mono">{{ c.CodeSeq ?? '—' }}</td>
            <td class="py-3 text-center">
              <div class="flex items-center justify-center gap-1.5">
                <button
                  v-if="boolToggle(c)"
                  class="text-xs text-amber-600 border border-amber-200 rounded-lg px-2 py-1 hover:bg-amber-50"
                  :title="`切換為 ${boolToggle(c)?.next}`"
                  @click="quickToggle(c)"
                >{{ boolToggle(c)?.label }}</button>
                <button
                  class="text-xs text-brand-600 border border-brand-200 rounded-lg px-2 py-1 hover:bg-brand-50"
                  @click="openEdit(c)"
                >編輯</button>
                <button
                  class="text-xs text-rose-500 border border-rose-200 rounded-lg px-2 py-1 hover:bg-rose-50"
                  @click="deleteTarget = c"
                >刪除</button>
              </div>
            </td>
          </tr>

          <tr v-if="!filtered.length">
            <td colspan="6" class="py-8 text-center text-slate-400">
              {{ configs.length ? '查無符合條件的參數' : '尚無系統參數資料' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ④ 表結構小提示 (放在底部，作為設計參考) -->
    <div class="text-xs text-slate-400 leading-relaxed">
      <p>
        資料表設計參考 <code class="text-slate-500">Pet_Dev_PI.dbo.tblsysCode</code>：
        <code>CodeID / CodeNo / CodeType / CodeStr / CodeValue / RoleID / CodeDesc / CodeSeq / StatusCode</code>
        ＋稽核欄位 <code>AddUser/AddDate/AddIpAddr/UpdUser/UpdDate/UpdIpAddr</code>。
      </p>
      <p class="mt-1">
        常用鍵：
        <code class="text-slate-500">SERVICE_FEE_RATE</code>（服務費率，例 0.10 = 10%）、
        <code class="text-slate-500">BUSINESS_STATUS</code>（OPEN/CLOSE）。
      </p>
    </div>

    <!-- ⑤ 新增 / 編輯彈窗 -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/50 flex items-start justify-center p-4 z-30 overflow-y-auto"
      @click.self="showModal = false"
    >
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg mt-8 mb-8">
        <div class="flex items-center justify-between px-6 pt-5 pb-4 border-b border-slate-100">
          <h2 class="text-lg font-semibold">{{ isEditing ? '編輯系統參數' : '新增系統參數' }}</h2>
          <button class="text-slate-400 hover:text-slate-700 text-xl" @click="showModal = false">✕</button>
        </div>

        <div class="px-6 py-4 space-y-4">

          <!-- CodeType + CodeNo -->
          <div class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-slate-700 mb-1">
                分類 CodeType <span class="text-rose-500">*</span>
              </label>
              <input
                v-model="form.CodeType"
                type="text"
                list="codeTypeOptions"
                maxlength="10"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                placeholder="例：系統參數 / 付款方式"
              />
              <datalist id="codeTypeOptions">
                <option v-for="t in codeTypes.filter(x => x !== '全部')" :key="t" :value="t" />
              </datalist>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">類型代碼 CodeNo</label>
              <input
                v-model="form.CodeNo"
                type="text"
                maxlength="5"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                placeholder="00"
              />
            </div>
          </div>

          <!-- CodeStr -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">
              參數鍵 CodeStr <span class="text-rose-500">*</span>
            </label>
            <input
              v-model="form.CodeStr"
              type="text"
              maxlength="30"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-400"
              placeholder="SERVICE_FEE_RATE"
            />
            <p class="text-xs text-slate-400 mt-1">建議使用 UPPER_SNAKE_CASE，程式端會用這個鍵讀值。</p>
          </div>

          <!-- CodeValue -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">
              參數值 CodeValue <span class="text-rose-500">*</span>
            </label>
            <input
              v-model="form.CodeValue"
              type="text"
              maxlength="100"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              placeholder="0.10"
            />
          </div>

          <!-- CodeDesc -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">說明 CodeDesc</label>
            <input
              v-model="form.CodeDesc"
              type="text"
              maxlength="50"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              placeholder="服務費率 10%"
            />
          </div>

          <!-- CodeSeq + RoleID -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">排序 CodeSeq</label>
              <input
                v-model="form.CodeSeq"
                type="text"
                maxlength="3"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                placeholder="001"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">使用角色 RoleID (0=不限)</label>
              <input
                v-model.number="form.RoleID"
                type="number"
                min="0"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
            </div>
          </div>

          <div v-if="formError" class="text-sm text-rose-600 bg-rose-50 rounded-lg px-3 py-2">{{ formError }}</div>
        </div>

        <div class="flex justify-end gap-3 px-6 pb-5">
          <button class="btn-ghost text-sm" @click="showModal = false">取消</button>
          <button class="btn-primary text-sm min-w-20" :disabled="saving" @click="submitForm">
            <span v-if="saving">儲存中...</span>
            <span v-else>{{ isEditing ? '儲存變更' : '新增參數' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ⑥ 刪除確認 -->
    <div v-if="deleteTarget" class="fixed inset-0 bg-black/50 flex items-center justify-center p-6 z-40">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4 text-center">
        <div class="text-4xl">🗑️</div>
        <h2 class="text-lg font-semibold">確認刪除？</h2>
        <p class="text-sm text-slate-600">
          即將刪除「<span class="font-semibold">{{ deleteTarget.CodeStr }}</span>」。
          <br/>此操作為軟刪除（StatusCode → 000），稽核紀錄會保留。
        </p>
        <div class="flex gap-3">
          <button class="flex-1 btn-ghost" @click="deleteTarget = null">取消</button>
          <button
            class="flex-1 text-sm font-medium bg-rose-500 text-white rounded-xl py-2 hover:bg-rose-600"
            @click="confirmDelete"
          >確認刪除</button>
        </div>
      </div>
    </div>

  </div>
</template>
