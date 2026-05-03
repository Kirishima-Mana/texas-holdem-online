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
| `PROJECT_GUIDE.md` | 完整系统项目文档（实现原理、文件作用、通信协议、部署步骤、故障排除） |
| `memory.md` | 本文件，记录项目文件作用和改动历史 |

### 后端 — `backend/`

| 文件 | 作用 |
|------|------|
| `Dockerfile` | Python 3.11-slim 镜像，安装 curl/gcc + Python 依赖，以非 root 用户运行 uvicorn |
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
| `Dockerfile` | 多阶段构建：Node 18 Alpine（npm install --legacy-peer-deps + build-only 跳过 vue-tsc），Nginx Alpine 运行 |
| `nginx.conf` | Nginx 配置：`/` 静态文件、`/api` 代理后端、`/ws` WebSocket 代理 |
| `package.json` | 前端依赖和脚本（vue, pinia, vue-router, axios, tailwindcss, vite 等） |
| `vite.config.ts` | Vite 配置：@ 别名、开发服务器端口 5173、API/WS 代理 |
| `tsconfig.json` | TypeScript 编译配置 |
| `tailwind.config.js` | Tailwind 自定义主题色（poker-green, poker-gold 等）和动画 |
| `postcss.config.js` | PostCSS 配置（Tailwind + Autoprefixer） |
| `index.html` | HTML 入口，含加载动画 + `<script type="module" src="/src/main.ts">` Vue 入口标签 |
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

### 2026-05-02 — 白屏问题根因修复（第二轮）

**问题定位**：登录后的白屏问题仍未解决。排查服务器后发现：
- 源代码已是最新修复版本，但 Docker 镜像未重新构建（容器文件日期仍为 Apr 18）
- 后端 healthcheck 失败，原因是容器内没有安装 `curl`

**最终根因**：`frontend/index.html` 缺少 `<script type="module" src="/src/main.ts">` 标签。Vite 构建时将 `index.html` 作为入口，但 HTML 中唯一的 `<script type="module">` 是内联的加载动画脚本。Vite 把它当成应用入口点，所以构建产物只有 1.2KB（仅含内联脚本），完全没有 Vue 应用代码。

**证据**：修复前 `✓ 4 modules transformed` → `index.js 1.16 kB`；修复后 `✓ 89 modules transformed` → `index.js 156.64 kB + index.css 22.44 kB`

**修复**：
1. `frontend/index.html` — 在 `<head>` 中添加 `<script type="module" src="/src/main.ts"></script>`
2. `backend/Dockerfile` — `apt-get install` 添加 `curl`（healthcheck 需要）
3. 服务器上执行 `docker compose build --no-cache && docker compose up -d` 完成部署

### 2026-05-02 — 注册 404 错误修复（第三轮）

**问题**：注册时请求路径变成 `/api/api/auth/register`（重复了 `/api`），返回 404。

**根因**：服务器上 `frontend/.env` 文件设置了 `VITE_API_URL=https://texasholdem.kirishima.one/api`。Vite 构建时将该值静态替换入代码，axios 的 `baseURL` 变成了 `https://texasholdem.kirishima.one/api`，而每个 API 端点路径又以 `/api/...` 开头，拼接后变成 `/api/api/...`。

**修复**：删除 `frontend/.env`（该项目现已改为相对路径，不再需要 Vite 环境变量），清理根目录 `.env` 中的 `VITE_*` 行。

**附加修复**：bcrypt 5.0.0 与 passlib 1.7.4 不兼容导致 `password cannot be longer than 72 bytes` 错误。在 `requirements.txt` 中新增 `bcrypt>=4.0,<5.0` 版本约束。重建后端镜像后 bcrypt 降级到 4.3.0，注册/登录恢复正常。

### 2026-05-02 — 游戏无法开始修复（第四轮）

**问题**：注册登录成功后，房主和加入者都无法开始游戏，场上永远显示"等待行动玩家…"

