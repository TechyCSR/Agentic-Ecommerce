"""Track the Merchant-side orders an agent order synced into

Revision ID: e5d8a2c7b410
Revises: 9b21d4c6e5a7
Create Date: 2026-09-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e5d8a2c7b410'
down_revision = '9b21d4c6e5a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('merchant_order_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
        )
        batch_op.add_column(
            sa.Column('merchant_synced_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('merchant_synced_at')
        batch_op.drop_column('merchant_order_ids')
