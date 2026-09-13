from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobPayload(BaseModel):
    duration: int = Field(default=2, ge=0, le=30)
    fail_until_attempt: int = Field(default=0, ge=0, le=10)


class JobCreate(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=255)
    payload: JobPayload
    priority: int = Field(default=0, ge=0, le=2)
    max_attempts: int = Field(default=3, ge=1, le=10)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    idempotency_key: str
    payload: JobPayload
    status: str
    priority: int
    result: dict | None
    error: str | None
    attempt_count: int
    max_attempts: int
    available_at: datetime
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
