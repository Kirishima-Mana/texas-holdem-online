# 德州扑克在线游戏 — 项目记忆

## 项目概述

在线德州扑克游戏，支持 2-10 人实时对战、断线重连、旁观者上帝视角、锦标赛盲注模式。

- **后端**: FastAPI + WebSocket + SQLite (SQLAlchemy async)
- **前端**: Vue 3 + TypeScript + Vite + Pinia + Tailwind CSS
- **部署**: Docker Compose (Nginx 反向代理 + FastAPI 后端)

---

## 文件作用清单

### 根目录

| 文件 | 作用 |
|------|------|
| `docker-compose.yml` | Docker 编排，定义 frontend（Nginx:80）和 backend（FastAPI:8000）两个服务 |
| `deploy.sh` | 一键部署脚本，检查环境、构建镜像、启动服务、健康检查 |
| `.env.example` | 环境变量模板，包含 SECRET_KEY、端口配置等 |
| `README.md` | 项目说明文档 |
| `ARCHITECTURE.md` | 架构设计文档（状态机、通信协议、数据模型等） |
| `QUICK_START.md` | 快速开始指南 |
| `WorksFoFar.md` | Gemini 留下的交接文档，记录了白屏 Bug 的排查线索 |
| `memory.md` | 本文件，记录项目文件作用和改动历史 |

### 后端 — `backend/`

| 文件 | 作用 |
|------|------|
| `Dockerfile` | Python 3.11-slim 镜像，安装依赖后以非 root 用户运行 uvicorn |
| `requirements.txt` | Python 依赖（fastapi, uvicorn, sqlalchemy, aiosqlite, treys, python-jose, passlib 等） |
| `test_game.py` | 游戏引擎测试脚本，测试基本游戏流程和扑克牌型逻辑 |
| `app/main.py` | FastAPI 应用入口，定义 REST API（/api/auth/register, /api/auth/login, /api/room/info）和 WebSocket 端点（/ws），CORS 和异常处理 |
| `app/config.py` | Pydantic Settings 配置类，读取环境变量（游戏参数、数据库 URL、JWT 密钥等） |
| `app/database.py` | SQLAlchemy 异步引擎和会话工厂，`init_db()` 初始化表结构 |
| `app/models.py` | ORM 模型：User, UserSession, GameState, PlayerHand, GameRecord, ChatMessage |
| `app/schemas.py` | Pydantic 请求/响应模型（用户、游戏状态、WebSocket 消息、房间信息） |
| `app/auth.py` | 认证逻辑：密码哈希（bcrypt）、JWT 令牌创建/验证、用户 CRUD、会话管理 |
| `app/game/__init__.py` | 游戏引擎模块初始化 |
| `app/game/engine.py` | **核心游戏引擎**：状态机控制（preflop→flop→turn→river→showdown）、玩家行动处理、盲注收取、回合推进、胜负判定、筹码分配、超时处理、断线重连 |
| `app/game/table.py` | **牌桌管理**：玩家座位、牌堆/公共牌管理、下注池、边池计算、盲注升级、庄家轮转 |
| `app/game/player.py` | **玩家状态**：筹码、手牌、下注、弃牌/全下标记、行动权限检查 |
| `app/utils/poker_logic.py` | **扑克牌型评估**：基于 treys 库的牌型比较、牌堆创建/洗牌/发牌 |
| `app/websocket/manager.py` | **WebSocket 连接管理器**：连接/断开管理、消息路由（action/chat/join_table/leave_table/start_game/heartbeat）、广播消息、游戏状态广播 |
| `app/websocket/handlers.py` | WebSocket 端点处理：JWT 验证、会话恢复、消息接收循环 |

