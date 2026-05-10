"""Salesforce OAuth and connection management endpoints."""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import FRONTEND_URL, SALESFORCE_CLIENT_ID
from app.core.security import encrypt_credentials, decrypt_credentials
from app.core.dependencies import require_auth
from app.models.user import User
from app.models.salesforce import SalesforceConnection
from app.schemas.salesforce import SalesforceConnectionResponse
from app.services.salesforce_service import (
    get_oauth_authorize_url,
    exchange_code_for_tokens,
    get_user_info,
    get_valid_access_token,
    revoke_token,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/salesforce", tags=["salesforce"])

# In-memory state store for OAuth CSRF protection.
# In production, use a signed JWT or server-side session instead.
_oauth_states: dict[str, str] = {}


@router.get("/connect")
async def salesforce_connect(
    user: User = Depends(require_auth),
):
    """Start the Salesforce OAuth flow. Returns the authorization URL."""
    if not SALESFORCE_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="Salesforce integration is not configured. Set SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET.",
        )

    state = f"{user.id}:{uuid.uuid4().hex}"
    _oauth_states[state] = user.id
    authorize_url = get_oauth_authorize_url(state)
    return {"authorize_url": authorize_url}


@router.get("/callback")
async def salesforce_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """Handle the Salesforce OAuth callback. Exchanges code for tokens and stores the connection."""
    user_id = _oauth_states.pop(state, None)
    if not user_id:
        return RedirectResponse(
            f"{FRONTEND_URL}/settings?salesforce=error&reason=invalid_state"
        )

    try:
        token_data = await exchange_code_for_tokens(code)
    except Exception as e:
        logger.error(f"Salesforce token exchange failed: {e}")
        return RedirectResponse(
            f"{FRONTEND_URL}/settings?salesforce=error&reason=token_exchange_failed"
        )

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    instance_url = token_data["instance_url"]

    # Fetch org info
    org_name = None
    username = None
    org_id = None
    try:
        user_info = await get_user_info(instance_url, access_token)
        username = user_info.get("preferred_username") or user_info.get("email")
        org_id = user_info.get("organization_id")
        org_name = user_info.get("organization_id")  # Will be enriched below
    except Exception:
        logger.warning("Failed to fetch Salesforce user info", exc_info=True)

    # Try to get org name from the org endpoint
    if org_id:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{instance_url}/services/data/v60.0/sobjects/Organization/{org_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    org_data = resp.json()
                    org_name = org_data.get("Name", org_id)
        except Exception:
            pass

    # Upsert: replace existing connection for this user, or create new
    existing = db.query(SalesforceConnection).filter(
        SalesforceConnection.user_id == user_id,
    ).first()

    if existing:
        existing.instance_url = instance_url
        existing.access_token_encrypted = encrypt_credentials({"access_token": access_token})
        existing.refresh_token_encrypted = encrypt_credentials({"refresh_token": refresh_token})
        existing.org_id = org_id
        existing.org_name = org_name
        existing.username = username
        existing.connection_status = "connected"
        existing.token_expires_at = datetime.utcnow() + timedelta(hours=2)
        existing.updated_at = datetime.utcnow()
    else:
        connection = SalesforceConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            instance_url=instance_url,
            access_token_encrypted=encrypt_credentials({"access_token": access_token}),
            refresh_token_encrypted=encrypt_credentials({"refresh_token": refresh_token}),
            org_id=org_id,
            org_name=org_name,
            username=username,
            connection_status="connected",
            token_expires_at=datetime.utcnow() + timedelta(hours=2),
        )
        db.add(connection)

    db.commit()
    return RedirectResponse(f"{FRONTEND_URL}/settings?salesforce=success")


@router.get("/status", response_model=SalesforceConnectionResponse | None)
async def salesforce_status(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the user's Salesforce connection status."""
    connection = db.query(SalesforceConnection).filter(
        SalesforceConnection.user_id == user.id,
    ).first()

    if not connection:
        return None

    return SalesforceConnectionResponse(
        id=connection.id,
        instance_url=connection.instance_url,
        org_name=connection.org_name,
        username=connection.username,
        connection_status=connection.connection_status,
        created_at=connection.created_at.isoformat() + "Z",
    )


@router.post("/test")
async def salesforce_test(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Test the Salesforce connection by refreshing the token."""
    connection = db.query(SalesforceConnection).filter(
        SalesforceConnection.user_id == user.id,
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="No Salesforce connection found")

    try:
        access_token = await get_valid_access_token(connection, db)
        # Verify the token works
        await get_user_info(connection.instance_url, access_token)
        connection.connection_status = "connected"
        db.commit()
        return {"success": True, "message": "Salesforce connection is active"}
    except Exception as e:
        connection.connection_status = "error"
        db.commit()
        return {"success": False, "error": str(e)}


@router.delete("/disconnect")
async def salesforce_disconnect(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Disconnect (delete) the user's Salesforce connection."""
    connection = db.query(SalesforceConnection).filter(
        SalesforceConnection.user_id == user.id,
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="No Salesforce connection found")

    # Revoke the token
    try:
        creds = decrypt_credentials(connection.access_token_encrypted)
        await revoke_token(creds["access_token"])
    except Exception:
        pass

    db.delete(connection)
    db.commit()
    return {"success": True}


@router.get("/objects")
async def salesforce_objects(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List available Salesforce objects."""
    connection = db.query(SalesforceConnection).filter(
        SalesforceConnection.user_id == user.id,
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="No Salesforce connection found")

    try:
        access_token = await get_valid_access_token(connection, db)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{connection.instance_url}/services/data/v60.0/sobjects/",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch Salesforce objects")
            data = resp.json()
            objects = [
                {"name": obj["name"], "label": obj.get("label", obj["name"])}
                for obj in data.get("sobjects", [])
                if obj.get("queryable", False)
            ]
            return {"objects": objects}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allowlist")
async def salesforce_allowlist(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get current allowed Salesforce objects."""
    connection = db.query(SalesforceConnection).filter(
        SalesforceConnection.user_id == user.id,
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="No Salesforce connection found")

    allowed = connection.allowed_objects
    if isinstance(allowed, str):
        allowed = json.loads(allowed)

    return {"allowed_objects": allowed}


class UpdateAllowlistRequest(BaseModel):
    allowed_objects: Optional[List[str]] = None


@router.put("/allowlist")
async def update_salesforce_allowlist(
    request: UpdateAllowlistRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update allowed Salesforce objects."""
    connection = db.query(SalesforceConnection).filter(
        SalesforceConnection.user_id == user.id,
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="No Salesforce connection found")

    connection.allowed_objects = request.allowed_objects
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "allowed_objects": connection.allowed_objects}
