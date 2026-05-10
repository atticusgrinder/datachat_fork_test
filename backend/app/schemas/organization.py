"""Pydantic schemas for the organization API."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


class OrganizationOut(BaseModel):
    id: str
    name: str
    domain: Optional[str]
    is_personal: bool
    member_count: int
    can_invite: bool
    created_at: datetime


class OrganizationMemberOut(BaseModel):
    id: str
    email: str
    name: Optional[str]
    is_admin: bool
    joined_at: datetime


class OrganizationMembersOut(BaseModel):
    members: List[OrganizationMemberOut]


class InviteRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _looks_like_email(cls, v: str) -> str:
        v = (v or "").strip()
        if "@" not in v or "." not in v.split("@", 1)[1]:
            raise ValueError("Invalid email address.")
        return v


class InviteResponse(BaseModel):
    success: bool
    message: str
