"""Scheduled report models."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Report(Base):
    """A dashboard-style report containing one or more saved visualizations."""
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    warehouse_id = Column(String, ForeignKey("warehouse_connections.id"), nullable=True)
    local_duckdb_id = Column(String, ForeignKey("local_duckdbs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="reports")
    warehouse_connection = relationship("WarehouseConnection", backref="reports")
    local_duckdb = relationship("LocalDuckDB", backref="reports")
    items = relationship(
        "ReportItem",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportItem.position",
    )
    schedule = relationship(
        "ReportSchedule",
        back_populates="report",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ReportItem(Base):
    """A visualization included in a report."""
    __tablename__ = "report_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    saved_visualization_id = Column(String, ForeignKey("saved_visualizations.id"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="items")
    visualization = relationship("SavedVisualization")


class ReportSchedule(Base):
    """Email send schedule for a report."""
    __tablename__ = "report_schedules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    cadence = Column(String, nullable=False)  # "daily" | "weekly" | "monthly"
    day_of_week = Column(Integer, nullable=True)  # 0=Monday .. 6=Sunday (weekly only)
    day_of_month = Column(Integer, nullable=True)  # 1..28 (monthly only)
    time_of_day = Column(String, nullable=False, default="08:00")  # "HH:MM" 24h
    timezone = Column(String, nullable=False, default="UTC")  # IANA tz name
    enabled = Column(Boolean, nullable=False, default=True)
    last_sent_at = Column(DateTime, nullable=True)
    next_send_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    report = relationship("Report", back_populates="schedule")

    __table_args__ = (
        UniqueConstraint("report_id", name="uq_report_schedules_report_id"),
    )
