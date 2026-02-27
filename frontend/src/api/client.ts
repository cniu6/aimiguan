import axios from 'axios'
import { toast } from 'vue-sonner'

const DEFAULT_REQUEST_ERROR = '请求失败'
const DEFAULT_UNAUTHORIZED_MESSAGE = '登录状态已失效，请重新登录'

let isHandlingUnauthorized = false

const extractMessage = (value: unknown): string | null => {
  if (typeof value === 'string' && value.trim()) {
    return value
  }

  if (!value || typeof value !== 'object') {
    return null
  }

  const record = value as Record<string, unknown>
  const message = record.message
  if (typeof message === 'string' && message.trim()) {
    return message
  }

  const detail = record.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (detail && typeof detail === 'object') {
    const detailRecord = detail as Record<string, unknown>
    const nestedMessage = detailRecord.message
    if (typeof nestedMessage === 'string' && nestedMessage.trim()) {
      return nestedMessage
    }
  }

  return null
}

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    const data = response.data
    // If wrapped in {code, message, data} format, unwrap
    if (data && typeof data === 'object' && 'code' in data && 'data' in data) {
      if (data.code !== 0) {
        return Promise.reject({ response: { data, status: response.status } })
      }
      return data.data
    }
    // Direct response (e.g. login returns TokenResponse directly)
    return data
  },
  (error) => {
    const responseData = error.response?.data
    const displayMessage = extractMessage(responseData) || DEFAULT_REQUEST_ERROR

    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')

      const currentPath = window.location.hash
      if (!isHandlingUnauthorized && currentPath !== '#/login') {
        isHandlingUnauthorized = true
        toast.warning(extractMessage(responseData) || DEFAULT_UNAUTHORIZED_MESSAGE, {
          duration: 1200,
        })

        window.setTimeout(() => {
          if (window.location.hash !== '#/login') {
            window.location.hash = '#/login'
          }
          isHandlingUnauthorized = false
        }, 1200)
      }
    }

    // Normalize error message
    error.displayMessage =
      error.response?.status === 401
        ? extractMessage(responseData) || DEFAULT_UNAUTHORIZED_MESSAGE
        : displayMessage

    return Promise.reject(error)
  }
)

export { apiClient }
