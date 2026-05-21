<script setup lang="ts">
/**
 * 後台訂單列表
 *
 * 【這頁的業務邏輯】
 * 這是廚房與收銀台共用的作業頁面：
 *
 *   顧客送單 → 訂單出現（OPEN 待備餐）
 *       ↓
 *   廚房備餐完畢，顧客用餐
 *       ↓
 *   店員點「結帳」→ PAID 已結帳 + 桌位回 IDLE
 *   （或）店員點「取消」→ CANCELLED 已取消
 *
 * 功能：
 *  - 依日期查詢訂單（預設今天）
 *  - 篩選 Tab：全部 / 待備餐 / 已結帳 / 已取消
 *  - 展開訂單看明細（誰點了什麼）
 *  - 一鍵結帳 / 取消
 *  - 每 30 秒自動重整（廚房不用一直手動按）
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '@/api/client'

// ── 型別定義 ──────────────────────────────────────────────────────
interface OrderDetail {
  FoodName:  string
  Quantity:  number
  UnitPrice: number
  Subtotal:  number
  Nickname:  string | null
  Note:      string | null
}

interface Order {
  OrderID:     number
  OrderNo:     string
  TableNo:     string
  TableName:   string | null
  AddDate:     string
  SubTotal:    number
  ServiceFee:  number
  TotalAmount: number
  OrderStatus: 'OPEN' | 'PAID' | 'CANCELLED'
  ItemCount:   number
  details:     OrderDetail[]
}

// 篩選 Tab 的選項型別
type FilterStatus = 'ALL' | 'OPEN' | 'PAID' | 'CANCELLED'

// ── 響應式狀態 ─────────────────────────────────────────────────────
const orders       = ref<Order[]>([])
const loading      = ref(true)
const actionMsg    = ref('')
const filterStatus = ref<FilterStatus>('ALL')

// 展開中的訂單 IDs（用 Set 管理，可同時展開多筆）
const expandedIds  = ref<Set<number>>(new Set())

// 日期篩選（預設今天，格式 YYYY-MM-DD）
const today      = new Date().toISOString().slice(0, 10)
const filterDate = ref(today)

// ── Computed ──────────────────────────────────────────────────────

/** 依 Tab 篩選後的訂單列表 */
const filteredOrders = computed(() => {
  if (filterStatus.value === 'ALL') return orders.value
  return orders.value.filter(o => o.OrderStatus === filterStatus.value)
})

/** 各狀態的筆數（Tab 上的 badge）*/
const counts = computed(() => ({
  ALL:       orders.value.length,
  OPEN:      orders.value.filter(o => o.OrderStatus === 'OPEN').length,
  PAID:      orders.value.filter(o => o.OrderStatus === 'PAID').length,
  CANCELLED: orders.value.filter(o => o.OrderStatus === 'CANCELLED').length,
}))

// ── 狀態顯示設定 ──────────────────────────────────────────────────
const statusCfg: Record<string, { label: string; dot: string; badge: string }> = {
  OPEN:      { label: '待備餐', dot: 'bg-amber-400',   badge: 'bg-amber-100 text-amber-700' },
  PAID:      { label: '已結帳', dot: 'bg-emerald-400', badge: 'bg-emerald-100 text-emerald-700' },
  CANCELLED: { label: '已取消', dot: 'bg-slate-300',   badge: 'bg-slate-100 text-slate-500' },
}

// ── 自動刷新 ──────────────────────────────────────────────────────
let refreshTimer: ReturnType<typeof setInterval> | null = null
const autoRefreshSec = ref(30)   // 倒數計秒，讓廚房知道下次刷新還多久

function startAutoRefresh() {
  // 每 30 秒自動呼叫一次 loadOrders
  refreshTimer = setInterval(() => {
    loadOrders(false)   // false = 靜默更新，不顯示 loading 骨架
  }, 30_000)
}

// ─────────────────────────────────────────────────────────────────
// API 函式
// ─────────────────────────────────────────────────────────────────

/**
 * 載入訂單
 * @param showLoader - true = 顯示 loading 骨架（第一次載入用）
 *                     false = 靜默更新（自動刷新用，不閃爍）
 */
async function loadOrders(showLoader = true) {
  if (showLoader) loading.value = true
  try {
    const res = await api.get<Order[]>('/admin/orders', {
      params: { date: filterDate.value },  // 傳日期篩選給後端
    })
    orders.value = res.data
  } catch {
    actionMsg.value = '載入失敗，請確認後端是否正在運行'
  } finally {
    loading.value = false
  }
}

