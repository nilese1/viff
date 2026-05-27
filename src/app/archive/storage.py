import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import Settings, get_settings


class ArchiveStorage(Protocol):
    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get_bytes(self, key: str) -> bytes: ...

    async def get_text(self, key: str) -> str:
        data = await self.get_bytes(key)
        return data.decode("utf-8", errors="replace")


class LocalArchiveStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path_for_key(self, key: str) -> Path:
        path = (self.root / key).resolve()
        root = self.root.resolve()
        path.relative_to(root)
        return path

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def get_bytes(self, key: str) -> bytes:
        return self._path_for_key(key).read_bytes()

    async def get_text(self, key: str) -> str:
        return (await self.get_bytes(key)).decode("utf-8", errors="replace")


class Boto3ArchiveStorage:
    def __init__(self, settings: Settings) -> None:
        if not settings.archive_bucket:
            raise RuntimeError("ARCHIVE_BUCKET must be set when ARCHIVE_STORAGE_BACKEND=gcs")

        import boto3

        self.bucket = settings.archive_bucket
        self.client = boto3.client("s3", endpoint_url=settings.archive_gcs_endpoint_url)

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get_bytes(self, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=key)
        except Exception as exc:
            if _is_missing_boto_object(exc):
                raise FileNotFoundError(key) from exc
            raise
        body = response["Body"]
        return await asyncio.to_thread(body.read)

    async def get_text(self, key: str) -> str:
        return (await self.get_bytes(key)).decode("utf-8", errors="replace")


def build_object_key(*parts: object) -> str:
    settings = get_settings()
    key_parts = [str(part).strip("/") for part in parts if str(part).strip("/")]
    prefix = settings.archive_prefix.strip("/")
    if prefix:
        key_parts.insert(0, prefix)
    return "/".join(key_parts)


def _is_missing_boto_object(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False

    error = response.get("Error")
    if not isinstance(error, dict):
        return False

    return error.get("Code") in {"NoSuchKey", "404", "NotFound"}


@lru_cache
def get_archive_storage() -> ArchiveStorage:
    settings = get_settings()
    if settings.archive_storage_backend == "gcs":
        return Boto3ArchiveStorage(settings)
    if settings.archive_storage_backend == "local":
        return LocalArchiveStorage(settings.resolved_archive_storage_path)
    raise RuntimeError(f"Unsupported archive storage backend: {settings.archive_storage_backend}")
