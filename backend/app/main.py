"""
德州扑克在线游戏 - 主应用
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import init_db, get_db
from .auth import authenticate_user, create_user, create_user_session, create_access_token
from .schemas import UserCreate, UserLogin, Token, SuccessResponse, RoomInfo
from .websocket.handlers import websocket_endpoint, get_room_info

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    logger.info("初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")
    
    yield
    
    # 关闭时清理资源
    logger.info("应用关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API 路由 ==========
@app.get("/")
async def root():
    """根端点"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/api/auth/register", response_model=SuccessResponse)
async def register(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    try:
        user = await create_user(db, user_create)
        
        # 创建用户会话
        session = await create_user_session(db, user, is_host=False)
        
        # 创建访问令牌
        access_token = create_access_token(
            data={"sub": user.username, "session_token": session.session_token}
        )
        
        return SuccessResponse(
            success=True,
            message="注册成功",
            data={
                "user": {
                    "id": user.id,
                    "username": user.username
                },
                "token": Token(
                    access_token=access_token,
                    token_type="bearer",
                    session_token=session.session_token
                ).dict()
            }
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"注册失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@app.post("/api/auth/login", response_model=SuccessResponse)
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    user = await authenticate_user(db, user_login.username, user_login.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    # 创建用户会话
    session = await create_user_session(db, user, is_host=False)
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": user.username, "session_token": session.session_token}
    )
    
    return SuccessResponse(
        success=True,
        message="登录成功",
        data={
            "user": {
                "id": user.id,
                "username": user.username
            },
            "token": Token(
                access_token=access_token,
                token_type="bearer",
                session_token=session.session_token
            ).dict()
        }
    )


@app.get("/api/room/info", response_model=SuccessResponse)
async def get_room_info_api():
    """获取房间信息"""
    try:
        room_info = await get_room_info()
        return SuccessResponse(
            success=True,
            message="房间信息获取成功",
            data={"room": room_info}
        )
    except Exception as e:
        logger.error(f"获取房间信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取房间信息失败"
        )


# ========== WebSocket 路由 ==========
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket, token: str = None):
    """WebSocket 连接"""
    await websocket_endpoint(websocket, token)


# ========== 错误处理 ==========
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "details": exc.headers if exc.headers else None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "服务器内部错误",
            "details": str(exc) if settings.debug else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )