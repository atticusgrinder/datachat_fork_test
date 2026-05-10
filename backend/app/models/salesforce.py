"""Salesforce connection model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class SalesforceConnection(Base):
    """Salesforce org OAuth connection."""
    __tablename__ = "salesforce_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    instance_url = Column(String, nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    org_id = Column(String, nullable=True)
    org_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    connection_status = Column(String, default="connected")
    allowed_objects = Column(JSON, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="salesforce_connections")
