from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class EvidenceCreate(BaseModel):

    request_id: str | None = None

    document_id: str | None = None
    chunk_id: str | None = None

    evidence_type: str = "document"

    page_number: int | None = Field(
        default=None,
        ge=1,
    )

    location: str | None = None

    quoted_text: str | None = None

    extracted_value: str | None = None

    source_label: str | None = None

    validation_status: str = "UNVERIFIED"
    validation_reason: str | None = None
    match_method: str | None = None
    confidence: float | None = None


class FindingCreate(BaseModel):

    project_id: str

    investigation_id: str | None = None

    workstream: str

    agent_name: str | None = None

    title: str

    issue: str

    why_it_matters: str | None = None

    evidence_conclusion: str | None = None

    recommended_action: str | None = None

    risk_severity: str = "medium"

    confidence: str = "medium"


class ReviewCreate(BaseModel):

    action: str

    reviewer: str = "Human Reviewer"

    comment: str | None = None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str | None = None
    chunk_id: str | None = None
    evidence_type: str = "document"
    page_number: int | None = None
    location: str | None = None
    quoted_text: str | None = None
    extracted_value: str | None = None
    source_label: str | None = None
    validation_status: str = "UNVERIFIED"
    validation_reason: str | None = None
    match_method: str | None = None
    confidence: float | None = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    reviewer: str
    comment: str | None = None
    reviewed_at: datetime | None = None


class FindingResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: str

    project_id: str

    investigation_id: str | None

    workstream: str

    agent_name: str | None

    title: str

    issue: str

    why_it_matters: str | None

    evidence_conclusion: str | None

    recommended_action: str | None

    risk_severity: str

    confidence: str

    status: str

    evidence: list[EvidenceResponse] = []

    reviews: list[ReviewResponse] = []


class FindingListResponse(BaseModel):

    findings: list[FindingResponse]
