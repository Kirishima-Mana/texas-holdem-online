<template>
  <div class="flex items-center">
    <!-- 单个大筹码显示 -->
    <div v-if="!showStack" :class="['chip', chipColorClass]" :title="`${amount} 筹码`">
      {{ formattedAmount }}
    </div>
    
    <!-- 筹码堆显示 -->
    <div v-else class="relative" :style="{ height: '3rem' }">
      <div
        v-for="(chip, index) in chipStack"
        :key="index"
        :class="['chip chip-small absolute', chip.color]"
        :style="{
          left: `${index * 3}px`,
          top: `${index * 2}px`,
          zIndex: chipStack.length - index
        }"
        :title="`${chip.value} 筹码`"
      >
        {{ chip.display }}
      </div>
    </div>
    
    <!-- 筹码数量标签 -->
    <div v-if="showLabel" class="ml-2">
      <div class="text-sm font-semibold">{{ formattedAmount }}</div>
      <div class="text-xs text-gray-400">筹码</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatChips, getChipColorClass } from '@/utils/poker'

interface Props {
  amount: number
  showStack?: boolean
  showLabel?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  amount: 0,
  showStack: false,
  showLabel: false
})

// 格式化金额
const formattedAmount = computed(() => formatChips(props.amount))

// 筹码颜色类
const chipColorClass = computed(() => getChipColorClass(props.amount))

// 筹码堆
const chipStack = computed(() => {
  if (!props.showStack || props.amount <= 0) return []
  
  const denominations = [
    { value: 10000, color: 'chip-black', display: '10K' },
    { value: 5000, color: 'chip-green', display: '5K' },
    { value: 1000, color: 'chip-blue', display: '1K' },
    { value: 500, color: 'chip-red', display: '500' },
    { value: 100, color: 'chip-white', display: '100' }
  ]
  
  let remaining = props.amount
  const stack = []
  
  for (const denom of denominations) {
    const count = Math.floor(remaining / denom.value)
    if (count > 0) {
      // 每种面额最多显示3个筹码
      const displayCount = Math.min(count, 3)
      for (let i = 0; i < displayCount; i++) {
        stack.push(denom)
      }
      remaining -= count * denom.value
    }
    
    if (stack.length >= 5) break // 最多显示5个筹码
  }
  
  return stack
})
</script>