from httpx import AsyncClient

from app.archive.assets import FetchedResource
from app.archive.storage import get_archive_storage
from app.archive.warc import build_warc


async def _create_monitored_url(client: AsyncClient) -> str:
    resp = await client.post(
        "/urls/",
        json={
            "url": "https://compare.example.com/",
            "label": "Compare",
            "check_interval": 120,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_snapshot(
    client: AsyncClient,
    monitored_url_id: str,
    content: str,
) -> tuple[str, str]:
    raw_html = f"<html><body><h1>{content}</h1></body></html>"
    warc_storage_key = f"tests/{monitored_url_id}/{content}/archive.warc.gz"
    storage = get_archive_storage()
    await storage.put_bytes(
        warc_storage_key,
        build_warc(
            [
                FetchedResource(
                    url="https://compare.example.com/",
                    status_code=200,
                    reason_phrase="OK",
                    headers=(("Content-Type", "text/html; charset=utf-8"),),
                    content=raw_html.encode("utf-8"),
                )
            ]
        ),
        "application/warc+gzip",
    )

    resp = await client.post(
        f"/urls/id/{monitored_url_id}/snapshots/",
        json={
            "warc_storage_key": warc_storage_key,
            "text_content": content,
            "content_hash": f"hash-{content}",
            "http_status": 200,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"], warc_storage_key


async def test_root_renders_snapshot_compare_page(client: AsyncClient) -> None:
    resp = await client.get("/")

    assert resp.status_code == 200
    assert "Snapshot Compare" in resp.text
    assert 'hx-get="/"' in resp.text
    assert 'id="snapshot-compare-results"' in resp.text


async def test_root_compares_snapshots_with_htmx_partial(client: AsyncClient) -> None:
    monitored_url_id = await _create_monitored_url(client)
    left_snapshot_id, left_storage_key = await _create_snapshot(client, monitored_url_id, "before")
    right_snapshot_id, right_storage_key = await _create_snapshot(client, monitored_url_id, "after")

    resp = await client.get(
        "/",
        params={
            "left_snapshot_id": left_snapshot_id,
            "right_snapshot_id": right_snapshot_id,
        },
        headers={"HX-Request": "true"},
    )

    assert resp.status_code == 200
    assert "<!doctype html>" not in resp.text
    assert "Left snapshot" in resp.text
    assert "Right snapshot" in resp.text
    assert left_snapshot_id in resp.text
    assert right_snapshot_id in resp.text
    assert left_storage_key in resp.text
    assert right_storage_key in resp.text

    left_asset_resp = await client.get(f"/archive/assets/page/{left_storage_key}")
    right_asset_resp = await client.get(f"/archive/assets/page/{right_storage_key}")
    assert left_asset_resp.text == "<html><body><h1>before</h1></body></html>"
    assert right_asset_resp.text == "<html><body><h1>after</h1></body></html>"
