"""Timed stock reservations, so two buyers can't pay for the same last unit

Revision ID: d5f1a92c6e83
Revises: c4a71f8b3d29
Create Date: 2026-09-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd5f1a92c6e83'
down_revision = 'c4a71f8b3d29'
branch_labels = None
depends_on = None


def upgrade():
    reservation_status = postgresql.ENUM(
        "HELD", "CONSUMED", "RELEASED", name="reservation_status"
    )
    reservation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "stock_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # Not a foreign key: the order lives in the Agent service's database.
        sa.Column("agent_order_id", sa.String(length=255), nullable=False),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            postgresql.ENUM(
                "HELD", "CONSUMED", "RELEASED",
                name="reservation_status",
                create_type=False,
            ),
            nullable=False,
            server_default="HELD",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("api_client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_variant_id"], ["product_variants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["api_client_id"], ["api_clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        # One hold per variant per agent order: re-pricing the same checkout
        # updates the hold instead of stacking a second one.
        sa.UniqueConstraint(
            "agent_order_id", "product_variant_id", name="uq_reservation_order_variant"
        ),
    )
    op.create_index(
        "ix_stock_reservations_agent_order_id", "stock_reservations", ["agent_order_id"]
    )
    op.create_index(
        "ix_stock_reservations_product_variant_id",
        "stock_reservations",
        ["product_variant_id"],
    )
    op.create_index("ix_stock_reservations_status", "stock_reservations", ["status"])
    op.create_index(
        "ix_stock_reservations_expires_at", "stock_reservations", ["expires_at"]
    )
    # Every availability read is "held, unexpired, for these variants" — the
    # one query that runs on the catalog hot path.
    op.create_index(
        "ix_stock_reservations_live",
        "stock_reservations",
        ["product_variant_id", "status", "expires_at"],
    )


def downgrade():
    op.drop_index("ix_stock_reservations_live", table_name="stock_reservations")
    op.drop_index("ix_stock_reservations_expires_at", table_name="stock_reservations")
    op.drop_index("ix_stock_reservations_status", table_name="stock_reservations")
    op.drop_index(
        "ix_stock_reservations_product_variant_id", table_name="stock_reservations"
    )
    op.drop_index(
        "ix_stock_reservations_agent_order_id", table_name="stock_reservations"
    )
    op.drop_table("stock_reservations")
    postgresql.ENUM(name="reservation_status").drop(op.get_bind(), checkfirst=True)
