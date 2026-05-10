"""add demo_messages table and user_agent to demo_usage

Revision ID: 006
Revises: 005
Create Date: 2026-03-17

Adds demo_messages table for per-message visibility into demo sessions,
and user_agent column to demo_usage for client identification.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add user_agent column to demo_usage
    demo_usage_columns = {c["name"] for c in inspector.get_columns("demo_usage")}
    if "user_agent" not in demo_usage_columns:
        op.add_column("demo_usage", sa.Column("user_agent", sa.String(), nullable=True))

    # Create demo_messages table
    if "demo_messages" not in inspector.get_table_names():
        op.create_table(
            "demo_messages",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("session_id", sa.String(), sa.ForeignKey("demo_usage.id"), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("input_tokens", sa.Integer(), nullable=True),
            sa.Column("output_tokens", sa.Integer(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("tool_call_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("demo_messages")
    op.drop_column("demo_usage", "user_agent")
