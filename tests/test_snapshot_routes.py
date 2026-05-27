from uuid import uuid4

from httpx import AsyncClient

from app.archive.assets import FetchedResource
from app.archive.storage import get_archive_storage
from app.archive.warc import build_warc


async def _create_monitored_url(client: AsyncClient, url: str = "https://example.com/") -> str:
    resp = await client.post(
        "/urls/",
        json={
            "url": url,
            "label": "Example",
            "check_interval": 120,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_snapshot_crud_endpoints_are_scoped_to_monitored_url(
    client: AsyncClient,
) -> None:
    monitored_url_id = await _create_monitored_url(client)
    other_monitored_url_id = await _create_monitored_url(client, "https://other.example.com/")
    base_path = f"/urls/id/{monitored_url_id}/snapshots"
    warc_storage_key = f"tests/{monitored_url_id}/archive.warc.gz"
    storage = get_archive_storage()
    await storage.put_bytes(
        warc_storage_key,
        build_warc(
            [
                FetchedResource(
                    url="https://example.com/",
                    status_code=200,
                    reason_phrase="OK",
                    headers=(("Content-Type", "text/html; charset=utf-8"),),
                    content=b"<html>first</html>",
                )
            ]
        ),
        "application/warc+gzip",
    )

    create_resp = await client.post(
        f"{base_path}/",
        json={
            "monitored_url_id": other_monitored_url_id,
            "warc_storage_key": warc_storage_key,
            "text_content": "first",
            "content_hash": "hash-1",
            "http_status": 200,
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["monitored_url_id"] == monitored_url_id
    assert created["warc_storage_key"] == warc_storage_key
    assert "raw_html_storage_key" not in created
    assert "raw_html" not in created
    assert created["text_content"] == "first"

    snapshot_id = created["id"]

    scoped_miss = await client.get(f"/urls/id/{other_monitored_url_id}/snapshots/id/{snapshot_id}")
    assert scoped_miss.status_code == 404

    get_resp = await client.get(f"{base_path}/id/{snapshot_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == snapshot_id
    assert "raw_html" not in fetched
    assert "raw_html_storage_key" not in fetched

    asset_resp = await client.get(f"/archive/assets/page/{warc_storage_key}")
    assert asset_resp.status_code == 200
    assert asset_resp.headers["content-type"].startswith("text/html")
    assert asset_resp.text == "<html>first</html>"

    list_resp = await client.get(f"{base_path}/list")
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert listed["cursor"] is None
    assert listed["cursor_id"] is None
    assert [snapshot["id"] for snapshot in listed["snapshots"]] == [snapshot_id]

    empty_list_resp = await client.get(f"/urls/id/{other_monitored_url_id}/snapshots/list")
    assert empty_list_resp.status_code == 200
    assert empty_list_resp.json()["snapshots"] == []

    update_resp = await client.put(
        f"{base_path}/id/{snapshot_id}",
        json={
            "text_content": "second",
            "content_hash": "hash-2",
            "http_status": 500,
            "error_message": "server error",
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert "raw_html" not in updated
    assert "raw_html_storage_key" not in updated
    assert updated["text_content"] == "second"
    assert updated["content_hash"] == "hash-2"
    assert updated["http_status"] == 500
    assert updated["error_message"] == "server error"

    delete_resp = await client.delete(f"{base_path}/id/{snapshot_id}")
    assert delete_resp.status_code == 204

    deleted_get_resp = await client.get(f"{base_path}/id/{snapshot_id}")
    assert deleted_get_resp.status_code == 404


async def test_archive_asset_endpoint_rejects_invalid_storage_keys(
    client: AsyncClient,
) -> None:
    resp = await client.get("/archive/assets/foo%5Cbar")

    assert resp.status_code == 400


async def test_snapshot_pagination_requires_existing_monitored_url(
    client: AsyncClient,
) -> None:
    missing_monitored_url_id = uuid4()

    resp = await client.get(f"/urls/id/{missing_monitored_url_id}/snapshots/list")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "URL not found"


async def test_snapshot_pagination_uses_monitored_url_cursor(
    client: AsyncClient,
) -> None:
    monitored_url_id = await _create_monitored_url(client)
    base_path = f"/urls/id/{monitored_url_id}/snapshots"

    first_resp = await client.post(
        f"{base_path}/",
        json={"text_content": "first", "content_hash": "hash-1"},
    )
    second_resp = await client.post(
        f"{base_path}/",
        json={"text_content": "second", "content_hash": "hash-2"},
    )
    assert first_resp.status_code == 201
    assert second_resp.status_code == 201

    page_one_resp = await client.get(f"{base_path}/list", params={"limit": 1})
    assert page_one_resp.status_code == 200
    page_one = page_one_resp.json()
    assert len(page_one["snapshots"]) == 1
    assert page_one["cursor"] is not None
    assert page_one["cursor_id"] is not None

    page_two_resp = await client.get(
        f"{base_path}/list",
        params={
            "limit": 1,
            "cursor": page_one["cursor"],
            "cursor_id": page_one["cursor_id"],
        },
    )
    assert page_two_resp.status_code == 200
    page_two = page_two_resp.json()
    assert len(page_two["snapshots"]) == 1
    assert page_two["snapshots"][0]["id"] != page_one["snapshots"][0]["id"]
    assert page_two["cursor"] is None
    assert page_two["cursor_id"] is None
