<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const nav = [
  { to: '/admin/dashboard', label: '儀表板', icon: '📊' },
  { to: '/admin/tables', label: '桌位管理', icon: '🪑' },
  { to: '/admin/foods', label: '餐點管理', icon: '🍱' },
  { to: '/admin/orders', label: '訂單列表', icon: '📋' },
  { to: '/admin/config', label: '系統參數', icon: '⚙️' },
]

const auth = useAuthStore()
const router = useRouter()

function onLogout() {
  auth.logout()
  router.replace({ name: 'admin-login' })
}
</script>

<template>
  <div class="min-h-full flex bg-slate-100">
    <aside class="w-56 bg-white border-r border-slate-200 hidden md:flex md:flex-col">
      <div class="px-4 py-4 border-b border-slate-100">
        <div class="font-bold text-brand-600">Food Admin</div>
        <div class="text-xs text-slate-400">店家後台</div>
      </div>
      <nav class="flex-1 py-2">
        <RouterLink
          v-for="n in nav"
          :key="n.to"
          :to="n.to"
          class="flex items-center gap-2 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
          active-class="bg-brand-50 text-brand-700 font-medium"
        >
          <span>{{ n.icon }}</span>
          <span>{{ n.label }}</span>
        </RouterLink>
      </nav>

      <!-- 登入者資訊 + 登出 -->
      <div class="border-t border-slate-100 px-4 py-3 space-y-2">
        <div class="text-xs text-slate-400">目前登入</div>
        <div class="text-sm font-medium text-slate-700 truncate">
          {{ auth.user?.UserName || auth.user?.Account || '—' }}
        </div>
        <button
          type="button"
          class="w-full text-xs text-slate-500 hover:text-red-600 border border-slate-200 hover:border-red-200 rounded px-2 py-1.5 transition-colors"
          @click="onLogout"
        >
          登出
        </button>
      </div>
    </aside>

    <main class="flex-1 p-6">
      <RouterView />
    </main>
  </div>
</template>
