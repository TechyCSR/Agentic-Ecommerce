"""Record when the merchant's stock hold on a priced order lapses

Revision ID: c8a4e60b17d9
Revises: a5e2c81b6f30
Create Date: 2026-09-04 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c8a4e60b17d9'
down_revision = 'a5e2c81b6f30'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "orders",
        sa.Column("stock_reserved_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("orders", "stock_reserved_until")
