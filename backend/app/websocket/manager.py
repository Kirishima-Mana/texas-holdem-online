"""
WebSocket 连接管理器
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional
from websockets.server import WebSocketServerProtocol
from datetime import datetime

from ..game.engine import GameEngine
from ..game.table import Table
from ..game.player import Player
from ..config import settings

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocketServerProtocol] = {}
        self.connection_to_user: Dict[str, int] = {}  # websocket_id -> user_id
        self.user_to_connection: Dict[int, str] = {}  # user_id -> websocket_id
        
        # 游戏引擎
        self.game_engine = GameEngine()
        
        # 广播锁，防止并发广播冲突
        self.broadcast_lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocketServerProtocol, user_id: int, session_token: str):
        """处理新连接"""
        websocket_id = id(websocket)
        
        # 存储连接
        self.active_connections[str(websocket_id)] = websocket
        self.connection_to_user[str(websocket_id)] = user_id
        self.user_to_connection[user_id] = str(websocket_id)
        
        # 处理玩家重连
        await self.game_engine.handle_player_reconnect(user_id, str(websocket_id))
        
        logger.info(f"用户 {user_id} 已连接，WebSocket ID: {websocket_id}")
        
        # 发送欢迎消息和当前游戏状态
        await self.send_personal_message(
            websocket,
            {
                "type": "welcome",
                "data": {
                    "message": "连接成功",
                    "session_token": session_token,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
        
        # 广播游戏状态更新
        await self.broadcast_game_state()
    
    async def disconnect(self, websocket: WebSocketServerProtocol):
        """处理连接断开"""
        websocket_id = str(id(websocket))
        
        if websocket_id in self.active_connections:
            # 获取用户ID
            user_id = self.connection_to_user.get(websocket_id)
            
            # 移除连接
            del self.active_connections[websocket_id]
            
            if websocket_id in self.connection_to_user:
                del self.connection_to_user[websocket_id]
            
            if user_id and user_id in self.user_to_connection:
                del self.user_to_connection[user_id]
            
            # 处理玩家断开连接
            if user_id:
                await self.game_engine.handle_player_disconnect(user_id)
            
            logger.info(f"WebSocket 连接断开: {websocket_id}, 用户: {user_id}")
            
            # 广播游戏状态更新
            await self.broadcast_game_state()
    
    async def receive_message(self, websocket: WebSocketServerProtocol, message: str):
        """处理接收到的消息"""
        websocket_id = str(id(websocket))
        user_id = self.connection_to_user.get(websocket_id)
        
        if not user_id:
            logger.warning(f"收到未知连接的消息: {websocket_id}")
            return
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            message_data = data.get("data", {})
            
            logger.debug(f"收到消息 from {user_id}: {message_type}")
            
            # 根据消息类型处理
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
                await self.handle_heartbeat(user_id, websocket)
            
            else:
                logger.warning(f"未知消息类型: {message_type}")
                await self.send_personal_message(
                    websocket,
                    {
                        "type": "error",
                        "data": {"error": f"未知消息类型: {message_type}"}
                    }
                )
        
        except json.JSONDecodeError:
            logger.error(f"消息JSON解析失败: {message}")
            await self.send_personal_message(
                websocket,
                {
                    "type": "error",
                    "data": {"error": "消息格式错误"}
                }
            )
        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            await self.send_personal_message(
                websocket,
                {
                    "type": "error",
                    "data": {"error": "服务器内部错误"}
                }
            )
    
    async def handle_player_action(self, user_id: int, data: dict):
        """处理玩家行动"""
        action = data.get("action")
        amount = data.get("amount")
        
        # 验证行动
        if action not in ["fold", "check", "call", "raise", "all_in"]:
            await self.send_to_user(
                user_id,
                {
                    "type": "error",
                    "data": {"error": f"无效行动: {action}"}
                }
            )
            return
        
        # 处理行动
        result = await self.game_engine.process_player_action(user_id, action, amount)
        
        if result["success"]:
            # 广播行动结果和游戏状态更新
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
            # 发送错误消息给玩家
            await self.send_to_user(
                user_id,
                {
                    "type": "error",
                    "data": {"error": result.get("error", "行动失败")}
                }
            )
    
    async def handle_chat_message(self, user_id: int, data: dict):
        """处理聊天消息"""
        message = data.get("message", "").strip()
        
        if not message:
            return
        
        # 获取用户名
        player = self.game_engine.table.get_player_by_user_id(user_id)
        username = player.username if player else f"用户{user_id}"
        
        # 广播聊天消息
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
        """处理玩家加入牌桌"""
        position = data.get("position")
        buyin_type = data.get("buyin_type", "new")  # new, rebuy
        
        player = self.game_engine.table.get_player_by_user_id(user_id)
        if not player:
            await self.send_to_user(
                user_id,
                {
                    "type": "error",
                    "data": {"error": "玩家不存在"}
                }
            )
            return
        
        # 检查游戏是否进行中
        if self.game_engine.is_game_active:
            await self.send_to_user(
                user_id,
                {
                    "type": "error",
                    "data": {"error": "游戏进行中，请等待当前手牌结束"}
                }
            )
            return
        
        # 计算买入筹码
        if buyin_type == "new":
            chips = settings.initial_chips
        elif buyin_type == "rebuy":
            # 重新买入：当前场上筹码中位数的50%
            active_players = self.game_engine.table.get_active_players()
            if active_players:
                chips_list = [p.chips for p in active_players]
                median_chips = sorted(chips_list)[len(chips_list) // 2]
                chips = median_chips // 2
            else:
                chips = settings.initial_chips
        else:
            chips = settings.initial_chips
        
        # 设置玩家筹码
        player.chips = chips
        
        # 添加到牌桌
        success = self.game_engine.table.add_player(player, position)
        
        if success:
            # 广播玩家加入
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
            await self.send_to_user(
                user_id,
                {
                    "type": "error",
                    "data": {"error": "加入牌桌失败"}
                }
            )
    
    async def handle_leave_table(self, user_id: int, data: dict):
        """处理玩家离开牌桌"""
        leave_type = data.get("type", "temporary")  # temporary, permanent
        
        player = self.game_engine.table.get_player_by_user_id(user_id)
        if not player:
            return
        
        # 如果游戏进行中且玩家正在行动，自动弃牌
        if (self.game_engine.is_game_active and 
            self.game_engine.table.current_player_position == player.position and 
            player.can_act()):
            await self.game_engine.process_player_action(user_id, "fold")
        
        # 从牌桌移除玩家
        keep_chips = (leave_type == "temporary")
        removed_player = self.game_engine.table.remove_player(user_id, keep_chips)
        
        if removed_player:
            # 广播玩家离开
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
        """处理开始游戏请求"""
        player = self.game_engine.table.get_player_by_user_id(user_id)
        if not player or not player.is_host:
            await self.send_to_user(
                user_id,
                {
                    "type": "error",
                    "data": {"error": "只有房主可以开始游戏"}
                }
            )
            return
        
        try:
            self.game_engine.start_game()
            
            # 广播游戏开始
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
            await self.send_to_user(
                user_id,
                {
                    "type": "error",
                    "data": {"error": str(e)}
                }
            )
    
    async def handle_heartbeat(self, user_id: int, websocket: WebSocketServerProtocol):
        """处理心跳"""
        await self.send_personal_message(
            websocket,
            {
                "type": "heartbeat_ack",
                "data": {"timestamp": datetime.utcnow().isoformat()}
            }
        )
    
    async def broadcast_message(self, message: dict):
        """广播消息给所有连接"""
        async with self.broadcast_lock:
            disconnected = []
            
            for websocket_id, websocket in self.active_connections.items():
                try:
                    await websocket.send(json.dumps(message))
                except Exception as e:
                    logger.error(f"广播消息失败: {e}")
                    disconnected.append(websocket_id)
            
            # 清理断开连接的客户端
            for websocket_id in disconnected:
                if websocket_id in self.active_connections:
                    websocket = self.active_connections[websocket_id]
                    await self.disconnect(websocket)
    
    async def broadcast_game_state(self):
        """广播游戏状态更新"""
        # 给每个玩家/旁观者发送适合他们视角的游戏状态
        for websocket_id, websocket in self.active_connections.items():
            user_id = self.connection_to_user.get(websocket_id)
            if user_id:
                game_state = self.game_engine.get_game_state(user_id)
                
                try:
                    await websocket.send(json.dumps({
                        "type": "game_state",
                        "data": game_state
                    }))
                except Exception as e:
                    logger.error(f"发送游戏状态失败: {e}")
    
    async def send_to_user(self, user_id: int, message: dict):
        """发送消息给特定用户"""
        websocket_id = self.user_to_connection.get(user_id)
        if not websocket_id:
            logger.warning(f"用户 {user_id} 未连接")
            return
        
        websocket = self.active_connections.get(websocket_id)
        if websocket:
            try:
                await websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"发送消息给用户 {user_id} 失败: {e}")
    
    async def send_personal_message(self, websocket: WebSocketServerProtocol, message: dict):
        """发送个人消息"""
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
    
    def get_room_info(self) -> dict:
        """获取房间信息"""
        active_players = self.game_engine.table.get_active_players()
        connected_players = self.game_engine.table.get_connected_players()
        
        host_player = None
        for player in self.game_engine.table.players.values():
            if player.is_host:
                host_player = player
                break
        
        return {
            "player_count": len(active_players),
            "spectator_count": len(connected_players) - len(active_players),
            "is_game_active": self.game_engine.is_game_active,
            "host_username": host_player.username if host_player else None,
            "blind_level": self.game_engine.table.blind_level,
            "max_players": settings.max_players,
            "min_players": settings.min_players
        }