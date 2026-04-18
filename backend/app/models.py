from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from .database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # 关系
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    game_records = relationship("GameRecord", back_populates="user")


class UserSession(Base):
    """用户会话模型（用于断线重连）"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, index=True)
    websocket_id = Column(String(100), nullable=True)  # 当前 WebSocket 连接 ID
    table_position = Column(Integer, nullable=True)  # 在牌桌上的位置，null 表示旁观
    chips = Column(Integer, default=0)  # 当前筹码量
    is_host = Column(Boolean, default=False)
    status = Column(String(20), default="spectator")  # active, spectator, disconnected
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="sessions")
    hand_cards = relationship("PlayerHand", back_populates="session")


class GameState(Base):
    """游戏全局状态"""
    __tablename__ = "game_state"
    
    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=False)
    current_hand_id = Column(Integer, nullable=True)
    small_blind = Column(Integer, default=50)
    big_blind = Column(Integer, default=100)
    blind_level = Column(Integer, default=1)
    last_blind_increase = Column(DateTime(timezone=True), server_default=func.now())
    dealer_position = Column(Integer, default=0)
    current_player_position = Column(Integer, nullable=True)
    pot_amount = Column(Integer, default=0)
    community_cards = Column(JSON, default=list)  # 公共牌列表
    stage = Column(String(20), default="waiting")  # waiting, preflop, flop, turn, river, showdown
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PlayerHand(Base):
    """玩家手牌记录"""
    __tablename__ = "player_hands"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False)
    hand_id = Column(Integer, nullable=False)  # 关联到哪一手牌
    card1 = Column(String(3), nullable=False)  # 如 "Ah" (Ace of hearts)
    card2 = Column(String(3), nullable=False)
    is_folded = Column(Boolean, default=False)
    current_bet = Column(Integer, default=0)
    has_acted = Column(Boolean, default=False)
    
    # 关系
    session = relationship("UserSession", back_populates="hand_cards")


class GameRecord(Base):
    """游戏记录"""
    __tablename__ = "game_records"
    
    id = Column(Integer, primary_key=True, index=True)
    hand_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)
    cards = Column(JSON, nullable=False)  # [card1, card2]
    action_history = Column(JSON, default=list)  # 行动记录
    result = Column(String(20), nullable=True)  # win, lose, tie
    chips_won = Column(Integer, default=0)
    chips_lost = Column(Integer, default=0)
    end_chips = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="game_records")


class ChatMessage(Base):
    """聊天消息"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    username = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User")