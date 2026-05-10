"""add allowed_objects to salesforce_connections

Revision ID: 005
Revises: 004
Create Date: 2026-03-13

Adds the allowed_objects JSON column to salesforce_connections for
object-level access control.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [c["name"] for c in inspector.get_columns("salesforce_connections")]

    if "allowed_objects" not in existing_columns:
        op.add_column(
            "salesforce_connections",
            sa.Column("allowed_objects", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("salesforce_connections", "allowed_objects")
