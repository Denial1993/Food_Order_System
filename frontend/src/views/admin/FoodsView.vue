<script setup lang="ts">
/**
 * 後台餐點管理 CRUD（多對多分類版本）
 *
 * 主要變動（相較於舊版）：
 *  - form.CategoryID → form.CategoryIDs: number[]（多選）
 *  - 表格顯示多個分類 Badge
 *  - 彈窗用 Checkbox 選分類，不再用單一下拉
 */
import { onMounted, reactive, ref } from 'vue'
import api from '@/api/client'

// ── 型別定義 ──────────────────────────────────────────────────────
interface Category {
  CategoryID:   number
  CategoryName: string
}

interface Food {
  FoodID:       number
  FoodName:     string
  FoodDesc:     string | null
  Price:        number
  categories:   Category[]    // ← 多分類陣列
  IsAvailable:  string
  Sort:         number
  StatusCode:   string
  PictureID:    number | null
  PicturePath:  string | null
  PictureName:  string | null
  AltText:      string | null
}

// ── 響應式狀態 ─────────────────────────────────────────────────────
const foods      = ref<Food[]>([])
const categories = ref<Category[]>([])
const loading    = ref(true)
const saving     = ref(false)
const successMsg = ref('')
const errorMsg   = ref('')

// ── 彈窗控制 ──────────────────────────────────────────────────────
const showModal  = ref(false)
const isEditing  = ref(false)
const editFoodID = ref<number | null>(null)

// ── 表單（CategoryIDs 是 number[]）──────────────────────────────
const form = reactive({
  FoodName:    '',
  FoodDesc:    '',
  Price:       0,
  CategoryIDs: [] as number[],   // ← 多選，存放已勾選的 CategoryID
  IsAvailable: 'Y',
  Sort:        0,
  PicturePath: '',
  PictureName: '',
  AltText:     '',
})
const formError    = ref('')
const uploading    = ref(false)   // 圖片上傳 loading
const uploadError  = ref('')

// ── 刪除確認 ──────────────────────────────────────────────────────
const deleteTarget = ref<Food | null>(null)

// ─────────────────────────────────────────────────────────────────
// API 函式
// ─────────────────────────────────────────────────────────────────

