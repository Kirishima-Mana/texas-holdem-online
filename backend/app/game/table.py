"""
牌桌管理 - 重构版
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random

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

    # 游戏阶段
    stage: str = "waiting"  # waiting, preflop, flop, turn, river, showdown
    current_player_position: Optional[int] = None
    dealer_position: int = -1
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

    # 房主
    host_user_id: Optional[int] = None

    def __post_init__(self):
        self.reset_deck()

    def reset_deck(self):
        """创建并洗牌"""
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        suits = ['h', 'd', 'c', 's']
        self.deck = [f"{r}{s}" for r in ranks for s in suits]
        random.shuffle(self.deck)

    def add_player(self, player: Player, position: Optional[int] = None) -> bool:
        """添加玩家到牌桌"""
        if len(self.players) >= settings.max_players:
            return False

        if position is None:
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

        if self.host_user_id is None:
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

            if not keep_chips:
                player.chips = 0

            player.is_active = False
            player.position = None

            # 转移房主权限
            if user_id == self.host_user_id and self.players:
                new_host_pos = min(self.players.keys())
                new_host = self.players[new_host_pos]
                new_host.is_host = True
                self.host_user_id = new_host.user_id

        return player

    def get_player_by_position(self, position: int) -> Optional[Player]:
        return self.players.get(position)

    def get_player_by_user_id(self, user_id: int) -> Optional[Player]:
        position = self.player_positions.get(user_id)
        if position is not None:
            return self.players.get(position)
        return None

    def get_active_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.is_active]

    def get_connected_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.is_active and p.is_connected]

    def reset_for_new_hand(self):
        """重置为新的一手牌"""
        self.reset_deck()
        self.community_cards = []
        self.pot_amount = 0
        self.current_max_bet = 0

        # 重置玩家状态
        for player in self.players.values():
            player.reset_for_new_hand()

        # 更新庄家位置
        self.dealer_position = self._next_active_position(self.dealer_position)

        active_count = len([p for p in self.players.values() if p.is_active])
        if active_count == 2:
            # Heads-up: 庄家 = 小盲注
            self.small_blind_position = self.dealer_position
            self.big_blind_position = self._next_active_position(self.dealer_position)
        else:
            # 正常: 小盲注 = 庄家下一个，大盲注 = 小盲注下一个
            self.small_blind_position = self._next_active_position(self.dealer_position)
            self.big_blind_position = self._next_active_position(self.small_blind_position)

        self.stage = "preflop"

    def _next_active_position(self, start_position: int) -> int:
        """获取下一个活跃玩家的位置（用于庄家/盲注轮转）"""
        positions = sorted(self.players.keys())
        if not positions:
            return 0

        # 找到 start_position 在排序后列表中的位置
        idx = -1
        for i, pos in enumerate(positions):
            if pos == start_position:
                idx = i
                break

        # 从 start_position 的下一个开始搜索
        for i in range(1, len(positions) + 1):
            check_idx = (idx + i) % len(positions)
            pos = positions[check_idx]
            player = self.players.get(pos)
            if player and player.is_active:
                return pos

        return positions[0]

    def should_increase_blinds(self) -> bool:
        """检查是否应该升级盲注"""
        time_since = datetime.utcnow() - self.last_blind_increase
        return time_since >= timedelta(minutes=settings.blind_increase_minutes)

    def increase_blinds(self):
        """升级盲注"""
        self.blind_level += 1
        self.small_blind *= 2
        self.big_blind *= 2
        self.last_blind_increase = datetime.utcnow()

    def to_dict(self, spectator_view: bool = False) -> dict:
        """转换为字典（用于广播）"""
        players_data = []
        for position in sorted(self.players.keys()):
            player = self.players[position]
            show_cards = spectator_view or (self.stage == "showdown")
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