"""Add local_duckdb_id to reports so local-file-backed reports can be scheduled.

Revision ID: 014
Revises: 013
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014"
down_revision: Union[str, Sequence[str], None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {c["name"] for c in inspector.get_columns("reports")}

    if "local_duckdb_id" not in existing_columns:
        with op.batch_alter_table("reports") as batch:
            batch.add_column(
                sa.Column(
                    "local_duckdb_id",
                    sa.String(),
                    sa.ForeignKey(
                        "local_duckdbs.id",
                        name="fk_reports_local_duckdb_id",
                    ),
                    nullable=True,
                )
            )


def downgrade() -> None:
    op.drop_column("reports", "local_duckdb_id")
