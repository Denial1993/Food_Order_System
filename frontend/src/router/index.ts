import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getToken } from '@/api/client'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  // 顧客端 (Mobile)
  {
    path: '/order',
    name: 'order',
    component: () => import('@/views/customer/OrderView.vue'),
  },
  {
    path: '/my-orders',
    name: 'my-orders',
    component: () => import('@/views/customer/MyOrdersView.vue'),
  },
  // 後台登入頁（meta.public = true 表示不用登入也能進）
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('@/views/admin/LoginView.vue'),
    meta: { public: true },
  },
  // 店家後台 (Tablet/Desktop) — 需要登入
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardView.vue') },
      { path: 'tables', name: 'admin-tables', component: () => import('@/views/admin/TablesView.vue') },
      { path: 'foods', name: 'admin-foods', component: () => import('@/views/admin/FoodsView.vue') },
      { path: 'orders', name: 'admin-orders', component: () => import('@/views/admin/OrdersView.vue') },
      { path: 'config', name: 'admin-config', component: () => import('@/views/admin/SystemConfigView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 全域路由守衛
 *
 * 規則：
 *  - 沒 token → 進 requiresAuth 路由直接踢回登入頁，原本要去的網址用 ?next= 帶過去
 *  - 有 token 但 store 沒 user（剛重整頁面）→ 先呼叫 /auth/me 補資料
 *  - 已登入又跑去登入頁 → 自動導到 dashboard
 */
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const hasToken = !!getToken()

  // 已登入用戶不該再看到登入頁
  if (to.name === 'admin-login' && hasToken && auth.user) {
    return { path: '/admin/dashboard' }
  }

  if (!to.meta.requiresAuth) return true

  if (!hasToken) {
    return { name: 'admin-login', query: { next: to.fullPath } }
  }

  // 有 token 但記憶體裡沒 user：剛重整頁面，回頭跟後端確認
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      // token 失效 → 401 interceptor 已經幫忙清掉 token 並 redirect
      return { name: 'admin-login', query: { next: to.fullPath } }
    }
  }

  return true
})

export default router
