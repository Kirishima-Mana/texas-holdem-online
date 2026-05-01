FROM node:18-alpine as builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖（使用 legacy-peer-deps 解决对等依赖冲突）
RUN npm install --legacy-peer-deps

# 复制源代码
COPY . .

# 构建应用（跳过 vue-tsc 类型检查，仅执行 vite build）
RUN npm run build-only

# 生产环境
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]