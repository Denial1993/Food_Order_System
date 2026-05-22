<script setup lang="ts">
/**
 * 顧客「我的訂單」頁
 * 路由: /my-orders?table=1
 * 顯示此桌本次所有已送出訂單：送出時間、每道餐點明細、金額
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'

// 取消視窗分鐘數（與後端預設相同，僅用於 UI 提示文字）
const CANCEL_WINDOW_MIN = 5

interface OrderDetail {
  FoodID: number
  FoodName: string
  Quantity: number
  UnitPrice: number
  Subtotal: number
  Nickname: string | null
  Note: string | null
}
interface Order {
  OrderID: number
  OrderNo: string
  AddDate: string
  SubTotal: number
  ServiceFee: number
  TotalAmount: number
  OrderStatus: 'OPEN' | 'PAID' | 'CANCELLED'
  details: OrderDetail[]
}

const route  = useRoute()
const router = useRouter()

const tableNo  = computed(() => String(route.query.table ?? ''))
const tableId  = computed(() => Number(route.query.tableId ?? 0))
const orders   = ref<Order[]>([])
const loading    = ref(true)
const errorMsg   = ref('')
const cancellingId = ref<number | null>(null)   // 正在取消中的 OrderID
const cancelError  = ref('')                     // 取消失敗訊息

// 計算全桌總計（所有訂單加總）
const grandTotal = computed(() =>
  orders.value.reduce((s, o) => s + Number(o.TotalAmount), 0)
)
const grandItems = computed(() =>
  orders.value.flatMap(o => o.details).reduce((s, d) => s + d.Quantity, 0)
)

/** 判斷訂單是否還在可取消時間窗 (OPEN + 下單未超過 CANCEL_WINDOW_MIN 分鐘) */
function isCancellable(order: Order): boolean {
  if (order.OrderStatus !== 'OPEN') return false
  if (!order.AddDate) return false
  const placed = new Date(order.AddDate).getTime()
  const elapsed = (Date.now() - placed) / 60000
  return elapsed <= CANCEL_WINDOW_MIN
}

/** 顧客自助取消：帶上本桌 SessionToken */
async function cancelOrder(order: Order) {
  const sessionToken = localStorage.getItem(`food.session.table.${tableNo.value}`)
  cancellingId.value = order.OrderID
  cancelError.value  = ''
  try {
    await api.post(`/orders/cancel-customer/${order.OrderID}`, { session_token: sessionToken })
    order.OrderStatus = 'CANCELLED'   // 直接更新本地狀態，不需重整整頁
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    cancelError.value = msg ?? '取消失敗，請聯絡店員'
    setTimeout(() => (cancelError.value = ''), 4000)
  } finally {
    cancellingId.value = null
  }
}

// 狀態 badge 樣式
const statusLabel: Record<string, string> = {
  OPEN:      '備餐中',
  PAID:      '已結帳',
  CANCELLED: '已取消',
}
const statusClass: Record<string, string> = {
  OPEN:      'bg-amber-100 text-amber-700',
  PAID:      'bg-emerald-100 text-emerald-700',
  CANCELLED: 'bg-slate-100 text-slate-500',
}

async function loadOrders() {
  if (!tableId.value) {
    errorMsg.value = 'URL 缺少 tableId 參數'
    loading.value = false
    return
  }
  try {
    const res = await api.get<Order[]>(`/orders/table/${tableId.value}`)
    orders.value = res.data
  } catch {
    errorMsg.value = '載入訂單失敗，請確認後端是否運行'
  } finally {
    loading.value = false
  }
}

onMounted(loadOrders)
</script>

