# 在线德州扑克游戏

一个为熟人娱乐设计的在线德州扑克游戏，支持断线重连、旁观者上帝视角、锦标赛盲注模式等功能。

## 功能特性

### 🎮 核心功能
- 2-10人实时在线对战
- 完整的德州扑克规则实现
- 锦标赛盲注递增模式
- 25秒行动时限，超时自动弃牌

### 🔐 账号与连接
- 用户注册与登录
- 断线自动重连恢复
- 会话保持，刷新页面不丢失状态
- 房主权限管理

### 💰 经济系统
- 初始筹码：20,000
- 常规买入：20,000筹码
- 重新买入：当前场上筹码中位数的50%（每人限1次）
- 破产处理：第二次破产转为旁观者

### 👁️ 旁观者模式
- 上帝视角：旁观者可查看所有玩家底牌
- 实时聊天系统
- 玩家状态实时显示

### 🎯 游戏流程
1. 玩家注册/登录
2. 加入牌桌（等待房主开始）
3. 游戏开始：发底牌 → 下盲注 → 翻牌前 → 翻牌 → 转牌 → 河牌 → 摊牌
4. 盲注每15分钟升级一次
5. 只剩1名玩家时游戏结束

## 技术架构

### 后端 (Python)
- **框架**: FastAPI + WebSocket
- **数据库**: SQLite + SQLAlchemy
- **游戏引擎**: treys (牌型评估)
- **认证**: JWT + 会话令牌

### 前端 (Vue 3)
- **框架**: Vue 3 + TypeScript
- **状态管理**: Pinia
- **样式**: Tailwind CSS
- **实时通信**: WebSocket

### 部署
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **数据库**: SQLite (文件存储)

## 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd texas-holdem-online

# 复制环境配置
cp .env.example .env
# 编辑 .env 文件，修改 SECRET_KEY
```

### 2. 使用 Docker 运行
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 访问应用
- 前端: http://localhost
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 4. 开发模式运行
```bash
# 后端开发
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端开发
cd frontend
npm install
npm run dev
```

## 项目结构

```
texas-holdem-online/
├── backend/                 # Python后端
│   ├── app/
│   │   ├── game/           # 游戏引擎
│   │   ├── websocket/      # WebSocket处理
│   │   ├── models.py       # 数据模型
│   │   ├── schemas.py      # Pydantic模型
│   │   └── main.py         # FastAPI应用
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # Vue前端
│   ├── src/
│   │   ├── components/     # Vue组件
│   │   ├── stores/         # Pinia状态管理
│   │   ├── services/       # API/WebSocket服务
│   │   └── types/          # TypeScript类型
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml      # Docker编排
└── README.md
```

## API 文档

启动服务后访问：http://localhost:8000/docs

### 主要端点
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/room/info` - 获取房间信息
- `WS /ws` - WebSocket连接（实时游戏）

## 游戏规则说明

### 座位与行动
1. 庄家位置顺时针轮转
2. 小盲注：庄家左侧玩家
3. 大盲注：小盲注左侧玩家
4. 行动顺序：大盲注左侧玩家开始

### 下注规则
1. **翻牌前**：大盲注为当前下注额
2. **翻牌/转牌/河牌**：从庄家左侧开始
3. **加注**：至少为大盲注的2倍
4. **全下**：投入全部剩余筹码

### 特殊规则
1. **断线处理**：行动时断线自动弃牌
2. **离桌**：保留筹码，可重新加入
3. **离开**：清空筹码，转为旁观者
4. **重新买入**：每人限1次，金额为场上筹码中位数的50%

## 部署到云服务器

### 1. 准备服务器
```bash
# 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin
```

### 2. 上传项目
```bash
scp -r texas-holdem-online user@your-server:/opt/
```

### 3. 配置与启动
```bash
cd /opt/texas-holdem-online
cp .env.example .env
# 编辑 .env，设置 SECRET_KEY 和域名
vim .env

# 启动服务
docker-compose up -d

# 设置开机自启
sudo systemctl enable docker
```

### 4. 配置域名和SSL（可选）
```bash
# 使用 Nginx 反向代理
# 配置 SSL 证书（Let's Encrypt）
```

## 故障排除

### 常见问题
1. **WebSocket连接失败**
   - 检查防火墙端口（80, 8000）
   - 验证后端服务是否正常运行
   - 检查浏览器控制台错误

2. **数据库问题**
   - 确保 data/ 目录有写入权限
   - 重启后端服务：`docker-compose restart backend`

3. **前端无法访问**
   - 检查Nginx配置
   - 查看前端容器日志：`docker-compose logs frontend`

### 日志查看
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

## 开发指南

### 添加新功能
1. 后端API：在 `app/api/` 添加新端点
2. 游戏逻辑：在 `app/game/` 修改引擎
3. 前端组件：在 `src/components/` 创建Vue组件
4. 类型定义：更新 `src/types/game.ts`

### 测试
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请通过项目仓库的 Issues 页面反馈。