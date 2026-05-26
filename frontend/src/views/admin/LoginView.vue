<script setup lang="ts">
/**
 * 後台登入頁
 *
 * 流程：
 *  1. 使用者輸入帳號密碼 → 呼叫 auth store 的 login()
 *  2. 成功 → 導向 ?next= 帶來的目標頁，沒有就去 /admin/dashboard
 *  3. 失敗 → 顯示錯誤訊息（不告知是帳號錯還是密碼錯，避免被列舉）
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function onSubmit() {
  error.value = ''
  submitting.value = true
  try {
    await auth.login(username.value, password.value)
    const next = typeof route.query.next === 'string' ? route.query.next : '/admin/dashboard'
    router.replace(next)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '登入失敗，請稍後再試'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="min-h-screen flex items-center justify-center bg-slate-100 p-6">
    <form
      class="w-full max-w-sm bg-white rounded-2xl shadow p-8 space-y-5"
      @submit.prevent="onSubmit"
    >
      <div class="text-center space-y-1">
        <div class="text-4xl">🔐</div>
        <h1 class="text-xl font-bold text-slate-800">店家後台登入</h1>
        <p class="text-xs text-slate-400">請輸入管理員帳號密碼</p>
      </div>

      <div class="space-y-1">
        <label class="text-sm text-slate-600">帳號</label>
        <input
          v-model="username"
          type="text"
          autocomplete="username"
          required
          class="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-300"
        />
      </div>

      <div class="space-y-1">
        <label class="text-sm text-slate-600">密碼</label>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          class="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-300"
        />
      </div>

      <p v-if="error" class="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
        {{ error }}
      </p>

      <button
        type="submit"
        :disabled="submitting"
        class="w-full btn-primary disabled:opacity-50"
      >
        {{ submitting ? '登入中…' : '登入' }}
      </button>

      <p class="text-xs text-slate-400 text-center">
        關閉瀏覽器後將自動登出，再次使用需重新登入。
      </p>
    </form>
  </main>
</template>
