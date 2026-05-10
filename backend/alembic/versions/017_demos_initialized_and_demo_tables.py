"""Track demo-attach state on User; flag demo tables in LocalDuckDBTable.

Adds:
  - users.demos_initialized — once true, the demo auto-attach won't re-create
    a demo connection the user has deleted.
  - local_duckdb_tables.is_demo — UI badge + schema flag.

Revision ID: 017
Revises: 016
Create Date: 2026-05-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "017"
down_revision: Union[str, Sequence[str], None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_cols = {c["name"] for c in inspector.get_columns("users")}
    if "demos_initialized" not in user_cols:
        with op.batch_alter_table("users") as batch:
            batch.add_column(
                sa.Column(
                    "demos_initialized",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )

    tbl_cols = {c["name"] for c in inspector.get_columns("local_duckdb_tables")}
    if "is_demo" not in tbl_cols:
        with op.batch_alter_table("local_duckdb_tables") as batch:
            batch.add_column(
                sa.Column(
                    "is_demo",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )

    # Backfill: any user who already has a demo warehouse from the previous
    # deploy is treated as initialized, so the new auto-attach won't insert a
    # duplicate on their next login.
    bind.execute(
        sa.text(
            "UPDATE users SET demos_initialized = TRUE "
            "WHERE id IN (SELECT DISTINCT user_id FROM warehouse_connections WHERE is_demo = TRUE)"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("local_duckdb_tables") as batch:
        batch.drop_column("is_demo")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("demos_initialized")
