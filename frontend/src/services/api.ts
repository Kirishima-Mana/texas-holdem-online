import axios from 'axios'
import type { AuthResponse, RoomInfo } from '@/types/game'
import { useAuthStore } from '@/stores/auth'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：添加认证令牌
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    const token = authStore.getAccessToken()
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // 未授权，清除认证状态
      const authStore = useAuthStore()
      authStore.logout()
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

export const api = {
  // 认证相关
  register: (username: string, password: string) => {
    return apiClient.post<AuthResponse>('/api/auth/register', {
      username,
      password,
    })
  },
  
  login: (username: string, password: string) => {
    return apiClient.post<AuthResponse>('/api/auth/login', {
      username,
      password,
    })
  },
  
  // 房间相关
  getRoomInfo: () => {
    return apiClient.get<{ room: RoomInfo }>('/api/room/info')
  },
  
  // 健康检查
  healthCheck: () => {
    return apiClient.get('/health')
  },
}