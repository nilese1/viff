from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import asset_repo, snapshot_repo, url_repo
from app.services import url_service


async def test_scrape(db_session: AsyncSession):
    # project is now tightly coupled to google good job me
    url = "https://www.google.com"

    monitored_url = await url_repo.create(db_session, url)

    await url_service.scrape_url(db_session, monitored_url)

    # should only be one, but have to do it this way
    snapshots = await snapshot_repo.get_paginated_by_monitored_url(db_session, monitored_url.id)

    first_snapshot = snapshots[0]

    assert first_snapshot
    assert first_snapshot.error_message is None
    assert first_snapshot.http_status is not None

    assets = await asset_repo.get_all_by_snapshot_id(db_session, first_snapshot.id)

    assert len(assets) > 0
