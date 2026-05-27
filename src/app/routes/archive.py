import mimetypes

from fastapi import APIRouter, HTTPException, Response

from app.archive.storage import get_archive_storage
from app.archive.warc import extract_page_html

router = APIRouter(prefix="/archive/assets", tags=["archive"])


def _validate_storage_key(storage_key: str) -> str:
    if (
        not storage_key
        or storage_key.startswith("/")
        or "\\" in storage_key
        or any(part in {"", ".", ".."} for part in storage_key.split("/"))
    ):
        raise HTTPException(status_code=400, detail="Invalid storage key")

    return storage_key


def _guess_media_type(storage_key: str) -> str:
    if storage_key.endswith(".warc.gz"):
        return "application/warc+gzip"

    media_type, _ = mimetypes.guess_type(storage_key)
    if media_type == "text/html":
        return "text/html; charset=utf-8"

    return media_type or "application/octet-stream"


@router.get("/page/{storage_key:path}", name="get_archive_warc_page")
async def get_archive_warc_page(storage_key: str) -> Response:
    storage_key = _validate_storage_key(storage_key)
    storage = get_archive_storage()

    try:
        content = await storage.get_bytes(storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Archive asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid storage key") from exc

    page_html = extract_page_html(content)
    if page_html is None:
        raise HTTPException(status_code=404, detail="Archived page HTML not found")

    html, content_type = page_html
    return Response(
        content=html,
        media_type=content_type or "text/html; charset=utf-8",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/{storage_key:path}", name="get_archive_asset")
async def get_archive_asset(storage_key: str) -> Response:
    storage_key = _validate_storage_key(storage_key)
    storage = get_archive_storage()

    try:
        content = await storage.get_bytes(storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Archive asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid storage key") from exc

    return Response(
        content=content,
        media_type=_guess_media_type(storage_key),
        headers={"Cache-Control": "private, max-age=3600"},
    )