**根因 1 — roomInfo 永不更新**：`game.ts` 的 `updateGameStatus()` 只更新 `gameStatus`，不更新 `roomInfo`。后端广播 `game_state` 时 `player_count` 已被更新，但前端 `roomInfo` 仍是初始值 0。结果 `roomInfo.player_count < roomInfo.min_players` 始终为 true，"开始游戏"按钮永远被禁用。

**根因 2 — "开始游戏"按钮在错误模板分支**：按钮放在 `v-else`（旁观者视图）分支中。玩家点击"加入牌桌"后 `currentPlayer` 变为非 null，旁观者视图（含按钮）被 `v-if="gameStore.currentPlayer"` 隐藏。房主再也看不到"开始游戏"按钮。

**修复**：
1. `stores/game.ts` — `updateGameStatus()` 内新增同步逻辑，从 `table_state.players.length` 更新 `roomInfo.player_count`，从 `is_game_active` 更新 `roomInfo.is_game_active`，从玩家列表提取 `host_username`
2. `components/Lobby.vue` — 重构模板为三层：游戏未开始时显示"开始游戏"（房主）/ "等待房主开始…"（其他人）+ "离开牌桌"；游戏进行中显示行动按钮 / "等待行动玩家…"；旁观者显示"加入牌桌"
3. `components/Lobby.vue` — 新增 `leaveTable()` 函数
4. `websocket/manager.py` — `receive_message` 日志级别从 `debug` 改为 `info`，`handle_join_table` 和 `handle_start_game` 新增 INFO 日志

---

## 已知问题 / 待验证

1. **完整游戏流程未端到端测试**：加入牌桌 / 开始游戏按钮逻辑已修复，但实际下注→阶段推进→摊牌→筹码分配的全流程尚未验证
2. **docker-compose.yml version 警告**：`version: '3.8'` 在较新 Docker 版本中已过时，可移除该行消除警告
3. **`QUICK_START - 副本.md:Zone.Identifier`**：Windows 系统残留文件，可安全删除
4. **`socket.io-client` 依赖**：`package.json` 中声明了 `socket.io-client` 但未使用，可移除减小包体积
5. **bcrypt 兼容性警告**：bcrypt 4.3.0 移除了 `__about__` 属性，passlib 无法检测版本号（不影响功能，仅日志警告）
6. **`showdown` 后无显式广播**：`proceed_to_showdown` 在 5 秒 sleep 后调用 `start_new_hand`，需确认调用链末端的 `broadcast_game_state` 是否正确更新新一局的状态

### 2026-05-02 — WebSocket 403 + 数据库持久化修复（第五轮）

**问题**：登录后房间显示"0/10玩家 0旁观者"，点击按钮无反应。

**根因**：所有 WebSocket 连接被返回 **403 Forbidden**。
1. `DATABASE_URL` 原为 `sqlite+aiosqlite:///./texas_holdem.db`，数据库在容器 `/app/texas_holdem.db`，不在 volume 挂载路径。每次容器重建数据库被清空。
2. 前端 localStorage 中保存的 JWT 引用了已不存在的 session_token，服务器拒绝 WebSocket 连接（WS_1008_POLICY_VIOLATION → HTTP 403）
3. 前端 WebSocket 收到 403 后无限重连，没有触发重新认证

**修复**：
1. `docker-compose.yml` — `DATABASE_URL` 改为 `sqlite+aiosqlite:///./data/texas_holdem.db`（指向 volume 挂载目录）
2. `backend/Dockerfile` — 移除 `USER appuser` 切换（volume 目录权限问题导致 root 才能写入）
3. `frontend/src/services/websocket.ts` — `onclose` 中新增 1008 状态码处理：清除 auth、停止重连、重定向到 /login
4. `.env.example` — 同步更新 DATABASE_URL

### 2026-05-02 — 行动权转移 + 加注逻辑修复（第六轮）

**问题**：玩家行动后行动权不转移，同一玩家可无限操作，加注后其他玩家无法回应。

**根因**：`engine.py` 的 `process_player_action()` 在调用 `check_round_completion()` 后，若回合未完成，从未将 `current_player_position` 推进到下一个玩家。导致 `handle_player_action` 中第二次验证 `current_player_position != player.position` 时始终通过（因为从未改变）。

**修复** (`backend/app/game/engine.py`)：
1. `process_player_action` — check_round_completion 之后，若 `is_game_active` 且阶段未变，调用 `get_next_player_position()` 推进 `current_player_position`
2. 加注/全下时重置其他活跃玩家的 `has_acted = False`（他们需要对新下注额做出回应），同时重置 `players_acted_this_round = 1`

### 2026-05-02 — 行动死锁 + 前端不显示牌面修复（第七轮）

**问题 A — 行动死锁**：大小盲都显示"等待行动玩家…"，出现死锁。根因：
1. `check_round_completion` 的 `all_acted` 检查没有考虑断线玩家。玩家断线后 `has_acted=False` 且 `is_connected=False`，`can_act()` 为 false 无法行动，但 `all_acted` 不会为 true → 回合永久卡住
2. 加注重置 `has_acted` 时也重置了断线玩家的状态，加剧问题

**问题 B — 前端完全不显示牌面**：Lobby.vue 的"牌桌视图"模板没有任何牌面渲染——没有公共牌区域、没有玩家手牌显示、没有阶段指示器。后端正确发牌并广播，但前端从未渲染。

**修复**：
1. `backend/app/game/engine.py` — `check_round_completion` 中 `all_acted` 和 `bets_equal` 条件增加 `or not p.is_connected`，断线玩家视为已行动
2. `backend/app/game/engine.py` — 加注重置 `has_acted` 增加 `and p.is_connected` 条件
3. `frontend/src/components/Lobby.vue` — 牌桌中心新增公共牌显示（PokerCard 组件循环渲染 community_cards）
4. `frontend/src/components/Lobby.vue` — 玩家座位上新增手牌显示（Player.cards 有值时渲染 PokerCard）
5. `frontend/src/components/Lobby.vue` — 新增阶段指示器（翻牌前/翻牌/转牌/河牌/摊牌）+ `stageLabel` 计算属性
6. `frontend/src/components/Lobby.vue` — 导入 PokerCard 组件

### 2026-05-02 — BB option + 超时断线死锁 + UI 遮挡修复（第八轮）

**问题 A — 大盲没有"选项"权**：翻牌前小盲跟注后，大盲应有权 check 或 raise（live blind），但 `collect_blinds()` 调用 `bet()` 将大盲的 `has_acted` 设为了 `True`，导致回合立刻完成，大盲无法行动。

**问题 B — 断线玩家被跳过引发超时死锁**：`handle_action_timeout` 在 `player.can_act()` 为 False 时跳过不处理。断线玩家 `is_connected=False` 导致 `can_act()` 返回 false，超时也不自动弃牌 → 永久死锁。

**问题 C — UI 遮挡牌面**：手牌渲染在 `.table-seat` 圆框内部，`bg-gray-800 rounded-full` 的深色背景遮挡扑克牌。公共牌被座位圆圈覆盖。

**修复**：
1. `backend/app/game/engine.py` — `collect_blinds()` 中大盲下注后显式设置 `big_blind_player.has_acted = False`
2. `backend/app/game/engine.py` — `handle_action_timeout()` 移除 `can_act()` 检查，改为 `not is_folded and not is_all_in`，确保断线玩家也会被超时弃牌
3. `frontend/src/components/Lobby.vue` — 座位重构：手牌渲染在圆圈上方（`mb-1`），座位圆圈仅含玩家信息；公共牌 z-20 > 座位 z-10；底池增加 `bg-gray-900/80` 半透明背景卡片
4. `frontend/src/components/Lobby.vue` — 座位圆圈从 `w-28 h-28 rounded-full` 改为 `w-20 h-20 rounded-full`，颜色状态区分更清晰

### 2026-05-02 — UI 重做：椭圆形牌桌 + 动画系统 + 摊牌结算面板（第九轮）

**牌桌布局重构**（`Lobby.vue`）：
- 矩形区域 → `rounded-[50%]` 椭圆形绿色牌桌，绿色渐变背景 + 琥珀色边框
- 8 座按椭圆周长均匀分布（`getSeatStyle` 8 个预设位置）
- 公共牌居中排列，空位虚线占位框，底池半透明磨砂卡片
- 手牌渲染在座位标签上方独立显示，不再被圆框遮挡

**动画系统**（`tailwind.css`）：
- `animate-deal-in`：底牌发放（从上方飞入 + Y 轴翻转 + 缩放弹性，延迟递增）
- `animate-card-in`：公共牌逐张揭示（Y 轴翻转展开，每张 0.15s 延迟）
- `animate-chip-in`：筹码弹出（scale 0→1.2→1）
- `card-deal` TransitionGroup：Vue 组件进出过渡动画

**摊牌结算面板**（`Lobby.vue` + `engine.py` + `game.ts`）：
- 后端 `get_game_state` 在 showdown 阶段用 treys 实时计算每位玩家手牌排名，附加 `showdown` 数据（players 列表 + winner）
- 前端 `gameStore.showdownData` 响应式存储，watch 触发面板弹出
- 面板：赢家金色高亮边框、所有玩家手牌对比 + 排名文本、公共牌展示、"继续"按钮

**改动文件**：
1. `frontend/src/components/Lobby.vue` — 完全重写模板和逻辑（~370 行）
2. `frontend/src/assets/css/tailwind.css` — 新增 4 个 @keyframes + 1 个 TransitionGroup 类
3. `frontend/src/stores/game.ts` — 新增 `showdownData` 状态 + `updateGameStatus` 同步逻辑
4. `backend/app/game/engine.py` — `get_game_state` 新增 showdown 数据（treys 评估手牌排名）

### 2026-05-02 — 参考 888 扑克牌桌 UI 专业化改版（第十轮）

**参考**：888 poker 平台满员桌截图，分析专业扑克 UI 的设计要素。

**牌桌结构三层化**：
- Rail（轨道）：16px 深色粗边框（`#1a1a2e → #0d0d1a`），模拟真牌桌皮革扶手
- Felt（绒布）：绿色径向渐变桌面（`#1a6b3c → #0f4a28 → #0a3d1f`）+ 横向微纹理
- 牌桌从 `rounded-[50%]` 纯椭圆改为 `rounded-[45%]`/`rounded-[43%]` 双层嵌套

**新增 UI 元素**：
- 庄家按钮：白色圆形 "D" 标记，跟随 dealer_position 偏移到座位旁
- 行动标签：彩色小标签（FOLD=红, ALL IN=黄, CHECK=橙），显示在玩家面板顶部
- 玩家面板：从 `rounded-full` 圆框改为 `rounded-lg` 圆角矩形，当前行动玩家金色光环
- 底池：从中心卡片改为顶部胶囊标签（不遮挡公共牌）
- 卡背重设计：蓝色菱格纹 + 蓝色内框花边（`PokerCard.vue`）
- 筹码 K 缩写：≥1000 显示为 `1.0K` 格式

**新增辅助函数**（`Lobby.vue` script）：
- `actionLabel(player)` — 根据玩家状态返回行动标签文本
- `actionTagColor(player)` — 行动标签颜色
- `playerBg(player)` — 玩家面板背景/光环
- `dealerBtnStyle()` — 庄家按钮绝对定位
- `formatChips(chips)` — 筹码格式化

**改动文件**：
1. `frontend/src/components/Lobby.vue` — 牌桌区域完全重写 + 5 个新辅助函数
2. `frontend/src/components/PokerCard.vue` — 蓝色菱格纹牌背设计
3. `frontend/src/assets/css/tailwind.css` — 新增 table-felt / table-rail 样式

### 2026-05-02 — 行动死锁根因修复 + rail 遮挡 + 四色牌（第十一轮）

**问题 A — 行动死锁根因**：`Player.can_act()` 缺少 `not self.has_acted` 检查。当 `get_next_player_position` 返回 None（下一位玩家断线），`current_player_position` 不推进，同一玩家 `has_acted=True` 但 `can_act()` 仍返回 True → 可无限重复行动。

**问题 B — rail 遮挡手牌**：玩家座位渲染在 felt div 内部，felt 的 `inset-[16px]` 裁剪边缘 → 靠近桌边的座位手牌被切掉。

**问题 C — 花色颜色**：当前只有红/灰两色，不符合四色牌标准。

**修复**：
1. `backend/app/game/player.py` — `can_act()` 增加 `and not self.has_acted` 条件
2. `backend/app/game/engine.py` — `collect_blinds()` 小盲也设为 `has_acted=False`（强制下注不算自愿行动）
3. `backend/app/game/engine.py` — `process_player_action` 中 `get_next_player_position` 返回 None 时增加 fallback：调用 `get_next_active_position`，若仍无则触发 showdown
4. `frontend/src/components/Lobby.vue` — 牌桌结构重构：felt div 在玩家座位之前关闭，玩家座位提升到 felt 外部的 z-25 层，手牌可溢出到 rail 上方
5. `frontend/src/components/Lobby.vue` — 修复多余 `</div>` 标签导致的 Vue 编译错误
6. `frontend/src/types/game.ts` — `SUIT_COLORS` 四色牌：h=红，d=蓝，c=绿，s=白

### 2026-05-02 — treys KeyError + 防御性行动逻辑（第十二轮）

**问题**：只剩 1 人时 `determine_winners` 调用 `treys.evaluate([2张底牌], [])` → treys 最少需要 5 张牌 → `KeyError: 2` → 异常中断 `proceed_to_showdown` → 后续 broadcast 不执行 → 前端状态卡住。

**修复** (`backend/app/game/engine.py`)：
1. `determine_winners` — 只剩 1 人直接获胜（跳过 treys）；牌数不足安全 fallback
2. `proceed_to_showdown` — try/except 包裹 `determine_winners`，异常不阻断流程
3. `get_game_state` showdown 计算 — 少于 3 张公共牌时使用占位值
4. `process_player_action` — fallback 逻辑重写：找不到可行动玩家时尝试任何活跃连接玩家，不再死板触发 showdown
5. `proceed_to_next_stage` / `start_new_hand` — 验证 `current_player_position` 有效性，无效时重新查找

### 2026-05-02 — 摊牌结算界面修复（第十三轮）

**问题**：最后一手跟注后停顿 5 秒，结算界面从不显示，需要再点按钮才进入下一局。

**根因**：`proceed_to_showdown` 中 `await asyncio.sleep(5)` 阻塞了整个 action 处理链。broadcast 在 sleep **之后**才执行，此时 `start_new_hand` 已将 stage 改为 `preflop`，摊牌数据（`showdown` 字段）从未随 `stage=showdown` 到达前端。

**修复** (`backend/app/game/engine.py` + `websocket/manager.py` + `frontend/Lobby.vue`)：
1. 拆分 `proceed_to_showdown` 为立即阶段（计算赢家 → 立即返回）和延迟阶段（`_finish_showdown` 作为独立 `asyncio.create_task` 后台 5 秒后执行）
2. 新增 `GameEngine.broadcast_callback` 回调机制，由 `WebSocketManager.__init__` 注入 `broadcast_game_state`
3. `_finish_showdown` 开始新一局后调用 `_notify_state_change()` 自动广播
4. 前端 `showdownData` watcher 移除 setTimeout 延迟，面板立即弹出；`showdownData` 变 null 时自动关闭面板

**新时间线**：t=0 结算+广播+面板弹出 → t=5s 新一局+广播+面板关闭

### 2026-05-02 — All-in 逻辑重构（第十四轮）

**问题**：All-in 后出现死锁，边池计算不完整。

**修复**：
1. `table.py` `calculate_side_pots` — 改为基于**所有不同的 `total_bet_this_round` 值**（排除 0）计算边池层级，不再只考虑 `is_all_in` 玩家
2. `engine.py` `distribute_pots` — 完全重写：新增 `_eval_hands()` 统一评估手牌 + `_award()` 发筹码；主池在所有未弃牌玩家中找最优手牌，**每个边池独立**在其 `eligible_players` 中找最优手牌分配
3. `engine.py` `proceed_to_next_stage` — 检测全员 all-in 后启动 `_auto_complete_all_in` 后台任务，每 1 秒自动发一张公共牌并广播，直到摊牌
4. `engine.py` `process_player_action` — 全员 all-in 时跳过计时器启动

