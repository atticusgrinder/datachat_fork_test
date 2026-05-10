"""Billing-related request/response schemas."""

from pydantic import BaseModel


class ChangePlanRequest(BaseModel):
    plan: str


class CheckoutRequest(BaseModel):
    plan: str
