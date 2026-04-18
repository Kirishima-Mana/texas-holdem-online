"""
玩家状态管理
"""
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


@dataclass
class Player:
    """玩家游戏状态"""
    user_id: int
    username: str
    session_token: str
    websocket_id: Optional[str] = None
    
    # 牌桌位置
    position: Optional[int] = None  # 0-9，None 表示旁观
    
    # 筹码相关
    chips: int = 0
    current_bet: int = 0
    total_bet_this_round: int = 0
    
    # 手牌
    hole_cards: List[str] = field(default_factory=list)
    is_folded: bool = False
    is_all_in: bool = False
    has_acted: bool = False
    
    # 状态
    is_active: bool = False  # 是否在牌桌上
    is_connected: bool = True
    is_host: bool = False
    
    # 重连相关
    rebuy_count: int = 0
    last_action_time: Optional[datetime] = None
    
    def reset_for_new_hand(self):
        """重置为新的一手牌"""
        self.hole_cards = []
        self.is_folded = False
        self.is_all_in = False
        self.has_acted = False
        self.current_bet = 0
        self.total_bet_this_round = 0
    
    def can_act(self) -> bool:
        """检查玩家是否可以行动"""
        return (
            self.is_active and 
            not self.is_folded and 
            not self.is_all_in and 
            self.is_connected
        )
    
    def bet(self, amount: int) -> bool:
        """下注"""
        if amount > self.chips:
            return False
        
        self.chips -= amount
        self.current_bet += amount
        self.total_bet_this_round += amount
        
        if self.chips == 0:
            self.is_all_in = True
        
        self.has_acted = True
        self.last_action_time = datetime.utcnow()
        return True
    
    def fold(self):
        """弃牌"""
        self.is_folded = True
        self.has_acted = True
        self.last_action_time = datetime.utcnow()
    
    def check_or_call(self, amount_to_call: int) -> bool:
        """过牌或跟注"""
        if amount_to_call == 0:
            # 过牌
            self.has_acted = True
            self.last_action_time = datetime.utcnow()
            return True
        else:
            # 跟注
            return self.bet(amount_to_call)
    
    def get_call_amount(self, current_max_bet: int) -> int:
        """获取需要跟注的金额"""
        return max(0, current_max_bet - self.current_bet)
    
    def to_dict(self, show_cards: bool = False) -> dict:
        """转换为字典（用于广播）"""
        data = {
            "user_id": self.user_id,
            "username": self.username,
            "position": self.position,
            "chips": self.chips,
            "current_bet": self.current_bet,
            "is_active": self.is_active,
            "has_acted": self.has_acted,
            "is_folded": self.is_folded,
            "is_all_in": self.is_all_in,
            "is_connected": self.is_connected,
            "is_host": self.is_host,
        }
        
        if show_cards and self.hole_cards:
            data["cards"] = self.hole_cards
        else:
            data["cards"] = None
        
        return data