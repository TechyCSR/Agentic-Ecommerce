"""Persist the agent's tool trace on each message

Revision ID: a5e2c81b6f30
Revises: b9d1f3a7c204
Create Date: 2026-09-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a5e2c81b6f30'
down_revision = 'b9d1f3a7c204'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chat_messages', schema=None) as b:
        b.add_column(sa.Column('tool_activity', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    with op.batch_alter_table('chat_messages', schema=None) as b:
        b.drop_column('tool_activity')
