<script setup lang="ts">
/**
 * 顧客端點餐畫面 (Mobile-First RWD)。
 * 規格書對應:
 *  - 掃碼後從 URL ?table= 取得桌號
 *  - 暱稱優先讀 LocalStorage,新顧客需輸入後存入
 *  - WebSocket 連線至 /ws/table/{TableID} 接收同桌共用購物車
 *  - 桌況為 IDLE 時提示「請通知店員開桌」(防呆機制)
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { useCustomerStore } from '@/stores/customer'

// 送單結果型別
interface OrderResult {
  OrderID: number
  OrderNo: string
  SubTotal: number
  ServiceFee: number
  TotalAmount: number
}

interface Food {
  FoodID: number
  FoodName: string
  Price: number
  CategoryID: number | null
  picture?: { PicturePath: string } | null
}
interface Category {
  CategoryID: number
  CategoryName: string
}
interface TableInfo {
  TableID: number
  TableNo: string
  TableStatus: 'IDLE' | 'ORDERING' | 'CLEANING'
}

const route  = useRoute()
const router = useRouter()
const customer = useCustomerStore()

const tableNo = computed(() => String(route.query.table ?? ''))
const table = ref<TableInfo | null>(null)
const categories = ref<Category[]>([])
const foods = ref<Food[]>([])
const activeCat = ref<number | null>(null)
const cart = ref<Record<number, number>>({})
const nicknameInput = ref(customer.nickname)
const askNickname = computed(() => !customer.nickname)
let ws: WebSocket | null = null

// 送單狀態
const submitting = ref(false)
const orderResult = ref<OrderResult | null>(null)   // 送單成功後的訂單資訊
const submitError = ref('')                          // 送單失敗訊息

const filteredFoods = computed(() =>
  activeCat.value === null ? foods.value : foods.value.filter((f) => f.CategoryID === activeCat.value),
)
const cartTotal = computed(() =>
  foods.value.reduce((sum, f) => sum + (cart.value[f.FoodID] ?? 0) * Number(f.Price), 0),
)

async function loadAll() {
  if (!tableNo.value) return
  try {
    const [t, c, f] = await Promise.all([
      api.get<TableInfo>(`/tables/${tableNo.value}`),
      api.get<Category[]>('/menu/categories'),
      api.get<Food[]>('/menu/foods'),
    ])
    table.value = t.data
    categories.value = c.data
    foods.value = f.data
  } catch {
    /* 後端尚未啟動時不影響畫面 */
  }
}

