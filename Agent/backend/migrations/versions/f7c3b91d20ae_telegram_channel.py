"""Telegram channel: buyer_profiles and telegram_links

Revision ID: f7c3b91d20ae
Revises: e5d8a2c7b410
Create Date: 2026-09-03 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f7c3b91d20ae'
down_revision = 'e5d8a2c7b410'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'buyer_profiles',
        sa.Column('clerk_user_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('buyer_profiles', schema=None) as b:
        b.create_index(b.f('ix_buyer_profiles_clerk_user_id'), ['clerk_user_id'], unique=True)
        b.create_index(b.f('ix_buyer_profiles_email'), ['email'], unique=True)

    op.create_table(
        'telegram_links',
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=255), nullable=True),
        sa.Column('buyer_clerk_user_id', sa.String(length=255), nullable=True),
        sa.Column('linked_email', sa.String(length=255), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('telegram_links', schema=None) as b:
        b.create_index(b.f('ix_telegram_links_telegram_user_id'), ['telegram_user_id'], unique=True)
        b.create_index(b.f('ix_telegram_links_buyer_clerk_user_id'), ['buyer_clerk_user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('telegram_links', schema=None) as b:
        b.drop_index(b.f('ix_telegram_links_buyer_clerk_user_id'))
        b.drop_index(b.f('ix_telegram_links_telegram_user_id'))
    op.drop_table('telegram_links')
    with op.batch_alter_table('buyer_profiles', schema=None) as b:
        b.drop_index(b.f('ix_buyer_profiles_email'))
        b.drop_index(b.f('ix_buyer_profiles_clerk_user_id'))
    op.drop_table('buyer_profiles')
