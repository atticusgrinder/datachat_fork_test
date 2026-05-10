"""Token usage service for weighted tracking and billing cycle management."""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.token_usage import TokenUsage
from app.models.user import User
from app.core.config import PLAN_LIMITS, BILLING_ENABLED


class TokenUsageService:
    """Static methods for token usage tracking and limits."""

    INPUT_WEIGHT = 1
    OUTPUT_WEIGHT = 5

    @staticmethod
    def compute_weighted_tokens(input_tokens: int, output_tokens: int) -> int:
        return (input_tokens * TokenUsageService.INPUT_WEIGHT) + (output_tokens * TokenUsageService.OUTPUT_WEIGHT)

    @staticmethod
    def get_billing_cycle_start(user: User) -> datetime:
        """Get the start of the current billing cycle for a user."""
        now = datetime.utcnow()
        if user.billing_cycle_start:
            day = user.billing_cycle_start.day
            try:
                cycle_start = now.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(now.year, now.month)[1]
                cycle_start = now.replace(day=last_day, hour=0, minute=0, second=0, microsecond=0)
            if cycle_start > now:
                if now.month == 1:
                    cycle_start = cycle_start.replace(year=now.year - 1, month=12)
                else:
                    try:
                        cycle_start = cycle_start.replace(month=now.month - 1)
                    except ValueError:
                        import calendar
                        prev_month = now.month - 1
                        last_day = calendar.monthrange(now.year, prev_month)[1]
                        cycle_start = cycle_start.replace(month=prev_month, day=last_day)
            return cycle_start
        else:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_billing_cycle_end(user: User) -> datetime:
        """Get the end of the current billing cycle."""
        cycle_start = TokenUsageService.get_billing_cycle_start(user)
        if cycle_start.month == 12:
            return cycle_start.replace(year=cycle_start.year + 1, month=1)
        else:
            import calendar
            next_month = cycle_start.month + 1
            try:
                return cycle_start.replace(month=next_month)
            except ValueError:
                last_day = calendar.monthrange(cycle_start.year, next_month)[1]
                return cycle_start.replace(month=next_month, day=last_day)

    @staticmethod
    def get_cycle_usage(db: Session, user: User) -> int:
        """Get total weighted tokens used in the current billing cycle."""
        cycle_start = TokenUsageService.get_billing_cycle_start(user)
        result = db.query(func.sum(TokenUsage.weighted_tokens)).filter(
            TokenUsage.user_id == user.id,
            TokenUsage.created_at >= cycle_start,
        ).scalar()
        return result or 0

    @staticmethod
    def get_effective_limit(user: User) -> int:
        """Get the effective monthly token limit for a user."""
        if user.monthly_token_limit is not None:
            return user.monthly_token_limit
        plan_config = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
        return plan_config["tokens_per_month"]

    @staticmethod
    def check_pre_query(db: Session, user: User) -> dict:
        """Check whether a user is allowed to send a query."""
        # OSS build: billing is disabled, so usage is tracked but not
        # gated. record_usage() below still writes to token_usage so
        # admins can monitor Anthropic spend at /usage.
        if not BILLING_ENABLED:
            return {"allowed": True, "status_code": 200, "warning": None,
                    "usage_percent": 0, "cycle_usage": 0, "cycle_limit": -1}
        cycle_usage = TokenUsageService.get_cycle_usage(db, user)
        cycle_limit = TokenUsageService.get_effective_limit(user)
        usage_percent = (cycle_usage / cycle_limit * 100) if cycle_limit > 0 else 0

        result = {
            "allowed": True,
            "status_code": 200,
            "warning": None,
            "usage_percent": round(usage_percent, 1),
            "cycle_usage": cycle_usage,
            "cycle_limit": cycle_limit,
        }

        if usage_percent >= 100:
            result["allowed"] = False
            result["status_code"] = 429
            result["warning"] = (
                "Monthly limit reached. Upgrade to a paid plan for more."
            )
        elif usage_percent >= 80:
            result["warning"] = f"You've used {usage_percent:.0f}% of your monthly tokens."

        return result

    @staticmethod
    def record_usage(
        db: Session,
        user: User,
        conversation_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        model: str,
    ) -> TokenUsage:
        """Record token usage."""
        weighted = TokenUsageService.compute_weighted_tokens(input_tokens, output_tokens)

        token_usage = TokenUsage(
            user_id=user.id,
            conversation_id=conversation_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            weighted_tokens=weighted,
            cost_usd=cost_usd,
            model=model,
        )
        db.add(token_usage)

        return token_usage
