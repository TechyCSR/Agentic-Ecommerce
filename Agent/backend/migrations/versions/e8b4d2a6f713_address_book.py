"""Address book and order shipping address

Revision ID: e8b4d2a6f713
Revises: d3a7f1c8b092
Create Date: 2026-09-03 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e8b4d2a6f713'
down_revision = 'd3a7f1c8b092'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'addresses',
        sa.Column('buyer_clerk_user_id', sa.String(length=255), nullable=False),
        sa.Column('label', sa.String(length=80), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=40), nullable=False),
        sa.Column('line1', sa.String(length=255), nullable=False),
        sa.Column('line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=120), nullable=False),
        sa.Column('state', sa.String(length=120), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('country', sa.String(length=80), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('addresses', schema=None) as b:
        b.create_index(b.f('ix_addresses_buyer_clerk_user_id'), ['buyer_clerk_user_id'], unique=False)

    with op.batch_alter_table('orders', schema=None) as b:
        b.add_column(sa.Column('shipping_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as b:
        b.drop_column('shipping_address')
    with op.batch_alter_table('addresses', schema=None) as b:
        b.drop_index(b.f('ix_addresses_buyer_clerk_user_id'))
    op.drop_table('addresses')
