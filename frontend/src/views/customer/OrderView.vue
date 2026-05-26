<script setup lang="ts">
/**
 * 顧客端點餐畫面 (Mobile-First RWD)。
 *
 * 【點餐流程】
 *  1. 掃碼 → 從 URL ?table= 取得桌號
 *  2. 輸入暱稱（存 LocalStorage，下次不用再輸）
 *  3. 若桌子是 IDLE → 自動呼叫開桌 API → ORDERING（不需要等店員）
 *  4. 後端回傳 SessionToken → 存 localStorage（安全機制）
 *  5. 正常點餐、送單（送單時帶 SessionToken，後端驗證是否為本次入座）
 *
 * 【SessionToken 防護】
 *  下次新客人入座時，開桌 API 會產生新的 Token。
 *  舊截圖的顧客送單時帶的是舊 Token → 後端拒絕 → 無法亂點餐。
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

interface CategoryBrief {
  CategoryID:   number
  CategoryName: string
}
interface Food {
  FoodID:     number
  FoodName:   string
  FoodDesc:   string | null   // ← 餐點描述
  Price:      number
  categories: CategoryBrief[]   // ← 多對多，一道菜可屬於多個分類
  picture?:   { PicturePath: string } | null
}
interface Category {
  CategoryID: number
  CategoryName: string
}
interface TableInfo {
  TableID:      number
  TableNo:      string
  TableStatus:  'IDLE' | 'ORDERING' | 'CLEANING'
  SessionToken: string | null   // 後端回傳的 Session Token
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
const askNickname   = computed(() => !customer.nickname)
const opening       = ref(false)   // 自動開桌 API 呼叫中
let ws: WebSocket | null = null

// Session Token 的 localStorage key（每桌獨立存）
const sessionKey = computed(() => `food.session.table.${tableNo.value}`)

/** 取出目前存在 localStorage 的 session token */
function getLocalToken(): string | null {
  return localStorage.getItem(sessionKey.value)
}
/** 把從後端拿到的 token 存進 localStorage */
function saveToken(token: string | null) {
  if (token) localStorage.setItem(sessionKey.value, token)
  else       localStorage.removeItem(sessionKey.value)
}

// 付款方式
interface PaymentMethod { code: string; label: string }
const paymentMethods   = ref<PaymentMethod[]>([])
const showPaymentModal = ref(false)       // 控制付款方式選擇彈窗
const selectedPayment  = ref<string>('')  // 目前選到的付款方式 code

// 送單狀態
const submitting = ref(false)
const orderResult = ref<OrderResult | null>(null)   // 送單成功後的訂單資訊
const submitError = ref('')                          // 送單失敗訊息

const filteredFoods = computed(() => {
  if (activeCat.value === null) return foods.value
  // .some() = 只要任一分類符合就顯示（多對多過濾）
  // 例：招牌雞腿飯 categories=[熱門推薦, 主食]，點「主食」tab 也能看到它
  return foods.value.filter(f => f.categories.some(c => c.CategoryID === activeCat.value))
})
const cartTotal = computed(() =>
  foods.value.reduce((sum, f) => sum + (cart.value[f.FoodID] ?? 0) * Number(f.Price), 0),
)

