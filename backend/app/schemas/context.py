"""Context file request/response schemas."""

from typing import Optional
from pydantic import BaseModel


class ContextFileResponse(BaseModel):
    id: str
    filename: str
    content: str
    source: str
    integration_id: Optional[str] = None
    created_at: str
    updated_at: str


class ContextFileUpdate(BaseModel):
    content: str


class ContextFileList(BaseModel):
    files: list[ContextFileResponse]
