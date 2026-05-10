"""Integration models for third-party repo connections (dbt, etc.)."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Integration(Base):
    """Third-party integration connection (e.g., dbt project repo)."""
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    integration_type = Column(String, nullable=False)  # 'dbt'
    name = Column(String, nullable=False)
    config_encrypted = Column(Text, nullable=False)  # Encrypted JSON: repo_url, branch, auth_token
    connection_status = Column(String, default="pending")  # pending, connected, error
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="integrations")
    syncs = relationship("IntegrationSync", back_populates="integration", cascade="all, delete-orphan")
    context_files = relationship("ContextFile", back_populates="integration", cascade="all, delete-orphan")


class IntegrationSync(Base):
    """Tracks sync operations for an integration."""
    __tablename__ = "integration_syncs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String, ForeignKey("integrations.id"), nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_count = Column(Integer, default=0)

    integration = relationship("Integration", back_populates="syncs")
