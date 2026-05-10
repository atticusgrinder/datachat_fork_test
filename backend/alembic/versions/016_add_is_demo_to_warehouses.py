"""Add is_demo flag to warehouse_connections.

Used to mark the auto-attached "Demo: RetailFlow" warehouse so it can't be
deleted by the user and is rendered with a Demo badge in the picker.

Revision ID: 016
Revises: 015
Create Date: 2026-05-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016"
down_revision: Union[str, Sequence[str], None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("warehouse_connections")}
    if "is_demo" not in columns:
        with op.batch_alter_table("warehouse_connections") as batch:
            batch.add_column(
                sa.Column(
                    "is_demo",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )


def downgrade() -> None:
    with op.batch_alter_table("warehouse_connections") as batch:
        batch.drop_column("is_demo")
