from typing import Any
from pydantic import BaseModel, Field


class LLMCallPayload(BaseModel):
    input: str = Field(..., min_length=1)
    output: str
    prompt: str = Field(..., min_length=0)
    model: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float | None = None  # unix epoch; server sets it if absent


class IngestResponse(BaseModel):
    request_id: str
    queued: bool


class BudgetAlertPayload(BaseModel):
    daily_budget_usd: float = Field(..., gt=0)
    webhook_url: str | None = None
    email: str | None = None


class BudgetAlertResponse(BaseModel):
    daily_budget_usd: float
    webhook_url: str | None
    email: str | None
    triggered_today: bool
    spent_today_usd: float
    percent_used: float
