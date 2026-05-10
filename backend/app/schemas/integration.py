"""Integration request/response schemas."""

from typing import Optional
from pydantic import BaseModel


class IntegrationCreate(BaseModel):
    integration_type: str  # 'dbt'
    name: str
    config: dict  # {repo_url, branch, auth_token}


class IntegrationResponse(BaseModel):
    id: str
    integration_type: str
    name: str
    connection_status: str
    last_synced_at: Optional[str] = None
    created_at: str


class IntegrationListResponse(BaseModel):
    integrations: list[IntegrationResponse]


class IntegrationSyncResponse(BaseModel):
    id: str
    integration_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata_count: int


