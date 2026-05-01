<template>
  <div
    :style="positionStyle"
    :class="[
      'table-seat transition-all duration-300',
      {
        'table-seat-active': player.is_active,
        'table-seat-current': isCurrentPlayer,
        'opacity-50': !player.is_connected
      }
    ]"
  >
    <!-- 玩家信息 -->
    <div class="text-center w-full">
      <!-- 玩家名和状态 -->
      <div class="flex items-center justify-center mb-2">
        <div
          class="w-2 h-2 rounded-full mr-1"
          :class="player.is_connected ? 'bg-green-500' : 'bg-red-500'"
        ></div>
        <div class="font-bold truncate px-2" :class="{
          'text-poker-gold': player.is_host,
          'text-gray-300': player.is_connected,
          'text-gray-500': !player.is_connected
        }">
          {{ player.username }}
          <span v-if="isCurrentPlayer" class="ml-1 text-xs">⚡</span>
        </div>
      </div>
      
      <!-- 筹码显示 -->
      <div class="mb-2">
        <ChipDisplay
          :amount="player.chips"
          :show-stack="true"
          size="sm"
        />
      </div>
      
      <!-- 当前下注 -->
      <div v-if="player.current_bet > 0" class="mb-1">
        <div class="text-xs text-poker-blue bg-gray-800/50 rounded px-2 py-1">
          下注: {{ player.current_bet.toLocaleString() }}
        </div>
      </div>
      
      <!-- 状态标签 -->
      <div v-if="player.is_folded" class="text-xs text-red-400 bg-red-900/30 rounded px-2 py-1">
        已弃牌
      </div>
      <div v-else-if="player.is_all_in" class="text-xs text-yellow-400 bg-yellow-900/30 rounded px-2 py-1">
        全下
      </div>
      <div v-else-if="player.has_acted" class="text-xs text-green-400 bg-green-900/30 rounded px-2 py-1">
        已行动
      </div>
      
      <!-- 玩家手牌（旁观者视角或摊牌时显示） -->
      <div v-if="showCards && player.cards && player.cards.length > 0" class="mt-2">
        <div class="flex justify-center space-x-1">
          <PokerCard
            v-for="(card, index) in player.cards"
            :key="index"
            :card="card"
            :size="'sm'"
            :rotation="index === 0 ? -5 : 5"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PlayerInfo } from '@/types/game'
import PokerCard from './PokerCard.vue'
import ChipDisplay from './ChipDisplay.vue'

interface Props {
  player: PlayerInfo
  position: number
  isCurrentPlayer?: boolean
  showCards?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isCurrentPlayer: false,
  showCards: false
})

// 位置样式
const positionStyle = computed(() => {
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
  
  return positions[props.position % positions.length]
})
</script>