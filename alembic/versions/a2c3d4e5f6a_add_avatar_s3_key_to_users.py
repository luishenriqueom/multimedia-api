"""add avatar_s3_key to users

Revision ID: a2c3d4e5f6a
Revises: 8bbb713d724f
Create Date: 2025-12-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision = 'a2c3d4e5f6a'
down_revision = '8bbb713d724f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new nullable column for storing user's avatar S3 key
    op.add_column('users', sa.Column('avatar_s3_key', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove the avatar column on downgrade
    op.drop_column('users', 'avatar_s3_key')
