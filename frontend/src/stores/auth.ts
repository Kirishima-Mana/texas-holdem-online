import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, Token } from '@/types/game'
import { api } from '@/services/api'

interface AuthState {
  user: User | null
  token: Token | null
  isAuthenticated: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<Token | null>(null)
  const isAuthenticated = computed(() => !!user.value && !!token.value)

  // 从 localStorage 恢复状态
  const loadFromStorage = () => {
    const savedUser = localStorage.getItem('poker_user')
    const savedToken = localStorage.getItem('poker_token')
    
    if (savedUser && savedToken) {
      user.value = JSON.parse(savedUser)
      token.value = JSON.parse(savedToken)
    }
  }

  // 保存到 localStorage
  const saveToStorage = () => {
    if (user.value) {
      localStorage.setItem('poker_user', JSON.stringify(user.value))
    }
    if (token.value) {
      localStorage.setItem('poker_token', JSON.stringify(token.value))
    }
  }

  // 清除存储
  const clearStorage = () => {
    localStorage.removeItem('poker_user')
    localStorage.removeItem('poker_token')
    user.value = null
    token.value = null
  }

  // 注册
  const register = async (username: string, password: string) => {
    try {
      const response = await api.register(username, password)
      
      if (response.success && response.data) {
        user.value = response.data.user
        token.value = response.data.token
        saveToStorage()
        return { success: true, data: response.data }
      } else {
        return { success: false, error: response.message || '注册失败' }
      }
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.error || '注册失败，请检查网络连接' 
      }
    }
  }

  // 登录
  const login = async (username: string, password: string) => {
    try {
      const response = await api.login(username, password)
      
      if (response.success && response.data) {
        user.value = response.data.user
        token.value = response.data.token
        saveToStorage()
        return { success: true, data: response.data }
      } else {
        return { success: false, error: response.message || '登录失败' }
      }
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.error || '登录失败，请检查用户名和密码' 
      }
    }
  }

  // 登出
  const logout = () => {
    clearStorage()
  }

  // 获取访问令牌
  const getAccessToken = () => {
    return token.value?.access_token || null
  }

  // 获取会话令牌
  const getSessionToken = () => {
    return token.value?.session_token || null
  }

  // 初始化
  loadFromStorage()

  return {
    user,
    token,
    isAuthenticated,
    register,
    login,
    logout,
    getAccessToken,
    getSessionToken
  }
})