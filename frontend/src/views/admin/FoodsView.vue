<script setup lang="ts">
/**
 * 後台餐點管理 CRUD
 *
 * 功能：
 *  - 列出所有餐點（含下架商品）
 *  - 新增餐點（彈窗表單）
 *  - 編輯餐點（同一個彈窗，點「編輯」帶入資料）
 *  - 切換上架 / 下架（IsAvailable Y↔N）
 *  - 刪除餐點（軟刪除，StatusCode → "000"）
 *
 * 【給新手的說明】
 * 整個頁面的互動都在「一個大 ref 物件 form」和「一個 showModal ref」之間。
 * 你不需要切換頁面，全部在同一個畫面上完成。
 */
import { onMounted, reactive, ref } from 'vue'
import api from '@/api/client'

// ── 型別定義 ──────────────────────────────────────────────────────
interface Category {
  CategoryID: number
  CategoryName: string
}

interface Food {
  FoodID:       number
  FoodName:     string
  FoodDesc:     string | null
  Price:        number
  CategoryID:   number | null
  CategoryName: string | null
  IsAvailable:  string          // "Y" | "N"
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
const saving     = ref(false)          // 表單提交中
const errorMsg   = ref('')             // 全域錯誤
const successMsg = ref('')             // 操作成功訊息

// ── 彈窗控制 ──────────────────────────────────────────────────────
const showModal  = ref(false)
const isEditing  = ref(false)          // true = 編輯模式，false = 新增模式
const editFoodID = ref<number | null>(null)

// ── 表單資料（reactive 代替 ref，適合有多個欄位的物件）─────────────
// reactive() 跟 ref() 類似，差別是不需要 .value，直接 form.xxx 就能用
const form = reactive({
  FoodName:    '',
  FoodDesc:    '',
  Price:       0,
  CategoryID:  null as number | null,
  IsAvailable: 'Y',
  Sort:        0,
  PicturePath: '',
  PictureName: '',
  AltText:     '',
})
const formError = ref('')

// ── 刪除確認 ──────────────────────────────────────────────────────
const deleteTarget = ref<Food | null>(null)   // 目前要刪的那筆，null = 不顯示確認框

// ─────────────────────────────────────────────────────────────────
// API 函式
// ─────────────────────────────────────────────────────────────────

/** 載入所有餐點（admin 版本，看得到下架商品）*/
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

/** 開啟新增彈窗：清空表單 */
function openCreate() {
  isEditing.value  = false
  editFoodID.value = null
  // 重設所有欄位
  Object.assign(form, {
    FoodName: '', FoodDesc: '', Price: 0,
    CategoryID: null, IsAvailable: 'Y', Sort: 0,
    PicturePath: '', PictureName: '', AltText: '',
  })
  formError.value = ''
  showModal.value = true
}

/** 開啟編輯彈窗：把餐點資料填入表單 */
function openEdit(food: Food) {
  isEditing.value  = true
  editFoodID.value = food.FoodID
  Object.assign(form, {
    FoodName:    food.FoodName,
    FoodDesc:    food.FoodDesc    ?? '',
    Price:       food.Price,
    CategoryID:  food.CategoryID,
    IsAvailable: food.IsAvailable,
    Sort:        food.Sort,
    PicturePath: food.PicturePath ?? '',
    PictureName: food.PictureName ?? '',
    AltText:     food.AltText     ?? '',
  })
  formError.value = ''
  showModal.value = true
}

/** 提交表單（新增或編輯）*/
async function submitForm() {
  if (!form.FoodName.trim()) {
    formError.value = '請輸入餐點名稱'
    return
  }
  if (form.Price < 0) {
    formError.value = '售價不可為負數'
    return
  }

  saving.value    = true
  formError.value = ''

  // 組合要送出的資料物件
  const payload = {
    FoodName:    form.FoodName.trim(),
    FoodDesc:    form.FoodDesc.trim() || null,
    Price:       form.Price,
    CategoryID:  form.CategoryID,
    IsAvailable: form.IsAvailable,
    Sort:        form.Sort,
    PicturePath: form.PicturePath.trim() || null,
    PictureName: form.PictureName.trim() || null,
    AltText:     form.AltText.trim()     || null,
  }

  try {
    if (isEditing.value && editFoodID.value !== null) {
      // 編輯：PUT /api/admin/foods/{food_id}
      await api.put(`/admin/foods/${editFoodID.value}`, payload)
      successMsg.value = `「${form.FoodName}」已更新`
    } else {
      // 新增：POST /api/admin/foods
      await api.post('/admin/foods', payload)
      successMsg.value = `「${form.FoodName}」已新增`
    }
    showModal.value = false
    await loadFoods()          // 重新拉一次清單，確保畫面最新
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    formError.value = msg ?? '儲存失敗，請再試一次'
  } finally {
    saving.value = false
    setTimeout(() => (successMsg.value = ''), 2500)
  }
}

/** 切換上下架狀態（IsAvailable Y ↔ N）*/
async function toggleAvailable(food: Food) {
  const next = food.IsAvailable === 'Y' ? 'N' : 'Y'
  try {
    await api.put(`/admin/foods/${food.FoodID}`, {
      FoodName:    food.FoodName,
      FoodDesc:    food.FoodDesc,
      Price:       food.Price,
      CategoryID:  food.CategoryID,
      IsAvailable: next,
      Sort:        food.Sort,
      PicturePath: food.PicturePath,
      PictureName: food.PictureName,
      AltText:     food.AltText,
    })
    // 直接在 local 更新，不用重新載入整個清單（更快）
    food.IsAvailable = next
    successMsg.value = `「${food.FoodName}」已${next === 'Y' ? '上架' : '下架'}`
  } catch {
    errorMsg.value = '操作失敗'
  }
  setTimeout(() => { successMsg.value = ''; errorMsg.value = '' }, 2500)
}

/** 確認刪除 */
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

