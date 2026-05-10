"""Unified context file CRUD endpoints."""

import re

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.user import User
from app.schemas.context import (
    ContextFileResponse,
    ContextFileUpdate,
    ContextFileList,
)
from app.services import context_service

router = APIRouter(tags=["context"])

FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+\.(md|yml)$")


def _to_response(cf) -> ContextFileResponse:
    return ContextFileResponse(
        id=cf.id,
        filename=cf.filename,
        content=cf.content,
        source=cf.source,
        integration_id=cf.integration_id,
        created_at=cf.created_at.isoformat() + "Z",
        updated_at=cf.updated_at.isoformat() + "Z",
    )


def _validate_filename(filename: str) -> None:
    if not FILENAME_PATTERN.match(filename):
        raise HTTPException(
            status_code=400,
            detail="Filename must match [a-zA-Z0-9_-]+.(md|yml)",
        )


@router.get("/api/context", response_model=ContextFileList)
async def list_context_files(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List user's context files. Creates defaults if user has none."""
    context_service.ensure_default_context(db, user.id)
    files = context_service.list_files(db, user.id)
    return ContextFileList(files=[_to_response(f) for f in files])


@router.get("/api/context/{filename}", response_model=ContextFileResponse)
async def get_context_file(
    filename: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Read a single context file."""
    _validate_filename(filename)
    cf = context_service.read_file(db, user.id, filename)
    if not cf:
        raise HTTPException(status_code=404, detail="Context file not found")
    return _to_response(cf)


@router.put("/api/context/{filename}", response_model=ContextFileResponse)
async def update_context_file(
    filename: str,
    request: ContextFileUpdate,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create or update a user context file."""
    _validate_filename(filename)
    try:
        cf = context_service.write_file(db, user.id, filename, request.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(cf)


@router.delete("/api/context/{filename}")
async def delete_context_file(
    filename: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a user context file."""
    _validate_filename(filename)
    try:
        deleted = context_service.delete_file(db, user.id, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Context file not found")
    return {"success": True}
