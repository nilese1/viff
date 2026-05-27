from io import BytesIO

from warcio.archiveiterator import ArchiveIterator
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter

from app.archive.assets import FetchedResource


def build_warc(resources: list[FetchedResource]) -> bytes:
    stream = BytesIO()
    writer = WARCWriter(stream, gzip=True)

    for resource in resources:
        statusline = f"{resource.status_code} {resource.reason_phrase}".strip()
        http_headers = StatusAndHeaders(
            statusline,
            list(resource.headers),
            protocol="HTTP/1.1",
        )
        record = writer.create_warc_record(
            resource.url,
            "response",
            payload=BytesIO(resource.content),
            http_headers=http_headers,
        )
        writer.write_record(record)

    return stream.getvalue()


def extract_page_html(warc_bytes: bytes) -> tuple[bytes, str] | None:
    first_response: tuple[bytes, str] | None = None

    for record in ArchiveIterator(BytesIO(warc_bytes)):
        if record.rec_type != "response" or record.http_headers is None:
            continue

        content_type = record.http_headers.get_header("Content-Type") or ""
        payload = record.content_stream().read()
        response = (payload, content_type or "application/octet-stream")

        if first_response is None:
            first_response = response

        if content_type.split(";", 1)[0].strip().lower() == "text/html":
            return response

    return first_response
