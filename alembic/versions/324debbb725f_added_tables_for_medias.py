"""added tables for medias

Revision ID: 324debbb725f
Revises: 1b2c3d4e5f6g
Create Date: 2025-12-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '324debbb725f'
down_revision = '1b2c3d4e5f6g'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for media_type
    media_type_enum = sa.Enum('image', 'video', 'audio', 'other', name='media_type_enum')
    media_type_enum.create(op.get_bind(), checkfirst=True)

    # Add columns to existing media table
    op.add_column('media', sa.Column('media_type', media_type_enum, nullable=False, server_default=sa.text("'other'::media_type_enum")))
    op.add_column('media', sa.Column('user_props', postgresql.JSONB(), nullable=True))
    op.add_column('media', sa.Column('upload_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))

    # Create thumbnails table
    op.create_table(
        'thumbnails',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='CASCADE'), nullable=False),
        sa.Column('s3_key', sa.Text(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('size', sa.BigInteger(), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_thumbnails_media_id', 'thumbnails', ['media_id'])

    # Create image_metadata
    op.create_table(
        'image_metadata',
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('color_depth', sa.Integer(), nullable=True),
        sa.Column('dpi_x', sa.Integer(), nullable=True),
        sa.Column('dpi_y', sa.Integer(), nullable=True),
        sa.Column('exif', postgresql.JSONB(), nullable=True),
        sa.Column('main_thumbnail_id', sa.Integer(), sa.ForeignKey('thumbnails.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('idx_image_metadata_dimensions', 'image_metadata', ['width', 'height'])

    # Create video_metadata
    op.create_table(
        'video_metadata',
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('duration_seconds', sa.Numeric(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('frame_rate', sa.Numeric(), nullable=True),
        sa.Column('video_codec', sa.Text(), nullable=True),
        sa.Column('audio_codec', sa.Text(), nullable=True),
        sa.Column('bitrate', sa.BigInteger(), nullable=True),
        sa.Column('main_thumbnail_id', sa.Integer(), sa.ForeignKey('thumbnails.id', ondelete='SET NULL'), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_video_metadata_resolution', 'video_metadata', ['width', 'height'])

    # Create audio_metadata
    op.create_table(
        'audio_metadata',
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('duration_seconds', sa.Numeric(), nullable=True),
        sa.Column('bitrate', sa.BigInteger(), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('channels', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
    )

    # Create video_renditions
    op.create_table(
        'video_renditions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('bitrate', sa.BigInteger(), nullable=True),
        sa.Column('s3_key', sa.Text(), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_video_renditions_media_id', 'video_renditions', ['media_id'])

    # Create tags and association table
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False, unique=True),
    )

    op.create_table(
        'media_tags',
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    )
    op.create_index('idx_media_tags_media_id', 'media_tags', ['media_id'])

    # Additional helpful indexes on media
    op.create_index('idx_media_owner_id', 'media', ['owner_id'])
    op.create_index('idx_media_media_type', 'media', ['media_type'])


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index('idx_media_media_type', table_name='media')
    op.drop_index('idx_media_owner_id', table_name='media')

    op.drop_index('idx_media_tags_media_id', table_name='media_tags')
    op.drop_table('media_tags')
    op.drop_table('tags')

    op.drop_index('idx_video_renditions_media_id', table_name='video_renditions')
    op.drop_table('video_renditions')

    op.drop_table('audio_metadata')

    op.drop_index('idx_video_metadata_resolution', table_name='video_metadata')
    op.drop_table('video_metadata')

    op.drop_index('idx_image_metadata_dimensions', table_name='image_metadata')
    op.drop_table('image_metadata')

    op.drop_index('idx_thumbnails_media_id', table_name='thumbnails')
    op.drop_table('thumbnails')

    # Remove columns from media
    op.drop_column('media', 'upload_at')
    op.drop_column('media', 'user_props')
    op.drop_column('media', 'media_type')

    # Drop enum type
    media_type_enum = sa.Enum('image', 'video', 'audio', 'other', name='media_type_enum')
    media_type_enum.drop(op.get_bind(), checkfirst=True)
