"""initial tables

Revision ID: 1b2c3d4e5f6g
Revises: 
Create Date: 2025-12-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1b2c3d4e5f6g'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_unique_constraint('uq_users_email', 'users', ['email'])

    op.create_table(
        'media',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('s3_key', sa.String(), nullable=False),
        sa.Column('mimetype', sa.String(), nullable=True),
        sa.Column('size', sa.BigInteger(), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_media_id'), 'media', ['id'], unique=False)
    op.create_index(op.f('ix_media_title'), 'media', ['title'], unique=False)
    op.create_unique_constraint('uq_media_s3_key', 'media', ['s3_key'])


def downgrade() -> None:
    op.drop_constraint('uq_media_s3_key', 'media', type_='unique')
    op.drop_index(op.f('ix_media_title'), table_name='media')
    op.drop_index(op.f('ix_media_id'), table_name='media')
    op.drop_table('media')

    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
