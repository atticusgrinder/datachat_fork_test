"""add saved_visualizations table and visualization columns to messages

Revision ID: 003
Revises: 002
Create Date: 2026-03-12

Adds the saved_visualizations table for storing user-saved chart
configurations, and visualization/chart_data columns to conversation_messages.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

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

    # Add visualization columns to conversation_messages
    msg_columns = {c["name"] for c in inspector.get_columns("conversation_messages")}
    if "visualization" not in msg_columns:
        op.add_column("conversation_messages", sa.Column("visualization", sa.Text(), nullable=True))
    if "chart_data" not in msg_columns:
        op.add_column("conversation_messages", sa.Column("chart_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversation_messages", "chart_data")
    op.drop_column("conversation_messages", "visualization")
    op.drop_table("saved_visualizations")
