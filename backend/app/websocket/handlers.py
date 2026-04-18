"""
WebSocket 处理器
"""
import json
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from ..config import settings
from ..auth import get_user_session, update_session_websocket, disconnect_session
from .manager import WebSocketManager

logger = logging.getLogger(__name__)

# 全局 WebSocket 管理器
ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """WebSocket 端点"""
    # 验证 token
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    try:
        # 解析 token 获取 session_token
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        session_token = payload.get("session_token")
        
        if not session_token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # 获取用户会话
        from ..database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            session = await get_user_session(db, session_token)
            
            if not session:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            user_id = session.user_id
            
            # 接受 WebSocket 连接
            await websocket.accept()
            
            # 更新会话的 WebSocket ID
            await update_session_websocket(db, session_token, str(id(websocket)))
            
            # 连接到管理器
            await ws_manager.connect(websocket, user_id, session_token)
            
            # 处理消息
            try:
                while True:
                    message = await websocket.receive_text()
                    await ws_manager.receive_message(websocket, message)
            
            except WebSocketDisconnect:
                logger.info(f"WebSocket 正常断开: {user_id}")
            
            except Exception as e:
                logger.error(f"WebSocket 错误: {e}", exc_info=True)
            
            finally:
                # 断开连接
                await ws_manager.disconnect(websocket)
                
                # 更新数据库中的会话状态
                async with AsyncSessionLocal() as db:
                    await disconnect_session(db, str(id(websocket)))
    
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.error(f"WebSocket 端点错误: {e}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


async def get_room_info():
    """获取房间信息"""
    return ws_manager.get_room_info()