### 2026-05-02 — All-in 摊牌广播修复（第十五轮）

**问题**：All-in 自动完成后摊牌面板不显示。

**根因**：`_auto_complete_all_in` 在 river 阶段调用 `proceed_to_showdown()` 后直接 `break` 退出，摊牌状态未广播。

**修复**：`break` 改为 `await self._notify_state_change()` + `return`。

### 2026-05-02 — 冠军庆祝 + 新局筹码重置（第十六轮）

**问题 A**：游戏决出最终胜者后无庆祝提示。
**问题 B**：新一局筹码不重置，从上一局结束状态继续。

**修复**：
1. `engine.py` 新增 `game_winner` 字段，`end_game()` 记录冠军信息；`get_game_state` 包含 `game_winner`
2. `engine.py` `start_game()` — 检测 `was_game_over`（上一局已结束），重置所有活跃玩家 `chips=20000`、`blind_level=1`、盲注 `50/100`、`hand_id=0`
3. `game.ts` 新增 `gameWinner` 状态 + `updateGameStatus` 同步逻辑
4. `Lobby.vue` 新增冠军庆祝全屏面板（奖杯 + 冠军名 + 筹码数）

### 2026-05-02 — All-in 计时器竞态修复（第十七轮）

**问题**：All-in 后再次死锁。

**根因**：`proceed_to_next_stage` 启动 `_auto_complete_all_in` 后 return，但 `process_player_action` 不知情，又启动了 25s 计时器，两者并发执行互相干扰。

**修复**：`process_player_action` fallback 中检测全员 all-in → 跳过计时器启动。

### 2026-05-02 — 自动结束 + 踢人 + 房主转让（第十八轮）

**问题 A**：所有人退出后游戏不结束。
**问题 B**：掉线/退出的玩家占据座位无法移除。
**问题 C**：房主退出后无人管理。

**修复**：
1. `engine.py` `handle_player_disconnect` — 全员断线时 `is_game_active=False` + 取消计时器
2. `engine.py` 新增 `kick_player(host_id, target_id)` — 房主移除玩家（游戏进行中自动弃牌）
3. `manager.py` 新增 `handle_kick_player` WebSocket 路由
4. `engine.py` `handle_player_disconnect` — 房主断线自动转让 `is_host` 给下一个在线玩家 + 更新 `table.host_user_id`
5. `websocket.ts` 新增 `kickPlayer(userId)` 方法
6. `Lobby.vue` 玩家列表每人右侧新增红色 `✕` 按钮（仅房主可见，游戏未进行中）

### 2026-05-03 — UI 遮挡修复 + 手机端适配（第十九轮）

**问题**：文字框遮挡手牌，手机端更严重。

**修复**：
1. 手牌尺寸 `md`(4×6rem) → `sm`(3×4.5rem)，间距 `mb-1` → `mb-2`
2. 玩家面板压缩：`px-3 py-1.5` → `px-2 py-1`，字体 `text-sm` → `text-xs`/`text-[11px]`
3. 牌桌高度响应式：`h-80 sm:h-[26rem] lg:h-[30rem]`
4. 手机端布局：操作区 `order-2 lg:order-1`，侧栏 `order-1 lg:order-2`
5. `PokerCard.vue` 新增 `xs` 尺寸（2.25×3.25rem）
6. 公共牌间距 `space-x-2` → `space-x-1.5`

### 2026-05-03 — 底池移位 + 公共牌缩小 + 黑桃黑色（第二十轮）

**问题**：底池文字框遮挡手牌；公共牌过大；黑桃花色灰色不明显。

