"""Demo and assessment request/response schemas."""

from typing import Optional
from pydantic import BaseModel


class MaturityAssessmentRequest(BaseModel):
    company_size: str
    has_warehouse: str
    dbt_status: str
    data_sources: Optional[str] = None


class MaturityAssessmentResponse(BaseModel):
    id: str
    routing_result: str


class ConsultingInquiryRequest(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    message: Optional[str] = None
    maturity_assessment_id: Optional[str] = None
