"""Organization assignment, membership, and invitations."""

import html
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from app.core.email_domains import domain_from_email, is_generic_domain
from app.models.organization import Organization
from app.models.user import User
from app.services import email_service

logger = logging.getLogger(__name__)


def _personal_org_name(user: User) -> str:
    return user.name or (user.email.split("@", 1)[0] if user.email else "Personal")


def get_or_create_org_for_user(db: Session, user: User) -> Organization:
    """Return the org this user belongs to, creating + linking it if needed.

    - Generic free-mail domains → a per-user "personal" org (is_personal=True, no domain).
    - Anything else → a single shared org keyed on the domain (is_personal=False).

    Idempotent: safe to call repeatedly.
    """
    if user.organization_id:
        existing = db.query(Organization).filter(
            Organization.id == user.organization_id,
        ).first()
        if existing:
            return existing

    domain = domain_from_email(user.email or "")

    if not domain or is_generic_domain(domain):
        org = Organization(
            name=_personal_org_name(user),
            domain=None,
            is_personal=True,
        )
        db.add(org)
        db.flush()
    else:
        org = db.query(Organization).filter(
            Organization.domain == domain,
            Organization.is_personal.is_(False),
        ).first()
        if org is None:
            org = Organization(
                name=domain,
                domain=domain,
                is_personal=False,
            )
            db.add(org)
            db.flush()

    user.organization_id = org.id
    db.commit()
    db.refresh(user)
    return org


def list_members(db: Session, org_id: str) -> list[User]:
    return (
        db.query(User)
        .filter(User.organization_id == org_id)
        .order_by(User.created_at)
        .all()
    )


def can_invite(org: Organization) -> bool:
    """Only non-personal (work-domain) orgs can invite teammates."""
    return not org.is_personal and bool(org.domain)


async def send_invite(
    db: Session,
    *,
    inviter: User,
    org: Organization,
    invitee_email: str,
) -> None:
    """Send an invitation email to invitee_email.

    Raises ValueError on rule violations (personal org, domain mismatch,
    self-invite, already-member). Caller should map these to 400.
    """
    if not can_invite(org):
        raise ValueError(
            "This is a personal workspace — invites are only available on a verified work domain."
        )

    invitee_domain = domain_from_email(invitee_email)
    if invitee_domain != (org.domain or ""):
        raise ValueError(
            f"Invitations are limited to teammates on @{org.domain}."
        )

    if invitee_email.lower() == (inviter.email or "").lower():
        raise ValueError("You can't invite yourself.")

    existing = db.query(User).filter(User.email == invitee_email).first()
    if existing and existing.organization_id == org.id:
        raise ValueError(f"{invitee_email} is already a member of this org.")

    inviter_name = inviter.name or inviter.email or "A teammate"
    sign_up_url = f"{FRONTEND_URL.rstrip('/')}/sign-up"
    subject = f"{inviter_name} invited you to datachat"
    safe_inviter = html.escape(inviter_name)
    safe_domain = html.escape(org.domain or "")
    safe_email = html.escape(invitee_email)
    body_html = f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;background:#f7f7f8;padding:24px;color:#222;">
  <div style="max-width:560px;margin:0 auto;background:#fff;padding:32px;border-radius:8px;border:1px solid #e5e7eb;">
    <h1 style="margin:0 0 12px 0;font-size:20px;">You've been invited to datachat</h1>
    <p style="color:#444;margin:0 0 16px 0;">
      <strong>{safe_inviter}</strong> invited you ({safe_email}) to join the <strong>{safe_domain}</strong> workspace
      on datachat — chat with your data using AI.
    </p>
    <p style="margin:24px 0;">
      <a href="{sign_up_url}" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;padding:10px 18px;border-radius:6px;">
        Accept invitation &rarr;
      </a>
    </p>
    <p style="color:#666;font-size:13px;margin:0;">
      Sign up with your @{safe_domain} email and you'll be added to the workspace automatically.
    </p>
  </div>
</body></html>"""

    await email_service.send_html(to=invitee_email, subject=subject, html=body_html)


def find_existing_org_by_domain(db: Session, domain: str) -> Optional[Organization]:
    if not domain or is_generic_domain(domain):
        return None
    return db.query(Organization).filter(
        Organization.domain == domain,
        Organization.is_personal.is_(False),
    ).first()
