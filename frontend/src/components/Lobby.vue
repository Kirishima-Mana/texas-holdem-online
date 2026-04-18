<template>
  <div class="min-h-screen bg-gray-900 p-4">
    <div class="max-w-6xl mx-auto">
      <!-- 顶部导航 -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-3xl font-bold text-poker-gold">德州扑克大厅</h1>
          <p class="text-gray-400 mt-1">欢迎，{{ authStore.user?.username }}</p>
        </div>
        
        <div class="flex items-center space-x-4">
          <div class="text-right">
            <div class="text-sm text-gray-400">房间状态</div>
            <div class="text-lg font-semibold">
              {{ roomInfo.player_count }}/{{ roomInfo.max_players }} 玩家
              <span class="text-gray-500">|</span>
              {{ roomInfo.spectator_count }} 旁观者
            </div>
          </div>
          
          <button
            @click="handleLogout"
            class="btn btn-secondary"
          >
            退出登录
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 左侧：牌桌信息 -->
        <div class="lg:col-span-2">
          <div class="card">
            <div class="flex justify-between items-center mb-6">
              <h2 class="text-2xl font-bold">牌桌</h2>
              
              <div class="flex items-center space-x-2">
                <div class="px-3 py-1 bg-gray-700 rounded-lg">
                  <span class="text-gray-300">盲注等级</span>
                  <span class="ml-2 font-bold text-poker-gold">{{ roomInfo.blind_level }}</span>
                </div>
                
                <div v-if="roomInfo.is_game_active" class="px-3 py-1 bg-red-900/50 rounded-lg">
                  <span class="text-red-300">游戏中</span>
                </div>
                <div v-else class="px-3 py-1 bg-green-900/50 rounded-lg">
                  <span class="text-green-300">等待中</span>
                </div>
              </div>
            </div>

            <!-- 牌桌视图 -->
            <div class="relative h-96 bg-poker-green/20 rounded-2xl border-2 border-poker-green/30 mb-6">
              <!-- 牌桌中心 -->
              <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <div class="text-center">
                  <div v-if="gameStore.gameStatus.table_state" class="mb-4">
                    <div class="text-lg font-bold text-poker-gold mb-2">底池</div>
                    <div class="text-3xl font-bold animate-pulse">
                      {{ gameStore.gameStatus.table_state.pot_amount.toLocaleString() }}
                    </div>
                  </div>
                  
                  <div v-if="roomInfo.host_username" class="text-gray-300">
                    房主: {{ roomInfo.host_username }}
                  </div>
                </div>
              </div>

              <!-- 玩家座位 -->
              <div
                v-for="player in gameStore.gameStatus.table_state?.players || []"
                :key="player.position"
                :style="gameStore.getPlayerPositionStyle(player.position)"
                :class="[
                  'table-seat w-24 h-24',
                  {
                    'table-seat-active': player.is_active,
                    'table-seat-current': gameStore.gameStatus.table_state?.current_player === player.position
                  }
                ]"
              >
                <div class="text-center">
                  <div class="font-bold truncate px-2" :class="{
                    'text-gray-300': player.is_connected,
                    'text-gray-500': !player.is_connected
                  }">
                    {{ player.username }}
                  </div>
                  <div class="text-sm mt-1 text-poker-gold">
                    {{ player.chips.toLocaleString() }}
                  </div>
                  <div v-if="player.current_bet > 0" class="text-xs mt-1 text-poker-blue">
                    下注: {{ player.current_bet }}
                  </div>
                  <div v-if="player.is_folded" class="text-xs mt-1 text-red-400">
                    已弃牌
                  </div>
                </div>
              </div>
            </div>

            <!-- 行动按钮 -->
            <div v-if="gameStore.currentPlayer" class="flex flex-wrap gap-3 justify-center">
              <template v-if="gameStore.isCurrentPlayer && gameStore.canAct">
                <button
                  @click="sendAction('fold')"
                  class="btn btn-danger"
                >
                  弃牌
                </button>
                
                <button
                  v-if="gameStore.callAmount === 0"
                  @click="sendAction('check')"
                  class="btn btn-secondary"
                >
                  过牌
                </button>
                
                <button
                  v-else
                  @click="sendAction('call')"
                  class="btn btn-secondary"
                >
                  跟注 {{ gameStore.callAmount }}
                </button>
                
                <button
                  @click="showRaiseDialog = true"
                  class="btn btn-primary"
                >
                  加注
                </button>
                
                <button
                  @click="sendAction('all_in')"
                  class="btn btn-success"
                >
                  全下 {{ gameStore.maxRaiseAmount }}
                </button>
              </template>
              
              <template v-else>
                <div class="text-gray-400 py-2">
                  {{ gameStore.isCurrentPlayer ? '请等待其他玩家行动...' : '等待行动玩家...' }}
                </div>
              </template>
            </div>

            <!-- 未在牌桌上的按钮 -->
            <div v-else class="text-center space-y-4">
              <div class="text-gray-400">
                您当前是旁观者
              </div>
              
              <div class="flex justify-center space-x-4">
                <button
                  @click="joinTable()"
                  :disabled="roomInfo.is_game_active"
                  class="btn btn-primary"
                  :class="{ 'opacity-50 cursor-not-allowed': roomInfo.is_game_active }"
                >
                  {{ roomInfo.is_game_active ? '游戏进行中，请等待' : '加入牌桌' }}
                </button>
                
                <button
                  v-if="gameStore.isHost && !roomInfo.is_game_active"
                  @click="startGame"
                  :disabled="roomInfo.player_count < roomInfo.min_players"
                  class="btn btn-success"
                  :class="{ 'opacity-50 cursor-not-allowed': roomInfo.player_count < roomInfo.min_players }"
                >
                  {{ roomInfo.player_count < roomInfo.min_players ? `需要至少 ${roomInfo.min_players} 名玩家` : '开始游戏' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：聊天和信息面板 -->
        <div class="space-y-6">
          <!-- 聊天面板 -->
          <div class="card h-96 flex flex-col">
            <h3 class="text-xl font-bold mb-4">聊天</h3>
            
            <div class="flex-1 overflow-y-auto mb-4 space-y-2" ref="chatContainer">
              <div
                v-for="message in gameStore.chatMessages"
                :key="message.timestamp"
                :class="[
                  'p-3 rounded-lg',
                  message.is_system ? 'bg-gray-800/50' : 'bg-gray-800'
                ]"
              >
                <div class="flex justify-between text-sm text-gray-400 mb-1">
                  <span :class="{ 'font-bold text-poker-green': !message.is_system }">
                    {{ message.username }}
                  </span>
                  <span>{{ formatTime(message.timestamp) }}</span>
                </div>
                <div :class="{ 'text-gray-300': !message.is_system, 'text-gray-400': message.is_system }">
                  {{ message.message }}
                </div>
              </div>
            </div>
            
            <form @submit.prevent="sendChat" class="flex">
              <input
                v-model="chatMessage"
                type="text"
                placeholder="输入消息..."
                class="input flex-1 rounded-r-none"
              />
              <button
                type="submit"
                class="btn btn-primary rounded-l-none"
              >
                发送
              </button>
            </form>
          </div>

          <!-- 游戏信息 -->
          <div class="card">
            <h3 class="text-xl font-bold mb-4">游戏信息</h3>
            
            <div class="space-y-3">
              <div class="flex justify-between">
                <span class="text-gray-400">盲注等级</span>
                <span class="font-bold">{{ roomInfo.blind_level }}</span>
              </div>
              
              <div class="flex justify-between">
                <span class="text-gray-400">小盲注</span>
                <span class="font-bold">{{ gameStore.gameStatus.table_state?.small_blind || 50 }}</span>
              </div>
              
              <div class="flex justify-between">
                <span class="text-gray-400">大盲注</span>
                <span class="font-bold">{{ gameStore.gameStatus.table_state?.big_blind || 100 }}</span>
              </div>
              
              <div class="flex justify-between">
                <span class="text-gray-400">行动时限</span>
                <span class="font-bold">{{ gameStore.gameStatus.table_state?.action_timeout || 25 }}秒</span>
              </div>
              
              <div v-if="gameStore.gameStatus.next_blind_increase" class="flex justify-between">
                <span class="text-gray-400">下次盲注升级</span>
                <span class="font-bold">{{ formatTime(gameStore.gameStatus.next_blind_increase) }}</span>
              </div>
            </div>
          </div>

          <!-- 玩家列表 -->
          <div class="card">
            <h3 class="text-xl font-bold mb-4">在线玩家</h3>
            
            <div class="space-y-2">
              <div
                v-for="player in gameStore.gameStatus.table_state?.players || []"
                :key="player.user_id"
                class="flex items-center justify-between p-2 rounded-lg bg-gray-800/50"
              >
                <div class="flex items-center">
                  <div
                    class="w-3 h-3 rounded-full mr-2"
                    :class="player.is_connected ? 'bg-green-500' : 'bg-red-500'"
                  ></div>
                  <span :class="{ 'font-bold text-poker-green': player.is_host }">
                    {{ player.username }}
                  </span>
                </div>
                <div class="text-sm text-gray-400">
                  {{ player.chips.toLocaleString() }}
                </div>
              </div>
              
              <div v-if="(!gameStore.gameStatus.table_state?.players || gameStore.gameStatus.table_state.players.length === 0)" class="text-gray-500 text-center py-4">
                暂无玩家在牌桌上
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加注对话框 -->
    <div v-if="showRaiseDialog" class="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div class="card w-full max-w-md">
        <h3 class="text-2xl font-bold mb-4">加注</h3>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">
              加注金额 (最小: {{ gameStore.minRaiseAmount }}, 最大: {{ gameStore.maxRaiseAmount }})
            </label>
            <input
              v-model.number="raiseAmount"
              type="number"
              :min="gameStore.minRaiseAmount"
              :max="gameStore.maxRaiseAmount"
              class="input w-full"
              @keyup.enter="confirmRaise"
            />
          </div>
          
          <div class="flex space-x-2">
            <button
              v-for="amount in quickRaiseAmounts"
              :key="amount"
              @click="raiseAmount = amount"
              class="btn btn-secondary flex-1"
            >
              {{ amount }}
            </button>
          </div>
          
          <div class="flex justify-end space-x-3 pt-4">
            <button
              @click="showRaiseDialog = false"
              class="btn btn-secondary"
            >
              取消
            </button>
            <button
              @click="confirmRaise"
              :disabled="!isValidRaiseAmount"
              class="btn btn-primary"
            >
              确认加注
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGameStore } from '@/stores/game'
import { wsService } from '@/services/websocket'
import { api } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()
const gameStore = useGameStore()

