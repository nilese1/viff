from app.db import SessionLocal
from app.schemas.url import URLListParams
from app.services import url_service


async def poll_due_urls():
    async with SessionLocal() as db:
        params = URLListParams(is_active="Y", is_due_for_check=True)

        due_urls = await url_service.get_all(db, params)

        for url in due_urls:
            await url_service.scrape_url(db, url)
