"""Agent order sync: agent_order_id/buyer_ref/placed_at + fulfillment statuses

Revision ID: c4a71f8b3d29
Revises: 45b55557cf8f
Create Date: 2026-09-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c4a71f8b3d29'
down_revision = '45b55557cf8f'
branch_labels = None
depends_on = None

NEW_ORDER_STATUSES = ["CONFIRMED", "PACKED", "SHIPPED", "DELIVERED"]


def upgrade():
    # Postgres enum types can't be extended by editing the Python enum — each
    # new label needs its own ALTER TYPE.
    for value in NEW_ORDER_STATUSES:
        op.execute(f"ALTER TYPE order_status ADD VALUE IF NOT EXISTS '{value}'")

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_order_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('buyer_ref', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('placed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f('ix_orders_buyer_ref'), ['buyer_ref'], unique=False)
        # Unique: this is the idempotency key for order sync.
        batch_op.create_index(
            batch_op.f('ix_orders_agent_order_id'), ['agent_order_id'], unique=True
        )


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_agent_order_id'))
        batch_op.drop_index(batch_op.f('ix_orders_buyer_ref'))
        batch_op.drop_column('placed_at')
        batch_op.drop_column('buyer_ref')
        batch_op.drop_column('agent_order_id')

    # Postgres has no ALTER TYPE ... DROP VALUE; the added labels stay.
