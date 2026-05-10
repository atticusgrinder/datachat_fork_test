"""Per-user context file model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class ContextFile(Base):
    """User context files that persist across conversations.

    source="user" for user-created files (e.g. context.md).
    source="integration" for files synced from integrations (e.g. dbt-project.yml).
    """
    __tablename__ = "context_files"
    __table_args__ = (
        UniqueConstraint("user_id", "filename", name="uq_context_files_user_filename"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="")
    source = Column(String, nullable=False, default="user")  # "user" or "integration"
    integration_id = Column(String, ForeignKey("integrations.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="context_files")
    integration = relationship("Integration", back_populates="context_files")
