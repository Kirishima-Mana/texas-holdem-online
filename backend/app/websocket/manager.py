"""
WebSocket 连接管理器
"""
import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket
from datetime import datetime

from ..game.engine import GameEngine
from ..game.table import Table
from ..game.player import Player
from ..config import settings

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_to_user: Dict[str, int] = {}  # websocket_id -> user_id
        self.user_to_connection: Dict[int, str] = {}  # user_id -> websocket_id

        # 游戏引擎
        self.game_engine = GameEngine()

        # 广播锁
        self.broadcast_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int, session_token: str):
        """处理新连接"""
        websocket_id = str(id(websocket))

        self.active_connections[websocket_id] = websocket
        self.connection_to_user[websocket_id] = user_id
        self.user_to_connection[user_id] = websocket_id

        # 处理玩家重连
        await self.game_engine.handle_player_reconnect(user_id, websocket_id)

        logger.info(f"用户 {user_id} 已连接，WebSocket ID: {websocket_id}")

        # 发送欢迎消息
        await self.send_personal_message(websocket, {
            "type": "welcome",
            "data": {
                "message": "连接成功",
                "session_token": session_token,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

        # 广播游戏状态
        await self.broadcast_game_state()

    async def disconnect(self, websocket: WebSocket):
        """处理连接断开"""
        websocket_id = str(id(websocket))

        if websocket_id in self.active_connections:
            user_id = self.connection_to_user.get(websocket_id)

            del self.active_connections[websocket_id]

            if websocket_id in self.connection_to_user:
                del self.connection_to_user[websocket_id]

            if user_id and user_id in self.user_to_connection:
                del self.user_to_connection[user_id]

            if user_id:
                await self.game_engine.handle_player_disconnect(user_id)

            logger.info(f"WebSocket 断开: {websocket_id}, 用户: {user_id}")

            await self.broadcast_game_state()

    async def receive_message(self, websocket: WebSocket, message: str):
        """处理接收到的消息"""
        websocket_id = str(id(websocket))
        user_id = self.connection_to_user.get(websocket_id)

        if not user_id:
            return

        try:
            data = json.loads(message)
            message_type = data.get("type")
            message_data = data.get("data", {})

            if message_type == "action":
                await self.handle_player_action(user_id, message_data)
            elif message_type == "chat":
                await self.handle_chat_message(user_id, message_data)
            elif message_type == "join_table":
                await self.handle_join_table(user_id, message_data)
            elif message_type == "leave_table":
                await self.handle_leave_table(user_id, message_data)
            elif message_type == "start_game":
                await self.handle_start_game(user_id)
            elif message_type == "heartbeat":
                await self.send_personal_message(websocket, {
                    "type": "heartbeat_ack",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                })
            else:
                await self.send_personal_message(websocket, {
                    "type": "error",
                    "data": {"error": f"未知消息类型: {message_type}"}
                })

        except json.JSONDecodeError:
            await self.send_personal_message(websocket, {
                "type": "error",
                "data": {"error": "消息格式错误"}
            })
        except Exception as e:
            logger.error(f"处理消息出错: {e}", exc_info=True)
            await self.send_personal_message(websocket, {
                "type": "error",
                "data": {"error": "服务器内部错误"}
            })

    async def handle_player_action(self, user_id: int, data: dict):
        action = data.get("action")
        amount = data.get("amount")

        if action not in ["fold", "check", "call", "raise", "all_in"]:
            await self.send_to_user(user_id, {
                "type": "error",
                "data": {"error": f"无效行动: {action}"}
            })
            return

        result = await self.game_engine.process_player_action(user_id, action, amount)

        if result["success"]:
            await self.broadcast_message({
                "type": "action_result",
                "data": {
                    "user_id": user_id,
                    "action": action,
                    "amount": amount,
                    "message": result.get("message", ""),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            await self.broadcast_game_state()
        else:
            await self.send_to_user(user_id, {
                "type": "error",
                "data": {"error": result.get("error", "行动失败")}
            })

    async def handle_chat_message(self, user_id: int, data: dict):
        message = data.get("message", "").strip()
        if not message:
            return

        player = self.game_engine.table.get_player_by_user_id(user_id)
        username = player.username if player else f"用户{user_id}"

        await self.broadcast_message({
            "type": "chat",
            "data": {
                "user_id": user_id,
                "username": username,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "is_system": False
            }
        })

    async def handle_join_table(self, user_id: int, data: dict):
        position = data.get("position")
        buyin_type = data.get("buyin_type", "new")

        player = self.game_engine.table.get_player_by_user_id(user_id)
        if not player:
            # 创建新玩家对象
            from ..auth import get_user_session
            from ..database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                from ..models import User
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if not user:
                    await self.send_to_user(user_id, {"type": "error", "data": {"error": "用户不存在"}})
                    return

                sessions = await db.execute(
                    select(User.__table__).where(User.id == user_id)
                )
                player = Player(
                    user_id=user.id,
                    username=user.username,
                    session_token="",
                    websocket_id=self.user_to_connection.get(user_id)
                )

        if self.game_engine.is_game_active:
            await self.send_to_user(user_id, {
                "type": "error",
                "data": {"error": "游戏进行中，请等待当前手牌结束"}
            })
            return

        # 计算买入筹码
        if buyin_type == "new":
            chips = settings.initial_chips
        elif buyin_type == "rebuy":
            active = self.game_engine.table.get_active_players()
            if active:
                chips_list = sorted([p.chips for p in active])
                median = chips_list[len(chips_list) // 2]
                chips = median // 2
            else:
                chips = settings.initial_chips
        else:
            chips = settings.initial_chips

        player.chips = chips
        player.is_connected = True

        success = self.game_engine.table.add_player(player, position)

        if success:
            await self.broadcast_message({
                "type": "player_joined",
                "data": {
                    "user_id": user_id,
                    "username": player.username,
                    "position": player.position,
                    "chips": chips,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            await self.broadcast_game_state()
        else:
            await self.send_to_user(user_id, {
                "type": "error",
                "data": {"error": "加入牌桌失败"}
            })

    async def handle_leave_table(self, user_id: int, data: dict):
        leave_type = data.get("type", "temporary")

        player = self.game_engine.table.get_player_by_user_id(user_id)
        if not player:
            return

        if (self.game_engine.is_game_active
                and self.game_engine.table.current_player_position == player.position
                and self.game_engine._can_player_act(player)):
            await self.game_engine.process_player_action(user_id, "fold")

        keep_chips = (leave_type == "temporary")
        removed = self.game_engine.table.remove_player(user_id, keep_chips)

        if removed:
            await self.broadcast_message({
                "type": "player_left",
                "data": {
                    "user_id": user_id,
                    "username": player.username,
                    "leave_type": leave_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            await self.broadcast_game_state()

    async def handle_start_game(self, user_id: int):
        player = self.game_engine.table.get_player_by_user_id(user_id)
        if not player or not player.is_host:
            await self.send_to_user(user_id, {
                "type": "error",
                "data": {"error": "只有房主可以开始游戏"}
            })
            return

        try:
            self.game_engine.start_game()
            await self.broadcast_message({
                "type": "game_started",
                "data": {
                    "hand_id": self.game_engine.hand_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": f"游戏开始！第 {self.game_engine.hand_id} 手牌"
                }
            })
            await self.broadcast_game_state()
        except ValueError as e:
            await self.send_to_user(user_id, {
                "type": "error",
                "data": {"error": str(e)}
            })

    async def broadcast_message(self, message: dict):
        async with self.broadcast_lock:
            disconnected = []
            for ws_id, websocket in self.active_connections.items():
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(ws_id)

            for ws_id in disconnected:
                if ws_id in self.active_connections:
                    del self.active_connections[ws_id]
                if ws_id in self.connection_to_user:
                    uid = self.connection_to_user.pop(ws_id)
                    self.user_to_connection.pop(uid, None)

    async def broadcast_game_state(self):
        for ws_id, websocket in self.active_connections.items():
            user_id = self.connection_to_user.get(ws_id)
            if user_id:
                game_state = self.game_engine.get_game_state(user_id)
                try:
                    await websocket.send_json({
                        "type": "game_state",
                        "data": game_state
                    })
                except Exception:
                    pass

    async def send_to_user(self, user_id: int, message: dict):
        ws_id = self.user_to_connection.get(user_id)
        if not ws_id:
            return
        websocket = self.active_connections.get(ws_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception:
                pass

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    def get_room_info(self) -> dict:
        active = self.game_engine.table.get_active_players()
        connected = self.game_engine.table.get_connected_players()
        host = None
        for p in self.game_engine.table.players.values():
            if p.is_host:
                host = p
                break

        return {
            "player_count": len(active),
            "spectator_count": max(0, len(connected) - len(active)),
            "is_game_active": self.game_engine.is_game_active,
            "host_username": host.username if host else None,
            "blind_level": self.game_engine.table.blind_level,
            "max_players": settings.max_players,
            "min_players": settings.min_players
        }