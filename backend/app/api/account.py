"""Account management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_auth
from app.models.user import User
from app.models.warehouse import WarehouseConnection
from app.models.token_usage import TokenUsage
from app.models.feedback import MessageFeedback
from app.models.demo import DataMaturityAssessment
from app.services.warehouse_service import evict_executor
from app.services import local_duckdb_service

router = APIRouter(tags=["account"])


@router.delete("/api/account")
async def delete_account(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete the authenticated user's account and all associated data."""
    warehouses = db.query(WarehouseConnection).filter(
        WarehouseConnection.user_id == user.id
    ).all()
    for warehouse in warehouses:
        evict_executor(warehouse.id)

    # Drop the user's persistent LocalDuckDB file + rows before user delete cascades.
    local_duckdb_service.delete_user_db(db, user.id)

    db.query(DataMaturityAssessment).filter(DataMaturityAssessment.user_id == user.id).delete()
    db.query(MessageFeedback).filter(MessageFeedback.user_id == user.id).delete()
    db.query(TokenUsage).filter(TokenUsage.user_id == user.id).delete()

    db.delete(user)
    db.commit()

    return {"success": True}
