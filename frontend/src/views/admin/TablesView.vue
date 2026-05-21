<script setup lang="ts">
/**
 * 後台桌位管理頁
 * - 顯示全部桌位卡片，顏色對應狀態
 * - 點「開桌」→ IDLE → ORDERING
 * - 點「清桌」→ 任意 → IDLE
 * - 點桌位卡片 → 展開該桌訂單列表
 */
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

interface TableInfo {
  TableID: number
  TableNo: string
  TableName: string | null
  Seats: number | null
  TableStatus: 'IDLE' | 'ORDERING' | 'CLEANING'
}

interface OrderDetail {
  FoodName: string
  Quantity: number
  UnitPrice: number
  Subtotal: number
  Nickname: string | null
}
interface Order {
  OrderID: number
  OrderNo: string
  AddDate: string
  TotalAmount: number
  OrderStatus: string
  details: OrderDetail[]
}

const tables    = ref<TableInfo[]>([])
const loading   = ref(true)
const actionMsg = ref('')                        // 操作成功/失敗訊息
const expanded  = ref<number | null>(null)       // 展開中的 TableID
const tableOrders = ref<Record<number, Order[]>>({})

// ── 排序 ──────────────────────────────────────────────────────────
// sortDir: 'asc' = 桌號由小到大，'desc' = 由大到小
const sortDir = ref<'asc' | 'desc'>('asc')

// computed 會根據 tables 和 sortDir 自動計算，兩者任一改變就重算
const sortedTables = computed(() => {
  // 先複製一份（不直接排原陣列，避免影響後面的 find 等操作）
  return [...tables.value].sort((a, b) => {
    // parseInt 把 "A1", "02", "3" 之類的桌號轉成數字比較
    // 如果不是純數字（如 "A1"），parseInt 回傳 NaN，|| 0 保護一下
    const na = parseInt(a.TableNo) || 0
    const nb = parseInt(b.TableNo) || 0
    return sortDir.value === 'asc' ? na - nb : nb - na
  })
})

// 狀態顏色設定
const statusCfg: Record<string, { label: string; dot: string; card: string }> = {
  IDLE:     { label: '空閒',  dot: 'bg-slate-400',   card: 'border-slate-200 bg-white' },
  ORDERING: { label: '點餐中', dot: 'bg-emerald-500', card: 'border-emerald-200 bg-emerald-50' },
  CLEANING: { label: '清潔中', dot: 'bg-amber-400',   card: 'border-amber-200 bg-amber-50' },
}

async function loadTables() {
  loading.value = true
  try {
    const res = await api.get<TableInfo[]>('/tables/')
    tables.value = res.data
  } finally {
    loading.value = false
  }
}

async function openTable(tableNo: string) {
  try {
    await api.post(`/tables/${tableNo}/open`)
    actionMsg.value = `桌號 ${tableNo} 已開桌`
    await loadTables()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    actionMsg.value = msg ?? '開桌失敗'
  }
  setTimeout(() => (actionMsg.value = ''), 2500)
}

async function cleanTable(tableNo: string) {
  try {
    await api.post(`/tables/${tableNo}/clean`)
    actionMsg.value = `桌號 ${tableNo} 已清桌`
    await loadTables()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    actionMsg.value = msg ?? '清桌失敗'
  }
  setTimeout(() => (actionMsg.value = ''), 2500)
}

async function toggleOrders(tableId: number) {
  if (expanded.value === tableId) {
    expanded.value = null
    return
  }
  expanded.value = tableId
  if (!tableOrders.value[tableId]) {
    const res = await api.get<Order[]>(`/orders/table/${tableId}`)
    tableOrders.value[tableId] = res.data
  }
}

onMounted(loadTables)
</script>

