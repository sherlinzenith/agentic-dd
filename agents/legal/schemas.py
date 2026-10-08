from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LegalRiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class LegalFinding(BaseModel):
    """
    A structured legal due-diligence finding produced by the Legal Agent.
    """

    title: str = Field(
        min_length=1,
        description="Short title describing the legal issue.",
    )

    issue: str = Field(
        min_length=1,
        description="What was identified in the legal documents.",
    )

    why_it_matters: str = Field(
        min_length=1,
        description="Business or transaction impact of the issue.",
    )

    risk_level: LegalRiskLevel = "medium"

    evidence_document_id: str | None = None

    evidence_document_name: str | None = None

    evidence_page: int | None = None

    evidence_location: str | None = None

    evidence_quote: str | None = None

    recommended_action: str | None = None

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class LegalInvestigationResult(BaseModel):
    """
    Final structured result returned by the Legal Agent.
    """

    findings: list[LegalFinding] = Field(
        default_factory=list
    )

    documents_reviewed: list[str] = Field(
        default_factory=list
    )

    missing_documents: list[str] = Field(
        default_factory=list
    )

    investigation_summary: str = ""

    investigation_complete: bool = False