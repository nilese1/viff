.PHONY: help install dev test lint fmt up down prod logs migrate revision shell

help:
	@echo "Targets:"
	@echo "  install    uv sync (with dev group)"
	@echo "  dev        docker compose up (dev, SQLite, live reload)"
	@echo "  prod       docker compose up with Postgres"
	@echo "  test       run pytest locally"
	@echo "  test-docker run pytest inside a container"
	@echo "  lint       ruff check"
	@echo "  fmt        ruff format + fix"
	@echo "  migrate    alembic upgrade head"
	@echo "  revision m='message'  alembic autogenerate revision"

install:
	uv sync --group dev

dev:
	docker compose up --build

down:
	docker compose down

prod:
	docker compose -f compose.yaml -f compose.prod.yaml up --build

logs:
	docker compose logs -f app

test:
	APP_ENV=test uv run pytest -q "$(files)"

test-docker:
	docker compose -f compose.yaml -f compose.test.yaml run --rm app

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

migrate:
	uv run alembic upgrade head

revision:
	@test -n "$(m)" || (echo "usage: make revision m='message'" && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

shell:
	docker compose exec app /bin/sh