/** 展開 / 收合某筆訂單的明細 */
function toggleExpand(orderId: number) {
  // Set 沒有 .has() 的響應式支援，需要重新賦值才能觸發 Vue 更新
  const next = new Set(expandedIds.value)
  if (next.has(orderId)) {
    next.delete(orderId)
  } else {
    next.add(orderId)
  }
  expandedIds.value = next
}

/** 結帳：OPEN → PAID，桌位自動回 IDLE（後端 checkout endpoint 處理）*/
async function checkout(order: Order) {
  try {
    await api.post(`/orders/checkout/${order.OrderID}`)
    // 直接在本地更新狀態，不需要重新載入整個列表（更快更流暢）
    order.OrderStatus = 'PAID'
    actionMsg.value   = `訂單 ${order.OrderNo} 結帳成功 ✓`
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    actionMsg.value = msg ?? '結帳失敗'
  }
  setTimeout(() => (actionMsg.value = ''), 3000)
}

/** 取消：OPEN → CANCELLED */
async function cancelOrder(order: Order) {
  try {
    await api.post(`/admin/orders/${order.OrderID}/cancel`)
    order.OrderStatus = 'CANCELLED'
    actionMsg.value   = `訂單 ${order.OrderNo} 已取消`
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    actionMsg.value = msg ?? '取消失敗'
  }
  setTimeout(() => (actionMsg.value = ''), 3000)
}

// ── 生命週期 ──────────────────────────────────────────────────────
onMounted(() => {
  loadOrders()
  startAutoRefresh()
})

