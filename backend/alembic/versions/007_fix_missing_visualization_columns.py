"""fix missing visualization and chart_data columns on conversation_messages

Revision ID: 007
Revises: 006
Create Date: 2026-03-18

Migration 003 was skipped on production due to a revision ID conflict fix.
This re-applies the missing schema changes: visualization/chart_data columns
on conversation_messages and the saved_visualizations table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add missing visualization columns to conversation_messages
    msg_columns = {c["name"] for c in inspector.get_columns("conversation_messages")}
    if "visualization" not in msg_columns:
        op.add_column("conversation_messages", sa.Column("visualization", sa.Text(), nullable=True))
    if "chart_data" not in msg_columns:
        op.add_column("conversation_messages", sa.Column("chart_data", sa.Text(), nullable=True))

    # Create saved_visualizations table if missing
    if "saved_visualizations" not in inspector.get_table_names():
        op.create_table(
            "saved_visualizations",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("chart_type", sa.String(), nullable=False),
            sa.Column("chart_config", sa.Text(), nullable=False),
            sa.Column("sql_query", sa.Text(), nullable=False),
            sa.Column("warehouse_id", sa.String(), sa.ForeignKey("warehouse_connections.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # Also ensure salesforce_connections table and allowed_objects column exist (from 004/005)
    if "salesforce_connections" not in inspector.get_table_names():
        op.create_table(
            "salesforce_connections",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("org_id", sa.String(), nullable=True),
            sa.Column("instance_url", sa.String(), nullable=False),
            sa.Column("access_token_encrypted", sa.Text(), nullable=False),
            sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
            sa.Column("connection_status", sa.String(), server_default="connected"),
            sa.Column("org_name", sa.String(), nullable=True),
            sa.Column("username", sa.String(), nullable=True),
            sa.Column("allowed_objects", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
    else:
        sf_columns = {c["name"] for c in inspector.get_columns("salesforce_connections")}
        if "allowed_objects" not in sf_columns:
            op.add_column("salesforce_connections", sa.Column("allowed_objects", sa.JSON(), nullable=True))


def downgrade() -> None:
    # This is a fixup migration — downgrade is a no-op since
    # these objects should have existed from earlier migrations
    pass
