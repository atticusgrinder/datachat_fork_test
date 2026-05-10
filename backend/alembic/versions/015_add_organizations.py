"""Add organizations table and organization_id on users; backfill from email.

Each user lands in either a shared work-domain org (one per verified work
domain) or a personal solo org (for generic free-mail domains). Resources
remain user-scoped — orgs only own identity + invite rules.

Revision ID: 015
Revises: 014
Create Date: 2026-05-08
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "015"
down_revision: Union[str, Sequence[str], None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Keep this list in sync with backend/app/core/email_domains.py.
GENERIC_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "msn.com", "yahoo.com", "yahoo.co.uk", "ymail.com", "icloud.com", "me.com",
    "mac.com", "aol.com", "proton.me", "protonmail.com", "pm.me",
    "tutanota.com", "tutanota.de", "tuta.io", "fastmail.com", "fastmail.fm",
    "gmx.com", "gmx.de", "gmx.net", "mail.com", "zoho.com", "zohomail.com",
    "yandex.com", "yandex.ru", "qq.com", "163.com", "126.com", "duck.com",
    "hey.com",
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "organizations" not in inspector.get_table_names():
        op.create_table(
            "organizations",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("domain", sa.String(), nullable=True),
            sa.Column("is_personal", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("domain", name="uq_organizations_domain"),
        )

    user_columns = {c["name"] for c in inspector.get_columns("users")}
    if "organization_id" not in user_columns:
        with op.batch_alter_table("users") as batch:
            batch.add_column(
                sa.Column(
                    "organization_id",
                    sa.String(),
                    sa.ForeignKey(
                        "organizations.id",
                        name="fk_users_organization_id",
                    ),
                    nullable=True,
                )
            )

    # Backfill: assign every user to an org. Build domain → org map first to
    # avoid creating duplicate work orgs for the same domain.
    users = bind.execute(
        sa.text("SELECT id, email, name FROM users WHERE organization_id IS NULL")
    ).fetchall()

    domain_to_org_id: dict[str, str] = {}
    for row in users:
        user_id, email, name = row[0], row[1], row[2]
        domain = (email.rsplit("@", 1)[1].lower() if email and "@" in email else "")
        is_generic = (not domain) or (domain in GENERIC_DOMAINS)

        if is_generic:
            org_id = str(uuid.uuid4())
            org_name = name or (email.split("@", 1)[0] if email and "@" in email else "Personal")
            bind.execute(
                sa.text(
                    "INSERT INTO organizations (id, name, domain, is_personal, created_at, updated_at) "
                    "VALUES (:id, :name, NULL, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": org_id, "name": org_name},
            )
        else:
            org_id = domain_to_org_id.get(domain)
            if org_id is None:
                # Re-use an org with the same domain if a previous run already created one.
                existing = bind.execute(
                    sa.text(
                        "SELECT id FROM organizations WHERE domain = :d AND is_personal = FALSE"
                    ),
                    {"d": domain},
                ).fetchone()
                if existing:
                    org_id = existing[0]
                else:
                    org_id = str(uuid.uuid4())
                    bind.execute(
                        sa.text(
                            "INSERT INTO organizations (id, name, domain, is_personal, created_at, updated_at) "
                            "VALUES (:id, :name, :domain, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                        ),
                        {"id": org_id, "name": domain, "domain": domain},
                    )
                domain_to_org_id[domain] = org_id

        bind.execute(
            sa.text("UPDATE users SET organization_id = :oid WHERE id = :uid"),
            {"oid": org_id, "uid": user_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_organization_id", type_="foreignkey")
        batch.drop_column("organization_id")
    op.drop_table("organizations")
