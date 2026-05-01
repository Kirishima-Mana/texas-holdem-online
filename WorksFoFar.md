# 德州扑克在线游戏 - 部署状态与 Debug 交接文档

## 1. 项目架构基线[cite: 2, 3]
- **后端**：FastAPI + WebSocket + SQLite (运行在容器内部的 `8000` 端口)
- **前端**：Vue 3 + TypeScript + Vite + Pinia + Nginx (暴露至宿主机的 `8888:80` 端口)
- **部署方式**：单体 Docker Compose (`docker-compose up -d`)[cite: 1]
- **网络拓扑**：采用了 Cloudflare Tunnel (Zero Trust) 进行内网穿透。`texasholdem.kirishima.one` 流量通过 mTLS 隧道直达宿主机的 `localhost:8888` 端口。宿主机层面无公网端口冲突。

## 2. 之前已解决的部署阻碍
为了让应用在现有的 Docker 环境中编译通过，我们修改了前端 `Dockerfile` 和 `package.json`：
1. 放弃了 `npm ci`，使用 `npm install --legacy-peer-deps` 解决对等依赖冲突。
2. 注入了 `npmmirror` 国内源解决跨国网络丢包。
3. 移除了 `package.json` 中 `build` 脚本的 `vue-tsc` 类型检查，以绕过 TypeScript 版本不匹配导致的正则表达式报错。
4. 解决了端口冲突，前端 Nginx 现已映射至宿主机的 `8888` 端口。

## 3. 当前面临的唯一核心 Bug：前端 SPA 白屏死机
- **症状表现**：用户通过域名 `https://texasholdem.kirishima.one` 访问时，成功获取了基础的 HTML 文件（页面短暂显示“正在加载德州扑克在线……”），但随后陷入白屏，无任何后续渲染。
- **排查线索 1（后端网络）**：查看后端的 Docker 日志，**没有任何**来自客户端 `/api` 或 `/ws` 的请求记录（只有公网扫描器的随机探测流量）。说明请求在浏览器端根本没有发向正确的服务器。
- **排查线索 2（前端打包）**：项目的根目录下有一个 `.env` 文件，里面定义了 `VITE_API_URL=https://texasholdem.kirishima.one/api` 和 `VITE_WS_URL=wss://texasholdem.kirishima.one/ws`。但我怀疑在执行 `docker compose build frontend` 时，前端的 Docker build context 并没有成功将外层的 `.env` 变量注入到 Vite 的静态编译产物中。导致浏览器端下载到的 JS 代码，依旧在请求 `localhost:8000` 或其他错误地址。

## 4. 你的任务
请基于以上信息，接手排查这个“白屏死机”问题。重点关注：
1. 如何在当前的多容器 Docker Compose 构建流程中，确保 Vite 正确读取并硬编码构建时的环境变量？
2. 请给我提供具体的排查命令（如何验证打包后的 Nginx 静态文件里的 API 地址）以及修复 Dockerfile 或 `docker-compose.yml` 的代码。