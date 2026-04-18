import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GameStatus, RoomInfo, ChatMessage, PlayerInfo } from '@/types/game'

export const useGameStore = defineStore('game', () => {
  // 游戏状态
  const gameStatus = ref<GameStatus>({
    is_game_active: false,
    table_state: null,
    blind_level: 1,
    next_blind_increase: null,
    is_spectator: true
  })

  // 房间信息
  const roomInfo = ref<RoomInfo>({
    player_count: 0,
    spectator_count: 0,
    is_game_active: false,
    host_username: null,
    blind_level: 1,
    max_players: 10,
    min_players: 2
  })

  // 聊天消息
  const chatMessages = ref<ChatMessage[]>([])
  const unreadChatCount = ref(0)

  // 当前玩家信息
  const currentPlayer = computed(() => {
    if (!gameStatus.value.table_state) return null
    
    const authStore = useAuthStore()
    if (!authStore.user) return null
    
    return gameStatus.value.table_state.players.find(
      p => p.user_id === authStore.user!.id
    )
  })

  // 是否房主
  const isHost = computed(() => {
    return currentPlayer.value?.is_host || false
  })

  // 是否当前行动玩家
  const isCurrentPlayer = computed(() => {
    if (!gameStatus.value.table_state || !currentPlayer.value) return false
    return gameStatus.value.table_state.current_player === currentPlayer.value.position
  })

  // 是否可以行动
  const canAct = computed(() => {
    if (!currentPlayer.value || !isCurrentPlayer.value) return false
    return !currentPlayer.value.is_folded && !currentPlayer.value.is_all_in
  })

  // 需要跟注的金额
  const callAmount = computed(() => {
    if (!currentPlayer.value || !gameStatus.value.table_state) return 0
    
    const currentMaxBet = Math.max(
      ...gameStatus.value.table_state.players.map(p => p.current_bet)
    )
    
    return Math.max(0, currentMaxBet - currentPlayer.value.current_bet)
  })

  // 最小加注金额
  const minRaiseAmount = computed(() => {
    if (!gameStatus.value.table_state) return 0
    return gameStatus.value.table_state.big_blind * 2
  })

  // 最大加注金额（玩家筹码）
  const maxRaiseAmount = computed(() => {
    return currentPlayer.value?.chips || 0
  })

  // 更新游戏状态
  const updateGameStatus = (status: GameStatus) => {
    gameStatus.value = status
  }

  // 更新房间信息
  const updateRoomInfo = (info: RoomInfo) => {
    roomInfo.value = info
  }

  // 添加聊天消息
  const addChatMessage = (message: ChatMessage) => {
    chatMessages.value.push(message)
    
    // 限制聊天记录数量
    if (chatMessages.value.length > 100) {
      chatMessages.value = chatMessages.value.slice(-100)
    }
    
    // 增加未读计数（如果不在聊天界面）
    // 这里需要根据实际UI状态来判断，暂时先不实现
  }

  // 添加系统消息
  const addSystemMessage = (message: string) => {
    addChatMessage({
      user_id: 0,
      username: '系统',
      message,
      timestamp: new Date().toISOString(),
      is_system: true
    })
  }

  // 清空未读计数
  const clearUnreadChat = () => {
    unreadChatCount.value = 0
  }

  // 重置游戏状态
  const resetGame = () => {
    gameStatus.value = {
      is_game_active: false,
      table_state: null,
      blind_level: 1,
      next_blind_increase: null,
      is_spectator: true
    }
    
    chatMessages.value = []
    unreadChatCount.value = 0
  }

  // 获取玩家位置样式
  const getPlayerPositionStyle = (position: number) => {
    const positions = [
      { top: '50%', left: '50%', transform: 'translate(-50%, -150%)' }, // 上
      { top: '30%', left: '75%', transform: 'translate(-50%, -50%)' },  // 右上
      { top: '50%', left: '90%', transform: 'translate(-50%, -50%)' },  // 右
      { top: '70%', left: '75%', transform: 'translate(-50%, -50%)' },  // 右下
      { top: '90%', left: '50%', transform: 'translate(-50%, 50%)' },   // 下
      { top: '70%', left: '25%', transform: 'translate(-50%, -50%)' },  // 左下
      { top: '50%', left: '10%', transform: 'translate(-50%, -50%)' },  // 左
      { top: '30%', left: '25%', transform: 'translate(-50%, -50%)' },  // 左上
    ]
    
    return positions[position % positions.length]
  }

  return {
    // 状态
    gameStatus,
    roomInfo,
    chatMessages,
    unreadChatCount,
    
    // 计算属性
    currentPlayer,
    isHost,
    isCurrentPlayer,
    canAct,
    callAmount,
    minRaiseAmount,
    maxRaiseAmount,
    
    // 方法
    updateGameStatus,
    updateRoomInfo,
    addChatMessage,
    addSystemMessage,
    clearUnreadChat,
    resetGame,
    getPlayerPositionStyle
  }
})