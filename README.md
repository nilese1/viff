# viff

FastAPI + HTMX starter. Postgres in production, SQLite in development and tests. Containerized end-to-end.

## Stack

- **FastAPI** + **Jinja2** + **HTMX** (CDN) — server-rendered, no JS build step
- **SQLAlchemy 2.x async** + **Alembic** for migrations
- **uv** for dependency management
- **Docker Compose** profiles for dev / prod / test

## Environments

| `APP_ENV`     | Database                          | How it runs                                  |
|---------------|-----------------------------------|----------------------------------------------|
| `development` | SQLite at `./data/dev.db`         | `docker compose up` (auto-uses override)     |
| `test`        | SQLite in-memory (per-test reset) | `make test` or `make test-docker`            |
| `production`  | Postgres via `DATABASE_URL`       | `docker compose -f compose.yaml -f compose.prod.yaml up` |

In `development` and `test`, tables are auto-created on startup. In `production`, run Alembic explicitly.

## Quick start

```bash
cp .env.example .env

# Local dev (host Python)
make install
make test

# Dev in Docker (live reload, SQLite)
make dev          # http://localhost:8000

# Prod-like (FastAPI + Postgres in containers)
make prod
docker compose -f compose.yaml -f compose.prod.yaml exec app alembic upgrade head
```

## Layout

```
src/app/
  config.py        pydantic-settings, env-aware DB URL resolution
  db.py            async engine + session, StaticPool for in-memory SQLite
  main.py          app factory, lifespan, /health
  models.py        SQLAlchemy models
  routes/items.py  HTMX CRUD demo
  templates/       Jinja2 + HTMX partials
migrations/        Alembic (async, batch mode for SQLite)
tests/             pytest-asyncio + httpx ASGI client
```

## Migrations

```bash
make revision m="add users table"
make migrate
```

Alembic reads the same `app.config` settings the app does, so migrations run against whichever DB the current `APP_ENV` selects. Batch mode is enabled automatically on SQLite.