async function loadAll() {
  if (!tableNo.value) return
  try {
    const [t, c, f, p] = await Promise.all([
      api.get<TableInfo>(`/tables/${tableNo.value}`),
      api.get<Category[]>('/menu/categories'),
      api.get<Food[]>('/menu/foods'),
      api.get<PaymentMethod[]>('/menu/payment-methods'),
    ])
    table.value          = t.data
    categories.value     = c.data
    foods.value          = f.data
    paymentMethods.value = p.data

    // 如果桌子已經是 ORDERING，且後端有 SessionToken，
    // 代表目前這桌已有人入座（可能是同桌其他人先開桌了）
    // 把 Token 存起來供後續送單使用
    if (t.data.SessionToken) {
      saveToken(t.data.SessionToken)
    }
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

/**
 * 顧客確認暱稱後：
 *  - 如果桌子是 IDLE → 自動呼叫開桌 API（不需要等店員！）
 *  - 開桌成功 → 後端回傳新 SessionToken → 存 localStorage
 *  - 然後連接 WebSocket 開始同步購物車
 */
async function confirmNickname() {
  if (!nicknameInput.value.trim()) return
  customer.setNickname(nicknameInput.value.trim())

  // 桌子是 IDLE → 自動開桌
  if (table.value?.TableStatus === 'IDLE') {
    opening.value = true
    try {
      const res = await api.post<TableInfo>(`/tables/${table.value.TableNo}/open`)
      // 更新本地桌況 + 儲存新 Token
      table.value = res.data
      saveToken(res.data.SessionToken)
    } catch {
      // 如果開桌失敗（可能有人搶先開了），重新拉一次桌況
      await loadAll()
    } finally {
      opening.value = false
    }
  }

  connectWs()
}

/** 點「送出訂單」→ 先開付款方式選擇視窗 */
function openPaymentModal() {
  if (!cartTotal.value || !table.value) return
  // 預設選第一個付款方式
  selectedPayment.value = paymentMethods.value[0]?.code ?? ''
  showPaymentModal.value = true
}

/** 顧客在付款視窗確認後，真正送出訂單 */
async function submitOrder() {
  if (!cartTotal.value || !table.value || submitting.value) return
  showPaymentModal.value = false
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
      {
        cart:           cartItems,
        nickname:       customer.nickname || 'guest',
        session_token:  getLocalToken(),       // 帶上 Token，後端驗證是否為本次入座
        payment_method: selectedPayment.value, // 顧客選的付款方式
      },
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
        <p class="text-sm text-slate-500">請輸入暱稱，方便同桌夥伴看到誰點了什麼</p>
        <input
          v-model="nicknameInput"
          class="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
          placeholder="例如：Daniel"
          @keyup.enter="confirmNickname"
        />
        <button
          class="btn-primary w-full"
          :disabled="!nicknameInput.trim() || opening"
          @click="confirmNickname"
        >
          <!-- 自動開桌中顯示 loading，避免顧客重複點擊 -->
          <span v-if="opening">開桌中...</span>
          <span v-else>開始點餐</span>
        </button>
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
      <!-- 桌況提示（CLEANING = 結帳後等待清潔，還不能點餐）-->
      <div v-if="table?.TableStatus === 'CLEANING'" class="bg-amber-100 text-amber-800 text-sm px-4 py-2 flex items-center gap-2">
        <span>🧹</span>
        <span>此桌正在清潔整理，請稍候。店員完成後即可掃碼入座點餐。</span>
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
        <div class="flex-1 min-w-0">
          <div class="font-medium">{{ f.FoodName }}</div>
          <div v-if="f.FoodDesc" class="text-xs text-slate-400 mt-0.5 leading-relaxed line-clamp-2">
            {{ f.FoodDesc }}
          </div>
          <div class="text-brand-600 font-semibold mt-1">NT$ {{ f.Price }}</div>
        </div>
        <button class="btn-primary text-sm" :disabled="table?.TableStatus !== 'ORDERING'" @click="addToCart(f)">
          +
        </button>
      </article>
    </section>

    <!-- 付款方式選擇彈窗 -->
    <div v-if="showPaymentModal" class="fixed inset-0 bg-black/50 flex items-center justify-center p-6 z-40">
      <div class="card w-full max-w-sm space-y-4">
        <h2 class="text-lg font-semibold">選擇付款方式</h2>
        <p class="text-sm text-slate-500">請選擇您要使用的結帳方式</p>

        <!-- 付款選項 -->
        <div class="space-y-2">
          <label
            v-for="pm in paymentMethods"
            :key="pm.code"
            class="flex items-center gap-3 border rounded-xl px-4 py-3 cursor-pointer transition"
            :class="selectedPayment === pm.code
              ? 'border-brand-500 bg-brand-50'
              : 'border-slate-200 hover:bg-slate-50'"
          >
            <input
              type="radio"
              :value="pm.code"
              v-model="selectedPayment"
              class="accent-brand-600"
            />
            <span class="font-medium">{{ pm.label }}</span>
          </label>
          <!-- 後台沒設定任何付款方式時的提示 -->
          <p v-if="!paymentMethods.length" class="text-sm text-slate-400 text-center py-2">
            目前無可用的付款方式，請聯繫店員
          </p>
        </div>

        <div class="flex gap-2 pt-1">
          <button class="btn-ghost flex-1" @click="showPaymentModal = false">取消</button>
          <button
            class="btn-primary flex-1"
            :disabled="!selectedPayment"
            @click="submitOrder"
          >
            確認送出
          </button>
        </div>
      </div>
    </div>

    <!-- 送單成功彈窗 -->
    <div v-if="orderResult" class="fixed inset-0 bg-black/50 flex items-center justify-center p-6 z-40">
      <div class="card w-full max-w-sm space-y-4 text-center">
        <div class="text-4xl">🎉</div>
        <h2 class="text-xl font-bold text-brand-600">訂單已送出！</h2>
        <div class="text-sm text-slate-600 space-y-1">
          <p>訂單編號：<span class="font-mono font-semibold">{{ orderResult.OrderNo }}</span></p>
          <p>餐點小計：NT$ {{ Math.round(Number(orderResult.SubTotal)) }}</p>
          <p v-if="Number(orderResult.ServiceFee) > 0">服務費：NT$ {{ Math.round(Number(orderResult.ServiceFee)) }}</p>
          <p class="text-lg font-bold text-slate-900 pt-1">合計：NT$ {{ Math.round(Number(orderResult.TotalAmount)) }}</p>
          <p v-if="selectedPayment" class="text-slate-500">
            付款方式：{{ paymentMethods.find(p => p.code === selectedPayment)?.label ?? selectedPayment }}
          </p>
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
        <button
          class="btn-primary min-w-24"
          :disabled="!cartTotal || submitting"
          @click="openPaymentModal"
        >
          <span v-if="submitting">送出中...</span>
          <span v-else>送出訂單</span>
        </button>
      </div>
    </footer>
  </main>
</template>
