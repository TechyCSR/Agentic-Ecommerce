"""Record how the buyer paid

Revision ID: f4c9b7e2a851
Revises: e8b4d2a6f713
Create Date: 2026-09-03 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f4c9b7e2a851'
down_revision = 'e8b4d2a6f713'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payments', schema=None) as b:
        b.add_column(sa.Column('method', sa.String(length=40), nullable=True))
        b.add_column(sa.Column('method_detail', sa.String(length=120), nullable=True))


def downgrade():
    with op.batch_alter_table('payments', schema=None) as b:
        b.drop_column('method_detail')
        b.drop_column('method')
