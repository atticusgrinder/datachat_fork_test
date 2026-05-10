"""Conversation-related request/response schemas."""

from typing import Any, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    salesforce_id: Optional[str] = None
    file_session_id: Optional[str] = None
    local_duckdb_id: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    conversation_id: str
    message_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    weighted_tokens: Optional[int] = None
    duration_ms: Optional[int] = None
    usage_warning: Optional[str] = None
    usage_percent: Optional[float] = None
    visualization: Optional[dict] = None
    chart_data: Optional[list[dict[str, Any]]] = None


class CreateConversationRequest(BaseModel):
    warehouse_id: Optional[str] = None
    salesforce_id: Optional[str] = None
    title: Optional[str] = "New Chat"


class ConversationResponse(BaseModel):
    id: str
    title: str
    warehouse_id: Optional[str] = None
    warehouse_name: Optional[str] = None
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    feedback: Optional[str] = None
    visualization: Optional[dict] = None
    chart_data: Optional[list[dict[str, Any]]] = None


class RenameConversationRequest(BaseModel):
    title: str


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str
