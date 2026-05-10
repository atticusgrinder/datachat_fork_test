"""Report request/response schemas."""

from typing import Optional
from pydantic import BaseModel


class CreateReportRequest(BaseModel):
    name: str
    description: Optional[str] = None
    warehouse_id: Optional[str] = None
    local_duckdb_id: Optional[str] = None


class UpdateReportRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AddReportItemRequest(BaseModel):
    saved_visualization_id: str


class SetScheduleRequest(BaseModel):
    cadence: str  # "daily" | "weekly" | "monthly"
    time_of_day: str = "08:00"
    timezone: str = "UTC"
    day_of_week: Optional[int] = None  # required for weekly: 0=Mon..6=Sun
    day_of_month: Optional[int] = None  # required for monthly: 1..28
    enabled: bool = True


class ScheduleResponse(BaseModel):
    cadence: str
    time_of_day: str
    timezone: str
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    enabled: bool
    last_sent_at: Optional[str] = None
    next_send_at: Optional[str] = None


class ReportItemResponse(BaseModel):
    id: str
    saved_visualization_id: str
    position: int


class ReportResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    warehouse_id: Optional[str] = None
    local_duckdb_id: Optional[str] = None
    created_at: str
    updated_at: str
    items: list[ReportItemResponse]
    schedule: Optional[ScheduleResponse] = None