const chatContainer = ref<HTMLElement>()
const chatMessage = ref('')
const showRaiseDialog = ref(false)
const raiseAmount = ref(0)

// 快速加注金额
const quickRaiseAmounts = computed(() => {
  const min = gameStore.minRaiseAmount
  const max = gameStore.maxRaiseAmount
  return [
    min,
    min * 2,
    min * 3,
    Math.floor(max / 2),
    max
  ].filter(amount => amount >= min && amount <= max)
})

// 验证加注金额
const isValidRaiseAmount = computed(() => {
  return raiseAmount.value >= gameStore.minRaiseAmount && 
         raiseAmount.value <= gameStore.maxRaiseAmount
})

// 房间信息
const roomInfo = computed(() => gameStore.roomInfo)

// 格式化时间
const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 发送行动
const sendAction = (action: string, amount?: number) => {
  wsService.sendAction({ action: action as any, amount })
}

// 确认加注
const confirmRaise = () => {
  if (isValidRaiseAmount.value) {
    sendAction('raise', raiseAmount.value)
    showRaiseDialog.value = false
    raiseAmount.value = 0
  }
}

// 发送聊天消息
const sendChat = () => {
  if (chatMessage.value.trim()) {
    wsService.sendChatMessage(chatMessage.value.trim())
    chatMessage.value = ''
  }
}

// 加入牌桌
const joinTable = () => {
  wsService.joinTable()
}

// 开始游戏
const startGame = () => {
  wsService.startGame()
}

// 退出登录
const handleLogout = () => {
  wsService.disconnect()
  authStore.logout()
  router.push('/login')
}

// 滚动到聊天底部
const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// 监听聊天消息变化
watch(() => gameStore.chatMessages.length, scrollChatToBottom)

// 初始化
onMounted(async () => {
  // 检查认证
  if (!authStore.isAuthenticated) {
    router.push('/login')
    return
  }

  // 连接WebSocket
  try {
    await wsService.connect()
    
    // 获取房间信息
    const response = await api.getRoomInfo()
    if (response.success) {
      gameStore.updateRoomInfo(response.data.room)
    }
  } catch (error) {
    console.error('初始化失败:', error)
    gameStore.addSystemMessage('连接服务器失败，请刷新页面重试')
  }
})

// 清理
onUnmounted(() => {
  // 注意：这里不主动断开WebSocket，因为用户可能只是切换路由
})
</script>