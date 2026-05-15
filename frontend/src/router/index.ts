import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

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
  // 店家後台 (Tablet/Desktop)
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
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

export default router
