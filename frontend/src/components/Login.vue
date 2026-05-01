<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-900">
    <div class="card w-full max-w-md">
      <h1 class="text-3xl font-bold text-center mb-8 text-poker-gold">
        德州扑克在线
      </h1>
      
      <div class="mb-6">
        <div class="flex border-b border-gray-700">
          <button
            @click="activeTab = 'login'"
            :class="[
              'flex-1 py-3 font-medium',
              activeTab === 'login'
                ? 'text-poker-green border-b-2 border-poker-green'
                : 'text-gray-400 hover:text-gray-300'
            ]"
          >
            登录
          </button>
          <button
            @click="activeTab = 'register'"
            :class="[
              'flex-1 py-3 font-medium',
              activeTab === 'register'
                ? 'text-poker-green border-b-2 border-poker-green'
                : 'text-gray-400 hover:text-gray-300'
            ]"
          >
            注册
          </button>
        </div>
      </div>

      <!-- 登录表单 -->
      <form v-if="activeTab === 'login'" @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label for="login-username" class="block text-sm font-medium text-gray-300 mb-1">
            用户名
          </label>
          <input
            id="login-username"
            v-model="loginForm.username"
            type="text"
            required
            class="input w-full"
            placeholder="请输入用户名"
          />
        </div>
        
        <div>
          <label for="login-password" class="block text-sm font-medium text-gray-300 mb-1">
            密码
          </label>
          <input
            id="login-password"
            v-model="loginForm.password"
            type="password"
            required
            class="input w-full"
            placeholder="请输入密码"
          />
        </div>
        
        <div v-if="loginError" class="p-3 bg-red-900/50 border border-red-700 rounded-lg">
          <p class="text-red-300 text-sm">{{ loginError }}</p>
        </div>
        
        <button
          type="submit"
          :disabled="isLoggingIn"
          class="btn btn-primary w-full py-3"
        >
          <span v-if="isLoggingIn">登录中...</span>
          <span v-else>登录</span>
        </button>
      </form>

      <!-- 注册表单 -->
      <form v-else @submit.prevent="handleRegister" class="space-y-4">
        <div>
          <label for="register-username" class="block text-sm font-medium text-gray-300 mb-1">
            用户名
          </label>
          <input
            id="register-username"
            v-model="registerForm.username"
            type="text"
            required
            class="input w-full"
            placeholder="请输入用户名"
          />
        </div>
        
        <div>
          <label for="register-password" class="block text-sm font-medium text-gray-300 mb-1">
            密码
          </label>
          <input
            id="register-password"
            v-model="registerForm.password"
            type="password"
            required
            class="input w-full"
            placeholder="请输入密码"
          />
        </div>
        
        <div>
          <label for="register-confirm" class="block text-sm font-medium text-gray-300 mb-1">
            确认密码
          </label>
          <input
            id="register-confirm"
            v-model="registerForm.confirmPassword"
            type="password"
            required
            class="input w-full"
            placeholder="请再次输入密码"
          />
        </div>
        
        <div v-if="registerError" class="p-3 bg-red-900/50 border border-red-700 rounded-lg">
          <p class="text-red-300 text-sm">{{ registerError }}</p>
        </div>
        
        <button
          type="submit"
          :disabled="isRegistering"
          class="btn btn-primary w-full py-3"
        >
          <span v-if="isRegistering">注册中...</span>
          <span v-else>注册</span>
        </button>
      </form>

      <div class="mt-6 text-center text-gray-400 text-sm">
        <p>这是一个私人德州扑克游戏房间，仅供好友娱乐使用。</p>
        <p class="mt-2">请妥善保管您的账号密码。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { wsService } from '@/services/websocket'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref<'login' | 'register'>('login')

// 登录表单
const loginForm = reactive({
  username: '',
  password: ''
})
const isLoggingIn = ref(false)
const loginError = ref('')

// 注册表单
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})
const isRegistering = ref(false)
const registerError = ref('')

const handleLogin = async () => {
  if (!loginForm.username.trim() || !loginForm.password.trim()) {
    loginError.value = '请输入用户名和密码'
    return
  }

  isLoggingIn.value = true
  loginError.value = ''

  try {
    const result = await authStore.login(loginForm.username, loginForm.password)
    
    if (result.success) {
      // 连接WebSocket
      await wsService.connect()
      // 跳转到大厅
      router.push('/lobby')
    } else {
      loginError.value = result.error || '登录失败'
    }
  } catch (error: any) {
    loginError.value = error.message || '登录失败，请检查网络连接'
  } finally {
    isLoggingIn.value = false
  }
}

const handleRegister = async () => {
  // 验证表单
  if (!registerForm.username.trim()) {
    registerError.value = '请输入用户名'
    return
  }
  
  if (registerForm.username.length < 3 || registerForm.username.length > 20) {
    registerError.value = '用户名长度应为3-20个字符'
    return
  }
  
  if (!registerForm.password.trim()) {
    registerError.value = '请输入密码'
    return
  }
  
  if (registerForm.password.length < 6) {
    registerError.value = '密码长度至少为6个字符'
    return
  }
  
  if (registerForm.password !== registerForm.confirmPassword) {
    registerError.value = '两次输入的密码不一致'
    return
  }

  isRegistering.value = true
  registerError.value = ''

  try {
    const result = await authStore.register(registerForm.username, registerForm.password)
    
    if (result.success) {
      // 连接WebSocket
      await wsService.connect()
      // 跳转到大厅
      router.push('/lobby')
    } else {
      registerError.value = result.error || '注册失败'
    }
  } catch (error: any) {
    registerError.value = error.message || '注册失败，请检查网络连接'
  } finally {
    isRegistering.value = false
  }
}
</script>