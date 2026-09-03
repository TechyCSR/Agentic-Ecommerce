"""Telegram link should not block deleting a chat session

Revision ID: b6f2c8e91d45
Revises: a1b8e4d6c37f
Create Date: 2026-09-03 18:00:00.000000

"""
from alembic import op

revision = 'b6f2c8e91d45'
down_revision = 'a1b8e4d6c37f'
branch_labels = None
depends_on = None

FK = "telegram_links_session_id_fkey"


def upgrade():
    # Without ON DELETE SET NULL, deleting a chat session that a Telegram
    # link points at raises a foreign-key error (a 500 on the delete-session
    # route, and a failure for any cascade that touches sessions). Clearing
    # the reference just starts that Telegram user a fresh conversation.
    op.drop_constraint(FK, "telegram_links", type_="foreignkey")
    op.create_foreign_key(
        FK, "telegram_links", "chat_sessions", ["session_id"], ["id"], ondelete="SET NULL"
    )


def downgrade():
    op.drop_constraint(FK, "telegram_links", type_="foreignkey")
    op.create_foreign_key(FK, "telegram_links", "chat_sessions", ["session_id"], ["id"])