<template>
  <div class="space-y-5">
    <!-- 標題 + 排序 + 重整 -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">桌位管理</h1>
      <div class="flex items-center gap-3">
        <span v-if="actionMsg" class="text-sm text-emerald-600 font-medium">{{ actionMsg }}</span>
        <!-- 排序切換按鈕：點一下在升冪/降冪之間切換 -->
        <button
          class="btn-ghost text-sm flex items-center gap-1"
          @click="sortDir = sortDir === 'asc' ? 'desc' : 'asc'"
          title="切換排序方向"
        >
          桌號
          <span>{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
        </button>
        <button class="btn-ghost text-sm" @click="loadTables">↻ 重整</button>
      </div>
    </div>

    <!-- 狀態說明 -->
    <div class="flex gap-4 text-sm text-slate-500">
      <span v-for="(cfg, key) in statusCfg" :key="key" class="flex items-center gap-1.5">
        <span class="w-2.5 h-2.5 rounded-full" :class="cfg.dot"></span>
        {{ cfg.label }}
      </span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-slate-400">載入中...</div>

    <!-- 桌位卡片網格（v-for 改用 sortedTables，才會照排序顯示） -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
      <div
        v-for="t in sortedTables"
        :key="t.TableID"
        class="rounded-2xl border-2 p-4 transition cursor-pointer"
        :class="statusCfg[t.TableStatus]?.card ?? 'border-slate-200 bg-white'"
        @click="toggleOrders(t.TableID)"
      >
        <!-- 桌號 + 狀態燈 -->
        <div class="flex items-center justify-between mb-2">
          <span class="text-xl font-bold">{{ t.TableNo }}</span>
          <span class="w-3 h-3 rounded-full" :class="statusCfg[t.TableStatus]?.dot"></span>
        </div>

        <!-- 區域 / 座位 -->
        <div class="text-xs text-slate-500 space-y-0.5 mb-3">
          <div v-if="t.TableName">{{ t.TableName }}</div>
          <div v-if="t.Seats">{{ t.Seats }} 人座</div>
        </div>

        <!-- 狀態標籤 -->
        <div class="text-xs font-medium mb-3" :class="{
          'text-slate-400': t.TableStatus === 'IDLE',
          'text-emerald-600': t.TableStatus === 'ORDERING',
          'text-amber-600': t.TableStatus === 'CLEANING',
        }">
          {{ statusCfg[t.TableStatus]?.label ?? t.TableStatus }}
        </div>

        <!-- 操作按鈕 -->
        <div class="flex gap-1.5" @click.stop>
          <button
            v-if="t.TableStatus === 'IDLE'"
            class="flex-1 text-xs btn-primary py-1"
            @click="openTable(t.TableNo)"
          >
            開桌
          </button>
          <button
            v-if="t.TableStatus === 'ORDERING'"
            class="flex-1 text-xs text-slate-600 border border-slate-200 rounded-lg py-1 hover:bg-slate-50"
            @click="toggleOrders(t.TableID)"
          >
            {{ expanded === t.TableID ? '收起' : '查看訂單' }}
          </button>
          <button
            v-if="t.TableStatus !== 'IDLE'"
            class="flex-1 text-xs text-rose-500 border border-rose-200 rounded-lg py-1 hover:bg-rose-50"
            @click="cleanTable(t.TableNo)"
          >
            清桌
          </button>
        </div>
      </div>
    </div>

    <!-- 展開訂單面板 -->
    <transition name="slide">
      <div
        v-if="expanded !== null && tableOrders[expanded]"
        class="card border border-slate-200 space-y-3"
      >
        <div class="flex items-center justify-between">
          <h2 class="font-semibold">
            桌號 {{ tables.find(t => t.TableID === expanded)?.TableNo }} — 訂單明細
          </h2>
          <button class="text-slate-400 hover:text-slate-700" @click="expanded = null">✕</button>
        </div>

        <div v-if="!tableOrders[expanded]?.length" class="text-sm text-slate-400">尚無訂單</div>

        <div
          v-for="order in tableOrders[expanded]"
          :key="order.OrderID"
          class="border border-slate-100 rounded-xl p-3 space-y-2"
        >
          <!-- 訂單標題 -->
          <div class="flex items-center justify-between text-sm">
            <span class="font-medium">{{ order.OrderNo }}</span>
            <div class="flex items-center gap-2">
              <span class="text-xs text-slate-400">{{ order.AddDate }}</span>
              <span
                class="text-xs px-2 py-0.5 rounded-full"
                :class="order.OrderStatus === 'PAID'
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-amber-100 text-amber-700'"
              >
                {{ order.OrderStatus === 'PAID' ? '已結帳' : '備餐中' }}
              </span>
            </div>
          </div>

          <!-- 明細 -->
          <div class="divide-y divide-slate-50 text-sm">
            <div
              v-for="d in order.details"
              :key="d.FoodName + d.Nickname"
              class="py-1.5 flex justify-between"
            >
              <span>
                {{ d.FoodName }}
                <span class="text-slate-400">× {{ d.Quantity }}</span>
                <span v-if="d.Nickname" class="ml-1 text-xs text-slate-400">（{{ d.Nickname }}）</span>
              </span>
              <span class="font-medium">NT$ {{ d.Subtotal }}</span>
            </div>
          </div>

          <!-- 合計 -->
          <div class="flex justify-between font-bold text-sm pt-1 border-t border-slate-100">
            <span>合計</span>
            <span>NT$ {{ order.TotalAmount }}</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