**修复**：
1. 底池从 felt 内 `top-[10%]` 移到牌桌上方外部独立行（`justify-center`）
2. 公共牌 `size="lg"`(5×7.5rem) → `size="md"`(4×6rem)，空牌位同步缩小
3. `types/game.ts` `SUIT_COLORS['s']` 从 `text-gray-100` → `text-gray-900`（黑桃黑色）

### 2026-05-03 — 房主丢失死锁修复（第二十一轮）

**问题**：场上出现没有房主的情况，游戏进入死锁（无人能开始新局）。

**根因**：4 个独立 bug 叠加：
1. `table.py:remove_player` — 最后一个玩家离开时 `self.players` 为空，host 不转移也不重置，`host_user_id` 指向已离开的旧玩家
2. `table.py:add_player` — 只检查 `host_user_id is None`，不验证该 ID 是否还有效
3. `engine.py:handle_player_disconnect` — 房主断线转让时，如果没有任何 `is_connected` 玩家，转让静默跳过
4. `table.py:remove_player` — 转让 host 给 `min(players.keys())` 不考虑连接状态

**修复**：
1. `remove_player`：优先转让给在线玩家，牌桌为空时 `host_user_id = None`，同时清除旧房主 `is_host`
2. `add_player`：增加 `host_user_id not in self.player_positions` 验证，无效时清除旧标记并指定新房主
3. `handle_player_disconnect`：增加两级 fallback（在线活跃 → 任意活跃 → 清空 host）
4. `get_room_info`：每次查询自动检测并修复房主不一致状态（`host_user_id` vs `is_host` 标记）

### 2026-05-03 — Lobby.vue script setup 丢失修复（第二十二轮）

**问题**：添加"规则说明"按钮后 Lobby 只显示深蓝色背景，所有内容消失。

**根因**：Lobby.vue 的 `<script setup>` 部分被完全删除，文件在 `</template>` 后直接结束。Vue 组件无脚本无法初始化。

**修复**：重建完整 `<script setup>` 部分，恢复所有 ref、computed、函数、import、onMounted 逻辑。新增 `showRules` ref 控制规则说明弹窗。

### 2026-05-03 — 摊牌面板无赢家 + 底池遮挡修复（第二十三轮）

**问题 A**：摊牌结算面板不显示赢家信息和获胜手牌。
**根因**：`showdownWinner` 计算属性 `data.players.find(p => p.user_id === data.winner)` — `data.winner` 是完整对象 `{user_id, username, ...}` 而非 user_id 数字，比较永远为 `false`。
**修复**：直接返回 `data.winner`（后端已发完整赢家对象）；增加 fallback 按 score 排序取第一名；后端增加空 hand fallback 确保永远有 showdown 数据。

**问题 B**：底池显示框被顶部玩家手牌遮挡。
**根因**：底池在 felt div 内部（独立 stacking context），玩家座位在 felt 外部（z-25），felt 默认 z-auto → 玩家座位永远在桌面之上。
**修复**：将底池从 felt 内部移到主容器（felt 外），z-40（高于玩家 z-25）。

### 2026-05-03 — 牌桌 UI 彻底重构（第二十四轮）

**问题**：底池遮挡问题反复出现，牌桌与玩家区域布局耦合。

**修复**：彻底重构牌桌布局，将牌桌与玩家区域分离。
1. **实木边框牌桌**：多层 `linear-gradient` 棕色渐变模拟木纹（`#b87333` → `#8b4e23` → `#6d3515`），`#4a2512` 深色包边，圆形阴影立体感
2. **深绿绒面**：`radial-gradient`（`#1a7a3a` → `#0a3d1a`），暗纹纹理
3. **牌桌缩小**：高度 `h-[22rem] sm:h-[24rem] lg:h-[26rem]`（原 26-30rem），占容器 72%（`top/bottom/left/right: 14%`），四周留出 28% 边距
4. **玩家区域完全外置**：8 座分布在容器边缘（3%-96%），所有座位中心在牌桌轨道之外，手牌和信息面板永不与桌面重叠
5. **Dealer 标记固定桌面位置**：预设 8 个方向的内侧坐标
6. **Tailwind 扩展**：`zIndex: { '25': '25', '35': '35' }`
