from __future__ import annotations
from pydantic import BaseModel, Field


class TaskStatusUpdate(BaseModel):
    status: str


class TaskCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1)
    description: str
    task_type: str = "INVESTIGATION_CHECK"
    priority: str = "medium"
    assigned_to: str | None = None
    assigned_agent: str | None = None
    investigation_id: str | None = None
    finding_id: str | None = None
    request_id: str | None = None
