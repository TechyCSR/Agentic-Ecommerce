"""Phase 3: orders and payments

Revision ID: 9b21d4c6e5a7
Revises: 7f3c9a1b2d4e
Create Date: 2026-09-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9b21d4c6e5a7'
down_revision = '7f3c9a1b2d4e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'orders',
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('buyer_clerk_user_id', sa.String(length=255), nullable=False),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('amount_total', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column(
            'status',
            sa.Enum('CREATED', 'CONFIRMED', 'CANCELLED', name='order_status'),
            nullable=False,
        ),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_orders_session_id'), ['session_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_orders_buyer_clerk_user_id'), ['buyer_clerk_user_id'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_orders_status'), ['status'], unique=False)

    op.create_table(
        'payments',
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('buyer_clerk_user_id', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.Enum('RAZORPAY', name='payment_provider'), nullable=False),
        sa.Column('provider_order_id', sa.String(length=255), nullable=True),
        sa.Column('provider_payment_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'CREATED', 'PENDING', 'AUTHORIZED', 'PAID', 'FAILED', 'CANCELLED',
                name='payment_status',
            ),
            nullable=False,
        ),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_payments_order_id'), ['order_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_payments_buyer_clerk_user_id'), ['buyer_clerk_user_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_payments_provider_order_id'), ['provider_order_id'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_payments_status'), ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payments_status'))
        batch_op.drop_index(batch_op.f('ix_payments_provider_order_id'))
        batch_op.drop_index(batch_op.f('ix_payments_buyer_clerk_user_id'))
        batch_op.drop_index(batch_op.f('ix_payments_order_id'))
    op.drop_table('payments')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_status'))
        batch_op.drop_index(batch_op.f('ix_orders_buyer_clerk_user_id'))
        batch_op.drop_index(batch_op.f('ix_orders_session_id'))
    op.drop_table('orders')

    sa.Enum(name='payment_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='payment_provider').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='order_status').drop(op.get_bind(), checkfirst=True)
