<template>
  <div class="flex flex-col h-full bg-gray-800 rounded-xl border border-gray-700">
    <!-- 标题 -->
    <div class="flex items-center justify-between p-4 border-b border-gray-700">
      <h3 class="text-lg font-bold">聊天</h3>
      <div class="flex items-center space-x-2">
        <div class="text-sm text-gray-400">
          {{ unreadCount > 0 ? `${unreadCount} 条未读` : '全部已读' }}
        </div>
        <button
          v-if="unreadCount > 0"
          @click="clearUnread"
          class="text-xs text-poker-green hover:text-green-400"
        >
          标记已读
        </button>
      </div>
    </div>
    
    <!-- 消息列表 -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-3"
      @scroll="handleScroll"
    >
      <!-- 系统消息 -->
      <div
        v-for="message in filteredMessages"
        :key="message.timestamp"
        :class="[
          'p-3 rounded-lg transition-colors duration-200',
          message.is_system 
            ? 'bg-gray-800/50 hover:bg-gray-800/70' 
            : 'bg-gray-800 hover:bg-gray-700',
          isNewMessage(message) ? 'border-l-4 border-poker-green' : ''
        ]"
      >
        <!-- 消息头部 -->
        <div class="flex justify-between items-start mb-1">
          <div class="flex items-center">
            <span
              :class="[
                'font-medium',
                message.is_system ? 'text-gray-400' : 'text-poker-green'
              ]"
            >
              {{ message.username }}
            </span>
            <span
              v-if="message.user_id === currentUserId"
              class="ml-2 text-xs px-2 py-0.5 bg-poker-green/20 text-poker-green rounded"
            >
              我
            </span>
          </div>
          <span class="text-xs text-gray-500">
            {{ formatTime(message.timestamp) }}
          </span>
        </div>
        
        <!-- 消息内容 -->
        <div
          :class="[
            'break-words',
            message.is_system ? 'text-gray-300' : 'text-gray-100'
          ]"
          v-html="formatMessage(message.message)"
        ></div>
      </div>
      
      <!-- 空状态 -->
      <div
        v-if="filteredMessages.length === 0"
        class="text-center py-8 text-gray-500"
      >
        暂无聊天消息
      </div>
      
      <!-- 加载更多 -->
      <div
        v-if="hasMoreMessages && !isNearBottom"
        class="text-center py-4"
      >
        <button
          @click="loadMoreMessages"
          class="text-sm text-poker-green hover:text-green-400"
        >
          加载更多消息
        </button>
      </div>
    </div>
    
    <!-- 输入框 -->
    <div class="p-4 border-t border-gray-700">
      <form @submit.prevent="sendMessage" class="flex space-x-2">
        <input
          v-model="inputMessage"
          type="text"
          placeholder="输入消息..."
          class="input flex-1"
          :disabled="!isConnected"
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.ctrl.enter="handleCtrlEnter"
        />
        <button
          type="submit"
          class="btn btn-primary whitespace-nowrap"
          :disabled="!isConnected || !inputMessage.trim()"
        >
          发送
        </button>
      </form>
      
      <!-- 连接状态 -->
      <div v-if="!isConnected" class="mt-2 text-sm text-red-400">
        聊天连接已断开，请刷新页面重试
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import type { ChatMessage } from '@/types/game'

interface Props {
  messages: ChatMessage[]
  currentUserId?: number
  isConnected?: boolean
  showSystemMessages?: boolean
  maxMessages?: number
}

const props = withDefaults(defineProps<Props>(), {
  messages: () => [],
  currentUserId: undefined,
  isConnected: true,
  showSystemMessages: true,
  maxMessages: 100
})

const emit = defineEmits<{
  'send': [message: string]
  'clear-unread': []
  'load-more': []
}>()

const messagesContainer = ref<HTMLElement>()
const inputMessage = ref('')
const unreadCount = ref(0)
const lastReadIndex = ref(-1)
const isNearBottom = ref(true)
const hasMoreMessages = ref(false)

// 过滤消息
const filteredMessages = computed(() => {
  let messages = props.messages
  
  if (!props.showSystemMessages) {
    messages = messages.filter(msg => !msg.is_system)
  }
  
  // 限制显示数量
  if (props.maxMessages > 0 && messages.length > props.maxMessages) {
    messages = messages.slice(-props.maxMessages)
    hasMoreMessages.value = true
  } else {
    hasMoreMessages.value = false
  }
  
  return messages
})

// 检查是否是新消息
const isNewMessage = (message: ChatMessage) => {
  const index = props.messages.indexOf(message)
  return index > lastReadIndex.value
}

// 格式化时间
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) {
    return '刚刚'
  } else if (diffMins < 60) {
    return `${diffMins}分钟前`
  } else if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
}

// 格式化消息内容
const formatMessage = (text: string) => {
  // 简单处理：转义HTML，保留换行
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="text-poker-blue hover:underline">$1</a>')
}

// 发送消息
const sendMessage = () => {
  const message = inputMessage.value.trim()
  if (message && props.isConnected) {
    emit('send', message)
    inputMessage.value = ''
    
    // 滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
  }
}

// Ctrl+Enter 换行
const handleCtrlEnter = () => {
  const textarea = document.querySelector('input[type="text"]') as HTMLInputElement
  if (textarea) {
    const start = textarea.selectionStart || 0
    const end = textarea.selectionEnd || 0
    inputMessage.value = inputMessage.value.substring(0, start) + '\n' + inputMessage.value.substring(end)
    
    // 移动光标位置
    nextTick(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 1
    })
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    isNearBottom.value = true
  }
}

// 处理滚动
const handleScroll = () => {
  if (!messagesContainer.value) return
  
  const container = messagesContainer.value
  const scrollBottom = container.scrollHeight - container.scrollTop - container.clientHeight
  
  isNearBottom.value = scrollBottom < 50
  
  // 标记已读
  if (isNearBottom.value && unreadCount.value > 0) {
    clearUnread()
  }
}

// 清除未读
const clearUnread = () => {
  lastReadIndex.value = props.messages.length - 1
  unreadCount.value = 0
  emit('clear-unread')
}

// 加载更多消息
const loadMoreMessages = () => {
  emit('load-more')
}

// 监听新消息
watch(
  () => props.messages.length,
  (newLength, oldLength) => {
    if (newLength > oldLength) {
      // 有新消息
      const newMessagesCount = newLength - oldLength
      
      // 如果用户不在底部，增加未读计数
      if (!isNearBottom.value) {
        unreadCount.value += newMessagesCount
      }
      
      // 如果用户在底部，自动滚动并标记已读
      if (isNearBottom.value) {
        nextTick(() => {
          scrollToBottom()
          clearUnread()
        })
      }
    }
  },
  { immediate: true }
)

// 初始化
onMounted(() => {
  scrollToBottom()
  clearUnread()
})

// 暴露方法
defineExpose({
  scrollToBottom,
  clearUnread
})
</script>