"""Salesforce-related request/response schemas."""

from typing import Optional
from pydantic import BaseModel


class SalesforceOAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None


class SalesforceConnectionResponse(BaseModel):
    id: str
    instance_url: str
    org_name: Optional[str] = None
    username: Optional[str] = None
    connection_status: str
    created_at: str
