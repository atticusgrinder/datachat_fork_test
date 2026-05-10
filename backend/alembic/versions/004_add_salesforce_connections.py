"""add salesforce_connections table

Revision ID: 004
Revises: 003
Create Date: 2026-03-13

Adds the salesforce_connections table for storing Salesforce OAuth
credentials and org metadata.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "salesforce_connections" not in existing_tables:
        op.create_table(
            "salesforce_connections",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("instance_url", sa.String(), nullable=False),
            sa.Column("access_token_encrypted", sa.Text(), nullable=False),
            sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
            sa.Column("org_id", sa.String(), nullable=True),
            sa.Column("org_name", sa.String(), nullable=True),
            sa.Column("username", sa.String(), nullable=True),
            sa.Column("connection_status", sa.String(), server_default="connected"),
            sa.Column("token_expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("salesforce_connections")
