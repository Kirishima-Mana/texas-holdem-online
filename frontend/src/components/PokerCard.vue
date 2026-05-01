<template>
  <div
    :class="[
      'poker-card transition-all duration-300',
      showBack ? 'poker-card-back' : 'poker-card-front',
      hoverEffect && 'hover:scale-110 hover:z-10',
      className
    ]"
    :style="cardStyle"
    @click="$emit('click')"
  >
    <div v-if="showBack" class="text-center">
      <div class="text-2xl">♠</div>
      <div class="text-xs mt-1">TEXAS</div>
    </div>
    
    <div v-else class="text-center">
      <div :class="['text-3xl font-bold', cardInfo.colorClass]">
        {{ cardInfo.suit }}
      </div>
      <div class="text-xl font-bold mt-1">
        {{ cardInfo.rank }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatCard } from '@/utils/poker'

interface Props {
  card?: string
  showBack?: boolean
  hoverEffect?: boolean
  className?: string
  size?: 'sm' | 'md' | 'lg'
  rotation?: number
}

const props = withDefaults(defineProps<Props>(), {
  card: '',
  showBack: false,
  hoverEffect: true,
  className: '',
  size: 'md',
  rotation: 0
})

const emit = defineEmits<{
  click: []
}>()

// 卡片信息
const cardInfo = computed(() => formatCard(props.card))

// 卡片样式
const cardStyle = computed(() => {
  const sizeMap = {
    sm: { width: '3rem', height: '4.5rem', fontSize: '0.875rem' },
    md: { width: '4rem', height: '6rem', fontSize: '1rem' },
    lg: { width: '5rem', height: '7.5rem', fontSize: '1.25rem' }
  }
  
  const size = sizeMap[props.size]
  
  return {
    width: size.width,
    height: size.height,
    fontSize: size.fontSize,
    transform: `rotate(${props.rotation}deg)`
  }
})
</script>