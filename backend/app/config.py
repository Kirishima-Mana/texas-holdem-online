from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    app_name: str = "Texas Hold'em Online"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///data/texas_holdem.db"
    
    # WebSocket 配置
    websocket_ping_interval: int = 20
    websocket_ping_timeout: int = 30
    websocket_max_size: int = 10 * 1024 * 1024  # 10MB
    
    # 游戏配置
    max_players: int = 10
    min_players: int = 2
    initial_chips: int = 20000
    small_blind: int = 50
    big_blind: int = 100
    action_timeout: int = 25  # 秒
    blind_increase_minutes: int = 15  # 每15分钟盲注升级
    
    # 认证配置
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24小时
    
    class Config:
        env_file = ".env"


settings = Settings()