.PHONY: install migrate migrate-create seed run lint fmt

install:
	pip install -e ".[dev]"

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python -m scripts.seed

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check app/

fmt:
	ruff format app/