async function loadFoods() {
  loading.value = true
  try {
    const [foodsRes, catsRes] = await Promise.all([
      api.get<Food[]>('/admin/foods'),
      api.get<Category[]>('/admin/categories'),
    ])
    foods.value      = foodsRes.data
    categories.value = catsRes.data
  } catch {
    errorMsg.value = '載入失敗，請確認後端是否正在運行'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEditing.value  = false
  editFoodID.value = null
  Object.assign(form, {
    FoodName: '', FoodDesc: '', Price: 0,
    CategoryIDs: [], IsAvailable: 'Y', Sort: 0,
    PicturePath: '', PictureName: '', AltText: '',
  })
  formError.value = ''
  showModal.value = true
}

function openEdit(food: Food) {
  isEditing.value  = true
  editFoodID.value = food.FoodID
  Object.assign(form, {
    FoodName:    food.FoodName,
    FoodDesc:    food.FoodDesc    ?? '',
    Price:       food.Price,
    CategoryIDs: food.categories.map(c => c.CategoryID),   // ← 把現有分類 ID 填入
    IsAvailable: food.IsAvailable,
    Sort:        food.Sort,
    PicturePath: food.PicturePath ?? '',
    PictureName: food.PictureName ?? '',
    AltText:     food.AltText     ?? '',
  })
  formError.value = ''
  showModal.value = true
}

async function submitForm() {
  if (!form.FoodName.trim()) { formError.value = '請輸入餐點名稱'; return }
  if (form.Price < 0)        { formError.value = '售價不可為負數'; return }

  saving.value    = true
  formError.value = ''

  const payload = {
    FoodName:    form.FoodName.trim(),
    FoodDesc:    form.FoodDesc.trim()    || null,
    Price:       form.Price,
    CategoryIDs: form.CategoryIDs,        // ← 送出陣列
    IsAvailable: form.IsAvailable,
    Sort:        form.Sort,
    PicturePath: form.PicturePath.trim() || null,
    PictureName: form.PictureName.trim() || null,
    AltText:     form.AltText.trim()     || null,
  }

  try {
    if (isEditing.value && editFoodID.value !== null) {
      await api.put(`/admin/foods/${editFoodID.value}`, payload)
      successMsg.value = `「${form.FoodName}」已更新`
    } else {
      await api.post('/admin/foods', payload)
      successMsg.value = `「${form.FoodName}」已新增`
    }
    showModal.value = false
    await loadFoods()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    formError.value = msg ?? '儲存失敗，請再試一次'
  } finally {
    saving.value = false
    setTimeout(() => (successMsg.value = ''), 2500)
  }
}

/** 上傳圖片到 Supabase Storage，成功後自動填入 PicturePath */
async function uploadImage(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value   = true
  uploadError.value = ''
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await api.post<{ url: string }>('/admin/upload-image', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    form.PicturePath = res.data.url
    if (!form.PictureName) form.PictureName = file.name.replace(/\.[^.]+$/, '')
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    uploadError.value = msg ?? '上傳失敗'
  } finally {
    uploading.value = false
    // 清空 input，讓同一張圖可以重複選
    ;(e.target as HTMLInputElement).value = ''
  }
}

/** 切換上下架：直接用現有 categories 的 IDs 送出 */
async function toggleAvailable(food: Food) {
  const next = food.IsAvailable === 'Y' ? 'N' : 'Y'
  try {
    await api.put(`/admin/foods/${food.FoodID}`, {
      FoodName:    food.FoodName,
      FoodDesc:    food.FoodDesc,
      Price:       food.Price,
      CategoryIDs: food.categories.map(c => c.CategoryID),  // ← 保持原有分類
      IsAvailable: next,
      Sort:        food.Sort,
      PicturePath: food.PicturePath,
      PictureName: food.PictureName,
      AltText:     food.AltText,
    })
    food.IsAvailable = next
    successMsg.value = `「${food.FoodName}」已${next === 'Y' ? '上架' : '下架'}`
  } catch {
    errorMsg.value = '操作失敗'
  }
  setTimeout(() => { successMsg.value = ''; errorMsg.value = '' }, 2500)
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    await api.delete(`/admin/foods/${deleteTarget.value.FoodID}`)
    successMsg.value = `「${deleteTarget.value.FoodName}」已刪除`
    deleteTarget.value = null
    await loadFoods()
  } catch {
    errorMsg.value = '刪除失敗'
  }
  setTimeout(() => { successMsg.value = ''; errorMsg.value = '' }, 2500)
}

onMounted(loadFoods)
</script>

