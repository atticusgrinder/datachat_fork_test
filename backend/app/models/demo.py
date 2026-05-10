"""Demo-related models: maturity assessment, consulting inquiry, demo usage."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class DataMaturityAssessment(Base):
    """Data maturity questionnaire responses."""
    __tablename__ = "data_maturity_assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    company_size = Column(String, nullable=False)
    has_warehouse = Column(String, nullable=False)
    dbt_status = Column(String, nullable=False)
    data_sources = Column(Text, nullable=True)
    routing_result = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class ConsultingInquiry(Base):
    """Consulting inquiry submissions."""
    __tablename__ = "consulting_inquiries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    maturity_assessment_id = Column(String, ForeignKey("data_maturity_assessments.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    maturity_assessment = relationship("DataMaturityAssessment")


class DemoUsage(Base):
    """Track demo mode usage for rate limiting."""
    __tablename__ = "demo_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    tokens_used = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("DemoMessage", back_populates="session", order_by="DemoMessage.created_at")


class DemoMessage(Base):
    """Individual demo chat messages for visibility."""
    __tablename__ = "demo_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("demo_usage.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    tool_call_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("DemoUsage", back_populates="messages")
