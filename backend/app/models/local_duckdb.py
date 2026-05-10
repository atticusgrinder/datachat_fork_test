"""Per-user persistent local DuckDB instance and its loaded tables."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class LocalDuckDB(Base):
    """One persistent DuckDB file per user, holding all uploaded local data files
    (csv/excel/parquet/json) as tables in a single connection so cross-file joins
    work natively."""
    __tablename__ = "local_duckdbs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="local_duckdb")
    tables = relationship(
        "LocalDuckDBTable",
        back_populates="local_duckdb",
        cascade="all, delete-orphan",
    )


class LocalDuckDBTable(Base):
    """A single table inside a user's LocalDuckDB, sourced from one upload."""
    __tablename__ = "local_duckdb_tables"
    __table_args__ = (
        UniqueConstraint("local_duckdb_id", "table_name", name="uq_local_duckdb_table_name"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    local_duckdb_id = Column(String, ForeignKey("local_duckdbs.id"), nullable=False)
    table_name = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # "excel_csv" or "local_upload"
    row_count = Column(Integer, nullable=False, default=0)
    columns = Column(JSON, nullable=False, default=list)  # [{name, type}, ...]
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    local_duckdb = relationship("LocalDuckDB", back_populates="tables")
