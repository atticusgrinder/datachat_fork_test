"""Warehouse connection model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class WarehouseConnection(Base):
    """Multi-warehouse connection storage."""
    __tablename__ = "warehouse_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    warehouse_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    credentials_encrypted = Column(Text, nullable=False)
    connection_status = Column(String, default="disconnected")
    is_read_only = Column(Boolean, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    allowed_tables = Column(JSON, nullable=True)
    last_tested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="warehouse_connections")
    conversations = relationship("Conversation", back_populates="warehouse_connection")
