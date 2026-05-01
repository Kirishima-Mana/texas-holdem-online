<template>
  <div class="flex flex-col items-center">
    <!-- 阶段指示器 -->
    <div class="mb-4">
      <div class="flex items-center justify-center space-x-2">
        <div
          v-for="stage in gameStages"
          :key="stage.key"
          :class="[
            'px-4 py-2 rounded-lg font-medium transition-all duration-300',
            currentStage === stage.key
              ? 'bg-poker-green text-white'
              : 'bg-gray-800 text-gray-400'
          ]"
        >
          {{ stage.label }}
        </div>
      </div>
    </div>
    
    <!-- 公共牌区域 -->
    <div class="relative bg-gray-800/50 rounded-2xl p-6 border-2 border-gray-700">
      <!-- 牌桌背景 -->
      <div class="absolute inset-0 bg-poker-green/10 rounded-2xl"></div>
      
      <!-- 公共牌 -->
      <div class="relative flex justify-center items-center space-x-4">
        <!-- 翻牌 -->
        <div v-if="cards.length >= 3" class="flex space-x-2">
          <PokerCard
            v-for="(card, index) in cards.slice(0, 3)"
            :key="`flop-${index}`"
            :card="card"
            :size="'lg'"
            :rotation="getCardRotation(index, 3)"
            hover-effect
          />
        </div>
        
        <!-- 转牌 -->
        <div v-if="cards.length >= 4" class="ml-4">
          <div class="relative">
            <div class="absolute -top-4 left-1/2 transform -translate-x-1/2 text-xs text-gray-400">
              转牌
            </div>
            <PokerCard
              :card="cards[3]"
              :size="'lg'"
              :rotation="5"
              hover-effect
            />
          </div>
        </div>
        
        <!-- 河牌 -->
        <div v-if="cards.length >= 5" class="ml-4">
          <div class="relative">
            <div class="absolute -top-4 left-1/2 transform -translate-x-1/2 text-xs text-gray-400">
              河牌
            </div>
            <PokerCard
              :card="cards[4]"
              :size="'lg'"
              :rotation="-5"
              hover-effect
            />
          </div>
        </div>
        
        <!-- 空牌位 -->
        <div
          v-for="i in emptyCardSlots"
          :key="`empty-${i}`"
          class="poker-card poker-card-back opacity-30"
          :style="{ width: '5rem', height: '7.5rem' }"
        >
          <div class="text-center">
            <div class="text-2xl">♠</div>
            <div class="text-xs mt-1">TEXAS</div>
          </div>
        </div>
      </div>
      
      <!-- 底池显示 -->
      <div class="absolute -bottom-6 left-1/2 transform -translate-x-1/2">
        <div class="bg-gray-900 border-2 border-poker-gold rounded-xl px-6 py-3 shadow-lg">
          <div class="text-center">
            <div class="text-sm text-gray-300 mb-1">底池</div>
            <div class="text-2xl font-bold text-poker-gold animate-pulse">
              {{ potAmount.toLocaleString() }}
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 游戏阶段描述 -->
    <div class="mt-6 text-center">
      <div class="text-gray-300 font-medium mb-1">
        {{ currentStageLabel }}
      </div>
      <div class="text-sm text-gray-400">
        {{ stageDescription }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PokerCard from './PokerCard.vue'

interface Props {
  cards: string[]
  potAmount: number
  stage: string
}

const props = defineProps<Props>()

// 游戏阶段定义
const gameStages = [
  { key: 'preflop', label: '翻牌前', description: '玩家持有底牌，进行第一轮下注' },
  { key: 'flop', label: '翻牌', description: '发出3张公共牌，进行第二轮下注' },
  { key: 'turn', label: '转牌', description: '发出第4张公共牌，进行第三轮下注' },
  { key: 'river', label: '河牌', description: '发出第5张公共牌，进行最后一轮下注' },
  { key: 'showdown', label: '摊牌', description: '剩余玩家亮出底牌，决定赢家' }
]

// 当前阶段信息
const currentStage = computed(() => props.stage)
const currentStageInfo = computed(() => 
  gameStages.find(stage => stage.key === props.stage) || gameStages[0]
)
const currentStageLabel = computed(() => currentStageInfo.value.label)
const stageDescription = computed(() => currentStageInfo.value.description)

// 空牌位数量
const emptyCardSlots = computed(() => {
  const totalSlots = 5
  return Math.max(0, totalSlots - props.cards.length)
})

// 获取卡片旋转角度
const getCardRotation = (index: number, total: number): number => {
  const center = (total - 1) / 2
  return (index - center) * 5 // 每张牌旋转5度
}
</script>