"""Allow a payment to be REFUNDED

Revision ID: c2e7a94f6b18
Revises: f4c9b7e2a851
Create Date: 2026-09-03 22:00:00.000000

"""
from alembic import op

revision = 'c2e7a94f6b18'
down_revision = 'f4c9b7e2a851'
branch_labels = None
depends_on = None


def upgrade():
    # Postgres enums can't be extended by editing the Python enum alone.
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'REFUNDED'")


def downgrade():
    # Postgres has no ALTER TYPE ... DROP VALUE; the label stays.
    pass