// 離開頁面時清掉定時器，避免 memory leak
onBeforeUnmount(() => {
  if (refreshTimer !== null) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="space-y-5">

    <!-- ① 標題列 -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div>
        <h1 class="text-2xl font-bold">訂單列表</h1>
        <p class="text-xs text-slate-400 mt-0.5">每 30 秒自動更新 ─ 廚房 / 收銀台作業頁面</p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <!-- 操作成功 / 失敗訊息 -->
        <span v-if="actionMsg" class="text-sm font-medium"
          :class="actionMsg.includes('失敗') ? 'text-rose-600' : 'text-emerald-600'">
          {{ actionMsg }}
        </span>
        <!-- 日期選擇器 -->
        <input
          v-model="filterDate"
          type="date"
          class="text-sm rounded-lg border border-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-400"
          @change="loadOrders()"
        />
        <button class="btn-ghost text-sm" @click="loadOrders()">↻ 重整</button>
      </div>
    </div>

    <!-- ② 篩選 Tab -->
    <!--
      每個 Tab 上顯示各狀態的筆數，
      讓廚房一眼看到有幾張單待備餐
    -->
    <div class="flex gap-2 flex-wrap">
      <button
        v-for="tab in ([
          { key: 'ALL',       label: '全部'   },
          { key: 'OPEN',      label: '待備餐' },
          { key: 'PAID',      label: '已結帳' },
          { key: 'CANCELLED', label: '已取消' },
        ] as { key: FilterStatus; label: string }[])"
        :key="tab.key"
        class="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium transition"
        :class="filterStatus === tab.key
          ? 'bg-brand-600 text-white'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
        @click="filterStatus = tab.key"
      >
        {{ tab.label }}
        <!-- 待備餐筆數用橙色 badge 強調 -->
        <span
          class="text-xs px-1.5 py-0.5 rounded-full font-semibold"
          :class="filterStatus === tab.key
            ? 'bg-white/20 text-white'
            : tab.key === 'OPEN' && counts.OPEN > 0
              ? 'bg-amber-500 text-white'
              : 'bg-slate-200 text-slate-500'"
        >
          {{ counts[tab.key] }}
        </span>
      </button>
    </div>

    <!-- ③ Loading 骨架 -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse h-16 bg-slate-100"></div>
    </div>

    <!-- 無資料 -->
    <div v-else-if="!filteredOrders.length" class="card text-center py-12 text-slate-400">
      <div class="text-4xl mb-2">📋</div>
      <p>{{ filterStatus === 'ALL' ? '今天還沒有訂單' : `沒有「${statusCfg[filterStatus]?.label ?? filterStatus}」的訂單` }}</p>
    </div>

    <!-- ④ 訂單列表 -->
    <div v-else class="space-y-3">
      <div
        v-for="order in filteredOrders"
        :key="order.OrderID"
        class="card border-2 transition"
        :class="{
          'border-amber-200 bg-amber-50/30':   order.OrderStatus === 'OPEN',
          'border-emerald-100 bg-white':        order.OrderStatus === 'PAID',
          'border-slate-100 bg-slate-50/50 opacity-60': order.OrderStatus === 'CANCELLED',
        }"
      >
        <!-- 訂單標題列（點擊展開 / 收合明細）-->
        <div
          class="flex items-center gap-3 cursor-pointer select-none"
          @click="toggleExpand(order.OrderID)"
        >
          <!-- 狀態燈 -->
          <span
            class="w-2.5 h-2.5 rounded-full flex-shrink-0"
            :class="statusCfg[order.OrderStatus]?.dot ?? 'bg-slate-300'"
          ></span>

          <!-- 桌號 -->
          <div class="flex-shrink-0 w-10 text-center">
            <div class="text-xl font-bold leading-none">{{ order.TableNo }}</div>
            <div v-if="order.TableName" class="text-xs text-slate-400">{{ order.TableName }}</div>
          </div>

          <!-- 訂單資訊 -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-xs text-slate-500">{{ order.OrderNo }}</span>
              <span class="text-xs text-slate-400">{{ order.AddDate.slice(11, 16) }}</span>
            </div>
            <div class="text-sm text-slate-600">共 {{ order.ItemCount }} 道餐點</div>
          </div>

          <!-- 金額 + 狀態 -->
          <div class="text-right flex-shrink-0">
            <div class="font-bold text-slate-800">NT$ {{ order.TotalAmount }}</div>
            <span
              class="text-xs px-2 py-0.5 rounded-full"
              :class="statusCfg[order.OrderStatus]?.badge ?? 'bg-slate-100 text-slate-500'"
            >
              {{ statusCfg[order.OrderStatus]?.label ?? order.OrderStatus }}
            </span>
          </div>

          <!-- 展開箭頭 -->
          <span
            class="text-slate-300 text-lg flex-shrink-0 transition-transform"
            :class="{ 'rotate-180': expandedIds.has(order.OrderID) }"
          >▾</span>
        </div>

        <!-- 操作按鈕（OPEN 狀態才顯示）-->
        <div
          v-if="order.OrderStatus === 'OPEN'"
          class="flex gap-2 mt-3 pt-3 border-t border-amber-100"
          @click.stop
        >
          <!--
            @click.stop = 阻止事件冒泡（避免點按鈕同時觸發上方的 toggleExpand）
          -->
          <button
            class="flex-1 text-sm font-medium bg-emerald-500 text-white rounded-xl py-2 hover:bg-emerald-600 transition"
            @click="checkout(order)"
          >
            ✓ 結帳
          </button>
          <button
            class="text-sm text-rose-500 border border-rose-200 rounded-xl px-4 py-2 hover:bg-rose-50 transition"
            @click="cancelOrder(order)"
          >
            取消
          </button>
        </div>

        <!-- 展開的訂單明細 -->
        <transition name="slide-down">
          <div
            v-if="expandedIds.has(order.OrderID)"
            class="mt-3 pt-3 border-t border-slate-100 space-y-1.5"
            @click.stop
          >
            <!-- 每道菜 -->
            <div
              v-for="(d, idx) in order.details"
              :key="idx"
              class="flex items-center justify-between text-sm py-1"
            >
              <div class="flex-1">
                <span class="font-medium">{{ d.FoodName }}</span>
                <span class="text-slate-400 ml-1">× {{ d.Quantity }}</span>
                <!-- 點餐人暱稱 + 備註 -->
                <div v-if="d.Nickname || d.Note" class="text-xs text-slate-400 mt-0.5">
                  <span v-if="d.Nickname" class="mr-1">👤 {{ d.Nickname }}</span>
                  <span v-if="d.Note">📝 {{ d.Note }}</span>
                </div>
              </div>
              <div class="text-right text-slate-600 font-medium ml-3">
                NT$ {{ d.Subtotal }}
              </div>
            </div>

            <!-- 金額小結 -->
            <div class="pt-2 border-t border-slate-100 space-y-1 text-sm">
              <div class="flex justify-between text-slate-500">
                <span>餐點小計</span>
                <span>NT$ {{ order.SubTotal }}</span>
              </div>
              <div v-if="order.ServiceFee > 0" class="flex justify-between text-slate-500">
                <span>服務費</span>
                <span>NT$ {{ order.ServiceFee }}</span>
              </div>
              <div class="flex justify-between font-bold text-slate-800 pt-1 border-t border-slate-100">
                <span>合計</span>
                <span>NT$ {{ order.TotalAmount }}</span>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* 展開動畫 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
  opacity: 1;
  max-height: 600px;
}
</style>
