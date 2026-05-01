import { CARD_RANKS, CARD_SUITS, SUIT_COLORS } from '@/types/game'

/**
 * 格式化扑克牌显示
 */
export function formatCard(cardCode: string): {
  rank: string
  suit: string
  colorClass: string
  display: string
} {
  if (!cardCode || cardCode.length < 2) {
    return {
      rank: '?',
      suit: '?',
      colorClass: 'text-gray-500',
      display: '??'
    }
  }

  const rank = cardCode[0].toUpperCase()
  const suit = cardCode[1].toLowerCase()
  
  return {
    rank: CARD_RANKS[rank as keyof typeof CARD_RANKS] || rank,
    suit: CARD_SUITS[suit as keyof typeof CARD_SUITS] || suit,
    colorClass: SUIT_COLORS[suit as keyof typeof SUIT_COLORS] || 'text-gray-300',
    display: `${CARD_RANKS[rank as keyof typeof CARD_RANKS] || rank}${CARD_SUITS[suit as keyof typeof CARD_SUITS] || suit}`
  }
}

/**
 * 获取牌型中文名称
 */
export function getHandRankChinese(rank: string): string {
  const translations: Record<string, string> = {
    'High Card': '高牌',
    'Pair': '一对',
    'Two Pair': '两对',
    'Three of a Kind': '三条',
    'Straight': '顺子',
    'Flush': '同花',
    'Full House': '葫芦',
    'Four of a Kind': '四条',
    'Straight Flush': '同花顺',
    'Royal Flush': '皇家同花顺'
  }
  
  return translations[rank] || rank
}

/**
 * 格式化筹码显示
 */
export function formatChips(chips: number): string {
  if (chips >= 1000000) {
    return `${(chips / 1000000).toFixed(1)}M`
  } else if (chips >= 1000) {
    return `${(chips / 1000).toFixed(1)}K`
  }
  return chips.toString()
}

/**
 * 获取筹码颜色类
 */
export function getChipColorClass(amount: number): string {
  if (amount >= 10000) return 'chip-black'
  if (amount >= 5000) return 'chip-green'
  if (amount >= 1000) return 'chip-blue'
  if (amount >= 500) return 'chip-red'
  return 'chip-white'
}

/**
 * 计算倒计时显示
 */
export function formatCountdown(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * 生成玩家头像颜色
 */
export function getPlayerColor(userId: number): string {
  const colors = [
    'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-red-500',
    'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-teal-500'
  ]
  return colors[userId % colors.length]
}

/**
 * 检查牌面是否有效
 */
export function isValidCard(cardCode: string): boolean {
  if (!cardCode || cardCode.length !== 2) return false
  
  const rank = cardCode[0].toUpperCase()
  const suit = cardCode[1].toLowerCase()
  
  const validRanks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
  const validSuits = ['h', 'd', 'c', 's']
  
  return validRanks.includes(rank) && validSuits.includes(suit)
}