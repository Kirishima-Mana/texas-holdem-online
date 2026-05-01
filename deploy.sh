#!/bin/bash

# 德州扑克在线游戏部署脚本
set -e

COMPOSE_FILE="docker-compose.yml"

echo "=== 德州扑克在线游戏部署 ==="

# 检测 docker compose 命令
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "错误: 未找到 Docker Compose，请先安装"
    exit 1
fi

# 创建必要目录
echo "[1/5] 创建数据目录..."
mkdir -p backend/data backend/logs

# 检查环境配置文件
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[!] 未找到 .env 文件，从 .env.example 复制"
        cp .env.example .env
        echo "[!] 请编辑 .env 文件中的 SECRET_KEY，然后重新运行部署脚本"
        exit 1
    else
        echo "错误: .env.example 文件不存在"
        exit 1
    fi
fi

# 加载 .env 文件中的变量
set -a
source .env 2>/dev/null || true
set +a

# 停止现有服务
echo "[2/5] 停止现有服务..."
$DOCKER_COMPOSE -f $COMPOSE_FILE down 2>/dev/null || true

# 构建镜像
echo "[3/5] 构建 Docker 镜像..."
$DOCKER_COMPOSE -f $COMPOSE_FILE build

# 启动服务
echo "[4/5] 启动服务..."
$DOCKER_COMPOSE -f $COMPOSE_FILE up -d

# 等待服务启动
echo "[5/5] 等待服务启动..."
sleep 5

# 健康检查
echo ""
echo "=== 健康检查 ==="
BACKEND_PORT="${BACKEND_PORT:-8000}"
if command -v curl &>/dev/null; then
    if curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        echo "后端: OK"
    else
        echo "后端: 未就绪 (请等待几秒后重试)"
    fi
else
    echo "后端: 跳过 (curl 未安装)"
fi

echo ""
echo "=== 部署完成 ==="
echo "前端页面: http://localhost:${FRONTEND_PORT:-8888}"
echo "后端 API: http://localhost:${BACKEND_PORT}"
echo ""
echo "管理命令:"
echo "  查看日志: $DOCKER_COMPOSE logs -f"
echo "  停止服务: $DOCKER_COMPOSE down"
echo "  重启服务: $DOCKER_COMPOSE restart"
