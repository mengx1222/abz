.PHONY: help init up down logs backend frontend migrate seed test clean lint build api-test

# ============================================================
# 安诊保 AI 副驾 — 开发命令
# ============================================================

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# -------------------- 初始化 --------------------

init: ## 初始化项目（安装依赖 + 数据库迁移 + 种子数据）
	@echo "🚀 安诊保 AI 副驾 — 项目初始化"
	docker compose up -d postgres redis
	@echo "⏳ 等待数据库启动..."
	@sleep 5
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
	cd backend && . .venv/bin/activate && alembic upgrade head
	cd backend && . .venv/bin/activate && python scripts/seed.py
	cd frontend && npm install
	@echo "✅ 初始化完成！运行 'make dev' 启动开发环境"

# -------------------- Docker --------------------

up: ## 启动所有 Docker 服务
	docker compose up -d

down: ## 停止所有 Docker 服务
	docker compose down

down-clean: ## 停止并清除所有数据卷
	docker compose down -v

logs: ## 查看服务日志（Ctrl+C 退出）
	docker compose logs -f

logs-backend: ## 查看后端日志
	docker compose logs -f backend

# -------------------- 本地开发 --------------------

dev: ## 启动本地开发环境（前端 + 后端）
	@echo "dev: 请在两个终端分别运行:"
	@echo "  make backend   (终端1)"
	@echo "  make frontend  (终端2)"
	@echo "或者运行: make up"

backend: ## 启动后端（本地开发模式，需要 .venv）
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## 启动前端（本地开发模式）
	cd frontend && npm run dev

# -------------------- 数据库 --------------------

migrate: ## 运行数据库迁移
	cd backend && . .venv/bin/activate && alembic upgrade head

migrate-create: ## 创建新迁移脚本（用法: make migrate-create msg="add_xxx_table"）
	cd backend && . .venv/bin/activate && alembic revision --autogenerate -m "$(msg)"

seed: ## 导入种子数据（幂等，跳过已存在的）
	cd backend && . .venv/bin/activate && python scripts/seed.py

reset-db: ## 重置数据库（删除并重建）
	cd backend && . .venv/bin/activate && alembic downgrade base
	cd backend && . .venv/bin/activate && alembic upgrade head
	cd backend && . .venv/bin/activate && python scripts/seed.py

# -------------------- 测试 --------------------

test: ## 运行所有测试
	cd backend && . .venv/bin/activate && pytest -x --tb=short

test-cov: ## 运行测试并生成覆盖率报告
	cd backend && . .venv/bin/activate && pytest --cov=app --cov-report=html --cov-report=term-missing

test-api: ## 运行 API 集成测试（需要后端运行中）
	@echo "测试 Health Check..."
	curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
	@echo "\n测试 Demo 登录..."
	curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"phone":"13800138000","verification_code":"888888"}' | python3 -m json.tool

# -------------------- 代码质量 --------------------

lint: ## 运行代码检查（后端 + 前端）
	cd backend && . .venv/bin/activate && ruff check app/ || true
	cd frontend && npx tsc --noEmit

lint-fix: ## 自动修复代码风格问题
	cd backend && . .venv/bin/activate && ruff check --fix app/ || true

# -------------------- 构建 --------------------

build: ## 构建前端生产版本
	cd frontend && npm run build

# -------------------- 清理 --------------------

clean: ## 清理构建产物和缓存
	rm -rf frontend/dist
	rm -rf backend/.venv
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 清理完成"
