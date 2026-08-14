# ============================================================
# 安诊保 AI 副驾 — 后端 Dockerfile（多阶段构建）
# ============================================================

# === 依赖安装阶段 ===
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装系统构建依赖（编译 asyncpg 等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# === 运行阶段 ===
FROM python:3.12-slim AS runtime

WORKDIR /app

# 仅安装运行时系统依赖（不含 build-essential）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制已安装的 Python 依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY . .

# 创建上传文件存储目录
RUN mkdir -p /app/uploads

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令（生产环境不使用 --reload）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