<template>
  <main class="min-h-full bg-slate-50 pb-6">
    <!-- 頂部導覽 -->
    <header class="sticky top-0 z-10 bg-white shadow-sm">
      <div class="flex items-center gap-3 px-4 py-3">
        <button
          class="text-slate-500 hover:text-slate-800 text-lg"
          @click="router.push({ path: '/order', query: { table: tableNo } })"
        >
          ← 返回點餐
        </button>
        <div class="flex-1 text-center">
          <span class="font-semibold">我的訂單</span>
          <span class="ml-1 text-sm text-slate-400">桌號 {{ tableNo }}</span>
        </div>
        <!-- 重整 -->
        <button class="text-slate-400 hover:text-brand-600" @click="loadOrders">↻</button>
      </div>
      <!-- 取消錯誤提示 -->
      <div v-if="cancelError" class="bg-rose-100 text-rose-700 text-sm px-4 py-2">
        {{ cancelError }}
      </div>
    </header>

    <!-- loading -->
    <div v-if="loading" class="flex justify-center py-16 text-slate-400">載入中...</div>

    <!-- 錯誤 -->
    <div v-else-if="errorMsg" class="mx-4 mt-6 card text-rose-600 text-sm">{{ errorMsg }}</div>

    <!-- 無訂單 -->
    <div v-else-if="!orders.length" class="flex flex-col items-center justify-center py-20 text-slate-400 gap-2">
      <span class="text-5xl">🍽️</span>
      <p>尚未送出任何訂單</p>
      <button
        class="btn-primary mt-2"
        @click="router.push({ path: '/order', query: { table: tableNo } })"
      >
        去點餐
      </button>
    </div>

    <!-- 訂單列表 -->
    <template v-else>
      <!-- 全桌合計卡 -->
      <div class="mx-4 mt-4 card bg-brand-50 border border-brand-100">
        <div class="flex justify-between items-center">
          <div>
            <div class="text-xs text-brand-600 font-medium">本桌累計</div>
            <div class="text-2xl font-bold text-brand-700">NT$ {{ grandTotal }}</div>
          </div>
          <div class="text-right text-sm text-slate-500">
            <div>{{ orders.length }} 筆訂單</div>
            <div>共 {{ grandItems }} 道</div>
          </div>
        </div>
      </div>

      <!-- 每筆訂單 -->
      <section
        v-for="order in orders"
        :key="order.OrderID"
        class="mx-4 mt-3 card space-y-3"
      >
        <!-- 訂單標題列 -->
        <div class="flex items-start justify-between gap-2">
          <div>
            <div class="font-semibold text-sm">{{ order.OrderNo }}</div>
            <div class="text-xs text-slate-400 mt-0.5">
              送出時間：{{ order.AddDate || '—' }}
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <!-- 取消按鈕：只有 OPEN + 時間內才出現 -->
            <button
              v-if="isCancellable(order)"
              class="text-xs text-rose-500 border border-rose-200 rounded-full px-3 py-1 hover:bg-rose-50 disabled:opacity-50"
              :disabled="cancellingId === order.OrderID"
              @click="cancelOrder(order)"
            >
              {{ cancellingId === order.OrderID ? '取消中...' : '取消訂單' }}
            </button>
            <span
              class="text-xs px-2 py-1 rounded-full font-medium"
              :class="statusClass[order.OrderStatus] ?? 'bg-slate-100 text-slate-500'"
            >
              {{ statusLabel[order.OrderStatus] ?? order.OrderStatus }}
            </span>
          </div>
        </div>

        <!-- 明細列表 -->
        <div class="divide-y divide-slate-100">
          <div
            v-for="d in order.details"
            :key="d.FoodID + '-' + d.Nickname"
            class="py-2 flex items-center justify-between text-sm"
          >
            <div class="flex-1">
              <span class="font-medium">{{ d.FoodName }}</span>
              <span class="ml-1 text-slate-400">× {{ d.Quantity }}</span>
              <!-- 點餐人 / 備註 -->
              <div v-if="d.Nickname || d.Note" class="text-xs text-slate-400 mt-0.5">
                <span v-if="d.Nickname">👤 {{ d.Nickname }}</span>
                <span v-if="d.Note" class="ml-1">／ {{ d.Note }}</span>
              </div>
            </div>
            <div class="text-right text-slate-700 font-medium">
              NT$ {{ d.Subtotal }}
            </div>
          </div>
        </div>

        <!-- 金額小計 -->
        <div class="pt-1 space-y-0.5 text-sm text-slate-600 border-t border-slate-100">
          <div class="flex justify-between">
            <span>餐點小計</span>
            <span>NT$ {{ order.SubTotal }}</span>
          </div>
          <div v-if="Number(order.ServiceFee) > 0" class="flex justify-between">
            <span>服務費</span>
            <span>NT$ {{ order.ServiceFee }}</span>
          </div>
          <div class="flex justify-between font-bold text-slate-900 pt-1">
            <span>合計</span>
            <span>NT$ {{ order.TotalAmount }}</span>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>
