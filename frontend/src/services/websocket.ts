import { ref } from 'vue'
import type { WSMessage, GameStatus, RoomInfo, ChatMessage, ActionRequest } from '@/types/game'
import { useAuthStore } from '@/stores/auth'
import { useGameStore } from '@/stores/game'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

class WebSocketService {
  private socket: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private heartbeatInterval: number | null = null
  private isConnecting = false

  // 连接状态
  isConnected = ref(false)
  connectionError = ref<string | null>(null)

  // 连接WebSocket
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnecting || this.socket?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      const authStore = useAuthStore()
      const token = authStore.getAccessToken()

      if (!token) {
        reject(new Error('未认证，请先登录'))
        return
      }

      this.isConnecting = true
      this.connectionError.value = null

      try {
        const wsUrl = `${WS_URL}/ws?token=${encodeURIComponent(token)}`
        this.socket = new WebSocket(wsUrl)

        this.socket.onopen = () => {
          console.log('WebSocket 连接成功')
          this.isConnected.value = true
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.startHeartbeat()
          resolve()
        }

        this.socket.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.socket.onerror = (error) => {
          console.error('WebSocket 错误:', error)
          this.connectionError.value = '连接错误'
          this.isConnecting = false
          reject(error)
        }

        this.socket.onclose = (event) => {
          console.log('WebSocket 连接关闭:', event.code, event.reason)
          this.isConnected.value = false
          this.isConnecting = false
          this.stopHeartbeat()
          
          // 如果不是正常关闭，尝试重连
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnect()
          }
        }
      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  // 断开连接
  disconnect(): void {
    if (this.socket) {
      this.socket.close(1000, '正常关闭')
      this.socket = null
    }
    this.isConnected.value = false
    this.stopHeartbeat()
  }

  // 重新连接
  private reconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('达到最大重连次数')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，延迟: ${delay}ms`)
    
    setTimeout(() => {
      this.connect().catch(console.error)
    }, delay)
  }

  // 发送消息
  send(message: WSMessage): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket 未连接')
      return
    }

    try {
      this.socket.send(JSON.stringify(message))
    } catch (error) {
      console.error('发送消息失败:', error)
    }
  }

  // 处理接收到的消息
  private handleMessage(data: string): void {
    try {
      const message: WSMessage = JSON.parse(data)
      const gameStore = useGameStore()

      switch (message.type) {
        case 'welcome':
          console.log('欢迎消息:', message.data)
          break

        case 'game_state':
          gameStore.updateGameStatus(message.data as GameStatus)
          break

        case 'room_info':
          gameStore.updateRoomInfo(message.data as RoomInfo)
          break

        case 'chat':
          gameStore.addChatMessage(message.data as ChatMessage)
          break

        case 'player_joined':
          gameStore.addSystemMessage(`${message.data.username} 加入了牌桌`)
          break

        case 'player_left':
          gameStore.addSystemMessage(`${message.data.username} 离开了牌桌`)
          break

        case 'game_started':
          gameStore.addSystemMessage(message.data.message)
          break

        case 'action_result':
          gameStore.addSystemMessage(message.data.message)
          break

        case 'heartbeat_ack':
          // 心跳响应，无需处理
          break

        case 'error':
          console.error('服务器错误:', message.data.error)
          gameStore.addSystemMessage(`错误: ${message.data.error}`)
          break

        default:
          console.warn('未知消息类型:', message.type, message.data)
      }
    } catch (error) {
      console.error('解析消息失败:', error, data)
    }
  }

  // 开始心跳
  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.send({ type: 'heartbeat', data: {} })
      }
    }, 30000) // 每30秒发送一次心跳
  }

  // 停止心跳
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  // 发送玩家行动
  sendAction(action: ActionRequest): void {
    this.send({
      type: 'action',
      data: action
    })
  }

  // 发送聊天消息
  sendChatMessage(message: string): void {
    this.send({
      type: 'chat',
      data: { message }
    })
  }

  // 加入牌桌
  joinTable(position?: number, buyinType: 'new' | 'rebuy' = 'new'): void {
    this.send({
      type: 'join_table',
      data: { position, buyin_type: buyinType }
    })
  }

  // 离开牌桌
  leaveTable(leaveType: 'temporary' | 'permanent' = 'temporary'): void {
    this.send({
      type: 'leave_table',
      data: { type: leaveType }
    })
  }

  // 开始游戏
  startGame(): void {
    this.send({
      type: 'start_game',
      data: {}
    })
  }
}

// 导出单例实例
export const wsService = new WebSocketService()