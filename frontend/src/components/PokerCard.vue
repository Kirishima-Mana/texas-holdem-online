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
    <div v-if="showBack" class="text-center w-full h-full rounded-lg flex flex-col items-center justify-center"
      style="background: repeating-linear-gradient(45deg, #1e3a5f, #1e3a5f 4px, #234b7a 4px, #234b7a 8px);">
      <div class="w-3/4 h-3/4 rounded border-2 border-blue-400/40 flex items-center justify-center bg-blue-900/60">
        <span class="text-blue-300 text-xl">♠</span>
      </div>
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
    xs: { width: '2.25rem', height: '3.25rem', fontSize: '0.75rem' },
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