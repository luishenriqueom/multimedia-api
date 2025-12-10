"""simplify metadata columns

Revision ID: 4a5b6c7d8e9f
Revises: 324debbb725f
Create Date: 2025-12-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4a5b6c7d8e9f'
down_revision = '324debbb725f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove user_props from media table
    op.drop_column('media', 'user_props')
    
    # Remove details from video_metadata and add new columns
    op.drop_column('video_metadata', 'details')
    op.add_column('video_metadata', sa.Column('url_1080', sa.String(), nullable=True))
    op.add_column('video_metadata', sa.Column('url_720', sa.String(), nullable=True))
    op.add_column('video_metadata', sa.Column('url_480', sa.String(), nullable=True))
    op.add_column('video_metadata', sa.Column('genero', sa.String(), nullable=True))
    
    # Remove details from audio_metadata and add genero
    op.drop_column('audio_metadata', 'details')
    op.add_column('audio_metadata', sa.Column('genero', sa.String(), nullable=True))


def downgrade() -> None:
    # Revert audio_metadata changes
    op.drop_column('audio_metadata', 'genero')
    op.add_column('audio_metadata', sa.Column('details', postgresql.JSONB(), nullable=True))
    
    # Revert video_metadata changes
    op.drop_column('video_metadata', 'genero')
    op.drop_column('video_metadata', 'url_480')
    op.drop_column('video_metadata', 'url_720')
    op.drop_column('video_metadata', 'url_1080')
    op.add_column('video_metadata', sa.Column('details', postgresql.JSONB(), nullable=True))
    
    # Revert media changes
    op.add_column('media', sa.Column('user_props', postgresql.JSONB(), nullable=True))

