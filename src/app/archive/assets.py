import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class FetchedResource:
    url: str
    status_code: int
    reason_phrase: str
    headers: tuple[tuple[str, str], ...]
    content: bytes


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlparse(url)
    default_port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, parsed.hostname or "", parsed.port or default_port


def _srcset_urls(value: str) -> Iterable[str]:
    for candidate in value.split(","):
        url = candidate.strip().split(" ", 1)[0]
        if url:
            yield url


def extract_same_origin_asset_urls(html: str, base_url: str) -> list[str]:
    base_origin = _origin(base_url)
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []

    for tag in soup.select("[src]"):
        candidates.append(tag["src"])
    for tag in soup.select("link[href]"):
        candidates.append(tag["href"])
    for tag in soup.select("[poster]"):
        candidates.append(tag["poster"])
    for tag in soup.select("object[data]"):
        candidates.append(tag["data"])
    for tag in soup.select("[srcset]"):
        candidates.extend(_srcset_urls(tag["srcset"]))

    urls: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        absolute = urldefrag(urljoin(base_url, candidate))[0]
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if _origin(absolute) != base_origin:
            continue
        if absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)

    return urls


async def fetch_same_origin_assets(
    client: httpx.AsyncClient,
    html: str,
    base_url: str,
) -> list[FetchedResource]:
    resources: list[FetchedResource] = []
    seen_digests: set[str] = set()

    for asset_url in extract_same_origin_asset_urls(html, base_url):
        try:
            response = await client.get(asset_url)
            response.raise_for_status()
        except httpx.HTTPError:
            continue

        digest = hashlib.sha256(response.content).hexdigest()
        if digest in seen_digests:
            continue

        seen_digests.add(digest)
        resources.append(
            FetchedResource(
                url=str(response.url),
                status_code=response.status_code,
                reason_phrase=response.reason_phrase,
                headers=tuple((key, value) for key, value in response.headers.items()),
                content=response.content,
            )
        )

    return resources
