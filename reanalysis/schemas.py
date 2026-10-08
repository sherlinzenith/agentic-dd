from pydantic import BaseModel


class ReanalysisCreate(BaseModel):
    project_id: str
    investigation_id: str | None = None
    finding_id: str | None = None
    request_id: str | None = None
    trigger_type: str = "NEW_EVIDENCE"
    reason: str | None = None