    <!-- Loading 骨架 -->
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
            <!-- 排序數字 -->
            <td class="py-3 text-slate-400 text-xs">{{ food.Sort }}</td>

            <!-- 縮圖 -->
            <td class="py-3">
              <img
                v-if="food.PicturePath"
                :src="food.PicturePath"
                :alt="food.FoodName"
                class="w-14 h-14 rounded-lg object-cover bg-slate-100"
              />
              <div
                v-else
                class="w-14 h-14 rounded-lg bg-slate-100 flex items-center justify-center text-slate-300 text-xs"
              >
                無圖
              </div>
            </td>

            <!-- 餐點名稱 + 描述 -->
            <td class="py-3">
              <div class="font-medium">{{ food.FoodName }}</div>
              <div v-if="food.FoodDesc" class="text-xs text-slate-400 mt-0.5 max-w-48 truncate">
                {{ food.FoodDesc }}
              </div>
            </td>

            <!-- 分類 -->
            <td class="py-3 text-slate-500">{{ food.CategoryName ?? '—' }}</td>

            <!-- 售價 -->
            <td class="py-3 text-right font-semibold">NT$ {{ food.Price }}</td>

            <!-- 上架狀態 -->
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

            <!-- 操作按鈕 -->
            <td class="py-3 text-center">
              <div class="flex items-center justify-center gap-2">
                <button
                  class="text-xs text-brand-600 border border-brand-200 rounded-lg px-2 py-1 hover:bg-brand-50"
                  @click="openEdit(food)"
                >
                  編輯
                </button>
                <button
                  class="text-xs text-rose-500 border border-rose-200 rounded-lg px-2 py-1 hover:bg-rose-50"
                  @click="deleteTarget = food"
                >
                  刪除
                </button>
              </div>
            </td>
          </tr>

          <!-- 空清單提示 -->
          <tr v-if="!foods.length">
            <td colspan="7" class="py-8 text-center text-slate-400">尚無餐點資料</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ③ 新增 / 編輯彈窗（Modal） -->
    <!--
      fixed inset-0 = 蓋住整個螢幕
      bg-black/50   = 半透明黑色背景
      z-30          = 確保在最上層
    -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/50 flex items-start justify-center p-4 z-30 overflow-y-auto"
      @click.self="showModal = false"
    >
      <!--
        @click.self = 只有點到「背景本身」才關閉，
        點到白色卡片內部不會誤觸關閉
      -->
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg mt-8 mb-8">

