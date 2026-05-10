"""Consolidate memory_files + model_metadata into context_files.

Revision ID: 010
Revises: 009
Create Date: 2026-04-07

Merges the separate memory and integration metadata concepts into a
unified context_files table. Migrates existing data from both tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010"
down_revision: Union[str, Sequence[str], None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Create context_files table
    if "context_files" not in existing_tables:
        op.create_table(
            "context_files",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("source", sa.String(), nullable=False, server_default="user"),
            sa.Column("integration_id", sa.String(), sa.ForeignKey("integrations.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "filename", name="uq_context_files_user_filename"),
        )

    # 2. Migrate memory_files → context_files (merge per user into single context.md)
    if "memory_files" in existing_tables:
        conn = op.get_bind()
        users_with_files = conn.execute(
            sa.text("SELECT DISTINCT user_id FROM memory_files")
        ).fetchall()

        for (user_id,) in users_with_files:
            rows = conn.execute(
                sa.text(
                    "SELECT filename, content FROM memory_files "
                    "WHERE user_id = :uid ORDER BY filename"
                ),
                {"uid": user_id},
            ).fetchall()

            if len(rows) == 1 and rows[0][0] == "context.md":
                merged = rows[0][1]
            else:
                sections = []
                for filename, content in rows:
                    if content and content.strip():
                        sections.append(content.strip())
                merged = "\n\n---\n\n".join(sections) if sections else ""

            import uuid
            conn.execute(
                sa.text(
                    "INSERT INTO context_files (id, user_id, filename, content, source) "
                    "VALUES (:id, :uid, 'context.md', :content, 'user')"
                ),
                {"id": str(uuid.uuid4()), "uid": user_id, "content": merged},
            )

        op.drop_table("memory_files")

    # 3. Drop model_metadata (integration sync now writes context files directly)
    if "model_metadata" in existing_tables:
        op.drop_table("model_metadata")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Recreate memory_files
    if "memory_files" not in existing_tables:
        op.create_table(
            "memory_files",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "filename", name="uq_memory_files_user_filename"),
        )

    # Recreate model_metadata
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

    if "context_files" in existing_tables:
        op.drop_table("context_files")
