"""add_pinterest_publishing_fields

Revision ID: c2b3d4e5f6a7
Revises: b1a2c3d4e5f6
Create Date: 2026-06-14 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2b3d4e5f6a7'
down_revision: Union[str, None] = 'b1a2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('artworks', sa.Column('pinterest_status', sa.String(length=50), nullable=True))
    op.add_column('artworks', sa.Column('pinterest_pin_id', sa.String(length=500), nullable=True))
    op.add_column('artworks', sa.Column('pinterest_url', sa.String(length=2000), nullable=True))
    op.add_column('artworks', sa.Column('pinterest_published_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('artworks', 'pinterest_published_at')
    op.drop_column('artworks', 'pinterest_url')
    op.drop_column('artworks', 'pinterest_pin_id')
    op.drop_column('artworks', 'pinterest_status')
