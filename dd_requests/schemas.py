from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RequestCreate(BaseModel):
    project_id: str
    investigation_id: str | None = None
    finding_id: str | None = None
    request_type: str = "EVIDENCE"
    title: str
    description: str
    requested_items: list[str] = Field(default_factory=list)
    priority: str = "medium"
    requested_from: str | None = None
    due_at: datetime | None = None


class RequestStatusUpdate(BaseModel):
    status: str


class TaskCreateFromRequest(BaseModel):
    assigned_to: str | None = None
