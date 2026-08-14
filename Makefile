.PHONY: help init up down logs backend frontend migrate seed test clean

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## 初始化项目（安装依赖+数据库迁移+种子数据）
	docker compose up -d postgres redis
	@echo "等待数据库启动..."
	sleep 5
	cd backend && pip install -e ".[dev]"
	cd backend && alembic upgrade head
	cd backend && python scripts/seed.py
	cd frontend && npm install
	@echo "初始化完成！"

up: ## 启动所有服务
	docker compose up -d

down: ## 停止所有服务
	docker compose down

logs: ## 查看日志
	docker compose logs -f

backend: ## 启动后端（本地开发）
	cd backend && uvicorn app.main:app --reload --port 8000

frontend: ## 启动前端（本地开发）
	cd frontend && npm run dev

migrate: ## 运行数据库迁移
	cd backend && alembic upgrade head

seed: ## 导入种子数据
	cd backend && python scripts/seed.py

test: ## 运行测试
	cd backend && pytest --cov=app
	cd frontend && npm run test

clean: ## 清理所有数据
	docker compose down -v
