"""Visualization-related request/response schemas."""

from typing import Optional
from pydantic import BaseModel


class VisualizationConfig(BaseModel):
    chart_type: str
    title: str
    x_column: str
    y_column: str
    reasoning: Optional[str] = None


class SaveVisualizationRequest(BaseModel):
    name: str
    description: Optional[str] = None
    chart_type: str
    chart_config: str  # JSON string
    sql_query: str
    warehouse_id: Optional[str] = None
    local_duckdb_id: Optional[str] = None


class UpdateVisualizationRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class VisualizationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    chart_type: str
    chart_config: str
    sql_query: str
    warehouse_id: Optional[str] = None
    local_duckdb_id: Optional[str] = None
    created_at: str
    updated_at: str


class VisualizationRefreshResponse(BaseModel):
    id: str
    chart_data: list[dict]
