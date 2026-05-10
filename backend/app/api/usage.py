"""Token usage endpoints."""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.config import PLAN_LIMITS
from app.core.dependencies import require_auth
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage
from app.models.token_usage import TokenUsage
from app.schemas.usage import UsageSummaryResponse, DailyUsageResponse, QueryHistoryItem
from app.services.token_usage_service import TokenUsageService

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get usage summary for the user."""
    totals = db.query(
        func.sum(TokenUsage.input_tokens).label("input"),
        func.sum(TokenUsage.output_tokens).label("output"),
        func.sum(TokenUsage.cost_usd).label("cost"),
    ).filter(TokenUsage.user_id == user.id).first()

    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_tokens = db.query(
        func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens)
    ).filter(
        TokenUsage.user_id == user.id,
        TokenUsage.created_at >= current_month_start,
    ).scalar() or 0

    cycle_weighted = TokenUsageService.get_cycle_usage(db, user)
    cycle_limit = TokenUsageService.get_effective_limit(user)
    usage_pct = round((cycle_weighted / cycle_limit * 100) if cycle_limit > 0 else 0, 1)

    total_conversations = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).count()

    total_messages = db.query(ConversationMessage).join(Conversation).filter(
        Conversation.user_id == user.id
    ).count()

    plan_config = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])

    return UsageSummaryResponse(
        total_input_tokens=totals.input or 0,
        total_output_tokens=totals.output or 0,
        total_cost_usd=round(totals.cost or 0, 4),
        total_conversations=total_conversations,
        total_messages=total_messages,
        current_month_tokens=current_month_tokens,
        current_month_weighted_tokens=cycle_weighted,
        token_limit=cycle_limit,
        plan=user.plan,
        plan_display_name=plan_config.get("display_name", user.plan.capitalize()),
        usage_percent=usage_pct,
    )


@router.get("/daily", response_model=List[DailyUsageResponse])
async def get_daily_usage(
    days: int = Query(30, ge=1, le=90),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get daily usage breakdown."""
    start_date = datetime.utcnow() - timedelta(days=days)

    daily_usage = db.query(
        func.date(TokenUsage.created_at).label("date"),
        func.sum(TokenUsage.input_tokens).label("input"),
        func.sum(TokenUsage.output_tokens).label("output"),
        func.sum(TokenUsage.cost_usd).label("cost"),
    ).filter(
        TokenUsage.user_id == user.id,
        TokenUsage.created_at >= start_date,
    ).group_by(
        func.date(TokenUsage.created_at)
    ).order_by(
        func.date(TokenUsage.created_at).asc()
    ).all()

    return [
        DailyUsageResponse(
            date=str(row.date),
            input_tokens=row.input or 0,
            output_tokens=row.output or 0,
            cost_usd=round(row.cost or 0, 4),
        )
        for row in daily_usage
    ]


@router.get("/history", response_model=List[QueryHistoryItem])
async def get_usage_history(
    limit: int = Query(default=50, le=200),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get individual query history with token usage."""
    usage_records = db.query(
        TokenUsage,
        Conversation.title,
    ).outerjoin(
        Conversation, TokenUsage.conversation_id == Conversation.id
    ).filter(
        TokenUsage.user_id == user.id
    ).order_by(
        TokenUsage.created_at.desc()
    ).limit(limit).all()

    return [
        QueryHistoryItem(
            id=record.TokenUsage.id,
            conversation_title=record.title or "Unknown",
            input_tokens=record.TokenUsage.input_tokens,
            output_tokens=record.TokenUsage.output_tokens,
            weighted_tokens=record.TokenUsage.weighted_tokens or 0,
            cost_usd=round(record.TokenUsage.cost_usd, 6),
            model=record.TokenUsage.model or "",
            created_at=record.TokenUsage.created_at.isoformat() + "Z",
        )
        for record in usage_records
    ]


@router.get("/current")
async def get_current_usage(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get current billing cycle usage details."""
    plan_config = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    cycle_start = TokenUsageService.get_billing_cycle_start(user)
    cycle_end = TokenUsageService.get_billing_cycle_end(user)
    cycle_usage = TokenUsageService.get_cycle_usage(db, user)
    cycle_limit = TokenUsageService.get_effective_limit(user)
    usage_pct = round((cycle_usage / cycle_limit * 100) if cycle_limit > 0 else 0, 1)

    return {
        "plan": user.plan,
        "plan_display_name": plan_config.get("display_name", user.plan.capitalize()),
        "billing_cycle_start": cycle_start.isoformat() + "Z",
        "billing_cycle_end": cycle_end.isoformat() + "Z",
        "weighted_tokens_used": cycle_usage,
        "weighted_token_limit": cycle_limit,
        "usage_percent": usage_pct,
    }
