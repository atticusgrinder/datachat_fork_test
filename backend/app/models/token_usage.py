"""Token usage tracking model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class TokenUsage(Base):
    """Token usage tracking for billing."""
    __tablename__ = "token_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    weighted_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    model = Column(String, default="claude-sonnet-4-6")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="token_usage")