function connectWs() {
  if (!table.value) return
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/table/${table.value.TableID}?nickname=${encodeURIComponent(customer.nickname || 'guest')}`
  ws = new WebSocket(url)
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.type === 'CART_SYNC' && msg.payload?.cart) {
      cart.value = msg.payload.cart
    }
  }
}

function addToCart(food: Food) {
  cart.value = { ...cart.value, [food.FoodID]: (cart.value[food.FoodID] ?? 0) + 1 }
  ws?.send(JSON.stringify({ type: 'CART_SYNC', payload: { cart: cart.value } }))
}

function confirmNickname() {
  customer.setNickname(nicknameInput.value)
  connectWs()
}

async function submitOrder() {
  if (!cartTotal.value || !table.value || submitting.value) return
  submitting.value = true
  submitError.value = ''

  // 把 cart (Record<FoodID, qty>) 轉成後端要的格式
  const cartItems = Object.entries(cart.value)
    .filter(([, qty]) => qty > 0)
    .map(([foodId, qty]) => ({
      food_id: Number(foodId),
      quantity: qty,
      nickname: customer.nickname || 'guest',
    }))

  try {
    const res = await api.post<OrderResult>(
      `/orders/submit/${table.value.TableID}`,
      { cart: cartItems, nickname: customer.nickname || 'guest' },
    )
    orderResult.value = res.data
    cart.value = {}   // 清空購物車
    // 通知同桌購物車已清空
    ws?.send(JSON.stringify({ type: 'CART_SYNC', payload: { cart: {} } }))
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })
      ?.response?.data?.detail
    submitError.value = msg || '送單失敗，請再試一次'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadAll()
  if (customer.nickname) connectWs()
})
onBeforeUnmount(() => ws?.close())
</script>

<template>
  <main class="min-h-full flex flex-col bg-slate-50">
    <!-- 暱稱輸入彈窗 -->
    <div v-if="askNickname" class="fixed inset-0 bg-black/40 flex items-center justify-center p-6 z-30">
      <div class="card w-full max-w-sm space-y-4">
        <h2 class="text-lg font-semibold">歡迎光臨 桌號 {{ tableNo }}</h2>
        <p class="text-sm text-slate-500">請輸入暱稱,方便同桌夥伴看到誰點了什麼</p>
        <input
          v-model="nicknameInput"
          class="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="例如:Daniel_丹丹"
        />
        <button class="btn-primary w-full" :disabled="!nicknameInput.trim()" @click="confirmNickname">開始點餐</button>
      </div>
    </div>

    <!-- 標題列 -->
    <header class="sticky top-0 z-10 bg-white shadow-sm">
      <div class="px-4 py-3 flex items-center justify-between">
        <div>
          <div class="text-xs text-slate-400">桌號</div>
          <div class="font-semibold">{{ tableNo || '—' }}</div>
        </div>
        <div class="flex items-center gap-3">
          <!-- 我的訂單入口 -->
          <button
            v-if="table"
            class="text-xs text-brand-600 border border-brand-200 rounded-full px-3 py-1 hover:bg-brand-50"
            @click="router.push({ path: '/my-orders', query: { table: tableNo, tableId: table.TableID } })"
          >
            訂單查詢
          </button>
          <div class="text-sm text-slate-600">Hi, {{ customer.nickname || '—' }}</div>
        </div>
      </div>
      <!-- 桌況防呆提示 -->
      <div v-if="table?.TableStatus === 'IDLE'" class="bg-amber-100 text-amber-800 text-sm px-4 py-2">
        ⚠️ 此桌尚未開桌,請通知店員協助開桌後即可點餐
      </div>
      <div v-else-if="table?.TableStatus === 'CLEANING'" class="bg-rose-100 text-rose-800 text-sm px-4 py-2">
        ⚠️ 此桌結帳後連結已失效
      </div>

      <!-- 分類 tabs -->
      <nav class="flex gap-2 overflow-x-auto px-4 py-2 border-t border-slate-100">
        <button
          class="px-3 py-1.5 rounded-full text-sm whitespace-nowrap"
          :class="activeCat === null ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'"
          @click="activeCat = null"
        >
          全部
        </button>
        <button
          v-for="c in categories"
          :key="c.CategoryID"
          class="px-3 py-1.5 rounded-full text-sm whitespace-nowrap"
          :class="activeCat === c.CategoryID ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'"
          @click="activeCat = c.CategoryID"
        >
          {{ c.CategoryName }}
        </button>
      </nav>
    </header>

    <!-- 餐點列表 -->
    <section class="flex-1 px-4 py-3 space-y-3 pb-32">
      <div v-if="!foods.length" class="card text-center text-slate-500">尚未載入餐點 (後端未啟動?)</div>
      <article v-for="f in filteredFoods" :key="f.FoodID" class="card flex items-center gap-3">
        <img
          v-if="f.picture"
          :src="f.picture.PicturePath"
          :alt="f.FoodName"
          class="w-20 h-20 rounded-xl object-cover bg-slate-100"
        />
        <div v-else class="w-20 h-20 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400 text-xs">
          無圖
        </div>
        <div class="flex-1">
          <div class="font-medium">{{ f.FoodName }}</div>
          <div class="text-brand-600 font-semibold">NT$ {{ f.Price }}</div>
        </div>
        <button class="btn-primary text-sm" :disabled="table?.TableStatus !== 'ORDERING'" @click="addToCart(f)">
          +
        </button>
      </article>
    </section>

    <!-- 送單成功彈窗 -->
    <div v-if="orderResult" class="fixed inset-0 bg-black/50 flex items-center justify-center p-6 z-40">
      <div class="card w-full max-w-sm space-y-4 text-center">
        <div class="text-4xl">🎉</div>
        <h2 class="text-xl font-bold text-brand-600">訂單已送出！</h2>
        <div class="text-sm text-slate-600 space-y-1">
          <p>訂單編號：<span class="font-mono font-semibold">{{ orderResult.OrderNo }}</span></p>
          <p>餐點小計：NT$ {{ orderResult.SubTotal }}</p>
          <p v-if="orderResult.ServiceFee > 0">服務費：NT$ {{ orderResult.ServiceFee }}</p>
          <p class="text-lg font-bold text-slate-900 pt-1">合計：NT$ {{ orderResult.TotalAmount }}</p>
        </div>
        <p class="text-xs text-slate-400">請稍候，餐點準備中...</p>
        <div class="flex flex-col gap-2">
          <button
            class="btn-primary w-full"
            @click="router.push({ path: '/my-orders', query: { table: tableNo, tableId: table?.TableID } })"
          >
            查看訂單明細
          </button>
          <button class="btn-ghost w-full" @click="orderResult = null">繼續瀏覽 / 加點</button>
        </div>
      </div>
    </div>

    <!-- 送單錯誤提示 -->
    <div
      v-if="submitError"
      class="fixed bottom-24 inset-x-4 bg-rose-600 text-white text-sm rounded-xl px-4 py-3 z-40 flex justify-between items-center"
    >
      <span>{{ submitError }}</span>
      <button class="ml-3 text-white/70 hover:text-white" @click="submitError = ''">✕</button>
    </div>

    <!-- 底部購物車摘要 -->
    <footer class="fixed bottom-0 inset-x-0 bg-white border-t border-slate-200 p-3">
      <div class="flex items-center justify-between max-w-screen-md mx-auto">
        <div>
          <div class="text-xs text-slate-500">小計</div>
          <div class="text-xl font-bold">NT$ {{ cartTotal }}</div>
        </div>
        <!-- ✅ 修正：補上 @click，加入 loading 狀態 -->
        <button
          class="btn-primary min-w-24"
          :disabled="!cartTotal || submitting"
          @click="submitOrder"
        >
          <span v-if="submitting">送出中...</span>
          <span v-else>送出訂單</span>
        </button>
      </div>
    </footer>
  </main>
</template>
