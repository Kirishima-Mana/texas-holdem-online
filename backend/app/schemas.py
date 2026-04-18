from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========== 用户相关 ==========
class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserLogin(UserBase):
    password: str


class UserInDB(UserBase):
    id: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    session_token: str


# ========== 游戏状态 ==========
class PlayerInfo(BaseModel):
    """玩家信息（用于广播）"""
    user_id: int
    username: str
    position: int
    chips: int
    current_bet: int
    is_active: bool
    has_acted: bool
    is_folded: bool
    is_all_in: bool
    cards: Optional[List[str]] = None  # 只有自己能看到


class TableState(BaseModel):
    """牌桌状态"""
    players: List[PlayerInfo]
    community_cards: List[str]
    pot_amount: int
    current_player: Optional[int] = None
    stage: str  # preflop, flop, turn, river, showdown
    small_blind: int
    big_blind: int
    dealer_position: int
    action_timeout: int


class GameStatus(BaseModel):
    """游戏状态"""
    is_active: bool
    table_state: Optional[TableState] = None
    blind_level: int
    next_blind_increase: Optional[datetime] = None


# ========== WebSocket 消息 ==========
class WSMessage(BaseModel):
    """WebSocket 消息基类"""
    type: str
    data: Dict[str, Any]


class ActionRequest(BaseModel):
    """玩家行动请求"""
    action: str  # fold, check, call, raise, all_in
    amount: Optional[int] = None  # raise 时的加注金额


class ChatMessage(BaseModel):
    """聊天消息"""
    message: str


# ========== 房间管理 ==========
class RoomInfo(BaseModel):
    """房间信息"""
    player_count: int
    spectator_count: int
    is_game_active: bool
    host_username: str
    blind_level: int


# ========== 响应模型 ==========
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None