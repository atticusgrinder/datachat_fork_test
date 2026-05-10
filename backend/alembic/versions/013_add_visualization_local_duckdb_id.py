"""Add local_duckdb_id to saved_visualizations for local-file-backed charts.

Revision ID: 013
Revises: 012
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013"
down_revision: Union[str, Sequence[str], None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {c["name"] for c in inspector.get_columns("saved_visualizations")}

    if "local_duckdb_id" not in existing_columns:
        # FK needs an explicit name for SQLite batch mode (alembic copy-and-move).
        with op.batch_alter_table("saved_visualizations") as batch:
            batch.add_column(
                sa.Column(
                    "local_duckdb_id",
                    sa.String(),
                    sa.ForeignKey(
                        "local_duckdbs.id",
                        name="fk_saved_visualizations_local_duckdb_id",
                    ),
                    nullable=True,
                )
            )


def downgrade() -> None:
    op.drop_column("saved_visualizations", "local_duckdb_id")
