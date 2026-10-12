from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ReportMetadata(BaseModel):
    project_id: str
    project_name: str
    target_company: str
    deal_type: Optional[str] = "N/A"
    industry: Optional[str] = "N/A"
    diligence_period: Optional[str] = "N/A"
    description: Optional[str] = None
    status: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ScopeWorkstreamDetail(BaseModel):
    workstream: str
    is_enabled: bool
    status: str
    custom_questions: List[str] = Field(default_factory=list)
    review_areas: List[str] = Field(default_factory=list)


class ReportScopeSummary(BaseModel):
    enabled_workstreams: List[str] = Field(default_factory=list)
    workstream_details: List[ScopeWorkstreamDetail] = Field(default_factory=list)


class ReportExecutiveSummary(BaseModel):
    total_findings: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    financial_count: int = 0
    legal_count: int = 0
    cross_domain_count: int = 0
    approved_count: int = 0
    pending_review_count: int = 0
    rejected_count: int = 0
    more_evidence_required_count: int = 0
    unverified_evidence_count: int = 0
    executive_overview: str = ""


class ReportEvidenceCitation(BaseModel):
    id: str
    document_id: Optional[str] = None
    document_name: str = "Unknown Document"
    page_number: Optional[int] = None
    chunk_id: Optional[str] = None
    evidence_type: str = "document"
    quoted_text: Optional[str] = None
    extracted_value: Optional[str] = None
    validation_status: str = "UNVERIFIED"
    validation_reason: Optional[str] = None
    match_method: Optional[str] = None
    confidence: Optional[float] = None


class ReportReviewHistory(BaseModel):
    id: str
    action: str
    reviewer_name: Optional[str] = None
    comments: Optional[str] = None
    requested_clarification: Optional[str] = None
    reviewed_at: datetime


class ReportFindingItem(BaseModel):
    id: str
    workstream: str
    agent_name: Optional[str] = None
    title: str
    issue: str
    why_it_matters: Optional[str] = None
    evidence_conclusion: Optional[str] = None
    recommended_action: Optional[str] = None
    risk_severity: str = "medium"
    status: str = "REVIEW_REQUIRED"
    confidence: str = "medium"
    created_at: datetime
    evidence: List[ReportEvidenceCitation] = Field(default_factory=list)
    reviews: List[ReportReviewHistory] = Field(default_factory=list)


class ReportOutstandingItem(BaseModel):
    item_type: str  # "request" or "task"
    id: str
    title: str
    description: str
    status: str
    priority: str = "medium"
    requested_from_or_assigned_to: Optional[str] = None
    due_at: Optional[datetime] = None
    created_at: datetime


class DueDiligenceReport(BaseModel):
    metadata: ReportMetadata
    scope: ReportScopeSummary
    executive_summary: ReportExecutiveSummary
    financial_findings: List[ReportFindingItem] = Field(default_factory=list)
    legal_findings: List[ReportFindingItem] = Field(default_factory=list)
    cross_domain_findings: List[ReportFindingItem] = Field(default_factory=list)
    all_findings: List[ReportFindingItem] = Field(default_factory=list)
    outstanding_items: List[ReportOutstandingItem] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
