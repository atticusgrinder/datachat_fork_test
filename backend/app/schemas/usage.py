"""Usage-related response schemas."""

from pydantic import BaseModel


class UsageSummaryResponse(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    total_conversations: int
    total_messages: int
    current_month_tokens: int
    current_month_weighted_tokens: int = 0
    token_limit: int
    plan: str
    plan_display_name: str = ""
    usage_percent: float = 0.0


class DailyUsageResponse(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class QueryHistoryItem(BaseModel):
    id: str
    conversation_title: str
    input_tokens: int
    output_tokens: int
    weighted_tokens: int = 0
    cost_usd: float
    model: str = ""
    created_at: str
