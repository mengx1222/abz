# ============================================================
# 安诊保 AI 副驾 — 前端 Dockerfile（多阶段构建）
# ============================================================

# === 构建阶段 ===
FROM node:20-alpine AS builder

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY package.json package-lock.json* ./
RUN npm ci

# 复制源代码并构建
COPY . .
RUN npm run build

# === 运行阶段 ===
FROM nginx:alpine AS runtime

# 移除 Nginx 默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制静态产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 启动 Nginx（前台运行）
CMD ["nginx", "-g", "daemon off;"]
