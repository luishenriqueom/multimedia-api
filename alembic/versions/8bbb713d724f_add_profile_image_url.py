"""add profile image url

Revision ID: 8bbb713d724f
Revises: 5f6g7h8i9j0k
Create Date: 2025-12-10 09:44:41.552362

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8bbb713d724f'
down_revision: Union[str, None] = '5f6g7h8i9j0k'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration was previously generated with destructive operations
    # (dropping many tables). That appears to be incorrect for the intended
    # purpose (adding a profile image column). To avoid accidental data
    # loss, this migration is intentionally a no-op. Any required schema
    # changes are implemented in dedicated, smaller migrations.
    return


def downgrade() -> None:
    # This downgrade previously attempted to recreate many tables that were
    # dropped by the (incorrect) upgrade. Since the upgrade is now a no-op,
    # the downgrade must also be a no-op to keep migrations consistent.
    return