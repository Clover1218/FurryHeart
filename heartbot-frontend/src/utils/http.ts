import axios from 'axios'
import { getToken } from './token'

// 主应用 HTTP 实例
export const http = axios.create({
  baseURL: '/api',
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

// 请求拦截器 - 添加 Authorization 头部
http.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

http.interceptors.response.use(
  (response) => {
    const res = response.data

    // 🔥 统一业务错误处理
    if (res.code !== 0) {
      console.error('[API ERROR]', res.message)

      return Promise.reject({
        code: res.code,
        message: res.message,
        data: res.data
      })
    }

    // ✅ 成功时只返回 data（关键优化点）
    return res.data
  },
  (error) => {
    console.error('[NETWORK ERROR]', error.message)
    return Promise.reject(error)
  }
)
export default http