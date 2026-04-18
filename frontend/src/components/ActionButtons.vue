<template>
  <div class="flex flex-col items-center space-y-4">
    <!-- 行动提示 -->
    <div v-if="isCurrentPlayer" class="text-center">
      <div class="text-xl font-bold text-poker-gold animate-pulse mb-2">
        ⚡ 轮到您行动
      </div>
      <div class="text-gray-300">
        请在 {{ actionTimeout }} 秒内做出决定
      </div>
    </div>
    <div v-else class="text-center">
      <div class="text-lg text-gray-400">
        等待 {{ currentPlayerName }} 行动...
      </div>
    </div>
    
    <!-- 倒计时 -->
    <Timer
      v-if="isCurrentPlayer"
      :total-seconds="actionTimeout"
      :is-active="isCurrentPlayer"
      :status-text="timerStatusText"
      :status-type="timerStatusType"
    />
    
    <!-- 行动按钮 -->
    <div v-if="isCurrentPlayer && canAct" class="flex flex-wrap gap-3 justify-center">
      <!-- 弃牌按钮 -->
      <button
        @click="emitAction('fold')"
        class="btn btn-danger flex items-center space-x-2"
        :disabled="!canFold"
      >
        <span>弃牌</span>
      </button>
      
      <!-- 过牌/跟注按钮 -->
      <button
        v-if="callAmount === 0"
        @click="emitAction('check')"
        class="btn btn-secondary flex items-center space-x-2"
        :disabled="!canCheck"
      >
        <span>过牌</span>
      </button>
      
      <button
        v-else
        @click="emitAction('call')"
        class="btn btn-secondary flex items-center space-x-2"
        :disabled="!canCall"
      >
        <span>跟注 {{ callAmount.toLocaleString() }}</span>
      </button>
      
      <!-- 加注按钮 -->
      <button
        @click="showRaiseDialog = true"
        class="btn btn-primary flex items-center space-x-2"
        :disabled="!canRaise"
      >
        <span>加注</span>
      </button>
      
      <!-- 全下按钮 -->
      <button
        @click="emitAction('all_in')"
        class="btn btn-success flex items-center space-x-2"
        :disabled="!canAllIn"
      >
        <span>全下 {{ playerChips.toLocaleString() }}</span>
      </button>
    </div>
    
    <!-- 玩家状态提示 -->
    <div v-else-if="isCurrentPlayer" class="text-center">
      <div class="p-4 bg-gray-800 rounded-lg">
        <div class="text-gray-300">
          <span v-if="isFolded">您已弃牌</span>
          <span v-else-if="isAllIn">您已全下</span>
          <span v-else>请等待其他玩家行动</span>
        </div>
      </div>
    </div>
    
    <!-- 加注对话框 -->
    <div v-if="showRaiseDialog" class="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div class="card w-full max-w-md">
        <h3 class="text-2xl font-bold mb-4">加注</h3>
        
        <div class="space-y-4">
          <!-- 当前下注信息 -->
          <div class="bg-gray-800/50 rounded-lg p-4">
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div class="text-gray-400">当前下注额</div>
                <div class="font-bold">{{ currentMaxBet.toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-gray-400">您的下注</div>
                <div class="font-bold">{{ playerCurrentBet.toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-gray-400">需要跟注</div>
                <div class="font-bold">{{ callAmount.toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-gray-400">您的筹码</div>
                <div class="font-bold">{{ playerChips.toLocaleString() }}</div>
              </div>
            </div>
          </div>
          
          <!-- 加注金额输入 -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">
              加注金额
              <span class="text-gray-400 ml-2">
                (最小: {{ minRaiseAmount.toLocaleString() }}, 最大: {{ maxRaiseAmount.toLocaleString() }})
              </span>
            </label>
            <div class="flex space-x-2">
              <input
                v-model.number="raiseAmount"
                type="number"
                :min="minRaiseAmount"
                :max="maxRaiseAmount"
                class="input flex-1"
                @keyup.enter="confirmRaise"
              />
              <button
                @click="raiseAmount = maxRaiseAmount"
                class="btn btn-secondary whitespace-nowrap"
              >
                全下
              </button>
            </div>
          </div>
          
          <!-- 快速加注按钮 -->
          <div>
            <div class="text-sm text-gray-400 mb-2">快速加注</div>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="amount in quickRaiseAmounts"
                :key="amount"
                @click="raiseAmount = amount"
                :class="[
                  'btn',
                  raiseAmount === amount ? 'btn-primary' : 'btn-secondary'
                ]"
              >
                {{ amount.toLocaleString() }}
              </button>
            </div>
          </div>
          
          <!-- 加注预览 -->
          <div v-if="raiseAmount >= minRaiseAmount" class="bg-poker-green/10 rounded-lg p-4">
            <div class="text-center">
              <div class="text-gray-300 mb-1">加注预览</div>
              <div class="text-xl font-bold text-poker-gold">
                总下注: {{ (callAmount + raiseAmount).toLocaleString() }}
              </div>
              <div class="text-sm text-gray-400 mt-1">
                剩余筹码: {{ (playerChips - callAmount - raiseAmount).toLocaleString() }}
              </div>
            </div>
          </div>
          
          <!-- 操作按钮 -->
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
import { ref, computed } from 'vue'
import Timer from './Timer.vue'

interface Props {
  // 玩家状态
  isCurrentPlayer: boolean
  canAct: boolean
  isFolded: boolean
  isAllIn: boolean
  
  // 下注信息
  callAmount: number
  playerChips: number
  playerCurrentBet: number
  currentMaxBet: number
  
  // 游戏设置
  actionTimeout: number
  minRaiseAmount: number
  maxRaiseAmount: number
  
  // 其他玩家信息
  currentPlayerName?: string
}

const props = withDefaults(defineProps<Props>(), {
  currentPlayerName: '其他玩家'
})

const emit = defineEmits<{
  action: [type: string, amount?: number]
}>()

const showRaiseDialog = ref(false)
const raiseAmount = ref(0)

// 计算属性
const canFold = computed(() => props.canAct && !props.isFolded)
const canCheck = computed(() => props.canAct && props.callAmount === 0)
const canCall = computed(() => props.canAct && props.callAmount > 0 && props.callAmount <= props.playerChips)
const canRaise = computed(() => props.canAct && props.playerChips >= props.minRaiseAmount)
const canAllIn = computed(() => props.canAct && props.playerChips > 0)

// 快速加注金额
const quickRaiseAmounts = computed(() => {
  const amounts = [
    props.minRaiseAmount,
    props.minRaiseAmount * 2,
    props.minRaiseAmount * 3,
    Math.floor(props.maxRaiseAmount / 2),
    props.maxRaiseAmount
  ]
  
  // 去重并排序
  return [...new Set(amounts)]
    .filter(amount => amount >= props.minRaiseAmount && amount <= props.maxRaiseAmount)
    .sort((a, b) => a - b)
})

// 验证加注金额
const isValidRaiseAmount = computed(() => {
  return raiseAmount.value >= props.minRaiseAmount && 
         raiseAmount.value <= props.maxRaiseAmount
})

// 计时器状态
const timerStatusText = computed(() => {
  if (props.isFolded) return '已弃牌'
  if (props.isAllIn) return '已全下'
  return '请行动'
})

const timerStatusType = computed(() => {
  if (props.isFolded || props.isAllIn) return 'warning'
  return 'normal'
})

// 发送行动
const emitAction = (type: string, amount?: number) => {
  emit('action', type, amount)
  showRaiseDialog.value = false
  raiseAmount.value = 0
}

// 确认加注
const confirmRaise = () => {
  if (isValidRaiseAmount.value) {
    emitAction('raise', raiseAmount.value)
  }
}

// 重置加注对话框
const resetRaiseDialog = () => {
  showRaiseDialog.value = false
  raiseAmount.value = 0
}

// 暴露方法
defineExpose({
  resetRaiseDialog
})
</script>