<template>
  <div class="space-y-5">

    <!-- ① 標題列 -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">餐點管理</h1>
      <div class="flex items-center gap-3">
        <span v-if="successMsg" class="text-sm text-emerald-600 font-medium">{{ successMsg }}</span>
        <span v-if="errorMsg"   class="text-sm text-rose-600 font-medium">{{ errorMsg }}</span>
        <button class="btn-ghost text-sm" @click="loadFoods">↻ 重整</button>
        <button class="btn-primary text-sm" @click="openCreate">＋ 新增餐點</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-slate-400 text-sm">載入中...</div>

    <!-- ② 餐點表格 -->
    <div v-else class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-slate-400 border-b border-slate-100">
            <th class="pb-2 font-medium w-12">排序</th>
            <th class="pb-2 font-medium w-20">圖片</th>
            <th class="pb-2 font-medium">餐點名稱</th>
            <th class="pb-2 font-medium">分類</th>
            <th class="pb-2 font-medium text-right">售價</th>
            <th class="pb-2 font-medium text-center">狀態</th>
            <th class="pb-2 font-medium text-center">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
            v-for="food in foods"
            :key="food.FoodID"
            class="hover:bg-slate-50"
            :class="{ 'opacity-40': food.IsAvailable === 'N' }"
          >
            <td class="py-3 text-slate-400 text-xs">{{ food.Sort }}</td>

            <!-- 縮圖 -->
            <td class="py-3">
              <img
                v-if="food.PicturePath"
                :src="food.PicturePath"
                :alt="food.FoodName"
                class="w-14 h-14 rounded-lg object-cover bg-slate-100"
              />
              <div v-else class="w-14 h-14 rounded-lg bg-slate-100 flex items-center justify-center text-slate-300 text-xs">無圖</div>
            </td>

            <!-- 名稱 + 描述 -->
            <td class="py-3">
              <div class="font-medium">{{ food.FoodName }}</div>
              <div v-if="food.FoodDesc" class="text-xs text-slate-400 mt-0.5 max-w-48 truncate">{{ food.FoodDesc }}</div>
            </td>

            <!-- 分類 Badges（多個）-->
            <td class="py-3">
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="cat in food.categories"
                  :key="cat.CategoryID"
                  class="text-xs bg-brand-50 text-brand-700 border border-brand-100 px-2 py-0.5 rounded-full"
                >
                  {{ cat.CategoryName }}
                </span>
                <span v-if="!food.categories.length" class="text-xs text-slate-300">—</span>
              </div>
            </td>

            <td class="py-3 text-right font-semibold">NT$ {{ food.Price }}</td>

            <!-- 上下架 Badge（點擊切換）-->
            <td class="py-3 text-center">
              <span
                class="text-xs px-2 py-0.5 rounded-full cursor-pointer select-none"
                :class="food.IsAvailable === 'Y'
                  ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                  : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
                title="點我切換上/下架"
                @click="toggleAvailable(food)"
              >
                {{ food.IsAvailable === 'Y' ? '上架中' : '已下架' }}
              </span>
            </td>

            <td class="py-3 text-center">
              <div class="flex items-center justify-center gap-2">
                <button
                  class="text-xs text-brand-600 border border-brand-200 rounded-lg px-2 py-1 hover:bg-brand-50"
                  @click="openEdit(food)"
                >編輯</button>
                <button
                  class="text-xs text-rose-500 border border-rose-200 rounded-lg px-2 py-1 hover:bg-rose-50"
                  @click="deleteTarget = food"
                >刪除</button>
              </div>
            </td>
          </tr>

          <tr v-if="!foods.length">
            <td colspan="7" class="py-8 text-center text-slate-400">尚無餐點資料</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ③ 新增 / 編輯彈窗 -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/50 flex items-start justify-center p-4 z-30 overflow-y-auto"
      @click.self="showModal = false"
    >
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg mt-8 mb-8">
        <div class="flex items-center justify-between px-6 pt-5 pb-4 border-b border-slate-100">
          <h2 class="text-lg font-semibold">{{ isEditing ? '編輯餐點' : '新增餐點' }}</h2>
          <button class="text-slate-400 hover:text-slate-700 text-xl" @click="showModal = false">✕</button>
        </div>

        <div class="px-6 py-4 space-y-4">

          <!-- 餐點名稱 -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">
              餐點名稱 <span class="text-rose-500">*</span>
            </label>
            <input v-model="form.FoodName" type="text"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              placeholder="例：招牌雞腿飯" />
          </div>

          <!-- 描述 -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">餐點描述</label>
            <textarea v-model="form.FoodDesc" rows="2"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 resize-none"
              placeholder="選填..."></textarea>
          </div>

          <!-- 售價 + 排序 -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">
                售價 (NT$) <span class="text-rose-500">*</span>
              </label>
              <input v-model.number="form.Price" type="number" min="0"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">排序（越小越前）</label>
              <input v-model.number="form.Sort" type="number"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
            </div>
          </div>

          <!-- 分類多選（Checkbox）-->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">
              所屬分類
              <span class="ml-1 text-xs text-slate-400 font-normal">（可多選，例如同時勾「熱門推薦」和「主食」）</span>
            </label>
            <div class="grid grid-cols-3 gap-2">
              <!--
                v-model 搭配 array：
                  - 勾選時把 cat.CategoryID 加入 form.CategoryIDs
                  - 取消時從陣列移除
                這是 Vue3 的內建行為，不需要手動處理
              -->
              <label
                v-for="cat in categories"
                :key="cat.CategoryID"
                class="flex items-center gap-2 cursor-pointer rounded-lg border p-2 transition"
                :class="form.CategoryIDs.includes(cat.CategoryID)
                  ? 'border-brand-400 bg-brand-50'
                  : 'border-slate-200 bg-white hover:bg-slate-50'"
              >
                <input
                  type="checkbox"
                  :value="cat.CategoryID"
                  v-model="form.CategoryIDs"
                  class="accent-brand-600"
                />
                <span class="text-sm">{{ cat.CategoryName }}</span>
              </label>
            </div>
          </div>

          <!-- 供應狀態 -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">供應狀態</label>
            <div class="flex gap-4">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="form.IsAvailable" value="Y" class="accent-brand-600" />
                <span class="text-sm">上架（顧客可點選）</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="form.IsAvailable" value="N" class="accent-rose-500" />
                <span class="text-sm">下架（隱藏不顯示）</span>
              </label>
            </div>
          </div>

          <!-- 圖片區塊 -->
          <div class="border-t border-slate-100 pt-4 space-y-3">
            <p class="text-xs text-slate-400 font-medium uppercase tracking-wide">圖片設定（選填）</p>

            <!-- 上傳 or URL 二選一 -->
            <div class="flex flex-col gap-2">
              <!-- 本機上傳 -->
              <label
                class="flex items-center gap-2 cursor-pointer border-2 border-dashed border-slate-200 rounded-xl px-4 py-3 hover:border-brand-400 hover:bg-brand-50 transition"
                :class="{ 'opacity-50 pointer-events-none': uploading }"
              >
                <svg class="w-5 h-5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span class="text-sm text-slate-600">
                  {{ uploading ? '上傳中...' : '從本機選擇圖片' }}
                </span>
                <input type="file" accept="image/*" class="sr-only" @change="uploadImage" />
              </label>
              <span v-if="uploadError" class="text-xs text-rose-500">{{ uploadError }}</span>

              <!-- 分隔線 -->
              <div class="flex items-center gap-2 text-xs text-slate-400">
                <div class="flex-1 border-t border-slate-200"></div>
                <span>或填入圖片網址</span>
                <div class="flex-1 border-t border-slate-200"></div>
              </div>

              <div>
                <input v-model="form.PicturePath" type="url"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                  placeholder="https://example.com/image.jpg" />
              </div>
            </div>
            <div v-if="form.PicturePath" class="flex items-center gap-3">
              <img :src="form.PicturePath" alt="預覽"
                class="w-20 h-20 rounded-xl object-cover bg-slate-100 border border-slate-200"
                @error="($event.target as HTMLImageElement).style.display='none'" />
              <span class="text-xs text-slate-400">圖片預覽</span>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">圖片名稱</label>
                <input v-model="form.PictureName" type="text"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                  placeholder="留空自動用餐點名稱" />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">Alt 替代文字</label>
                <input v-model="form.AltText" type="text"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
              </div>
            </div>
          </div>

          <!-- 表單錯誤 -->
          <div v-if="formError" class="text-sm text-rose-600 bg-rose-50 rounded-lg px-3 py-2">{{ formError }}</div>
        </div>

        <div class="flex justify-end gap-3 px-6 pb-5">
          <button class="btn-ghost text-sm" @click="showModal = false">取消</button>
          <button class="btn-primary text-sm min-w-20" :disabled="saving" @click="submitForm">
            <span v-if="saving">儲存中...</span>
            <span v-else>{{ isEditing ? '儲存變更' : '新增餐點' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ④ 刪除確認 -->
    <div v-if="deleteTarget" class="fixed inset-0 bg-black/50 flex items-center justify-center p-6 z-40">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4 text-center">
        <div class="text-4xl">🗑️</div>
        <h2 class="text-lg font-semibold">確認刪除？</h2>
        <p class="text-sm text-slate-600">
          即將刪除「<span class="font-semibold">{{ deleteTarget.FoodName }}</span>」。
          <br/>此操作為軟刪除，歷史訂單不受影響。
        </p>
        <div class="flex gap-3">
          <button class="flex-1 btn-ghost" @click="deleteTarget = null">取消</button>
          <button class="flex-1 text-sm font-medium bg-rose-500 text-white rounded-xl py-2 hover:bg-rose-600"
            @click="confirmDelete">確認刪除</button>
        </div>
      </div>
    </div>

  </div>
</template>
