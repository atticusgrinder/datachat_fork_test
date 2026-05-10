"""Add local_duckdbs and local_duckdb_tables for per-user persistent DuckDB files.

Revision ID: 011
Revises: 010
Create Date: 2026-05-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "011"
down_revision: Union[str, Sequence[str], None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "local_duckdbs" not in existing_tables:
        op.create_table(
            "local_duckdbs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", name="uq_local_duckdbs_user_id"),
        )

    if "local_duckdb_tables" not in existing_tables:
        op.create_table(
            "local_duckdb_tables",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("local_duckdb_id", sa.String(), sa.ForeignKey("local_duckdbs.id"), nullable=False),
            sa.Column("table_name", sa.String(), nullable=False),
            sa.Column("original_filename", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(), nullable=False),
            sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("columns", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("local_duckdb_id", "table_name", name="uq_local_duckdb_table_name"),
        )


def downgrade() -> None:
    op.drop_table("local_duckdb_tables")
    op.drop_table("local_duckdbs")
