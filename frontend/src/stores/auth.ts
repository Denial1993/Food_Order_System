/**
 * 後台登入狀態：JWT + 使用者資訊
 *
 * Token 存在 sessionStorage（關瀏覽器就清空，下次重開要再登入一次）。
 * user 物件存在 Pinia 記憶體：頁面重整後會消失，
 * 但我們在 router 守衛裡會用 token 呼叫 /auth/me 重新撈一次。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { clearToken, getToken, setToken } from '@/api/client'

export interface AdminUser {
  UserID: number
  Account: string
  UserName: string
  UserType: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AdminUser | null>(null)
  const isLoading = ref(false)

  const isLoggedIn = computed(() => !!user.value && !!getToken())

  async function login(username: string, password: string): Promise<void> {
    // OAuth2 標準是 form-urlencoded，不是 JSON
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)

    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })

    setToken(data.access_token)
    user.value = data.user
  }

  /**
   * 用既有 token 換目前使用者資料。
   * 場景：使用者按 F5 重整 → store 清空但 sessionStorage 還有 token，
   * 透過這個方法把 user 補回來；token 失效會丟出例外。
   */
  async function fetchMe(): Promise<void> {
    if (!getToken()) {
      user.value = null
      return
    }
    isLoading.value = true
    try {
      const { data } = await api.get('/auth/me')
      user.value = data
    } finally {
      isLoading.value = false
    }
  }

  function logout(): void {
    clearToken()
    user.value = null
  }

  return { user, isLoading, isLoggedIn, login, fetchMe, logout }
})
