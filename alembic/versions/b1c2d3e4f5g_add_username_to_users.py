"""add username to users

Revision ID: b1c2d3e4f5g
Revises: a2c3d4e5f6a
Create Date: 2025-12-10 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g'
down_revision = 'a2c3d4e5f6a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable username column to users table
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove username column on downgrade
    op.drop_column('users', 'username')
