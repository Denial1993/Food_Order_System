<script setup lang="ts">
/**
 * 【給新手的 Vue3 說明】
 *
 * ① import：把需要的工具從套件中引入
 *    - ref()     建立「響應式變數」（值一變，畫面自動更新）
 *    - computed() 建立「計算屬性」（依賴的 ref 變了，它也自動重算）
 *    - onMounted() 頁面「掛載到瀏覽器 DOM 後」才執行的鉤子函式
 *
 * ② <script setup> 是 Vue3 的 Composition API 寫法
 *    這裡宣告的變數/函式，template 可以直接用
 */
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'   // 我們自己包好的 axios，會自動帶 baseURL 和 Token

// ── 歷史營收 ─────────────────────────────────────────────────────
type RevenueMode = 'annual' | 'monthly' | 'daily'
interface RevenueData { mode: RevenueMode; labels: string[]; values: number[]; total: number }

const revenueMode   = ref<RevenueMode>('annual')
const revenueYear   = ref(new Date().getFullYear())
const revenueMonth  = ref(new Date().getMonth() + 1)
const revenueData   = ref<RevenueData | null>(null)
const revenueLoading = ref(false)

const currentYear = new Date().getFullYear()
// 提供年份下拉：近 3 年
const yearOptions = [currentYear, currentYear - 1, currentYear - 2]
const monthOptions = Array.from({ length: 12 }, (_, i) => i + 1)

async function loadRevenue() {
  revenueLoading.value = true
  try {
    const params: Record<string, string | number> = { mode: revenueMode.value }
    if (revenueMode.value !== 'annual') params.year = revenueYear.value
    if (revenueMode.value === 'daily') params.month = revenueMonth.value
    const res = await api.get<RevenueData>('/admin/revenue', { params })
    revenueData.value = res.data
  } catch {
    revenueData.value = null
  } finally {
    revenueLoading.value = false
  }
}

/** 最大值，用來計算進度條比例 */
const revenueMax = computed(() => {
  const vals = revenueData.value?.values ?? []
  return Math.max(...vals, 1)   // 避免除以 0
})

// ── 資料型別定義（TypeScript interface）──────────────────────────
// 這只是「告訴 TypeScript 這個物件長什麼樣子」，不影響執行
interface RecentOrder {
  OrderNo:       string
  TableNo:       string
  TotalAmount:   number
  OrderStatus:   string
  PaymentMethod: string | null
  AddDate:       string
  Items:         string
}

interface DashboardData {
  today_revenue:     number
  active_tables:     number
  pending_orders:    number
  today_order_count: number
  table_stats:       { IDLE: number; ORDERING: number; CLEANING: number }
  recent_orders:     RecentOrder[]
}

// ── 響應式狀態（ref）─────────────────────────────────────────────
// ref(null) 代表初始值是 null；當 data.value 被賦值，template 會自動重繪
const data    = ref<DashboardData | null>(null)
const loading = ref(true)    // true = 顯示「載入中」，false = 顯示真實資料
const error   = ref('')

// ── computed：從 data 組合出畫面需要的格式 ───────────────────────
// 只要 data.value 變化，cards 也自動重新計算
const cards = computed(() => {
  if (!data.value) return []
  const d = data.value
  return [
    {
      label: '今日營收',
      value: `NT$ ${d.today_revenue.toLocaleString()}`,
      sub:   '已結帳訂單合計',
      color: 'text-brand-600',
      bg:    'bg-brand-50',
      icon:  '💰',
    },
    {
      label: '在線桌數',
      value: `${d.active_tables} 桌`,
      sub:   `共 ${(d.table_stats.IDLE ?? 0) + d.active_tables + (d.table_stats.CLEANING ?? 0)} 桌`,
      color: 'text-emerald-600',
      bg:    'bg-emerald-50',
      icon:  '🪑',
    },
    {
      label: '待處理訂單',
      value: `${d.pending_orders} 筆`,
      sub:   '尚未結帳',
      color: 'text-amber-600',
      bg:    'bg-amber-50',
      icon:  '📋',
    },
    {
      label: '今日訂單數',
      value: `${d.today_order_count} 筆`,
      sub:   '含結帳與未結帳',
      color: 'text-blue-600',
      bg:    'bg-blue-50',
      icon:  '📊',
    },
  ]
})

// 桌況分佈的進度條寬度
const tableTotal = computed(() => {
  if (!data.value) return 1
  const s = data.value.table_stats
  return (s.IDLE + s.ORDERING + s.CLEANING) || 1  // 避免除以 0
})

// ── API 呼叫函式 ──────────────────────────────────────────────────
/**
 * async function = 非同步函式（不會卡住瀏覽器）
 * await         = 「等 API 回來再繼續」
 * try/catch     = 像 try...except in Python，發生錯誤時執行 catch
 */
