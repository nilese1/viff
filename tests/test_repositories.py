from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import snapshot_repo, url_repo


async def test_monitored_url_crud(db_session: AsyncSession) -> None:
    monitored_url = await url_repo.create(
        db_session,
        "https://example.com/",
        label="Example",
        check_interval=120,
        selector_ignore="nav, footer",
    )

    fetched = await url_repo.get(db_session, monitored_url.id)
    assert fetched is not None
    assert fetched.url == "https://example.com/"
    assert fetched.label == "Example"

    by_url = await url_repo.get_by_url(db_session, "https://example.com/")
    assert by_url is not None
    assert by_url.id == monitored_url.id

    urls = await url_repo.get_paginated(db_session)
    assert [url.id for url in urls] == [monitored_url.id]

    checked_at = datetime(2026, 1, 1, 12, 0, 0)
    updated = await url_repo.update(
        db_session,
        monitored_url,
        label=None,
        check_interval=300,
        selector_ignore=None,
        is_active="N",
    )
    updated.last_checked_at = checked_at
    await db_session.commit()
    await db_session.refresh(updated)
    assert updated.label is None
    assert updated.check_interval == 300
    assert updated.selector_ignore is None
    assert updated.is_active == "N"
    assert updated.last_checked_at == checked_at

    deleted = await url_repo.delete_by_id(db_session, monitored_url.id)
    assert deleted is True
    assert await url_repo.get(db_session, monitored_url.id) is None
    assert await url_repo.delete_by_id(db_session, monitored_url.id) is False


async def test_monitored_url_filters_active_and_due_urls(db_session: AsyncSession) -> None:
    now = datetime.now()
    due_url = await url_repo.create(
        db_session,
        "https://due.example.com/",
        is_active="Y",
        last_checked_at=now - timedelta(seconds=300),
        check_interval=120,
    )
    not_due_url = await url_repo.create(
        db_session,
        "https://not-due.example.com/",
        is_active="Y",
        last_checked_at=now,
        check_interval=120,
    )
    inactive_url = await url_repo.create(
        db_session,
        "https://inactive.example.com/",
        is_active="N",
        last_checked_at=now - timedelta(seconds=300),
        check_interval=120,
    )

    active_due_urls = await url_repo.get_all(
        db_session,
        is_active="Y",
        is_due_for_check=True,
    )
    assert [url.id for url in active_due_urls] == [due_url.id]

    active_not_due_urls = await url_repo.get_paginated(
        db_session,
        is_active="Y",
        is_due_for_check=False,
    )
    assert [url.id for url in active_not_due_urls] == [not_due_url.id]

    inactive_due_urls = await url_repo.get_all(
        db_session,
        is_active="N",
        is_due_for_check=True,
    )
    assert [url.id for url in inactive_due_urls] == [inactive_url.id]


async def test_snapshot_crud(db_session: AsyncSession) -> None:
    monitored_url = await url_repo.create(db_session, "https://example.com/")

    snapshot = await snapshot_repo.create(
        db_session,
        monitored_url.id,
        raw_html="<html>first</html>",
        text_content="first",
        content_hash="hash-1",
        http_status=200,
    )

    fetched = await snapshot_repo.get(db_session, snapshot.id)
    assert fetched is not None
    assert fetched.text_content == "first"

    by_hash = await snapshot_repo.get_by_content_hash(db_session, monitored_url.id, "hash-1")
    assert by_hash is not None
    assert by_hash.id == snapshot.id

    latest = await snapshot_repo.get_latest_by_monitored_url(db_session, monitored_url.id)
    assert latest is not None
    assert latest.id == snapshot.id

    notified_at = datetime(2026, 1, 1, 12, 0, 0)
    updated = await snapshot_repo.update(
        db_session,
        snapshot,
        raw_html=None,
        text_content="second",
        content_hash="hash-2",
        http_status=500,
        error_message="server error",
        notified_at=notified_at,
    )
    assert updated.raw_html is None
    assert updated.text_content == "second"
    assert updated.content_hash == "hash-2"
    assert updated.http_status == 500
    assert updated.error_message == "server error"
    assert updated.notified_at == notified_at

    updated = await snapshot_repo.update(
        db_session,
        snapshot,
        text_content="third",
    )
    assert updated.text_content == "third"
    assert updated.content_hash == "hash-2"
    assert updated.error_message == "server error"

    deleted = await snapshot_repo.delete_by_id(db_session, snapshot.id)
    assert deleted is True
    assert await snapshot_repo.get(db_session, snapshot.id) is None
    assert await snapshot_repo.delete_by_id(db_session, snapshot.id) is False
