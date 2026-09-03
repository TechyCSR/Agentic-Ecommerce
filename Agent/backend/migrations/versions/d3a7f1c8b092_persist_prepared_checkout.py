"""Persist the prepared checkout on the assistant message

Revision ID: d3a7f1c8b092
Revises: b6f2c8e91d45
Create Date: 2026-09-03 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd3a7f1c8b092'
down_revision = 'b6f2c8e91d45'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chat_messages', schema=None) as b:
        b.add_column(sa.Column('prepared_checkout', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    with op.batch_alter_table('chat_messages', schema=None) as b:
        b.drop_column('prepared_checkout')
