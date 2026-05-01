<template>
  <div class="flex flex-col items-center">
    <!-- 圆形进度条 -->
    <div class="relative w-16 h-16">
      <svg class="w-full h-full transform -rotate-90">
        <!-- 背景圆 -->
        <circle
          cx="32"
          cy="32"
          :r="radius"
          stroke-width="4"
          class="stroke-gray-700 fill-transparent"
        />
        
        <!-- 进度圆 -->
        <circle
          cx="32"
          cy="32"
          :r="radius"
          stroke-width="4"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="dashOffset"
          class="stroke-poker-green transition-all duration-1000 fill-transparent"
          :class="{ 'stroke-red-500': remainingSeconds <= 10 }"
        />
      </svg>
      
      <!-- 中心文本 -->
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="text-center">
          <div class="text-xl font-bold" :class="{
            'text-gray-300': remainingSeconds > 10,
            'text-red-400 animate-pulse': remainingSeconds <= 10
          }">
            {{ formattedTime }}
          </div>
          <div class="text-xs text-gray-400 mt-1">
            剩余时间
          </div>
        </div>
      </div>
    </div>
    
    <!-- 状态文本 -->
    <div v-if="statusText" class="mt-2 text-center">
      <div class="text-sm font-medium" :class="statusClass">
        {{ statusText }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { formatCountdown } from '@/utils/poker'

interface Props {
  totalSeconds: number
  isActive?: boolean
  statusText?: string
  statusType?: 'normal' | 'warning' | 'danger'
}

const props = withDefaults(defineProps<Props>(), {
  totalSeconds: 25,
  isActive: false,
  statusText: '',
  statusType: 'normal'
})

const remainingSeconds = ref(props.totalSeconds)
const timerInterval = ref<number | null>(null)

// 圆形进度条计算
const radius = 28
const circumference = 2 * Math.PI * radius
const dashOffset = computed(() => {
  const progress = remainingSeconds.value / props.totalSeconds
  return circumference * (1 - progress)
})

// 格式化时间显示
const formattedTime = computed(() => formatCountdown(remainingSeconds.value))

// 状态文本样式
const statusClass = computed(() => {
  switch (props.statusType) {
    case 'warning': return 'text-yellow-400'
    case 'danger': return 'text-red-400'
    default: return 'text-gray-300'
  }
})

// 开始计时器
const startTimer = () => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
  }
  
  remainingSeconds.value = props.totalSeconds
  
  timerInterval.value = window.setInterval(() => {
    if (remainingSeconds.value > 0) {
      remainingSeconds.value--
    } else {
      stopTimer()
    }
  }, 1000)
}

// 停止计时器
const stopTimer = () => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
}

// 重置计时器
const resetTimer = () => {
  stopTimer()
  remainingSeconds.value = props.totalSeconds
}

// 监听 isActive 变化
watch(() => props.isActive, (isActive) => {
  if (isActive) {
    startTimer()
  } else {
    stopTimer()
  }
}, { immediate: true })

// 监听 totalSeconds 变化
watch(() => props.totalSeconds, (newTotal) => {
  remainingSeconds.value = newTotal
})

// 组件生命周期
onMounted(() => {
  if (props.isActive) {
    startTimer()
  }
})

onUnmounted(() => {
  stopTimer()
})

// 暴露方法给父组件
defineExpose({
  startTimer,
  stopTimer,
  resetTimer
})
</script>