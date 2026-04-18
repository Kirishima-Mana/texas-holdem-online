export interface User {
  id: number
  username: string
}

export interface PlayerInfo {
  user_id: number
  username: string
  position: number
  chips: number
  current_bet: number
  is_active: boolean
  has_acted: boolean
  is_folded: boolean
  is_all_in: boolean
  is_connected: boolean
  is_host: boolean
  cards: string[] | null
}

export interface TableState {
  players: PlayerInfo[]
  community_cards: string[]
  pot_amount: number
  current_player: number | null
  stage: 'waiting' | 'preflop' | 'flop' | 'turn' | 'river' | 'showdown'
  small_blind: number
  big_blind: number
  dealer_position: number
  action_timeout: number
  blind_level: number
}

export interface GameStatus {
  is_game_active: boolean
  table_state: TableState | null
  blind_level: number
  next_blind_increase: string | null
  is_spectator: boolean
}

export interface RoomInfo {
  player_count: number
  spectator_count: number
  is_game_active: boolean
  host_username: string | null
  blind_level: number
  max_players: number
  min_players: number
}

export interface ChatMessage {
  user_id: number
  username: string
  message: string
  timestamp: string
  is_system: boolean
}

export interface Token {
  access_token: string
  token_type: string
  session_token: string
}

export interface AuthResponse {
  user: User
  token: Token
}

export interface WSMessage {
  type: string
  data: any
}

export type PlayerAction = 'fold' | 'check' | 'call' | 'raise' | 'all_in'

export interface ActionRequest {
  action: PlayerAction
  amount?: number
}

export interface Card {
  rank: string
  suit: string
  code: string
}

export const CARD_SUITS = {
  'h': '♥',
  'd': '♦',
  'c': '♣',
  's': '♠'
} as const

export const CARD_RANKS = {
  '2': '2',
  '3': '3',
  '4': '4',
  '5': '5',
  '6': '6',
  '7': '7',
  '8': '8',
  '9': '9',
  'T': '10',
  'J': 'J',
  'Q': 'Q',
  'K': 'K',
  'A': 'A'
} as const

export const SUIT_COLORS = {
  'h': 'text-red-500',
  'd': 'text-red-500',
  'c': 'text-gray-300',
  's': 'text-gray-300'
} as const