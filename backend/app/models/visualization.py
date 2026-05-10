"""Saved visualization model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class SavedVisualization(Base):
    """User-saved chart configurations."""
    __tablename__ = "saved_visualizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    chart_type = Column(String, nullable=False)
    chart_config = Column(Text, nullable=False)  # JSON string
    sql_query = Column(Text, nullable=False)
    warehouse_id = Column(String, ForeignKey("warehouse_connections.id"), nullable=True)
    local_duckdb_id = Column(String, ForeignKey("local_duckdbs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="saved_visualizations")
    warehouse_connection = relationship("WarehouseConnection", backref="saved_visualizations")
    local_duckdb = relationship("LocalDuckDB", backref="saved_visualizations")