### 前端 — `frontend/`

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 多阶段构建：Node 18 构建 Vue 应用，Nginx Alpine 运行 |
| `nginx.conf` | Nginx 配置：`/` 静态文件、`/api` 代理后端、`/ws` WebSocket 代理 |
| `package.json` | 前端依赖和脚本（vue, pinia, vue-router, axios, tailwindcss, vite 等） |
| `vite.config.ts` | Vite 配置：@ 别名、开发服务器端口 5173、API/WS 代理 |
| `tsconfig.json` | TypeScript 编译配置 |
| `tailwind.config.js` | Tailwind 自定义主题色（poker-green, poker-gold 等）和动画 |
| `postcss.config.js` | PostCSS 配置（Tailwind + Autoprefixer） |
| `index.html` | HTML 入口，含加载动画 |
| `src/main.ts` | Vue 应用入口，挂载 Pinia + Router |
| `src/App.vue` | 根组件，路由视图 + 自动重连逻辑 |
| `src/router/index.ts` | 路由定义（/login, /lobby）+ 认证守卫 |
| `src/types/game.ts` | TypeScript 类型定义（User, PlayerInfo, TableState, GameStatus, WSMessage 等） |
| `src/utils/poker.ts` | 工具函数：牌面格式化、牌型中文名、筹码格式化、倒计时格式化 |
| `src/services/api.ts` | Axios HTTP 客户端：register, login, getRoomInfo, healthCheck + JWT 拦截器 |
| `src/services/websocket.ts` | WebSocket 客户端：连接/重连/心跳、消息处理、action/chat/join/leave/start 发送方法 |
| `src/stores/auth.ts` | Pinia 认证状态：用户信息、JWT 令牌、localStorage 持久化、register/login/logout |
| `src/stores/game.ts` | Pinia 游戏状态：牌桌状态、房间信息、聊天消息、当前玩家计算属性 |
| `src/components/Login.vue` | 登录/注册页面：表单验证、API 调用、WebSocket 连接 |
| `src/components/Lobby.vue` | **游戏大厅（核心页面）**：牌桌视图、玩家座位、行动按钮、加注对话框、聊天面板、房间信息、玩家列表 |
| `src/components/PokerCard.vue` | 扑克牌组件：正面/背面显示、花式/点数、尺寸和旋转 |
| `src/components/CommunityCards.vue` | 公共牌区域：翻牌/转牌/河牌展示、阶段指示器、底池显示 |
| `src/components/ActionButtons.vue` | 行动按钮组件（fold/check/call/raise/all_in）+ 加注对话框 |
| `src/components/PlayerSeat.vue` | 玩家座位组件：头像、筹码、手牌（旁观/摊牌时可见）、状态标签 |
| `src/components/ChatPanel.vue` | 聊天面板：消息列表、输入框、未读计数、时间格式化 |
| `src/components/Timer.vue` | 倒计时组件：圆形进度条、剩余时间显示、颜色变化（≤10s 红色闪烁） |
| `src/components/ChipDisplay.vue` | 筹码显示：单枚/筹码堆、金额缩写（K/M）、颜色编码 |
| `src/assets/css/tailwind.css` | Tailwind 基础样式 + 组件层自定义样式（btn, card, input, table-seat, poker-card, chip） |

---

## 改动记录

### 2026-05-01 — 首轮修复（Claude）

**修复内容**：

1. **前端白屏** — `api.ts` 默认 baseURL 改为 `''`（相对路径），`websocket.ts` 改为从 `window.location` 动态构造 WebSocket URL，彻底解决 Vite 环境变量在 Docker 构建时未注入导致的白屏死机问题。

2. **WebSocket send 方法名错误** — `manager.py` 中所有 `await websocket.send()` 改为 `await websocket.send_text()`，修复广播消息全部静默失败的问题。同时修正了错误的类型导入（`WebSocketServerProtocol` → `WebSocket`）。

3. **Player 对象从未创建** — `manager.py` 的 `handle_join_table` 中，当 `table.get_player_by_user_id()` 返回 None 时不再直接报错，而是自动创建 Player 对象。同时在 `connect` 中新增 `user_info` 字典存储用户名和 session_token（`handlers.py` 传递给 manager）。

4. **玩家看不到自己手牌** — `table.py` 的 `to_dict()` 新增 `requesting_user_id` 参数，`engine.py` 的 `get_game_state()` 传入当前用户 ID，确保活跃玩家始终能看到自己的手牌。

5. **game.ts 缺失 import** — 添加 `import { useAuthStore } from '@/stores/auth'`，修复运行时报错。

6. **CORS 配置** — `config.py` 中 `cors_origins` 改为字符串类型，`main.py` 中按逗号分割，支持通过环境变量配置多个来源。

7. **main.py 缺失 WebSocket import** — 添加 `WebSocket` 到 fastapi 导入，修复 `NameError`。

8. **Docker 构建配置** — `Dockerfile` 改用 `npm install --legacy-peer-deps` + `npm run build-only`（新增脚本跳过 vue-tsc）；`docker-compose.yml` 端口支持 `${FRONTEND_PORT}` 和 `${BACKEND_PORT}` 环境变量；`deploy.sh` 重写为现代 `docker compose` 语法。

9. **房间信息修正** — `manager.py` 的 `get_room_info()` 修正旁观者计数和活跃玩家计数逻辑。

10. **聊天用户名获取** — `handle_chat_message` 在玩家不在牌桌上时从 `user_info` 字典获取用户名。

### 2026-05-02 — 创建项目文档

- 新增 `PROJECT_GUIDE.md`：完整的系统项目文档，涵盖系统概述、游戏规则与实现原理、系统架构、文件清单、通信协议、Docker 部署步骤、配置说明、故障排除
- 新增 `memory.md`：项目记忆文件，记录文件作用和改动历史
