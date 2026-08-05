"""Track desktop client update status.

Revision ID: 0004_desktop_statuses
Revises: 0003_import_merged_status
Create Date: 2026-08-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_desktop_statuses"
down_revision = "0003_import_merged_status"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("desktop_client_statuses"):
        op.create_table(
            "desktop_client_statuses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("machine_id", sa.String(length=80), nullable=False),
            sa.Column("hostname", sa.String(length=160)),
            sa.Column("username", sa.String(length=80)),
            sa.Column("user_id", sa.Integer()),
            sa.Column("branch_id", sa.Integer()),
            sa.Column("app_version", sa.String(length=40), nullable=False),
            sa.Column("latest_version", sa.String(length=40)),
            sa.Column("min_desktop_version", sa.String(length=40)),
            sa.Column("certificate_trusted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("update_available", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updates_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("details", sa.JSON()),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("machine_id", name="uq_desktop_client_statuses_machine_id"),
        )
    inspector = sa.inspect(op.get_bind())
    indexes = {index.get("name") for index in inspector.get_indexes("desktop_client_statuses")}
    if "ix_desktop_client_statuses_machine_id" not in indexes:
        op.create_index("ix_desktop_client_statuses_machine_id", "desktop_client_statuses", ["machine_id"])
    if "ix_desktop_client_statuses_last_seen_at" not in indexes:
        op.create_index("ix_desktop_client_statuses_last_seen_at", "desktop_client_statuses", ["last_seen_at"])


def downgrade():
    if sa.inspect(op.get_bind()).has_table("desktop_client_statuses"):
        op.drop_index("ix_desktop_client_statuses_last_seen_at", table_name="desktop_client_statuses")
        op.drop_index("ix_desktop_client_statuses_machine_id", table_name="desktop_client_statuses")
        op.drop_table("desktop_client_statuses")