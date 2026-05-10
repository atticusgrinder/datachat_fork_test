"""Organization API: read your org, list members, invite a teammate."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import (
    InviteRequest,
    InviteResponse,
    OrganizationMemberOut,
    OrganizationMembersOut,
    OrganizationOut,
)
from app.services import email_service, org_service

router = APIRouter()


def _ensure_org(db: Session, user: User) -> Organization:
    if user.organization_id:
        org = db.query(Organization).filter(
            Organization.id == user.organization_id,
        ).first()
        if org:
            return org
    return org_service.get_or_create_org_for_user(db, user)


@router.get("/api/organization", response_model=OrganizationOut)
async def get_org(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _ensure_org(db, user)
    members = org_service.list_members(db, org.id)
    return OrganizationOut(
        id=org.id,
        name=org.name,
        domain=org.domain,
        is_personal=org.is_personal,
        member_count=len(members),
        can_invite=org_service.can_invite(org),
        created_at=org.created_at,
    )


@router.get("/api/organization/members", response_model=OrganizationMembersOut)
async def list_members(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _ensure_org(db, user)
    members = org_service.list_members(db, org.id)
    return OrganizationMembersOut(
        members=[
            OrganizationMemberOut(
                id=m.id,
                email=m.email,
                name=m.name,
                is_admin=bool(m.is_admin),
                joined_at=m.created_at,
            )
            for m in members
        ],
    )


@router.post("/api/organization/invite", response_model=InviteResponse)
async def invite_teammate(
    body: InviteRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _ensure_org(db, user)
    try:
        await org_service.send_invite(
            db, inviter=user, org=org, invitee_email=body.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except email_service.EmailNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except email_service.EmailSendError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Email provider rejected the invite: {e.message}",
        )
    return InviteResponse(success=True, message=f"Invitation sent to {body.email}.")
