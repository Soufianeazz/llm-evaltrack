from typing import Any
from pydantic import BaseModel, Field


class LLMCallPayload(BaseModel):
    input: str = Field(..., min_length=1)
    output: str
    prompt: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float | None = None  # unix epoch; server sets it if absent


class IngestResponse(BaseModel):
    request_id: str
    queued: bool
