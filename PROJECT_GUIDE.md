# 在线德州扑克游戏 — 项目文档

## 目录

1. [系统概述](#1-系统概述)
2. [游戏规则与实现原理](#2-游戏规则与实现原理)
3. [系统架构](#3-系统架构)
4. [项目文件清单与作用](#4-项目文件清单与作用)
5. [通信协议](#5-通信协议)
6. [通过 Docker 部署到云服务器](#6-通过-docker-部署到云服务器)
7. [配置说明](#7-配置说明)
8. [故障排除](#8-故障排除)

---

## 1. 系统概述

这是一个为熟人娱乐设计的在线德州扑克游戏，支持 2-10 人实时对战。核心特性：

- 完整的德州扑克规则（翻牌前 → 翻牌 → 转牌 → 河牌 → 摊牌）
- 25 秒行动时限，超时自动弃牌
- 断线自动重连恢复
- 旁观者上帝视角（可查看所有玩家底牌）
- 锦标赛盲注递增模式（每 15 分钟翻倍）
- 初始筹码 20,000，支持 1 次重新买入
- 实时聊天系统

**技术栈**：

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python) + WebSocket |
| 数据库 | SQLite + SQLAlchemy (异步) |
| 牌型评估 | treys 库 |
| 认证 | JWT (python-jose) + bcrypt |
| 前端框架 | Vue 3 + TypeScript |
| 状态管理 | Pinia |
| 样式 | Tailwind CSS |
| 构建工具 | Vite |
| 部署 | Docker Compose (Nginx + FastAPI) |

---

## 2. 游戏规则与实现原理

### 2.1 游戏状态机

```
waiting (等待中)
    ↓ 房主点击开始，至少 2 名玩家
preflop (翻牌前)
    ↓ 所有玩家行动完成
flop (翻牌，发 3 张公共牌)
    ↓ 所有玩家行动完成
turn (转牌，发 1 张公共牌)
    ↓ 所有玩家行动完成
river (河牌，发 1 张公共牌)
    ↓ 所有玩家行动完成
showdown (摊牌)
    ↓ 分配筹码后 5 秒
waiting / 下一手牌
```

状态机在 `backend/app/game/engine.py` 的 `GameEngine` 中实现。

### 2.2 游戏流程详解

**一手牌的完整流程**：

1. **收集盲注** (`collect_blinds`)：小盲注玩家自动下注 small_blind，大盲注玩家自动下注 big_blind（初始 100），设置当前最大下注额为 big_blind

2. **发底牌** (`deal_hole_cards`)：给每个已连接的非弃牌玩家发 2 张私有底牌

3. **行动回合**：从大盲注左侧玩家开始，顺时针依次行动。每个玩家可选择：
   - **fold（弃牌）**：退出当前手牌
   - **check（过牌）**：无需跟注时可以过
   - **call（跟注）**：补齐当前最大下注额
   - **raise（加注）**：至少为 big_blind × 2
   - **all_in（全下）**：投入全部剩余筹码

4. **回合完成条件** (`check_round_completion`)：
   - 只剩 1 个未弃牌玩家 → 直接摊牌
   - 所有未弃牌玩家都已行动且下注持平 → 进入下一阶段

5. **下注收集** (`collect_bets`)：每轮结束收集玩家的当前下注到主池，`pot_amount` 累加，玩家 `current_bet` 归零

6. **边池计算** (`calculate_side_pots`)：当有玩家 all_in 产生时，计算边池。例如：
   ```
   玩家A 全下 1000, 玩家B 下注 2000, 玩家C 下注 2000
   → 主池: 1000×3 = 3000 (三人竞争)
   → 边池: (2000-1000)×2 = 2000 (B和C竞争)
   ```

7. **摊牌** (`proceed_to_showdown`)：用 treys 库评估每个玩家的最佳 5 张牌组合（2 张底牌 + 5 张公共牌），分数最低者为赢家。平分主池和边池。

8. **盲注升级** (`increase_blinds`)：每 15 分钟小盲/大盲翻倍

### 2.3 牌型评估

使用 [treys](https://github.com/ihendley/treys) 库（Python 扑克牌评估器），`backend/app/utils/poker_logic.py` 对其进行了封装：

```python
# treys 分数越低牌型越好（1 = 皇家同花顺, 7462 = 高牌）
evaluator = PokerEvaluator()
score, hand_rank = evaluator.evaluate_hand(["Ah", "Kh"], ["Qh", "Jh", "Th", "2d", "3s"])
# score = 1, hand_rank = "Royal Flush"
```

牌型从强到弱：

| 中文名 | 英文名 |
|--------|--------|
| 皇家同花顺 | Royal Flush |
| 同花顺 | Straight Flush |
| 四条 | Four of a Kind |
| 葫芦 | Full House |
| 同花 | Flush |
| 顺子 | Straight |
| 三条 | Three of a Kind |
| 两对 | Two Pair |
| 一对 | Pair |
| 高牌 | High Card |

### 2.4 断线重连机制

- 玩家 WebSocket 断开时，`handle_player_disconnect` 将玩家标记为 `is_connected = False`
- 玩家重新连接时，`handle_player_reconnect` 恢复连接状态
- 如果断线时正轮到该玩家行动，自动执行 fold
- 会话状态通过 `session_token` 持久化到 SQLite 的 `user_sessions` 表

### 2.5 经济系统

- **初始筹码**：20,000
- **重新买入**：场上筹码中位数的 50%，每人限 1 次
- **第二次破产**：转为旁观者

### 2.6 旁观者上帝视角

旁观者可以看到**所有玩家**的底牌，而玩家只能看到自己的底牌。实现方式：
- `Table.to_dict(spectator_view=True)` 对所有玩家显示手牌
- `Table.to_dict(requesting_user_id=user_id)` 只对该用户显示手牌

---

## 3. 系统架构

### 3.1 部署拓扑

```
                       互联网
                         │
                  Cloudflare Tunnel
                  (texasholdem.kirishima.one)
                         │
                  localhost:8888
                         │
              ┌──────────────────┐
              │  Nginx (前端容器)  │  ← 宿主机端口 8888 → 容器端口 80
              │  /          静态文件│
              │  /api   → 代理到后端│
              │  /ws    → 代理到后端│
              └────────┬─────────┘
                       │ Docker 内部网络 (poker-network)
              ┌────────┴─────────┐
              │  FastAPI (后端容器) │  ← 容器端口 8000
              │  SQLite 数据库     │
              │  WebSocket 服务    │
              └──────────────────┘
```

### 3.2 请求路径

用户浏览器发起请求时：
- **HTML/JS/CSS**：`GET /` → Nginx 返回 dist/ 下的静态文件
- **API 请求**：`POST /api/auth/login` → Nginx 代理到 `http://backend:8000/api/auth/login`
- **WebSocket**：`wss://域名/ws?token=xxx` → Nginx 升级连接代理到 `http://backend:8000/ws`

前端代码使用**相对路径**（`api.ts` 默认 baseURL 为 `''`，`websocket.ts` 从 `window.location` 动态构造 URL），因此无论通过什么域名或 IP 访问都能正确工作。

---

## 4. 项目文件清单与作用

### 4.1 根目录文件

| 文件 | 作用 |
|------|------|
| `docker-compose.yml` | Docker Compose 编排文件，定义 frontend + backend 两个服务及其网络 |
| `deploy.sh` | 一键部署脚本：检查环境 → 创建目录 → 构建镜像 → 启动服务 → 健康检查 |
| `.env.example` | 环境变量模板（SECRET_KEY、端口配置） |
| `.env` | 实际环境变量（需自行从 .env.example 复制并修改） |
| `README.md` | 项目简介和基本使用说明 |
| `PROJECT_GUIDE.md` | **本文档** |
| `memory.md` | 项目记忆文件，记录文件作用和改动历史 |

### 4.2 后端文件 (`backend/`)

#### 入口与配置

| 文件 | 作用 |
|------|------|
| `Dockerfile` | Python 3.11-slim 镜像，安装 gcc + Python 依赖，以非 root 用户 uvicorn 启动 |
| `requirements.txt` | Python 依赖清单 |
| `app/main.py` | **FastAPI 应用入口**：定义 REST API 路由（/, /health, /api/auth/register, /api/auth/login, /api/room/info）和 WebSocket 端点（/ws），配置 CORS 中间件和全局异常处理，`lifespan` 管理数据库初始化 |
| `app/config.py` | **Pydantic Settings 配置类**：从环境变量加载所有配置项（游戏参数、数据库 URL、JWT 密钥和算法、CORS 源列表等） |

#### 数据层

| 文件 | 作用 |
|------|------|
| `app/database.py` | **SQLAlchemy 异步引擎**：`create_async_engine` 连接 SQLite、`AsyncSessionLocal` 会话工厂、`get_db()` 依赖注入、`init_db()` 建表 |
| `app/models.py` | **ORM 模型**（6 个表）：`User`（用户）、`UserSession`（会话/断线重连）、`GameState`（游戏状态）、`PlayerHand`（手牌记录）、`GameRecord`（游戏记录）、`ChatMessage`（聊天消息） |
| `app/schemas.py` | **Pydantic 数据模型**：请求验证和响应序列化（用户注册/登录、牌桌状态、WebSocket 消息格式、房间信息等） |

#### 认证

| 文件 | 作用 |
|------|------|
| `app/auth.py` | **认证逻辑**：bcrypt 密码哈希、JWT 令牌创建和验证、用户创建/认证、会话管理（创建/获取/更新 WebSocket ID/断开） |

#### 游戏引擎 (`app/game/`)

| 文件 | 作用 |
|------|------|
| `app/game/__init__.py` | 模块初始化 |
| `app/game/player.py` | **玩家状态**：筹码管理（`chips`）、下注方法 `bet()`、弃牌/全下标记、行动权限检查 `can_act()`、跟注金额计算 |
| `app/game/table.py` | **牌桌管理**：玩家座位（0-9）、牌堆（`deck`）+ 公共牌（`community_cards`）、主池（`pot_amount`）+ 边池（`side_pots`）、盲注升级、庄家轮转、发底牌/公共牌、下注收集、`to_dict()` 序列化 |
| `app/game/engine.py` | **核心游戏引擎**：状态机控制（preflop→flop→turn→river→showdown）、`start_game()` 开始、`process_player_action()` 处理行动、`check_round_completion()` 回合完成判断、`proceed_to_next_stage()` 阶段推进、`determine_winners()` 胜负判定、`distribute_pots()` 筹码分配、`handle_action_timeout()` 超时处理、`handle_player_disconnect/reconnect()` 断线重连 |

#### 牌型评估

| 文件 | 作用 |
|------|------|
| `app/utils/poker_logic.py` | **扑克牌评估器**：封装 treys 库，`evaluate_hand()` 评估单副手牌、`compare_hands()` 比较多个玩家、`create_deck()` 创建 52 张牌、`shuffle_deck()` 洗牌、`deal_cards()` 发牌 |

#### WebSocket 通信

| 文件 | 作用 |
|------|------|
| `app/websocket/handlers.py` | **WebSocket 端点处理**：JWT 验证、数据库会话查询、WebSocket 接受/关闭、消息接收循环、断开清理 |
| `app/websocket/manager.py` | **WebSocket 连接管理器**：连接/断开管理、`user_info` 用户信息存储、消息路由（`action`/`chat`/`join_table`/`leave_table`/`start_game`/`heartbeat`）、广播消息、个性化游戏状态发送 |

#### 测试

| 文件 | 作用 |
|------|------|
| `test_game.py` | 游戏引擎测试（基本流程 + 扑克牌型逻辑） |

### 4.3 前端文件 (`frontend/`)

#### 构建与配置

| 文件 | 作用 |
|------|------|
| `Dockerfile` | **多阶段构建**：阶段 1 (Node 18 Alpine) 安装依赖并 `vite build` 构建，阶段 2 (Nginx Alpine) 复制静态文件 + nginx.conf |
| `nginx.conf` | **Nginx 配置**：`/` 静态文件 SPA 路由（`try_files $uri /index.html`）、`/api` 反向代理到 `backend:8000`、`/ws` WebSocket 代理（附带 Upgrade 头） |
| `package.json` | npm 依赖和脚本（`dev`, `build`, `build-only`, `preview`） |
| `vite.config.ts` | Vite 配置：`@` 路径别名、开发端口 5173、本地 API/WS 代理 |
| `tsconfig.json` | TypeScript 编译配置 |
| `tailwind.config.js` | Tailwind 自定义颜色（poker-green 等）、自定义动画（chip-bounce, card-deal, pulse-slow） |
| `postcss.config.js` | PostCSS 插件（tailwindcss + autoprefixer） |
| `index.html` | **HTML 入口**：加载屏幕动画、SPA 挂载点 `#app`、页面可见性和误离开监听 |

#### 应用核心 (`src/`)

| 文件 | 作用 |
|------|------|
| `main.ts` | **Vue 应用入口**：创建 app → 挂载 Pinia → 挂载 Router → 挂载到 `#app` |
| `App.vue` | **根组件**：路由视图 `<router-view />`，`onMounted` 中检查认证状态并尝试 WebSocket 自动重连 |

#### 路由 (`src/router/`)

| 文件 | 作用 |
|------|------|
| `index.ts` | **路由定义**：`/login`（登录页，无需认证）、`/lobby`（游戏大厅，需认证），路由守卫检查 `authStore.isAuthenticated` |

#### 类型定义 (`src/types/`)

| 文件 | 作用 |
|------|------|
| `game.ts` | **TypeScript 类型**：`User`, `PlayerInfo`, `TableState`, `GameStatus`, `RoomInfo`, `ChatMessage`, `Token`, `WSMessage`, `ActionRequest` 等，以及 `CARD_SUITS`/`CARD_RANKS` 常量映射 |

#### 工具函数 (`src/utils/`)

| 文件 | 作用 |
|------|------|
| `poker.ts` | `formatCard()` 牌面格式化、`getHandRankChinese()` 牌型中文名、`formatChips()` 筹码缩写（K/M）、`formatCountdown()` 倒计时、`getChipColorClass()` 筹码颜色、`isValidCard()` 牌面校验 |

#### 服务层 (`src/services/`)

| 文件 | 作用 |
|------|------|
| `api.ts` | **Axios HTTP 客户端**：`register()`, `login()`, `getRoomInfo()`, `healthCheck()`。请求拦截器自动添加 `Authorization: Bearer <token>` 头，响应拦截器处理 401 自动登出。**生产环境使用相对路径**（空 baseURL），开发环境使用 `VITE_API_URL` 环境变量 |
| `websocket.ts` | **WebSocket 客户端**：连接/断开/重连（指数退避，最多 5 次）、30s 心跳、`sendAction()`/`sendChatMessage()`/`joinTable()`/`leaveTable()`/`startGame()`。**生产环境从 `window.location` 动态构造 WebSocket URL**，开发环境使用 `VITE_WS_URL` |

#### 状态管理 (`src/stores/`)

| 文件 | 作用 |
|------|------|
| `auth.ts` | **Pinia 认证 Store**：`user`（用户信息）、`token`（JWT + session_token）、`isAuthenticated`（计算属性）、`register()`/`login()`/`logout()`、localStorage 持久化 |
| `game.ts` | **Pinia 游戏 Store**：`gameStatus`（牌桌状态）、`roomInfo`（房间信息）、`chatMessages`（聊天记录）、计算属性（`currentPlayer`, `isHost`, `isCurrentPlayer`, `canAct`, `callAmount`, `minRaiseAmount`, `maxRaiseAmount`）、`getPlayerPositionStyle()` 8 人座位布局 |

#### 页面组件 (`src/components/`)

| 文件 | 作用 |
|------|------|
| `Login.vue` | **登录/注册页**：Tab 切换、表单验证（用户名 3-20 字符、密码 ≥6 字符、确认密码一致）、调用 authStore 进行注册/登录、成功后连接 WebSocket 并跳转大厅 |
| `Lobby.vue` | **游戏大厅（核心页面）**：顶部导航栏（房间状态、盲注等级、退出按钮）、左侧牌桌视图（椭圆形牌桌、玩家座位分布、公共牌区域、底池显示、行动按钮）、右侧面板（聊天、游戏信息、在线玩家列表）、加注对话框（金额输入 + 快捷按钮） |

#### UI 组件 (`src/components/`)

| 文件 | 作用 |
|------|------|
| `PokerCard.vue` | **扑克牌组件**：正面（花色 + 点数）/背面显示，三档尺寸（sm/md/lg），旋转效果，hover 放大 |
| `CommunityCards.vue` | **公共牌区域**：5 张公共牌展示（翻牌 3 张、转牌 1 张、河牌 1 张），阶段指示器，底池展示 |
| `ActionButtons.vue` | **行动按钮**：fold/check/call/raise/all_in，动态显示可用行动，加注对话框（金额输入 + 快捷金额会 + 预览） |
| `PlayerSeat.vue` | **玩家座位**：位置样式（8 个预设位置）、连接状态灯、筹码显示、当前下注显示、状态标签（已弃牌/全下/已行动）、手牌显示（旁观/摊牌时） |
| `ChatPanel.vue` | **聊天面板**：消息列表自动滚动、系统消息/玩家消息区分、未读计数、"我"标签、时间格式化、Ctrl+Enter 换行 |
| `Timer.vue` | **倒计时**：SVG 圆形进度条、≤10 秒红色闪烁、状态文本（已弃牌/已全下/请行动） |
| `ChipDisplay.vue` | **筹码显示**：单枚筹码 / 筹码堆（最多 5 枚），金额缩写显示，5 种面额颜色（白/红/蓝/绿/黑） |

#### 样式

| 文件 | 作用 |
|------|------|
| `src/assets/css/tailwind.css` | Tailwind 基础层 + 组件层（`.btn`, `.card`, `.input`, `.table-seat`, `.poker-card`, `.chip`）+ 工具层 |

---

## 5. 通信协议

### 5.1 REST API

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/` | 根端点，返回应用信息 | 无 |
| `GET` | `/health` | 健康检查，返回 `{"status":"healthy"}` | 无 |
| `POST` | `/api/auth/register` | 用户注册 `{username, password}` | 无 |
| `POST` | `/api/auth/login` | 用户登录 `{username, password}` | 无 |
| `GET` | `/api/room/info` | 获取房间信息 | Bearer Token |
| `WS` | `/ws?token=<jwt>` | WebSocket 连接 | Query Token |

### 5.2 WebSocket 消息

#### 客户端 → 服务器

```json
// 玩家行动
{"type": "action", "data": {"action": "fold|check|call|raise|all_in", "amount": 200}}

// 聊天
{"type": "chat", "data": {"message": "大家好"}}

// 加入牌桌
{"type": "join_table", "data": {"position": 0, "buyin_type": "new|rebuy"}}

// 离开牌桌
{"type": "leave_table", "data": {"type": "temporary|permanent"}}

// 开始游戏（仅房主）
{"type": "start_game", "data": {}}

// 心跳
{"type": "heartbeat", "data": {}}
```

#### 服务器 → 客户端

```json
// 欢迎消息（连接成功时发送）
{"type": "welcome", "data": {"message": "连接成功", "session_token": "..."}}

// 游戏状态（每次状态变化时广播，根据用户视角个性化）
{"type": "game_state", "data": {"is_game_active": true, "table_state": {...}, ...}}

// 玩家行动结果
{"type": "action_result", "data": {"user_id": 1, "action": "raise", "amount": 200, "message": "玩家1 加注到 200"}}

// 玩家加入
{"type": "player_joined", "data": {"user_id": 1, "username": "玩家1", "position": 0, "chips": 20000}}

// 玩家离开
{"type": "player_left", "data": {"user_id": 1, "username": "玩家1", "leave_type": "temporary"}}

// 游戏开始
{"type": "game_started", "data": {"hand_id": 1, "message": "游戏开始！第 1 手牌"}}

// 聊天消息
{"type": "chat", "data": {"user_id": 1, "username": "玩家1", "message": "大家好", "is_system": false}}

// 心跳响应
{"type": "heartbeat_ack", "data": {"timestamp": "..."}}

// 错误
{"type": "error", "data": {"error": "错误描述"}}
```

### 5.3 GameState 数据结构

```json
{
  "is_game_active": true,
  "hand_id": 3,
  "table_state": {
    "players": [
      {
        "user_id": 1,
        "username": "Alice",
        "position": 0,
        "chips": 18500,
        "current_bet": 200,
        "is_active": true,
        "has_acted": true,
        "is_folded": false,
        "is_all_in": false,
        "is_connected": true,
        "is_host": true,
        "cards": ["Ah", "Kh"]     // 只有本人/旁观者/摊牌时可见
      }
    ],
    "community_cards": ["Ts", "Jc", "Qh", "2d"],
    "pot_amount": 1500,
    "current_player": 2,
    "stage": "turn",
    "small_blind": 50,
    "big_blind": 100,
    "dealer_position": 0,
    "action_timeout": 25,
    "blind_level": 1
  },
  "blind_level": 1,
  "next_blind_increase": "2026-05-02T12:15:00",
  "is_spectator": false
}
```

---

## 6. 通过 Docker 部署到云服务器

### 6.1 服务器要求

- **操作系统**：Linux（Ubuntu 20.04+ / Debian / CentOS 8+）
- **内存**：≥ 512MB（推荐 1GB+）
- **磁盘**：≥ 1GB 可用空间
- **软件**：Docker 20.10+、Docker Compose v2

### 6.2 第一步：安装 Docker

```bash
# 一键安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动 Docker 并设置开机自启
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER
# 退出重新登录使生效
exit
```

### 6.3 第二步：上传项目到服务器

```bash
# 在本地电脑上执行：将项目文件夹上传到服务器
scp -r texas-holdem-online user@你的服务器IP:/opt/

# 或者使用 rsync（支持断点续传）
rsync -avz texas-holdem-online/ user@你的服务器IP:/opt/texas-holdem-online/
```

### 6.4 第三步：配置环境变量

```bash
# SSH 登录服务器
ssh user@你的服务器IP

# 进入项目目录
cd /opt/texas-holdem-online

# 从模板创建 .env 文件
cp .env.example .env

# 编辑 .env 文件
vim .env
```

**必须修改的配置**：

```bash
# ！！！必须改为一个随机字符串！！！
SECRET_KEY=your-secret-key-change-in-production

# 前端对外端口（外部访问端口）
FRONTEND_PORT=8888

# 后端端口（通常不需要改）
BACKEND_PORT=8000
```

> **生成安全密钥**：`openssl rand -base64 32`

### 6.5 第四步：启动服务

```bash
# 赋予执行权限
chmod +x deploy.sh

# 一键部署
./deploy.sh
```

部署脚本会自动：
1. 检查 Docker 环境
2. 创建数据目录（`backend/data/`, `backend/logs/`）
3. 检查 `.env` 文件
4. 构建前端和后端 Docker 镜像
5. 启动容器
6. 执行健康检查

### 6.6 第五步：验证部署

```bash
# 查看容器运行状态
docker compose ps

# 应该看到两个容器都在运行：
# texas-holdem-frontend    Up
# texas-holdem-backend     Up (healthy)

# 查看日志
docker compose logs -f

# 测试 API
curl http://localhost:8000/health
# 返回: {"status":"healthy"}

# 测试前端（如果服务器有外网 IP）
curl http://localhost:8888
# 返回: HTML 页面
```

### 6.7 第六步：配置外网访问

有几种方式让外网访问你的游戏：

#### 方式一：Cloudflare Tunnel（推荐，无需开放端口）

```bash
# 安装 cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# 登录（会打开浏览器，先在本机执行然后复制 cert）
cloudflared tunnel login

# 创建隧道
cloudflared tunnel create texas-poker

# 配置 DNS（在 Cloudflare 控制台）
# CNAME: texasholdem.kirishima.one → <tunnel-id>.cfargotunnel.com

# 启动隧道
cloudflared tunnel run --url localhost:8888 texas-poker

# 长期运行（创建 systemd 服务）
cloudflared tunnel install --name texas-poker --url localhost:8888
```

#### 方式二：Nginx 反向代理 + Let's Encrypt SSL

```bash
# 安装 Nginx
sudo apt-get install nginx certbot python3-certbot-nginx -y

# 配置 Nginx
sudo vim /etc/nginx/sites-available/texas-poker
```

```nginx
server {
    listen 80;
    server_name 你的域名.com;

    location / {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/texas-poker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 配置 SSL 证书
sudo certbot --nginx -d 你的域名.com
```

#### 方式三：直接暴露端口（仅测试用）

```bash
# 开放防火墙端口
sudo ufw allow 8888/tcp
```

然后直接访问 `http://服务器IP:8888`

### 6.8 常用管理命令

```bash
# 查看日志
docker compose logs -f                    # 所有服务
docker compose logs -f backend            # 仅后端
docker compose logs -f frontend           # 仅前端
docker compose logs --tail=50             # 最近 50 行

# 重启服务
docker compose restart                    # 重启所有
docker compose restart backend            # 仅重启后端

# 停止服务
docker compose down

# 更新代码后重新部署
git pull                                  # 拉取最新代码
docker compose build --no-cache           # 重新构建镜像
docker compose up -d                      # 启动

# 重置数据库（清空所有数据）
docker compose down
rm -rf backend/data/*
docker compose up -d
```

---

## 7. 配置说明

### 7.1 环境变量 (`.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEBUG` | `false` | 调试模式（生产环境必须为 false） |
| `DATABASE_URL` | `sqlite+aiosqlite:///./texas_holdem.db` | 数据库连接 URL |
| `SECRET_KEY` | — | **必须修改！** JWT 签名密钥 |
| `FRONTEND_PORT` | `8888` | 前端对外端口 |
| `BACKEND_PORT` | `8000` | 后端对外端口 |

### 7.2 游戏参数 (`backend/app/config.py`)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_players` | 10 | 最大玩家数 |
| `min_players` | 2 | 最小开局人数 |
| `initial_chips` | 20000 | 初始筹码 |
| `small_blind` | 50 | 小盲注 |
| `big_blind` | 100 | 大盲注 |
| `action_timeout` | 25 | 行动时限（秒） |
| `blind_increase_minutes` | 15 | 盲注升级间隔（分钟） |

修改后需重启后端容器生效：
```bash
docker compose restart backend
```

---

## 8. 故障排除

### 问题：页面白屏

1. 打开浏览器开发者工具（F12）→ Network 标签
2. 刷新页面，检查 JS 文件是否正常加载
3. 检查 API 请求是否发往正确的地址（应该发往当前域名，不是 localhost）
4. 查看前端容器日志：`docker compose logs frontend`

### 问题：WebSocket 连接失败

```bash
# 检查后端是否正常运行
docker compose ps
curl http://localhost:8000/health

# 检查 Nginx 日志
docker compose logs frontend | grep -i error
```

### 问题：数据库错误

```bash
# 重置数据库
docker compose down
rm -rf backend/data/*
docker compose up -d
```

### 问题：端口冲突

```bash
# 查看端口占用
sudo lsof -i :8888
sudo lsof -i :8000

# 修改 .env 中的端口配置
vim .env
# FRONTEND_PORT=其他端口
# BACKEND_PORT=其他端口

# 重新部署
docker compose down
docker compose up -d
```

### 问题：磁盘空间不足

```bash
# 清理 Docker 垃圾
docker system prune -a
docker volume prune
```

### 问题：前端构建失败

```bash
# 查看构建日志
docker compose build frontend --no-cache
```

常见原因：npm 依赖下载失败（网络问题），可尝试在 Dockerfile 中使用国内镜像源：

```dockerfile
# 在 RUN npm install 之前添加
RUN npm config set registry https://registry.npmmirror.com
```

---

## 附录：快速排查命令

```bash
# 一键状态检查
echo "=== 容器状态 ===" && docker compose ps && \
echo "=== 后端健康 ===" && curl -s localhost:8000/health && \
echo "" && echo "=== 前端可访问 ===" && curl -s -o /dev/null -w "%{http_code}" localhost:8888
```

---

**文档版本**：2.0  
**最后更新**：2026-05-02
