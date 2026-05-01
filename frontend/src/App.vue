<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { wsService } from './services/websocket'

// 初始化
onMounted(() => {
  // 检查是否有已保存的认证信息，尝试自动重连
  const authStore = useAuthStore()
  
  if (authStore.isAuthenticated) {
    // 尝试重新连接WebSocket
    wsService.connect().catch(console.error)
  }
})
</script>