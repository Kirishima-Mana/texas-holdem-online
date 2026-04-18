# 德州扑克在线游戏 - 快速开始

## 🚀 一键部署

### 使用 Docker Compose（推荐）

```bash
# 1. 克隆或下载项目
cd /path/to/your/project

# 2. 复制环境配置
cp .env.example .env
# 编辑 .env 文件，修改 SECRET_KEY

# 3. 运行部署脚本
chmod +x deploy.sh
./deploy.sh

# 或者手动部署
docker-compose up -d
```

### 访问应用
- 前端界面: http://localhost
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 🎮 游戏流程

### 1. 注册账号
- 访问 http://localhost
- 点击"注册"标签
- 输入用户名和密码
- 点击注册按钮

### 2. 登录游戏
- 使用注册的账号登录
- 系统自动连接WebSocket

### 3. 加入牌桌
- 在大厅页面点击"加入牌桌"
- 等待房主开始游戏

### 4. 开始游戏（房主）
- 需要至少2名玩家
- 房主点击"开始游戏"
- 系统自动发牌并开始第一轮下注

### 5. 游戏进行
- 每个玩家有25秒行动时间
- 可选择的行动：弃牌、过牌、跟注、加注、全下
- 游戏阶段：翻牌前 → 翻牌 → 转牌 → 河牌 → 摊牌

## ⚙️ 配置说明

### 环境变量 (.env)
```bash
# 后端配置
DEBUG=false                         # 调试模式
DATABASE_URL=sqlite+aiosqlite:///./texas_holdem.db  # 数据库路径
SECRET_KEY=your-secret-key-change-in-production     # JWT密钥

# 前端配置
VITE_API_URL=http://localhost:8000  # 后端API地址
VITE_WS_URL=ws://localhost:8000     # WebSocket地址
```

### 游戏配置 (backend/app/config.py)
```python
# 可调整的游戏参数
max_players = 10                    # 最大玩家数
min_players = 2                     # 最小开始玩家数
initial_chips = 20000               # 初始筹码
small_blind = 50                    # 小盲注
big_blind = 100                     # 大盲注
action_timeout = 25                 # 行动时限（秒）
blind_increase_minutes = 15         # 盲注升级间隔（分钟）
```

## 🐳 Docker 管理命令

### 常用命令
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f
docker-compose logs -f backend      # 仅后端日志
docker-compose logs -f frontend     # 仅前端日志

# 重启服务
docker-compose restart

# 重建镜像
docker-compose build --no-cache

# 查看服务状态
docker-compose ps
```

### 数据持久化
- 数据库文件: `backend/data/texas_holdem.db`
- 日志文件: `backend/logs/`
- 这些目录已挂载到容器，数据不会丢失

## 🔧 故障排除

### 常见问题

#### 1. WebSocket连接失败
```bash
# 检查端口是否开放
netstat -tulpn | grep :8000
netstat -tulpn | grep :80

# 检查防火墙
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp
```

#### 2. 数据库问题
```bash
# 重置数据库
docker-compose down
rm -rf backend/data/*
docker-compose up -d
```

#### 3. 前端无法访问
```bash
# 检查Nginx配置
docker-compose exec frontend nginx -t

# 重启前端服务
docker-compose restart frontend
```

#### 4. 内存不足
```bash
# 清理Docker资源
docker system prune -a
docker volume prune
```

### 日志分析
```bash
# 查看完整日志
docker-compose logs --tail=100

# 搜索错误
docker-compose logs | grep -i error
docker-compose logs | grep -i exception

# 实时监控
docker-compose logs -f --tail=50
```

## 📱 多玩家测试

### 本地测试
1. 使用不同浏览器（Chrome, Firefox, Edge）
2. 每个浏览器注册不同账号
3. 同时登录进行游戏测试

### 网络测试
```bash
# 测试WebSocket连接
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Host: localhost:8000" -H "Origin: http://localhost" \
  http://localhost:8000/ws

# 测试API端点
curl http://localhost:8000/health
curl http://localhost:8000/api/room/info
```

## 🔄 更新部署

### 代码更新后
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建和部署
./deploy.sh

# 或者手动更新
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 配置更新后
```bash
# 修改 .env 文件后
docker-compose down
docker-compose up -d
```

## 🎯 高级功能

### 旁观者上帝视角
- 旁观者可以看到所有玩家的底牌
- 增强熟人局的娱乐性
- 信息隔离：玩家只能看到自己的底牌

### 断线重连
- 玩家断线后自动保留座位和筹码
- 重新登录后恢复游戏状态
- 行动时断线自动弃牌

### 经济系统
- 初始筹码：20,000
- 重新买入：场上筹码中位数的50%
- 每人限重新买入1次
- 第二次破产转为旁观者

### 锦标赛模式
- 盲注每15分钟升级一次
- 小盲注和大盲注翻倍增长
- 游戏持续到只剩1名玩家

## 📞 技术支持

### 获取帮助
1. 查看日志：`docker-compose logs`
2. 检查状态：`docker-compose ps`
3. 验证配置：检查 `.env` 文件

### 报告问题
请提供以下信息：
- 错误日志
- 复现步骤
- 环境信息（Docker版本等）

## 📚 相关文档

- [完整文档](README.md)
- [API文档](http://localhost:8000/docs)
- [架构设计](ARCHITECTURE.md)

---

**祝您游戏愉快！** 🎲♠️♥️♣️♦️