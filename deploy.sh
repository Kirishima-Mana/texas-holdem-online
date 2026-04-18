#!/bin/bash

# 德州扑克在线游戏部署脚本
# 使用方法: ./deploy.sh [环境]

set -e

ENV=${1:-production}
COMPOSE_FILE="docker-compose.yml"

echo "🚀 开始部署德州扑克在线游戏 (环境: $ENV)"

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建数据目录..."
mkdir -p backend/data backend/logs
chmod 755 backend/data backend/logs

# 检查环境配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，从 .env.example 复制"
    cp .env.example .env
    echo "📝 请编辑 .env 文件，然后重新运行部署脚本"
    exit 1
fi

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose -f $COMPOSE_FILE down || true

# 清理旧的镜像和容器
echo "🧹 清理旧资源..."
docker system prune -f

# 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose -f $COMPOSE_FILE build

# 启动服务
echo "🚀 启动服务..."
docker-compose -f $COMPOSE_FILE up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
if docker-compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    echo "✅ 服务启动成功！"
    
    # 显示服务信息
    echo ""
    echo "📊 服务状态:"
    docker-compose -f $COMPOSE_FILE ps
    
    echo ""
    echo "🌐 访问地址:"
    echo "前端: http://$(curl -s ifconfig.me)"
    echo "后端API: http://$(curl -s ifconfig.me):8000"
    echo "API文档: http://$(curl -s ifconfig.me):8000/docs"
    
    echo ""
    echo "📋 日志查看:"
    echo "查看所有日志: docker-compose logs -f"
    echo "查看后端日志: docker-compose logs -f backend"
    echo "查看前端日志: docker-compose logs -f frontend"
    
    echo ""
    echo "🛠️  管理命令:"
    echo "停止服务: docker-compose down"
    echo "重启服务: docker-compose restart"
    echo "更新服务: ./deploy.sh"
    
else
    echo "❌ 服务启动失败，请检查日志"
    docker-compose -f $COMPOSE_FILE logs
    exit 1
fi

# 健康检查
echo ""
echo "🏥 执行健康检查..."
HEALTH_CHECK_URL="http://localhost:8000/health"
if curl -s --retry 3 --retry-delay 5 $HEALTH_CHECK_URL | grep -q "healthy"; then
    echo "✅ 健康检查通过"
else
    echo "⚠️  健康检查失败，服务可能仍在启动中"
fi

echo ""
echo "🎉 部署完成！"
echo "💡 提示: 首次使用请访问前端页面注册账号"