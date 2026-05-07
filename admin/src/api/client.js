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

// 响应拦截器 — 解包统一格式 + 401 跳转
// 兼容两种: {code:0, message, data} (api/response.py) 和 {ret_code, ret_msg, data} (memory API)
client.interceptors.response.use(
  resp => {
    const d = resp.data
    if (!d || typeof d !== 'object') return resp
    // 格式1: {code: 0, message: "ok", data: {...}}
    if (typeof d.code === 'number' && 'data' in d) {
      if (d.code !== 0) {
        ElMessage.error(d.message || '请求失败')
        return Promise.reject(new Error(d.message || '请求失败'))
      }
      resp.data = d.data
    }
    // 格式2: {ret_code: "000000", ret_msg: "success", data: {...}}
    else if (typeof d.ret_code === 'string' && 'data' in d) {
      if (d.ret_code !== '000000') {
        ElMessage.error(d.ret_msg || '请求失败')
        return Promise.reject(new Error(d.ret_msg || '请求失败'))
      }
      resp.data = d.data
    }
    return resp
  },
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
