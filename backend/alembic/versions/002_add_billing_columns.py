"""add billing columns to users and weighted tokens to token_usage

Revision ID: 002
Revises: 001
Create Date: 2026-02-28

Adds billing-related columns to the users table (monthly_token_limit,
billing_cycle_start, stripe_customer_id, stripe_subscription_id) and
weighted_tokens to the token_usage table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {c["name"] for c in inspector.get_columns("users")}
    token_columns = {c["name"] for c in inspector.get_columns("token_usage")}

    # Users: billing columns
    if "monthly_token_limit" not in user_columns:
        op.add_column("users", sa.Column("monthly_token_limit", sa.Integer(), nullable=True))
    if "billing_cycle_start" not in user_columns:
        op.add_column("users", sa.Column("billing_cycle_start", sa.DateTime(), nullable=True))
    if "stripe_customer_id" not in user_columns:
        op.add_column("users", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    if "stripe_subscription_id" not in user_columns:
        op.add_column("users", sa.Column("stripe_subscription_id", sa.String(), nullable=True))

    # Add unique constraint if stripe_customer_id was just added or constraint doesn't exist.
    # Use batch_alter_table so this works on SQLite (which doesn't support ALTER TABLE
    # ... ADD CONSTRAINT — alembic falls back to a copy-and-move). Postgres skips the
    # batch indirection.
    user_unique = {
        frozenset(c["column_names"])
        for c in inspector.get_unique_constraints("users")
    }
    if frozenset(["stripe_customer_id"]) not in user_unique:
        with op.batch_alter_table("users") as batch_op:
            batch_op.create_unique_constraint("uq_users_stripe_customer_id", ["stripe_customer_id"])

    # Token usage: weighted tokens
    if "weighted_tokens" not in token_columns:
        op.add_column("token_usage", sa.Column("weighted_tokens", sa.Integer(), server_default=sa.text("0")))


def downgrade() -> None:
    op.drop_column("token_usage", "weighted_tokens")
    op.drop_constraint("uq_users_stripe_customer_id", "users", type_="unique")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "billing_cycle_start")
    op.drop_column("users", "monthly_token_limit")
