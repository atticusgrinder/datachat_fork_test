"""Add integrations, integration_syncs, and model_metadata tables.

Revision ID: 008
Revises: 007
Create Date: 2026-04-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "integrations" not in existing_tables:
        op.create_table(
            "integrations",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("integration_type", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("config_encrypted", sa.Text(), nullable=False),
            sa.Column("connection_status", sa.String(), server_default="pending"),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "integration_syncs" not in existing_tables:
        op.create_table(
            "integration_syncs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("integration_id", sa.String(), sa.ForeignKey("integrations.id"), nullable=False),
            sa.Column("status", sa.String(), server_default="pending"),
            sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("metadata_count", sa.Integer(), server_default="0"),
        )

    if "model_metadata" not in existing_tables:
        op.create_table(
            "model_metadata",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("integration_id", sa.String(), sa.ForeignKey("integrations.id"), nullable=False),
            sa.Column("metadata_type", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("schema_name", sa.String(), nullable=True),
            sa.Column("database", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("columns", sa.JSON(), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("relationships", sa.JSON(), nullable=True),
            sa.Column("raw_definition", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("model_metadata")
    op.drop_table("integration_syncs")
    op.drop_table("integrations")
