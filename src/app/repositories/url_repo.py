from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MonitoredURL


async def get_by_url(db: AsyncSession, url: str) -> MonitoredURL | None:
    result = await db.execute(select(MonitoredURL).filter_by(url=url))

    return result.scalar_one_or_none()


async def create(db: AsyncSession, url: str) -> MonitoredURL:
    monitored_url = MonitoredURL(url=url)

    db.add(monitored_url)
    await db.commit()

    return monitored_url
