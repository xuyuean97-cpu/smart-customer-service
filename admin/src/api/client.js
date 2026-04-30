import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const client = axios.create({
  baseURL: '/',
  timeout: 30000,
})

// 请求拦截器 — 自动附加 JWT Token
client.interceptors.request.use(config => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// 响应拦截器 — 401 跳转登录
client.interceptors.response.use(
  resp => resp,
  error => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
    }
    ElMessage.error(error.response?.data?.detail || error.message)
    return Promise.reject(error)
  }
)

export default client
