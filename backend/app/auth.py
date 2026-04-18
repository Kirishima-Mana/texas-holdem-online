from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from .config import settings
from .models import User, UserSession
from .schemas import UserCreate, UserLogin


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def generate_session_token() -> str:
    """生成会话 token（用于断线重连）"""
    return secrets.token_urlsafe(32)


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """验证用户"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """创建新用户"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_create.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise ValueError("用户名已存在")
    
    # 创建用户
    user = User(
        username=user_create.username,
        password_hash=get_password_hash(user_create.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_user_session(db: AsyncSession, user: User, is_host: bool = False) -> UserSession:
    """创建用户会话"""
    session_token = generate_session_token()
    
    user_session = UserSession(
        user_id=user.id,
        session_token=session_token,
        is_host=is_host,
        status="spectator",
        chips=0
    )
    
    db.add(user_session)
    await db.commit()
    await db.refresh(user_session)
    return user_session


async def get_user_session(db: AsyncSession, session_token: str) -> Optional[UserSession]:
    """获取用户会话"""
    result = await db.execute(
        select(UserSession).where(UserSession.session_token == session_token)
    )
    return result.scalar_one_or_none()


async def update_session_websocket(db: AsyncSession, session_token: str, websocket_id: str) -> None:
    """更新会话的 WebSocket ID"""
    result = await db.execute(
        select(UserSession).where(UserSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()
    
    if session:
        session.websocket_id = websocket_id
        session.status = "spectator" if session.table_position is None else "active"
        session.last_heartbeat = datetime.utcnow()
        await db.commit()


async def disconnect_session(db: AsyncSession, websocket_id: str) -> None:
    """断开会话连接"""
    result = await db.execute(
        select(UserSession).where(UserSession.websocket_id == websocket_id)
    )
    session = result.scalar_one_or_none()
    
    if session:
        session.websocket_id = None
        session.status = "disconnected"
        await db.commit()