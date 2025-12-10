"""remove title from media

Revision ID: 5f6g7h8i9j0k
Revises: 4a5b6c7d8e9f
Create Date: 2025-12-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5f6g7h8i9j0k'
down_revision = '4a5b6c7d8e9f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove title column from media table
    op.drop_column('media', 'title')


def downgrade() -> None:
    # Re-add title column
    op.add_column('media', sa.Column('title', sa.String(), nullable=True))

