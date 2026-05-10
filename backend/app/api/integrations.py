"""Integration endpoints for third-party repo connections."""

from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.user import User
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationResponse,
    IntegrationSyncResponse,
)
from app.services import integration_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def _integration_response(integration) -> IntegrationResponse:
    return IntegrationResponse(
        id=integration.id,
        integration_type=integration.integration_type,
        name=integration.name,
        connection_status=integration.connection_status,
        last_synced_at=integration.last_synced_at.isoformat() + "Z" if integration.last_synced_at else None,
        created_at=integration.created_at.isoformat() + "Z",
    )


def _sync_response(sync) -> IntegrationSyncResponse:
    return IntegrationSyncResponse(
        id=sync.id,
        integration_id=sync.integration_id,
        status=sync.status,
        started_at=sync.started_at.isoformat() + "Z",
        completed_at=sync.completed_at.isoformat() + "Z" if sync.completed_at else None,
        error_message=sync.error_message,
        metadata_count=sync.metadata_count,
    )


@router.post("", response_model=IntegrationResponse)
async def create_integration(
    request: IntegrationCreate,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new integration."""
    try:
        integration = integration_service.create_integration(
            db=db,
            user_id=user.id,
            integration_type=request.integration_type,
            name=request.name,
            config=request.config,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _integration_response(integration)


@router.get("", response_model=List[IntegrationResponse])
async def list_integrations(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List all integrations for the authenticated user."""
    integrations = integration_service.list_integrations(db, user.id)
    return [_integration_response(i) for i in integrations]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get a specific integration."""
    integration = integration_service.get_integration(db, user.id, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return _integration_response(integration)


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete an integration and all associated metadata."""
    deleted = integration_service.delete_integration(db, user.id, integration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True}


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResponse)
async def sync_integration(
    integration_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Trigger a sync for an integration."""
    try:
        sync = integration_service.sync_integration(db, user.id, integration_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _sync_response(sync)


@router.get("/{integration_id}/sync/status", response_model=IntegrationSyncResponse)
async def get_sync_status(
    integration_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the latest sync status for an integration."""
    integration = integration_service.get_integration(db, user.id, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    sync = integration_service.get_latest_sync(db, integration_id)
    if not sync:
        raise HTTPException(status_code=404, detail="No syncs found")
    return _sync_response(sync)


