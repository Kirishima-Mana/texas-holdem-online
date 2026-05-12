import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GameStatus, RoomInfo, ChatMessage, PlayerInfo } from '@/types/game'
import { useAuthStore } from '@/stores/auth'

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

  // 系统通知消息（独立于聊天）
  const systemMessages = ref<ChatMessage[]>([])

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

  // 当前轮最大下注
  const currentMaxBet = computed(() => {
    if (!gameStatus.value.table_state) return 0
    return Math.max(
      ...gameStatus.value.table_state.players.map(p => p.current_bet)
    )
  })

  // 需要跟注的金额
  const callAmount = computed(() => {
    if (!currentPlayer.value || !gameStatus.value.table_state) return 0
    return Math.max(0, currentMaxBet.value - currentPlayer.value.current_bet)
  })

  // 最小下注金额（第一个下注的玩家）
  const minBetAmount = computed(() => {
    if (!gameStatus.value.table_state) return 0
    return gameStatus.value.table_state.big_blind
  })

  // 最大下注金额（玩家可投入的总筹码）
  const maxBetAmount = computed(() => {
    if (!currentPlayer.value) return 0
    return currentPlayer.value.chips + currentPlayer.value.current_bet
  })

  // 最小加注到金额（前方玩家下注的2倍）
  const minRaiseAmount = computed(() => {
    if (!gameStatus.value.table_state) return 0
    return Math.max(currentMaxBet.value * 2, gameStatus.value.table_state.big_blind * 2)
  })

  // 最大加注到金额（玩家可投入的总筹码）
  const maxRaiseAmount = computed(() => {
    if (!currentPlayer.value) return 0
    return currentPlayer.value.chips + currentPlayer.value.current_bet
  })

  // 摊牌信息
  const showdownData = ref<any>(null)
  // 冠军信息
  const gameWinner = ref<any>(null)

  // 更新游戏状态（同时同步 roomInfo）
  const updateGameStatus = (status: any) => {
    gameStatus.value = status
    // 从牌桌状态同步房间信息
    if (status.table_state) {
      roomInfo.value.player_count = status.table_state.players.length
      roomInfo.value.is_game_active = status.is_game_active
      const host = status.table_state.players.find((p: any) => p.is_host)
      if (host) {
        roomInfo.value.host_username = host.username
      }
    }
    // 同步摊牌数据
    if (status.showdown) {
      showdownData.value = status.showdown
    } else {
      showdownData.value = null
    }
    // 同步冠军数据
    if (status.game_winner) {
      gameWinner.value = status.game_winner
    } else if (status.is_game_active) {
      gameWinner.value = null
    }
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

  // 添加系统消息（进入独立的通知列表，不混入聊天）
  const addSystemMessage = (message: string) => {
    systemMessages.value.push({
      user_id: 0,
      username: '系统',
      message,
      timestamp: new Date().toISOString(),
      is_system: true
    })
    if (systemMessages.value.length > 200) {
      systemMessages.value = systemMessages.value.slice(-100)
    }
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
    systemMessages,
    unreadChatCount,
    showdownData,
    gameWinner,
    
    // 计算属性
    currentPlayer,
    isHost,
    isCurrentPlayer,
    canAct,
    callAmount,
    minBetAmount,
    maxBetAmount,
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