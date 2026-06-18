"""add_category_to_artwork

Revision ID: bbbe6062787a
Revises: c2b3d4e5f6a7
Create Date: 2026-06-17 08:42:04.972798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbbe6062787a'
down_revision: Union[str, None] = 'c2b3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'artworks',
        sa.Column(
            'category',
            sa.String(length=100),
            server_default='gallery',
            nullable=False,
            comment='Category/section of the upload (e.g. gallery, photography)'
        )
    )


def downgrade() -> None:
    op.drop_column('artworks', 'category')
