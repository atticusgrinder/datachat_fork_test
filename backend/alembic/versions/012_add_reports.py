"""Add reports, report_items, report_schedules.

Revision ID: 012
Revises: 011
Create Date: 2026-05-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012"
down_revision: Union[str, Sequence[str], None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "reports" not in existing_tables:
        op.create_table(
            "reports",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("warehouse_id", sa.String(), sa.ForeignKey("warehouse_connections.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "report_items" not in existing_tables:
        op.create_table(
            "report_items",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("report_id", sa.String(), sa.ForeignKey("reports.id"), nullable=False),
            sa.Column("saved_visualization_id", sa.String(), sa.ForeignKey("saved_visualizations.id"), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "report_schedules" not in existing_tables:
        op.create_table(
            "report_schedules",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("report_id", sa.String(), sa.ForeignKey("reports.id"), nullable=False),
            sa.Column("cadence", sa.String(), nullable=False),
            sa.Column("day_of_week", sa.Integer(), nullable=True),
            sa.Column("day_of_month", sa.Integer(), nullable=True),
            sa.Column("time_of_day", sa.String(), nullable=False, server_default="08:00"),
            sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_sent_at", sa.DateTime(), nullable=True),
            sa.Column("next_send_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("report_id", name="uq_report_schedules_report_id"),
        )


def downgrade() -> None:
    op.drop_table("report_schedules")
    op.drop_table("report_items")
    op.drop_table("reports")
