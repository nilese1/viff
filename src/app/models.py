import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db import Base


class TimestampedUUIDBase(Base):
    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# ------------------------------------------------------------------------------
# MonitoredURL — a URL the user wants to watch
# ------------------------------------------------------------------------------
class MonitoredURL(TimestampedUUIDBase):
    """
    Represents a URL being tracked for changes.

    selector_ignore : comma-separated CSS selectors to strip before diffing
                      (e.g. "nav, footer, .ads") so noise doesn't trigger alerts
    check_interval  : how often to scrape, in seconds (default 3600 = 1 hour)
    is_active       : soft toggle so users can pause without deleting history
    """

    __tablename__ = "monitored_urls"

    url = Column(String(2048), nullable=False, unique=True)
    label = Column(String(255), nullable=True)  # friendly name
    check_interval = Column(Integer, nullable=False, default=3600)
    # CSS selectors to strip
    selector_ignore = Column(Text, nullable=True)
    is_active = Column(String(1), nullable=False, default="Y")
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

    # relationships
    snapshots = relationship(
        "Snapshot",
        back_populates="monitored_url",
        cascade="all, delete-orphan",
        order_by="Snapshot.created_at.desc()",
    )
    diffs = relationship(
        "Diff",
        back_populates="monitored_url",
        cascade="all, delete-orphan",
        order_by="Diff.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<MonitoredURL id={self.id} url={self.url!r}>"


class Snapshot(TimestampedUUIDBase):
    """
    A single scrape result for a MonitoredURL.

    raw_html         : full page HTML before any cleaning
    text_content     : extracted/cleaned text used for diffing
    content_hash     : SHA-256 of text_content; lets us skip storing a full
                       duplicate snapshot if nothing changed
    http_status      : the HTTP status code returned by the server
    error_message    : populated if the scrape failed (timeout, DNS, etc.)
    notified_at      : populated once the user has been alerted about this change;
                       null means notification is still pending
    """

    __tablename__ = "snapshots"
    __table_args__ = (
        UniqueConstraint("monitored_url_id", "content_hash", name="uq_snapshot_url_hash"),
    )

    monitored_url_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monitored_urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_html = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    http_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)

    monitored_url = relationship("MonitoredURL", back_populates="snapshots")

    def __repr__(self) -> str:
        return (
            f"<Snapshot id={self.id} url_id={self.monitored_url_id} "
            f"status={self.http_status} hash={self.content_hash!r}>"
        )
