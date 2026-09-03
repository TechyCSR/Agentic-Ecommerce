"""An order must survive deleting the chat it came from

Revision ID: b9d1f3a7c204
Revises: c2e7a94f6b18
Create Date: 2026-09-03 23:00:00.000000

"""
from alembic import op

revision = 'b9d1f3a7c204'
down_revision = 'c2e7a94f6b18'
branch_labels = None
depends_on = None

FK = "orders_session_id_fkey"


def upgrade():
    # Without ON DELETE SET NULL, deleting a chat session that has orders
    # raised a foreign-key error and the delete-session route returned 500.
    op.drop_constraint(FK, "orders", type_="foreignkey")
    op.create_foreign_key(
        FK, "orders", "chat_sessions", ["session_id"], ["id"], ondelete="SET NULL"
    )


def downgrade():
    op.drop_constraint(FK, "orders", type_="foreignkey")
    op.create_foreign_key(FK, "orders", "chat_sessions", ["session_id"], ["id"])
