/**
 * axios 实例 + CSRF + 错误处理。对照 Spring `RestTemplate` interceptors。
 *
 * - withCredentials=true：跨端口（5173 → 5000）发 session cookie。
 * - CSRF：启动调 /api/auth/csrf-token 拿 token；写操作请求头加 X-CSRFToken。
 * - 错误：401 → 强制登出 + 跳登录页；其余抛给调用方，配合 Element Plus 提示。
 */
import axios, { AxiosError, type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'

let csrfToken = ''

export const http: AxiosInstance = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 10000,
})

http.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (['post', 'put', 'patch', 'delete'].includes(method) && csrfToken) {
    config.headers = config.headers ?? {}
    ;(config.headers as Record<string, string>)['X-CSRFToken'] = csrfToken
  }
  return config
})

http.interceptors.response.use(
  (resp) => {
    const token = resp.headers['x-csrftoken']
    if (typeof token === 'string' && token) csrfToken = token
    return resp
  },
  (err: AxiosError<{ error?: string; details?: unknown }>) => {
    const status = err.response?.status
    const code = err.response?.data?.error

    if (status === 401) {
      // 路由守卫负责跳转；这里只清状态、给提示
      if (code !== 'unauthorized') ElMessage.error('请先登录')
    } else if (status === 403) {
      ElMessage.error(code === 'forbidden' ? '没有权限' : code || '操作被拒绝')
    } else if (status && status >= 500) {
      ElMessage.error('服务器异常，请稍后再试')
    } else if (code) {
      // 业务错误：交给页面决定要不要再 toast，这里不重复
    }
    return Promise.reject(err)
  },
)

export async function fetchCsrfToken(): Promise<void> {
  const resp = await http.get<{ csrf_token: string }>('/auth/csrf-token')
  csrfToken = resp.data.csrf_token
}

export function getCsrfToken(): string {
  return csrfToken
}
