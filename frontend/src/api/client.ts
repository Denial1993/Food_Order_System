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

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('food.token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export default api
