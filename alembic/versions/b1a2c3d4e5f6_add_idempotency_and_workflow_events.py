"""add_idempotency_and_workflow_events

Phase 3: Add image_hash and source_url columns to artworks table.
Phase 5: Create workflow_events table for node execution tracking.

Revision ID: b1a2c3d4e5f6
Revises: 0cc13612f78e
Create Date: 2026-06-13 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f6"
down_revision: str = "0cc13612f78e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Phase 3: Add idempotency columns to artworks ─────────────────────
    op.add_column(
        "artworks",
        sa.Column(
            "image_hash",
            sa.String(64),
            nullable=True,
            unique=True,
            comment="SHA-256 hash of file bytes for duplicate detection",
        ),
    )
    op.create_index("ix_artworks_image_hash", "artworks", ["image_hash"], unique=True)

    op.add_column(
        "artworks",
        sa.Column(
            "source_url",
            sa.String(2000),
            nullable=True,
            comment="Original URL if ingested via webhook",
        ),
    )

    # ── Phase 5: Create workflow_events table ────────────────────────────
    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("node_name", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "duration_ms",
            sa.Integer,
            nullable=True,
            comment="Execution duration in milliseconds",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSON,
            nullable=True,
            comment="Node-specific data: track selected, tokens used, etc.",
        ),
        sa.Column(
            "attempt_number",
            sa.Integer,
            default=1,
            nullable=False,
            comment="Attempt number for retry tracking (1 = first attempt)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Drop workflow_events table
    op.drop_table("workflow_events")

    # Drop idempotency columns from artworks
    op.drop_index("ix_artworks_image_hash", table_name="artworks")
    op.drop_column("artworks", "source_url")
    op.drop_column("artworks", "image_hash")
