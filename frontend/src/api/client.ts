import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('food.token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export default api
