from httpx import AsyncClient


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


async def _create_snapshot(client: AsyncClient, monitored_url_id: str, content: str) -> str:
    resp = await client.post(
        f"/urls/id/{monitored_url_id}/snapshots/",
        json={
            "raw_html": f"<html><body><h1>{content}</h1></body></html>",
            "text_content": content,
            "content_hash": f"hash-{content}",
            "http_status": 200,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_root_renders_snapshot_compare_page(client: AsyncClient) -> None:
    resp = await client.get("/")

    assert resp.status_code == 200
    assert "Snapshot Compare" in resp.text
    assert 'hx-get="/"' in resp.text
    assert 'id="snapshot-compare-results"' in resp.text


async def test_root_compares_snapshots_with_htmx_partial(client: AsyncClient) -> None:
    monitored_url_id = await _create_monitored_url(client)
    left_snapshot_id = await _create_snapshot(client, monitored_url_id, "before")
    right_snapshot_id = await _create_snapshot(client, monitored_url_id, "after")

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
    assert "before" in resp.text
    assert "after" in resp.text
