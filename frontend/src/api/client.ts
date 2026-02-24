import axios from 'axios'

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
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      const currentPath = window.location.hash
      if (currentPath !== '#/login') {
        window.location.href = '/#/login'
      }
    }
    // Normalize error message
    const msg = error.response?.data?.message || error.response?.data?.detail || '请求失败'
    error.displayMessage = msg
    return Promise.reject(error)
  }
)

export { apiClient }