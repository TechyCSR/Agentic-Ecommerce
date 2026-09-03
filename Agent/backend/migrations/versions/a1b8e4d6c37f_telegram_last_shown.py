"""Telegram: remember last shown products/suggestions for short callbacks

Revision ID: a1b8e4d6c37f
Revises: f7c3b91d20ae
Create Date: 2026-09-03 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b8e4d6c37f'
down_revision = 'f7c3b91d20ae'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('telegram_links', schema=None) as b:
        b.add_column(sa.Column('last_cards', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        b.add_column(sa.Column('last_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    with op.batch_alter_table('telegram_links', schema=None) as b:
        b.drop_column('last_suggestions')
        b.drop_column('last_cards')
