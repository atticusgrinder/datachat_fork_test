"""Schemas for the per-user persistent local DuckDB."""

from typing import Optional
from pydantic import BaseModel


class LocalDuckDBTableInfo(BaseModel):
    id: str
    table_name: str
    original_filename: str
    source_type: str
    row_count: int
    columns: list[dict]
    is_demo: bool = False
    created_at: str


class LocalDuckDBStatus(BaseModel):
    """Returned by GET /api/local-duckdb. `null` exists field means the user
    hasn't uploaded anything yet."""
    exists: bool
    id: Optional[str] = None
    tables: list[LocalDuckDBTableInfo] = []


class LocalDuckDBUploadResponse(BaseModel):
    local_duckdb_id: str
    table: LocalDuckDBTableInfo
