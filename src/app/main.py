from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db import Base, engine
from app.routes import snapshots, urls

STATIC_DIR = Path(__file__).parent / "static"

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # In non-production we create tables on startup so the demo runs without
    # needing an Alembic migration step. Production uses Alembic only.
    if not settings.is_production:
        # Import models so they are registered on Base.metadata.
        from app import models  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    from app.scheduler.tasks import poll_due_urls
    scheduler.add_job(
        poll_due_urls,
        trigger=IntervalTrigger(seconds=settings.url_polling_rate_secs),  # check every minute which URLs are due
        id="poll_due_urls",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="viff",
        debug=not settings.is_production,
        lifespan=lifespan,
    )
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(urls.router)
    app.include_router(snapshots.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env.value}

    return app


app = create_app()
