"""store archives in object storage

Revision ID: 2fd0d7f0ef3b
Revises: 80c576073fbf
Create Date: 2026-05-27 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2fd0d7f0ef3b"
down_revision: str | None = "80c576073fbf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("snapshots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("warc_storage_key", sa.String(length=2048), nullable=True))
        batch_op.drop_column("raw_html")


def downgrade() -> None:
    with op.batch_alter_table("snapshots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("raw_html", sa.Text(), nullable=True))
        batch_op.drop_column("warc_storage_key")
