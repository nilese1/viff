from httpx import AsyncClient


async def _create_monitored_url(
    client: AsyncClient,
    *,
    url: str,
    label: str,
    check_interval: int,
    selector_ignore: str | None = None,
) -> str:
    resp = await client.post(
        "/urls/",
        json={
            "url": url,
            "label": label,
            "check_interval": check_interval,
            "selector_ignore": selector_ignore,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_url_pagination_accepts_url_base_filters(client: AsyncClient) -> None:
    expected_id = await _create_monitored_url(
        client,
        url="https://example.com/",
        label="Example",
        check_interval=120,
        selector_ignore="nav, footer",
    )
    await _create_monitored_url(
        client,
        url="https://other.example.com/",
        label="Other",
        check_interval=300,
        selector_ignore="aside",
    )

    resp = await client.get(
        "/urls/list",
        params={
            "url": "https://example.com/",
            "label": "Example",
            "check_interval": 120,
            "selector_ignore": "nav, footer",
        },
    )

    assert resp.status_code == 200
    urls = resp.json()["urls"]
    assert [url["id"] for url in urls] == [expected_id]

