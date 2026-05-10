"""Admin endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.config import PLAN_LIMITS
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.token_usage import TokenUsage
from app.models.demo import ConsultingInquiry

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def admin_list_users(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.created_at.desc()).all()

    result = []
    for u in users:
        total_tokens = db.query(
            func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens)
        ).filter(TokenUsage.user_id == u.id).scalar() or 0

        result.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "plan": u.plan,
            "is_admin": u.is_admin,
            "total_tokens": total_tokens,
            "created_at": u.created_at.isoformat() + "Z",
        })

    return result


@router.get("/usage")
async def admin_get_usage(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get platform-wide usage stats (admin only)."""
    total_users = db.query(User).count()

    totals = db.query(
        func.sum(TokenUsage.input_tokens).label("input"),
        func.sum(TokenUsage.output_tokens).label("output"),
        func.sum(TokenUsage.cost_usd).label("cost"),
    ).first()

    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_totals = db.query(
        func.sum(TokenUsage.input_tokens).label("input"),
        func.sum(TokenUsage.output_tokens).label("output"),
        func.sum(TokenUsage.cost_usd).label("cost"),
    ).filter(TokenUsage.created_at >= current_month_start).first()

    plan_counts = db.query(
        User.plan,
        func.count(User.id),
    ).group_by(User.plan).all()

    return {
        "total_users": total_users,
        "total_input_tokens": totals.input or 0,
        "total_output_tokens": totals.output or 0,
        "total_cost_usd": round(totals.cost or 0, 2),
        "monthly_input_tokens": monthly_totals.input or 0,
        "monthly_output_tokens": monthly_totals.output or 0,
        "monthly_cost_usd": round(monthly_totals.cost or 0, 2),
        "users_by_plan": {plan: count for plan, count in plan_counts},
    }


@router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: str,
    plan: Optional[str] = None,
    is_admin: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user (admin only)."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if plan is not None:
        if plan not in PLAN_LIMITS:
            raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")
        target_user.plan = plan

    if is_admin is not None:
        target_user.is_admin = is_admin

    db.commit()

    return {"success": True}


@router.get("/consulting-inquiries")
async def admin_list_consulting_inquiries(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all consulting inquiries (admin only)."""
    inquiries = db.query(ConsultingInquiry).order_by(ConsultingInquiry.created_at.desc()).all()

    return [
        {
            "id": i.id,
            "name": i.name,
            "email": i.email,
            "company": i.company,
            "message": i.message,
            "created_at": i.created_at.isoformat() + "Z",
        }
        for i in inquiries
    ]


