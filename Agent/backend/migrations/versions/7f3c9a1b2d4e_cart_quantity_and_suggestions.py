"""Cart: quantity + image snapshot + REMOVED status; suggested_replies on chat_messages

Revision ID: 7f3c9a1b2d4e
Revises: d6e0be574c3a
Create Date: 2026-09-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7f3c9a1b2d4e'
down_revision = 'd6e0be574c3a'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE selection_status ADD VALUE IF NOT EXISTS 'REMOVED'")

    with op.batch_alter_table('selected_products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_url_snapshot', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column('quantity', sa.Integer(), nullable=False, server_default='1')
        )

    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('suggested_replies', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.drop_column('suggested_replies')

    with op.batch_alter_table('selected_products', schema=None) as batch_op:
        batch_op.drop_column('quantity')
        batch_op.drop_column('image_url_snapshot')

    # Postgres has no ALTER TYPE ... DROP VALUE — leaving 'REMOVED' in the
    # enum on downgrade is intentionally a no-op (matches how this project
    # has otherwise avoided destructive downgrade behavior).