async function loadDashboard() {
  loading.value = true
  error.value   = ''
  try {
    const res = await api.get<DashboardData>('/admin/dashboard')
    // res.data 就是後端 return 的那個 dict，已自動解析成 JS 物件
    data.value = res.data
  } catch {
    error.value = '載入失敗，請確認後端是否正在運行'
  } finally {
    // finally 不管成功失敗都會執行
    loading.value = false
  }
}

// ── 生命週期鉤子 ──────────────────────────────────────────────────
/**
 * onMounted = 頁面的 HTML 渲染到瀏覽器後，自動執行一次
 * 類似 Python 的 __init__，但是在「畫面出現後」才跑
 * 在這裡呼叫 API 是最常見的用法
 */
onMounted(() => {
  loadDashboard()
  loadRevenue()
})
</script>

<template>
  <!--
    【給新手的 Vue template 說明】
    v-if   = 條件顯示（像 Python 的 if）
    v-for  = 迴圈（像 Python 的 for item in list）
    {{ }}  = 顯示 JS 變數的值（雙大括號）
    :class = 動態 CSS class（冒號開頭代表「這是 JS 表達式」）
    @click = 點擊事件（@ 開頭代表事件監聽）
  -->
  <div class="space-y-6">

    <!-- 標題列 -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">儀表板</h1>
      <button
        class="btn-ghost text-sm"
        :disabled="loading"
        @click="loadDashboard"
      >
        {{ loading ? '載入中...' : '↻ 重整' }}
      </button>
    </div>

    <!-- 錯誤提示 -->
    <div v-if="error" class="card bg-rose-50 text-rose-600 text-sm">
      {{ error }}
    </div>

    <!-- ① 四個統計卡 -->
    <!--
      v-for="card in cards" → 把 cards 陣列每個元素取出來，命名為 card
      :key="card.label"     → Vue 需要一個唯一識別，用 label 就好
      card.xxx              → 使用 computed cards 裡定義的屬性
    -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div
        v-for="card in cards"
        :key="card.label"
        class="card space-y-1"
        :class="card.bg"
      >
        <div class="flex items-center gap-2">
          <span class="text-xl">{{ card.icon }}</span>
          <span class="text-sm text-slate-500">{{ card.label }}</span>
        </div>
        <div class="text-2xl font-bold" :class="card.color">
          <!-- loading 時顯示灰色骨架，否則顯示真實數字 -->
          <span v-if="loading" class="inline-block w-20 h-7 bg-slate-200 rounded animate-pulse"></span>
          <span v-else>{{ card.value }}</span>
        </div>
        <div class="text-xs text-slate-400">{{ card.sub }}</div>
      </div>
    </div>

    <!-- loading 時先用骨架佔位，等資料到了才顯示真正內容 -->
    <template v-if="!loading && data">

      <!-- ② 桌況視覺化 -->
      <div class="card space-y-3">
        <h2 class="font-semibold text-slate-700">桌況分佈</h2>
        <div class="flex rounded-full overflow-hidden h-4 gap-px">
          <!--
            :style = 動態 inline style
            這三段 div 的寬度加起來是 100%
          -->
          <div
            class="bg-slate-300 transition-all"
            :style="{ width: (data.table_stats.IDLE / tableTotal * 100) + '%' }"
          ></div>
          <div
            class="bg-emerald-400 transition-all"
            :style="{ width: (data.table_stats.ORDERING / tableTotal * 100) + '%' }"
          ></div>
          <div
            class="bg-amber-400 transition-all"
            :style="{ width: (data.table_stats.CLEANING / tableTotal * 100) + '%' }"
          ></div>
        </div>
        <div class="flex gap-6 text-sm">
          <span class="flex items-center gap-1.5">
            <span class="w-3 h-3 rounded-full bg-slate-300"></span>
            空閒 {{ data.table_stats.IDLE }} 桌
          </span>
          <span class="flex items-center gap-1.5">
            <span class="w-3 h-3 rounded-full bg-emerald-400"></span>
            點餐中 {{ data.table_stats.ORDERING }} 桌
          </span>
          <span class="flex items-center gap-1.5">
            <span class="w-3 h-3 rounded-full bg-amber-400"></span>
            清潔中 {{ data.table_stats.CLEANING }} 桌
          </span>
        </div>
      </div>

      <!-- ③ 最新訂單列表 -->
      <div class="card space-y-3">
        <h2 class="font-semibold text-slate-700">最新訂單</h2>

        <div v-if="!data.recent_orders.length" class="text-sm text-slate-400">
          今日尚無訂單
        </div>

        <!-- 表格 -->
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-slate-400 border-b border-slate-100">
                <th class="pb-2 font-medium">時間</th>
                <th class="pb-2 font-medium">桌號</th>
                <th class="pb-2 font-medium">訂單編號</th>
                <th class="pb-2 font-medium">餐點</th>
                <th class="pb-2 font-medium text-center">付款方式</th>
                <th class="pb-2 font-medium text-right">金額</th>
                <th class="pb-2 font-medium text-center">狀態</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-50">
              <!--
                v-for 可以同時取出索引值：(item, index) in list
                這裡我們只用 order，不需要 index
              -->
              <tr
                v-for="order in data.recent_orders"
                :key="order.OrderNo"
                class="hover:bg-slate-50"
              >
                <td class="py-2.5 text-slate-400 whitespace-nowrap">{{ order.AddDate }}</td>
                <td class="py-2.5 font-medium">{{ order.TableNo }}</td>
                <td class="py-2.5 font-mono text-xs text-slate-500">{{ order.OrderNo }}</td>
                <td class="py-2.5 text-slate-600 max-w-48 truncate">{{ order.Items }}</td>
                <td class="py-2.5 text-center text-slate-600 whitespace-nowrap">
                  {{ order.PaymentMethod ?? '—' }}
                </td>
                <td class="py-2.5 text-right font-semibold">NT$ {{ order.TotalAmount }}</td>
                <td class="py-2.5 text-center">
                  <!--
                    三元運算子: condition ? valueIfTrue : valueIfFalse
                    等同 Python 的: valueIfTrue if condition else valueIfFalse
                  -->
                  <span
                    class="text-xs px-2 py-0.5 rounded-full"
                    :class="{
                      'bg-emerald-100 text-emerald-700': order.OrderStatus === 'PAID',
                      'bg-amber-100 text-amber-700':    order.OrderStatus === 'OPEN',
                      'bg-slate-100 text-slate-500':    order.OrderStatus === 'CANCELLED',
                    }"
                  >
                    {{
                      order.OrderStatus === 'PAID'      ? '已結帳' :
                      order.OrderStatus === 'CANCELLED' ? '已取消' : '備餐中'
                    }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </template>

    <!-- ④ 歷史營收分析 -->
    <div class="card space-y-4">
      <div class="flex flex-wrap items-center gap-3">
        <h2 class="font-semibold text-slate-700">營業額分析</h2>

        <!-- 模式切換 -->
        <div class="flex rounded-lg overflow-hidden border border-slate-200 text-sm">
          <button
            v-for="m in [['annual','年度'],['monthly','月份'],['daily','日']] as [RevenueMode, string][]"
            :key="m[0]"
            class="px-3 py-1 transition"
            :class="revenueMode === m[0]
              ? 'bg-brand-600 text-white'
              : 'bg-white text-slate-600 hover:bg-slate-50'"
            @click="revenueMode = m[0]; loadRevenue()"
          >{{ m[1] }}</button>
        </div>

        <!-- 年份下拉（monthly / daily 才出現）-->
        <select
          v-if="revenueMode !== 'annual'"
          v-model="revenueYear"
          class="text-sm rounded-lg border border-slate-200 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-brand-400"
          @change="loadRevenue"
        >
          <option v-for="y in yearOptions" :key="y" :value="y">{{ y }} 年</option>
        </select>

        <!-- 月份下拉（daily 才出現）-->
        <select
          v-if="revenueMode === 'daily'"
          v-model="revenueMonth"
          class="text-sm rounded-lg border border-slate-200 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-brand-400"
          @change="loadRevenue"
        >
          <option v-for="m in monthOptions" :key="m" :value="m">{{ m }} 月</option>
        </select>

        <span v-if="revenueData" class="ml-auto text-sm text-slate-500">
          合計 <span class="font-bold text-slate-800">NT$ {{ revenueData.total.toLocaleString() }}</span>
        </span>
      </div>

      <!-- Loading 骨架 -->
      <div v-if="revenueLoading" class="space-y-2">
        <div v-for="i in 3" :key="i" class="flex items-center gap-2">
          <div class="w-10 h-3 bg-slate-200 rounded animate-pulse"></div>
          <div class="flex-1 h-5 bg-slate-200 rounded animate-pulse"></div>
        </div>
      </div>

      <!-- 橫向長條圖（CSS，不需 chart 套件）-->
      <div v-else-if="revenueData" class="space-y-2">
        <div
          v-for="(label, i) in revenueData.labels"
          :key="label"
          class="flex items-center gap-2 text-sm"
        >
          <!-- 標籤 -->
          <span class="w-10 text-right text-slate-500 text-xs shrink-0">{{ label }}</span>
          <!-- 進度條 -->
          <div class="flex-1 bg-slate-100 rounded-full h-5 overflow-hidden">
            <div
              class="h-5 bg-brand-500 rounded-full transition-all duration-500 flex items-center justify-end pr-2"
              :style="{ width: (revenueData.values[i] / revenueMax * 100) + '%' }"
            >
              <span
                v-if="revenueData.values[i] > 0"
                class="text-xs text-white font-medium whitespace-nowrap"
              >NT$ {{ revenueData.values[i].toLocaleString() }}</span>
            </div>
          </div>
          <!-- 無資料時顯示灰色文字 -->
          <span v-if="revenueData.values[i] === 0" class="text-xs text-slate-300">—</span>
        </div>
      </div>

      <div v-else class="text-sm text-slate-400">資料讀取失敗，請確認後端是否運行</div>
    </div>

  </div>
</template>
