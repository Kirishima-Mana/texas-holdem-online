"""
牌桌管理
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import asyncio
from datetime import datetime, timedelta

from .player import Player
from ..config import settings


@dataclass
class Table:
    """牌桌状态管理"""
    
    # 玩家管理
    players: Dict[int, Player] = field(default_factory=dict)  # position -> Player
    player_positions: Dict[int, int] = field(default_factory=dict)  # user_id -> position
    
    # 牌局状态
    deck: List[str] = field(default_factory=list)
    community_cards: List[str] = field(default_factory=list)
    pot_amount: int = 0
    side_pots: List[Dict] = field(default_factory=list)
    
    # 游戏阶段
    stage: str = "waiting"  # waiting, preflop, flop, turn, river, showdown
    current_player_position: Optional[int] = None
    dealer_position: int = 0
    small_blind_position: int = 0
    big_blind_position: int = 0
    
    # 盲注
    small_blind: int = settings.small_blind
    big_blind: int = settings.big_blind
    blind_level: int = 1
    last_blind_increase: datetime = field(default_factory=datetime.utcnow)
    
    # 行动管理
    action_timeout: int = settings.action_timeout
    current_max_bet: int = 0
    players_acted_this_round: int = 0
    
    # 房主
    host_user_id: Optional[int] = None
    
    def __post_init__(self):
        """初始化牌堆"""
        self.reset_deck()
    
    def reset_deck(self):
        """重置牌堆"""
        from ..utils.poker_logic import create_deck, shuffle_deck
        self.deck = shuffle_deck(create_deck())
    
    def add_player(self, player: Player, position: Optional[int] = None) -> bool:
        """添加玩家到牌桌"""
        if len(self.players) >= settings.max_players:
            return False
        
        if position is None:
            # 寻找空位置
            for pos in range(settings.max_players):
                if pos not in self.players:
                    position = pos
                    break
        
        if position is None or position in self.players:
            return False
        
        player.position = position
        player.is_active = True
        self.players[position] = player
        self.player_positions[player.user_id] = position
        
        # 如果没有有效房主，设为房主
        need_host = (
            self.host_user_id is None or
            self.host_user_id not in self.player_positions
        )
        if need_host:
            # 清除旧房主标记（如果存在）
            for p in self.players.values():
                p.is_host = False
            self.host_user_id = player.user_id
            player.is_host = True
        
        return True
    
    def remove_player(self, user_id: int, keep_chips: bool = False) -> Optional[Player]:
        """从牌桌移除玩家"""
        if user_id not in self.player_positions:
            return None
        
        position = self.player_positions[user_id]
        player = self.players.pop(position, None)
        
        if player:
            del self.player_positions[user_id]

            # 如果移除的是房主，转移房主权限
            if user_id == self.host_user_id:
                player.is_host = False
                if self.players:
                    # 优先转给在线玩家，其次才是任意玩家
                    new_host = None
                    for pos in sorted(self.players.keys()):
                        p = self.players[pos]
                        if p.is_connected:
                            new_host = p
                            break
                    if not new_host:
                        new_host = self.players[min(self.players.keys())]
                    new_host.is_host = True
                    self.host_user_id = new_host.user_id
                else:
                    # 牌桌为空，重置房主
                    self.host_user_id = None
            
            # 如果不保留筹码，清空
            if not keep_chips:
                player.chips = 0
            
            player.is_active = False
            player.position = None
        
        return player
    
    def get_player_by_position(self, position: int) -> Optional[Player]:
        """根据位置获取玩家"""
        return self.players.get(position)
    
    def get_player_by_user_id(self, user_id: int) -> Optional[Player]:
        """根据用户ID获取玩家"""
        position = self.player_positions.get(user_id)
        if position is not None:
            return self.players.get(position)
        return None
    
    def get_active_players(self) -> List[Player]:
        """获取活跃玩家（未弃牌）"""
        return [
            player for player in self.players.values()
            if player.is_active and not player.is_folded
        ]
    
    def get_connected_players(self) -> List[Player]:
        """获取已连接的玩家"""
        return [
            player for player in self.players.values()
            if player.is_active and player.is_connected
        ]
    
    def get_next_player_position(self, start_position: int) -> Optional[int]:
        """获取下一个需要行动的玩家位置"""
        positions = sorted(self.players.keys())
        if not positions:
            return None
        
        # 找到起始位置在列表中的索引
        try:
            start_idx = positions.index(start_position)
        except ValueError:
            start_idx = 0
        
        # 循环查找下一个可行动的玩家
        for i in range(len(positions)):
            idx = (start_idx + i + 1) % len(positions)
            position = positions[idx]
            player = self.players[position]
            
            if player.can_act():
                return position
        
        return None
    
    def deal_hole_cards(self):
        """发底牌"""
        from ..utils.poker_logic import deal_cards
        
        # 给每个活跃玩家发2张牌
        for player in self.get_active_players():
            if player.is_connected:  # 只给已连接的玩家发牌
                cards, self.deck = deal_cards(self.deck, 2)
                player.hole_cards = cards
    
    def deal_community_cards(self, count: int):
        """发公共牌"""
        from ..utils.poker_logic import deal_cards
        
        cards, self.deck = deal_cards(self.deck, count)
        self.community_cards.extend(cards)
    
    def reset_for_new_hand(self):
        """重置为新的一手牌"""
        # 重置牌堆和公共牌
        self.reset_deck()
        self.community_cards = []
        self.pot_amount = 0
        self.side_pots = []
        self.current_max_bet = 0
        self.players_acted_this_round = 0
        
        # 重置玩家状态
        for player in self.players.values():
            player.reset_for_new_hand()
        
        # 更新庄家位置
        self.dealer_position = self.get_next_active_position(self.dealer_position)
        
        # 更新大小盲位置
        self.small_blind_position = self.get_next_active_position(self.dealer_position)
        self.big_blind_position = self.get_next_active_position(self.small_blind_position)
        
        # 设置当前玩家（大盲注后面的玩家）
        self.current_player_position = self.get_next_active_position(self.big_blind_position)
        
        # 设置游戏阶段
        self.stage = "preflop"
    
    def get_next_active_position(self, start_position: int) -> int:
        """获取下一个活跃玩家的位置"""
        positions = sorted(self.players.keys())
        if not positions:
            return 0
        
        try:
            start_idx = positions.index(start_position)
        except ValueError:
            start_idx = -1
        
        # 循环查找
        for i in range(len(positions)):
            idx = (start_idx + i + 1) % len(positions)
            position = positions[idx]
            player = self.players.get(position)
            
            if player and player.is_active and player.is_connected and not player.is_all_in:
                return position

        # 没有可行动玩家：尝试找任何活跃连接的非 all-in 玩家
        for p in self.players.values():
            if p.is_active and p.is_connected and not p.is_all_in:
                return p.position
        return positions[0]
    
    def collect_bets(self):
        """收集下注到主池"""
        total = 0
        for player in self.players.values():
            total += player.current_bet
            player.current_bet = 0
        
        self.pot_amount += total
        self.current_max_bet = 0
        self.players_acted_this_round = 0
    
    def calculate_side_pots(self):
        """计算边池 — 基于所有不同的下注金额层级"""
        # 获取所有唯一的下注总额（排除 0）
        amounts = sorted(set(
            p.total_bet_this_round
            for p in self.players.values()
            if p.total_bet_this_round > 0
        ))

        if len(amounts) <= 1:
            self.side_pots = []
            return

        self.side_pots = []
        previous_amount = 0

        for amount in amounts:
            side_pot = 0
            for player in self.players.values():
                if player.total_bet_this_round <= 0:
                    continue
                contribution = min(amount, player.total_bet_this_round) - previous_amount
                if contribution > 0:
                    side_pot += contribution

            if side_pot > 0:
                self.side_pots.append({
                    "amount": side_pot,
                    "eligible_players": [
                        p.user_id for p in self.players.values()
                        if p.total_bet_this_round >= amount and not p.is_folded
                    ]
                })

            previous_amount = amount
    
    def should_increase_blinds(self) -> bool:
        """检查是否应该升级盲注"""
        time_since_increase = datetime.utcnow() - self.last_blind_increase
        return time_since_increase >= timedelta(minutes=settings.blind_increase_minutes)
    
    def increase_blinds(self):
        """升级盲注"""
        self.blind_level += 1
        self.small_blind *= 2
        self.big_blind *= 2
        self.last_blind_increase = datetime.utcnow()
    
    def to_dict(self, spectator_view: bool = False, requesting_user_id: int = None) -> dict:
        """转换为字典（用于广播）"""
        players_data = []
        for position in sorted(self.players.keys()):
            player = self.players[position]
            # 旁观者、摊牌阶段、或玩家本人可以看到手牌
            show_cards = spectator_view or (self.stage == "showdown") or (player.user_id == requesting_user_id)
            players_data.append(player.to_dict(show_cards=show_cards))
        
        return {
            "players": players_data,
            "community_cards": self.community_cards,
            "pot_amount": self.pot_amount,
            "current_player": self.current_player_position,
            "stage": self.stage,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer_position": self.dealer_position,
            "action_timeout": self.action_timeout,
            "blind_level": self.blind_level,
        }