        <!-- 彈窗標題 -->
        <div class="flex items-center justify-between px-6 pt-5 pb-4 border-b border-slate-100">
          <h2 class="text-lg font-semibold">
            {{ isEditing ? '編輯餐點' : '新增餐點' }}
          </h2>
          <button class="text-slate-400 hover:text-slate-700 text-xl" @click="showModal = false">✕</button>
        </div>

        <!-- 表單本體 -->
        <div class="px-6 py-4 space-y-4">

          <!-- 餐點名稱（必填） -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">
              餐點名稱 <span class="text-rose-500">*</span>
            </label>
            <input
              v-model="form.FoodName"
              type="text"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              placeholder="例：招牌雞腿飯"
            />
          </div>

          <!-- 描述（選填） -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">餐點描述</label>
            <textarea
              v-model="form.FoodDesc"
              rows="2"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 resize-none"
              placeholder="選填，例：香嫩雞腿搭配白飯..."
            ></textarea>
          </div>

          <!-- 售價 + 排序（並排） -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">
                售價 (NT$) <span class="text-rose-500">*</span>
              </label>
              <input
                v-model.number="form.Price"
                type="number"
                min="0"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">排序（越小越前）</label>
              <input
                v-model.number="form.Sort"
                type="number"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
              />
            </div>
          </div>

          <!-- 分類下拉 -->
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">分類</label>
            <select
              v-model="form.CategoryID"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 bg-white"
            >
              <option :value="null">— 不指定分類 —</option>
              <option
                v-for="cat in categories"
                :key="cat.CategoryID"
                :value="cat.CategoryID"
              >
                {{ cat.CategoryName }}
              </option>
            </select>
          </div>

          <!-- 上架狀態 -->
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

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">圖片 URL</label>
              <input
                v-model="form.PicturePath"
                type="url"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                placeholder="https://example.com/image.jpg"
              />
            </div>

            <!-- 即時預覽 -->
            <div v-if="form.PicturePath" class="flex items-center gap-3">
              <img
                :src="form.PicturePath"
                alt="預覽"
                class="w-20 h-20 rounded-xl object-cover bg-slate-100 border border-slate-200"
                @error="($event.target as HTMLImageElement).style.display='none'"
              />
              <span class="text-xs text-slate-400">圖片預覽（載入失敗時不顯示）</span>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">圖片名稱</label>
                <input
                  v-model="form.PictureName"
                  type="text"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                  placeholder="留空自動用餐點名稱"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">Alt 替代文字</label>
                <input
                  v-model="form.AltText"
                  type="text"
                  class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
                  placeholder="圖片替代文字"
                />
              </div>
            </div>
          </div>

          <!-- 表單錯誤訊息 -->
          <div v-if="formError" class="text-sm text-rose-600 bg-rose-50 rounded-lg px-3 py-2">
            {{ formError }}
          </div>
        </div>

        <!-- 彈窗底部按鈕 -->
        <div class="flex justify-end gap-3 px-6 pb-5">
          <button class="btn-ghost text-sm" @click="showModal = false">取消</button>
          <button
            class="btn-primary text-sm min-w-20"
            :disabled="saving"
            @click="submitForm"
          >
            <span v-if="saving">儲存中...</span>
            <span v-else>{{ isEditing ? '儲存變更' : '新增餐點' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ④ 刪除確認對話框 -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 bg-black/50 flex items-center justify-center p-6 z-40"
    >
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4 text-center">
        <div class="text-4xl">🗑️</div>
        <h2 class="text-lg font-semibold">確認刪除？</h2>
        <p class="text-sm text-slate-600">
          即將刪除「<span class="font-semibold">{{ deleteTarget.FoodName }}</span>」。
          <br/>此操作為軟刪除，歷史訂單不受影響。
        </p>
        <div class="flex gap-3">
          <button class="flex-1 btn-ghost" @click="deleteTarget = null">取消</button>
          <button
            class="flex-1 text-sm font-medium bg-rose-500 text-white rounded-xl py-2 hover:bg-rose-600"
            @click="confirmDelete"
          >
            確認刪除
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
