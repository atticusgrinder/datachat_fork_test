"""Warehouse-related request/response schemas."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class WarehouseConfigRequest(BaseModel):
    warehouse_type: str
    name: str
    credentials: Dict[str, Any]


class WarehouseResponse(BaseModel):
    id: str
    warehouse_type: str
    name: str
    connection_status: str
    is_read_only: Optional[bool] = None
    is_demo: bool = False
    last_tested_at: Optional[str] = None
    created_at: str


class AllowlistRequest(BaseModel):
    allowed_tables: Optional[List[str]] = None
