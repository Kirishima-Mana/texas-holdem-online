<template>
  <div class="min-h-screen bg-gray-900 p-4">
    <div class="max-w-7xl mx-auto">
      <!-- 顶部导航 -->
      <div class="flex justify-between items-center mb-4">
        <div>
          <h1 class="text-2xl font-bold text-poker-gold">德州扑克大厅</h1>
          <p class="text-gray-400 text-sm">欢迎，{{ authStore.user?.username }}</p>
        </div>
        <div class="flex items-center space-x-4">
          <div class="text-right text-sm">
            <span class="text-gray-400">房间状态</span>
            <span class="ml-2 font-semibold">{{ roomInfo.player_count }}/{{ roomInfo.max_players }} 玩家</span>
            <span class="text-gray-500 mx-1">|</span>
            <span>{{ roomInfo.spectator_count }} 旁观</span>
          </div>
          <button @click="handleLogout" class="btn btn-secondary text-sm">退出</button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-4 gap-3">
        <!-- 牌桌主区域 -->
        <div class="lg:col-span-3 order-2 lg:order-1">
          <div class="card p-3 sm:p-4">
            <!-- 牌桌头部 -->
            <div class="flex justify-between items-center mb-3">
              <h2 class="text-lg font-bold">牌桌</h2>
              <div class="flex items-center space-x-2 text-sm">
                <span class="text-gray-400">盲注 Lv.{{ roomInfo.blind_level }}</span>
                <span v-if="gameStore.gameStatus.table_state" class="text-gray-400">
                  {{ gameStore.gameStatus.table_state.small_blind }}/{{ gameStore.gameStatus.table_state.big_blind }}
                </span>
                <span :class="gameStore.gameStatus.is_game_active ? 'text-red-400' : 'text-green-400'" class="font-bold">
                  {{ gameStore.gameStatus.is_game_active ? '游戏中' : '等待中' }}
                </span>
                <span v-if="gameStore.gameStatus.is_game_active" class="px-2 py-0.5 rounded text-xs font-bold bg-poker-gold text-gray-900">
                  {{ stageLabel }}
                </span>
              </div>
            </div>

            <!-- 牌桌容器（开阔布局，玩家在桌外） -->
            <div class="relative h-[22rem] sm:h-[24rem] lg:h-[26rem] mb-4 select-none overflow-visible">

              <!-- 实木牌桌边框 (Rail) — 温暖木纹 -->
              <div class="absolute rounded-[42%] shadow-2xl"
                style="top: 14%; left: 14%; right: 14%; bottom: 14%;
                  background: linear-gradient(175deg, #b87333 0%, #9c5a2a 8%, #8b4e23 16%, #a0623b 25%,
                    #7a3f1a 35%, #9c5a2a 45%, #8b4e23 55%, #6d3515 65%,
                    #8b4e23 75%, #a0623b 85%, #7a3f1a 92%, #6d3515 100%);
                  border: 5px solid #4a2512;
                  box-shadow: 0 0 30px rgba(0,0,0,0.6), inset 0 0 12px rgba(0,0,0,0.3);">
              </div>

              <!-- 绒布面 (Felt) — 深绿色 -->
              <div class="absolute rounded-[40%]"
                style="top: calc(14% + 16px); left: calc(14% + 16px); right: calc(14% + 16px); bottom: calc(14% + 16px);
                  background: radial-gradient(ellipse at center, #1a7a3a 0%, #0f5628 35%, #0a3d1a 100%);">
                <!-- 绒布暗纹 -->
                <div class="absolute inset-0 opacity-8 rounded-[40%]"
                  style="background: repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.02) 3px, rgba(255,255,255,0.02) 6px);">
                </div>

                <!-- 公共牌区域（正中） -->
                <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-30">
                  <div class="flex justify-center items-center space-x-1.5">
                    <PokerCard
                      v-for="(card, idx) in (gameStore.gameStatus.table_state?.community_cards || [])"
                      :key="'comm-' + idx"
                      :card="card"
                      size="md"
                      class="animate-card-in"
                      :style="{ animationDelay: idx * 0.12 + 's' }"
                    />
                    <div
                      v-for="i in emptyCommunitySlots"
                      :key="'empty-' + i"
                      class="w-[4rem] h-[6rem] rounded-lg flex items-center justify-center"
                      style="background: rgba(255,255,255,0.03); box-shadow: inset 0 0 15px rgba(0,0,0,0.3);">
                    </div>
                  </div>
                </div>

                <!-- 底池显示（牌桌内上方） -->
                <div v-if="gameStore.gameStatus.table_state && gameStore.gameStatus.table_state.pot_amount > 0"
                  class="absolute top-[15%] left-1/2 transform -translate-x-1/2 z-30">
                  <div class="px-3 py-0.5 bg-gray-900/90 rounded-full border border-poker-gold/50 text-center shadow">
                    <span class="text-[10px] text-gray-400 mr-0.5">底池</span>
                    <span class="text-xs font-bold text-poker-gold">{{ gameStore.gameStatus.table_state.pot_amount.toLocaleString() }}</span>
                  </div>
                </div>

                <!-- 庄家按钮 (D) -->
                <div v-if="gameStore.gameStatus.table_state"
                  :style="dealerBtnStyle()"
                  class="absolute z-30 w-7 h-7 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center text-[10px] font-bold text-gray-700 shadow"
                  style="transform: translate(-50%, -50%);">
                  D
                </div>
              </div><!-- /Felt -->

              <!-- 牌桌外玩家区域（8座，绝不对牌桌重叠） -->
              <div
                v-for="player in gameStore.gameStatus.table_state?.players || []"
                :key="'seat-' + player.position"
                :style="getSeatStyle(player.position)"
                class="absolute z-25"
              >
                  <!-- 手牌 -->
                  <div v-if="player.cards && player.cards.length && !player.is_folded" class="flex justify-center -space-x-1 mb-1.5">
                    <PokerCard
                      v-for="(card, idx) in player.cards"
                      :key="'hole-' + player.position + '-' + idx"
                      :card="card"
                      size="sm"
                      :show-back="false"
                      :rotation="idx === 0 ? -3 : 3"
                      class="animate-deal-in"
                      :style="{ animationDelay: (0.2 + idx * 0.15) + 's' }"
                    />
                  </div>
                  <div v-else-if="player.is_folded && player.cards && player.cards.length" class="flex justify-center -space-x-1 mb-1.5 opacity-40">
                    <PokerCard
                      v-for="(card, idx) in player.cards"
                      :key="'hole-' + player.position + '-' + idx"
                      :card="card"
                      size="sm"
                      :show-back="true"
                      :rotation="idx === 0 ? -3 : 3"
                    />
                  </div>

                  <!-- 玩家面板 -->
                  <div :class="[
                    'relative px-2 py-1 rounded-lg text-center min-w-[4.5rem] transition-all duration-300',
                    playerBg(player)
                  ]">
                    <div v-if="actionLabel(player)" :class="[
                      'absolute -top-2.5 left-1/2 transform -translate-x-1/2 px-1.5 py-0.5 rounded text-[10px] font-bold text-white whitespace-nowrap shadow',
                      actionTagColor(player)
                    ]">
                      {{ actionLabel(player) }}
                    </div>
                    <div class="flex items-center justify-center space-x-0.5">
                      <span class="w-1 h-1 rounded-full" :class="player.is_connected ? 'bg-green-400' : 'bg-red-500'"></span>
                      <span class="font-bold text-xs truncate max-w-[4rem]"
                        :class="player.is_connected ? 'text-gray-100' : 'text-gray-500'">
                        {{ player.username }}
                      </span>
                      <span v-if="player.is_host" class="text-poker-gold text-[10px]" title="房主">★</span>
                    </div>
                    <div class="text-[11px] text-gray-300 mt-0.5 font-mono">{{ formatChips(player.chips) }}</div>
                    <div v-if="player.current_bet > 0" class="text-[11px] text-poker-gold mt-0.5 animate-chip-in font-semibold">
                      +{{ player.current_bet.toLocaleString() }}
                    </div>
                  </div>
                </div>
            </div>

            <!-- 操作区域 -->
            <div v-if="gameStore.currentPlayer" class="flex flex-col gap-2 items-center">
              <template v-if="!gameStore.gameStatus.is_game_active">
                <div class="flex flex-wrap gap-2 justify-center">
                  <button v-if="gameStore.isHost" @click="startGame"
                    :disabled="roomInfo.player_count < roomInfo.min_players"
                    class="btn btn-success" :class="{ 'opacity-50': roomInfo.player_count < roomInfo.min_players }">
                    {{ roomInfo.player_count < roomInfo.min_players ? `需至少${roomInfo.min_players}人 (${roomInfo.player_count})` : '开始游戏' }}
                  </button>
                  <div v-else class="text-gray-400 py-2 text-sm">等待房主开始游戏...</div>
                  <button @click="leaveTable()" class="btn btn-secondary text-sm">离开牌桌</button>
                </div>
              </template>
              <template v-else>
                <div class="flex flex-wrap gap-2 justify-center">
                  <template v-if="gameStore.isCurrentPlayer && gameStore.canAct">
                    <button @click="sendAction('fold')" class="btn btn-danger">弃牌</button>
                    <button v-if="gameStore.callAmount === 0" @click="sendAction('check')" class="btn btn-secondary">过牌</button>
                    <button v-else @click="sendAction('call')" class="btn btn-secondary">跟注 {{ gameStore.callAmount.toLocaleString() }}</button>
                    <button @click="showRaiseDialog = true" class="btn btn-primary">加注</button>
                    <button @click="sendAction('all_in')" class="btn btn-success">全下 {{ gameStore.maxRaiseAmount.toLocaleString() }}</button>
                  </template>
                  <template v-else>
                    <span class="text-gray-400 py-2 text-sm">
                      {{ gameStore.isCurrentPlayer ? '请等待其他玩家行动...' : '等待行动玩家...' }}
                    </span>
                  </template>
                </div>
              </template>
            </div>
            <div v-else class="text-center space-y-3">
              <div class="text-gray-400 text-sm">您当前是旁观者</div>
              <button @click="joinTable()" :disabled="gameStore.gameStatus.is_game_active"
                class="btn btn-primary" :class="{ 'opacity-50': gameStore.gameStatus.is_game_active }">
                {{ gameStore.gameStatus.is_game_active ? '游戏进行中，请等待' : '加入牌桌' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 右侧面板 -->
        <div class="space-y-4 order-1 lg:order-2">
          <!-- 聊天 -->
          <div class="card p-3 h-64 flex flex-col">
            <div class="flex justify-between items-center mb-2">
              <h3 class="text-sm font-bold">聊天</h3>
              <button @click="showRules = true" class="text-xs text-poker-gold hover:text-yellow-300 border border-poker-gold/40 rounded px-2 py-0.5">规则说明</button>
            </div>
            <div class="flex-1 overflow-y-auto mb-2 space-y-1 text-sm" ref="chatContainer">
              <div v-for="msg in gameStore.chatMessages" :key="msg.timestamp"
                :class="['p-2 rounded', msg.is_system ? 'bg-gray-800/40 text-gray-400' : 'bg-gray-800 text-gray-200']">
                <span v-if="!msg.is_system" class="font-bold text-poker-green text-xs">{{ msg.username }} </span>
                <span class="text-xs">{{ msg.message }}</span>
              </div>
            </div>
            <form @submit.prevent="sendChat" class="flex">
              <input v-model="chatMessage" type="text" placeholder="输入..." class="input flex-1 rounded-r-none text-sm py-1" />
              <button type="submit" class="btn btn-primary rounded-l-none text-sm py-1 px-3">发</button>
            </form>
          </div>

          <!-- 信息面板 -->
          <div class="card p-3 text-sm space-y-2">
            <div class="flex justify-between"><span class="text-gray-400">小/大盲</span><span>{{ gameStore.gameStatus.table_state?.small_blind || 50 }} / {{ gameStore.gameStatus.table_state?.big_blind || 100 }}</span></div>
            <div class="flex justify-between"><span class="text-gray-400">行动时限</span><span>{{ gameStore.gameStatus.table_state?.action_timeout || 25 }}秒</span></div>
          </div>

          <!-- 玩家列表 -->
          <div class="card p-3 text-sm">
            <h3 class="font-bold mb-2">玩家</h3>
            <div v-for="p in gameStore.gameStatus.table_state?.players || []" :key="p.user_id"
              class="flex justify-between items-center py-1 border-b border-gray-700/50 last:border-0">
              <div class="flex items-center">
                <span class="w-2 h-2 rounded-full mr-1.5" :class="p.is_connected ? 'bg-green-500' : 'bg-red-500'"></span>
                <span :class="p.is_host ? 'text-poker-gold' : 'text-gray-300'">{{ p.username }}</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-poker-gold text-xs">{{ p.chips.toLocaleString() }}</span>
                <button v-if="gameStore.isHost && p.user_id !== authStore.user?.id && (!gameStore.gameStatus.is_game_active || !p.is_connected)"
                  @click="kickPlayer(p.user_id)" class="text-xs text-red-400 hover:text-red-300 ml-1" title="移除玩家">✕</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加注对话框 -->
    <div v-if="showRaiseDialog" class="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div class="card w-full max-w-sm">
        <h3 class="text-xl font-bold mb-3">加注</h3>
        <div class="space-y-3">
          <input v-model.number="raiseAmount" type="number" :min="gameStore.minRaiseAmount" :max="gameStore.maxRaiseAmount"
            class="input w-full" @keyup.enter="confirmRaise" placeholder="输入加注金额" />
          <div class="grid grid-cols-3 gap-1.5">
            <button v-for="amount in quickRaiseAmounts" :key="amount" @click="raiseAmount = amount"
              :class="['btn text-xs py-1', raiseAmount === amount ? 'btn-primary' : 'btn-secondary']">{{ amount }}</button>
          </div>
          <div class="flex justify-end space-x-2">
            <button @click="showRaiseDialog = false" class="btn btn-secondary text-sm">取消</button>
            <button @click="confirmRaise" :disabled="!isValidRaiseAmount" class="btn btn-primary text-sm">确认加注</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 冠军庆祝面板 -->
    <div v-if="gameStore.gameWinner" class="fixed inset-0 bg-black/90 flex items-center justify-center z-50">
      <div class="text-center">
        <div class="text-6xl mb-4">&#127942;</div>
        <div class="text-3xl font-bold text-poker-gold mb-2">冠军诞生！</div>
        <div class="text-4xl font-bold text-white mb-4">{{ gameStore.gameWinner.username }}</div>
        <div class="text-xl text-gray-300 mb-2">
          最终筹码：<span class="text-poker-gold font-bold text-2xl">{{ gameStore.gameWinner.chips.toLocaleString() }}</span>
        </div>
        <div class="text-gray-500 text-sm mt-6">房主可以开始新一局</div>
        <button @click="gameStore.gameWinner = null" class="btn btn-primary mt-4">关闭</button>
      </div>
    </div>

    <!-- 摊牌结算面板 -->
    <div v-if="showShowdown" class="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" @click.self="showShowdown = false">
      <div class="card w-full max-w-xl max-h-[90vh] overflow-y-auto" @click.stop>
        <h3 class="text-2xl font-bold text-poker-gold text-center mb-4">摊牌结算</h3>

        <!-- 公共牌 -->
        <div class="text-center mb-3">
          <div class="text-xs text-gray-400 mb-1">公共牌</div>
          <div class="flex justify-center space-x-2">
            <PokerCard v-for="(card, idx) in (gameStore.gameStatus.table_state?.community_cards || [])" :key="'sd-'+idx" :card="card" size="sm" />
          </div>
        </div>

        <!-- 赢家区域 -->
        <div v-if="showdownWinner" class="bg-poker-gold/10 border-2 border-poker-gold rounded-lg p-4 mb-3 text-center">
          <div class="text-sm text-gray-400 mb-1">获胜玩家</div>
          <div class="text-2xl font-bold text-poker-gold mb-1">{{ showdownWinner.username }}</div>
          <div class="text-sm text-gray-300">
            牌型：<span class="text-poker-gold font-bold">{{ showdownWinner.hand_rank }}</span>
          </div>
          <div class="text-sm text-gray-300 mt-1">
            赢得底池：<span class="text-poker-gold font-bold text-lg">{{ (gameStore.gameStatus.table_state?.pot_amount || 0).toLocaleString() }}</span>
          </div>
          <div class="flex justify-center space-x-1 mt-2">
            <PokerCard v-for="(card, idx) in (showdownWinner.hole_cards || [])" :key="'winner-'+idx" :card="card" size="md" />
          </div>
        </div>
        <div v-else class="text-center text-gray-400 py-4">所有玩家均已弃牌</div>

        <!-- 所有摊牌玩家对比 -->
        <div v-if="showdownPlayers.length > 1" class="border-t border-gray-700 pt-3 mt-3">
          <div class="text-xs text-gray-400 mb-2 text-center">所有摊牌玩家</div>
          <div class="grid grid-cols-2 gap-2">
            <div v-for="p in showdownPlayers" :key="p.user_id"
              :class="['p-2 rounded-lg border text-center', p.user_id === showdownWinner?.user_id ? 'border-poker-gold bg-poker-gold/10' : 'border-gray-600 bg-gray-800']">
              <div class="font-bold text-sm" :class="p.user_id === showdownWinner?.user_id ? 'text-poker-gold' : 'text-gray-300'">{{ p.username }}</div>
              <div class="flex justify-center space-x-1 my-1">
                <PokerCard v-for="(card, idx) in (p.hole_cards || [])" :key="idx" :card="card" size="xs" />
              </div>
              <div class="text-[10px]" :class="p.user_id === showdownWinner?.user_id ? 'text-poker-gold' : 'text-gray-400'">{{ p.hand_rank || '' }}</div>
            </div>
          </div>
        </div>

        <button @click="showShowdown = false" class="btn btn-primary w-full mt-3">继续</button>
      </div>
    </div>

    <!-- 规则说明弹窗 -->
    <div v-if="showRules" class="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" @click.self="showRules = false">
      <div class="card w-full max-w-lg max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-3"><h3 class="text-xl font-bold text-poker-gold">德州扑克规则说明</h3><button @click="showRules = false" class="text-gray-400 hover:text-white text-2xl leading-none">&times;</button></div>
        <div class="space-y-3 text-sm text-gray-300">
          <div><h4 class="font-bold text-white mb-1">基本规则</h4><p>每位玩家发2张底牌，桌面上发出5张公共牌。用底牌与公共牌组合出最好的5张牌型比大小。</p></div>
          <div><h4 class="font-bold text-white mb-1">游戏流程</h4><ol class="list-decimal pl-4 space-y-1"><li><span class="text-poker-gold font-bold">翻牌前</span> — 发2张底牌，小盲/大盲强制下注，小盲左侧开始行动</li><li><span class="text-poker-gold font-bold">翻牌</span> — 发3张公共牌，第二轮下注</li><li><span class="text-poker-gold font-bold">转牌</span> — 发第4张公共牌，第三轮下注</li><li><span class="text-poker-gold font-bold">河牌</span> — 发第5张公共牌，最后一轮下注</li><li><span class="text-poker-gold font-bold">摊牌</span> — 剩余玩家亮牌，比较牌型大小</li></ol></div>
          <div><h4 class="font-bold text-white mb-1">可选行动</h4><ul class="space-y-1"><li><span class="text-red-400 font-bold">弃牌 (Fold)</span> — 放弃当前手牌</li><li><span class="text-gray-300 font-bold">过牌 (Check)</span> — 无人下注时可选</li><li><span class="text-gray-300 font-bold">跟注 (Call)</span> — 补齐当前最高下注额</li><li><span class="text-blue-400 font-bold">加注 (Raise)</span> — 至少为大盲注2倍</li><li><span class="text-green-400 font-bold">全下 (All-in)</span> — 投入全部剩余筹码</li></ul></div>
          <div><h4 class="font-bold text-white mb-1">牌型大小（从大到小）</h4><div class="space-y-1">
            <div class="flex justify-between p-1 bg-poker-gold/10 rounded"><span class="text-poker-gold font-bold">皇家同花顺</span><span class="text-xs text-gray-400">同花 A-K-Q-J-10</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">同花顺</span><span class="text-xs text-gray-400">同花连续五张</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">四条</span><span class="text-xs text-gray-400">四张相同点数</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">葫芦</span><span class="text-xs text-gray-400">三条+一对</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">同花</span><span class="text-xs text-gray-400">五张同花色</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">顺子</span><span class="text-xs text-gray-400">五张连续点数</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">三条</span><span class="text-xs text-gray-400">三张相同点数</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">两对</span><span class="text-xs text-gray-400">两个对子</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">一对</span><span class="text-xs text-gray-400">一个对子</span></div>
            <div class="flex justify-between p-1 bg-gray-800 rounded"><span class="text-white font-bold">高牌</span><span class="text-xs text-gray-400">无组合比单张</span></div>
          </div></div>
          <div><h4 class="font-bold text-white mb-1">边池说明</h4><p>有玩家全下但筹码不足以匹配当前下注时，超出部分进入边池。该全下玩家只能赢取主池，边池由剩余玩家竞争。</p></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGameStore } from '@/stores/game'
import { wsService } from '@/services/websocket'
import { api } from '@/services/api'
import PokerCard from './PokerCard.vue'

const router = useRouter()
const authStore = useAuthStore()
const gameStore = useGameStore()

const chatContainer = ref<HTMLElement>()
const chatMessage = ref('')
const showRaiseDialog = ref(false)
const showRules = ref(false)
const raiseAmount = ref(0)

const quickRaiseAmounts = computed(() => {
  const min = gameStore.minRaiseAmount
  const max = gameStore.maxRaiseAmount
  return [
    min,
    min * 2,
    min * 3,
    Math.floor(max / 2),
    max
  ].filter(amount => amount >= min && amount <= max)
})

const isValidRaiseAmount = computed(() => {
  return raiseAmount.value >= gameStore.minRaiseAmount &&
         raiseAmount.value <= gameStore.maxRaiseAmount
})

const roomInfo = computed(() => gameStore.roomInfo)

const stageLabel = computed(() => {
  const stage = gameStore.gameStatus.table_state?.stage
  const map: Record<string, string> = {
    'waiting': '等待中',
    'preflop': '翻牌前',
    'flop': '翻牌',
    'turn': '转牌',
    'river': '河牌',
    'showdown': '摊牌'
  }
  return map[stage] || stage || ''
})

const emptyCommunitySlots = computed(() => {
  const cards = gameStore.gameStatus.table_state?.community_cards || []
  return Math.max(0, 5 - cards.length)
})

const showShowdown = computed({
  get: () => !!gameStore.showdownData,
  set: (val: boolean) => { if (!val) gameStore.showdownData = null }
})

const showdownWinner = computed(() => {
  const data = gameStore.showdownData
  if (!data) return null
  // 优先使用 winner 字段
  if (data.winner) return data.winner
  // fallback: 从 players 中找最低分的
  if (data.players?.length) {
    const sorted = [...data.players].sort((a: any, b: any) => (a.score ?? 9999) - (b.score ?? 9999))
    return sorted[0] || null
  }
  return null
})

const showdownPlayers = computed(() => {
  return gameStore.showdownData?.players || []
})

const formatChips = (chips: number) => {
  if (chips >= 1000000) return (chips / 1000000).toFixed(1) + 'M'
  if (chips >= 1000) return (chips / 1000).toFixed(1) + 'K'
  return chips.toLocaleString()
}

const playerBg = (player: any) => {
  if (!player.is_connected) return 'bg-gray-700/40 text-gray-500'
  if (gameStore.gameStatus.table_state?.current_player === player.position)
    return 'bg-poker-gold/20 ring-2 ring-poker-gold text-gray-100'
  if (player.is_folded) return 'bg-gray-700/50 text-gray-500'
  if (player.is_all_in) return 'bg-yellow-900/40 ring-1 ring-yellow-500/50 text-gray-100'
  return 'bg-gray-800/80 text-gray-100'
}

const actionLabel = (player: any) => {
  if (player.is_folded) return 'FOLD'
  if (player.is_all_in) return 'ALL IN'
  if (player.has_acted && player.current_bet === 0) return 'CHECK'
  return ''
}

const actionTagColor = (player: any) => {
  if (player.is_folded) return 'bg-red-600'
  if (player.is_all_in) return 'bg-yellow-500'
  return 'bg-orange-500'
}

const dealerBtnStyle = () => {
  const pos = gameStore.gameStatus.table_state?.dealer_position ?? 0
  // Dealer 按钮在桌面上，靠近对应玩家座位方向的桌边
  const btnPositions = [
    { top: '18%', left: '50%' },
    { top: '24%', left: '76%' },
    { top: '50%', left: '78%' },
    { top: '74%', left: '76%' },
    { top: '80%', left: '50%' },
    { top: '74%', left: '24%' },
    { top: '50%', left: '22%' },
    { top: '24%', left: '24%' },
  ]
  return btnPositions[pos % 8]
}

const getSeatStyle = (position: number) => {
  // 8 座围绕牌桌，完全在桌外（桌面 rail 占 14%-86%）
  const positions = [
    { top: '3%', left: '50%', transform: 'translate(-50%, -50%)' },
    { top: '8%', left: '88%', transform: 'translate(-50%, -50%)' },
    { top: '50%', left: '95%', transform: 'translate(-50%, -50%)' },
    { top: '90%', left: '88%', transform: 'translate(-50%, -50%)' },
    { top: '96%', left: '50%', transform: 'translate(-50%, -50%)' },
    { top: '90%', left: '12%', transform: 'translate(-50%, -50%)' },
    { top: '50%', left: '5%', transform: 'translate(-50%, -50%)' },
    { top: '8%', left: '12%', transform: 'translate(-50%, -50%)' },
  ]
  return positions[position % 8]
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const sendAction = (action: string, amount?: number) => {
  wsService.sendAction({ action: action as any, amount })
}

const confirmRaise = () => {
  if (isValidRaiseAmount.value) {
    sendAction('raise', raiseAmount.value)
    showRaiseDialog.value = false
    raiseAmount.value = 0
  }
}

const sendChat = () => {
  if (chatMessage.value.trim()) {
    wsService.sendChatMessage(chatMessage.value.trim())
    chatMessage.value = ''
  }
}

const joinTable = () => wsService.joinTable()
const startGame = () => wsService.startGame()
const leaveTable = () => wsService.leaveTable()
const kickPlayer = (userId: number) => wsService.kickPlayer(userId)

const handleLogout = () => {
  wsService.disconnect()
  authStore.logout()
  router.push('/login')
}

const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

watch(() => gameStore.chatMessages.length, scrollChatToBottom)

// 调试：监听摊牌数据
watch(() => gameStore.showdownData, (data) => {
  if (data) {
    console.log('showdownData arrived:', JSON.stringify(data))
    console.log('winner:', data.winner)
    console.log('players:', data.players?.length)
  } else {
    console.log('showdownData cleared')
  }
}, { deep: true })

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    router.push('/login')
    return
  }
  try {
    await wsService.connect()
    const response = await api.getRoomInfo()
    if (response.success) {
      gameStore.updateRoomInfo(response.data.room)
    }
  } catch (error) {
    console.error('初始化失败:', error)
    gameStore.addSystemMessage('连接服务器失败，请刷新页面重试')
  }
})

onUnmounted(() => {})
</script>
