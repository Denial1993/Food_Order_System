import axios from 'axios'

/**
 * API Base URL 決策：
 *
 * 開發環境：VITE_API_BASE_URL 沒設 → 用 '/api'，Vite dev server proxy 轉到 localhost:8000
 * 正式環境：Render 部署時在 Static Site 的環境變數填入
 *           VITE_API_BASE_URL=https://food-order-backend.onrender.com/api
 *           Vite build 時會把這個值直接編譯進 JS bundle
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

/**
 * Token 儲存位置：sessionStorage
 *
 * - localStorage：關瀏覽器後仍保留，下次打開不用重新登入。
 * - sessionStorage：分頁/視窗關閉就清空，下次開新分頁必須重新登入。
 *
 * 後台是敏感操作（改菜單、看營收），採用 sessionStorage 比較安全；
 * 顧客端的暱稱仍走 localStorage（在 stores/customer.ts），不受影響。
 */
export const TOKEN_KEY = 'food.token'

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

api.interceptors.request.use((cfg) => {
  const token = getToken()
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

/**
 * 401 攔截：token 過期或被踢出 → 自動清掉並導去登入頁
 *
 * 為什麼用 window.location 而不是 vue-router？
 * 這個檔不該依賴 router 實例（會循環 import），
 * 而且強制整頁 reload 也能順便重置所有 Pinia store，更乾淨。
 */
api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err?.response?.status === 401) {
      clearToken()
      // 只在「不是已經在登入頁」的時候才導向，避免無窮循環
      if (!window.location.pathname.startsWith('/admin/login')) {
        const next = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.assign(`/admin/login?next=${next}`)
      }
    }
    return Promise.reject(err)
  },
)

export default api
